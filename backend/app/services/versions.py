"""Explicit immutable section revisions. Callers own transactions and write locks."""
from copy import deepcopy
import re
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from ..retrieval.service import identity
from .drafting import DraftRequest, DraftingService
from .readiness import ReadinessService
from .locks import RevisionConflict, require_working


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    role: Literal['CA'] = 'CA'
    expected_draft_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=0)
    expected_input_fingerprint: str = Field(min_length=1)


class EditRequest(VersionRequest):
    # Replace narrative claims by ID; source markers, gaps and computed cells are
    # server-owned. New typed facts/numeric inputs and chat belong to B24.
    replacements: dict[str, str] = Field(min_length=1, max_length=100)


class RedraftRequest(VersionRequest):
    model_id: str | None = None
    computation_id: str | None = None
    confirm_unsecured: bool = False
    ca_position: str | None = Field(default=None, min_length=1, max_length=10000, pattern=r'.*\S.*')


class VersionService:
    def __init__(self, repository, storage_root, template_storage_root=None, provider=None):
        self.repo = repository
        self.drafting = DraftingService(repository, storage_root, template_storage_root, provider)

    def sections(self, case_id):
        return ReadinessService(self.repo).refresh(case_id)[1]

    def history(self, case_id, section_id):
        state = next((v for v in self.sections(case_id) if v.section_id == section_id), None)
        if not state:
            raise ValueError('Unknown configured section')
        return dict(section=state, versions=sorted(
            [d for d in self.repo.list_for_case(s.DraftVersion, case_id) if d.section_id == section_id],
            key=lambda d: (d.created_at, d.id)), confirmations=sorted(
            [c for c in self.repo.list_for_case(s.SectionConfirmation, case_id) if c.section_id == section_id],
            key=lambda c: (c.created_at, c.id)))

    def prepare(self, case_id, section_id, request):
        require_working(self.repo, case_id, section_id)
        states = self.sections(case_id)
        state = next((v for v in states if v.section_id == section_id), None)
        if not state or not state.applicable:
            raise ValueError('Unknown or not applicable section')
        if (state.current_draft_id != request.expected_draft_id or
                state.editor_revision != request.expected_revision or
                state.input_fingerprint != request.expected_input_fingerprint):
            raise RevisionConflict('Section revision or inputs changed; reload before applying this action')
        draft = self.repo.get(s.DraftVersion, state.current_draft_id)
        if draft.case_id != case_id or draft.section_id != section_id:
            raise ValueError('Draft does not belong to this section')
        return state, draft

    def redraft(self, case_id, section_id, request):
        _, parent = self.prepare(case_id, section_id, request)
        return self.drafting.generate(case_id, section_id, DraftRequest(
            actor=request.actor, template_version_id=parent.template_version_id,
            computation_id=request.computation_id, confirm_unsecured=request.confirm_unsecured,
            ca_position=request.ca_position, model_id=request.model_id), parent_id=parent.id)

    def save(self, case_id, section_id, request):
        state, parent = self.prepare(case_id, section_id, request)
        if not parent.claim_spans or parent.claim_spans[0].get('kind') != 'draft_metadata':
            raise ValueError('Structured draft required; redraft legacy free text before editing')
        spans = deepcopy(parent.claim_spans)
        by_id = {c['id']: c for c in spans[1:]}
        if not set(request.replacements) <= set(by_id):
            raise ValueError('Unknown claim ID')
        changed = False
        timestamp = s.utcnow()
        for key, replacement in request.replacements.items():
            claim = by_id[key]
            if not replacement.strip() or len(replacement) > 20000:
                raise ValueError('Edited wording must be nonblank and at most 20000 characters')
            if (claim.get('computed_value_id') or claim.get('computed_value_ids') or
                    claim['kind'] in {'computed_summary', 'case_input', 'ca_position', 'ca_input'} or
                    claim.get('internal_rating') or claim.get('requires_unsecured_confirmation')):
                raise ValueError('Protected supplied/computed claim; use its dedicated input or redraft operation')
            if re.findall(r'\d+(?:[.,]\d+)*', replacement) != re.findall(r'\d+(?:[.,]\d+)*', claim['text']):
                raise ValueError('Numeric edits require validated inputs and Python recomputation')
            if replacement != claim['text']:
                changed = True
                claim['ca_edit'] = dict(actor=request.actor, role='CA', recorded_at=timestamp.isoformat(),
                    base_draft_id=parent.id, original=claim['text'], replacement=replacement,
                    basis='CA-edited wording; source links retained for review, not independent verification')
        if not changed:
            raise ValueError('No wording changes supplied')
        # Replace only the claim wording inside its exact prior span. Preserve all
        # source markers, public dates, labels, gap text and protected cells.
        cursor, text = 0, ''
        for original, claim in zip(parent.claim_spans[1:], spans[1:]):
            start, end = original.get('start'), original.get('end')
            if not isinstance(start, int) or not isinstance(end, int) or not cursor <= start < end <= len(parent.text):
                raise ValueError('Invalid claim span; explicit redraft required')
            segment = parent.text[start:end]
            if original['text'] not in segment:
                raise ValueError('Claim text does not match its span')
            text += parent.text[cursor:start]
            claim['start'] = len(text)
            if original['id'] in request.replacements and request.replacements[original['id']] != original['text']:
                replacement = request.replacements[original['id']]
                segment = segment.replace(original['text'], replacement, 1)
                claim['text'] = replacement
                claim['id'] = 'ca-edit-' + identity(parent.id, original['id'], replacement)
                claim['origin_claim_ids'] = [claim['id']]
                segment += f"CA-edited wording: {request.actor}; {timestamp.isoformat()}. Source links retained for review; not independently verified.\n"
            text += segment
            claim['end'] = len(text)
            cursor = end
        text += parent.text[cursor:]
        spans[0]['edit_format'] = 'b13-claim-edits-v1'
        draft = self.repo.save(s.DraftVersion.model_validate(parent.model_dump() | dict(
            id=str(uuid4()), created_at=timestamp, parent_id=parent.id, text=text,
            claim_spans=spans, ca_edits=True, author=request.actor)))
        for i, claim in enumerate(spans[1:]):
            for ref in claim.get('evidence_ids', []):
                self.repo.save(s.Citation(case_id=case_id, draft_id=draft.id, evidence_id=ref,
                    claim_or_cell=f'claim:{i}:{claim["id"]}'))
        self.repo.save(state.model_copy(update=dict(current_draft_id=draft.id, confirmed_draft_id=None,
            readiness='Stale' if state.readiness == 'Stale' else 'Drafted', editor_revision=state.editor_revision + 1)))
        self.sections(case_id)
        return self.drafting.get(case_id, draft.id)

    def confirm(self, case_id, section_id, request):
        state, draft = self.prepare(case_id, section_id, request)
        if state.readiness == 'Stale' or draft.input_fingerprint != state.input_fingerprint:
            raise RevisionConflict('Stale content cannot be confirmed; explicitly redraft against current inputs')
        # Integrity is checked at confirmation too, not just when drafting.
        for ref in {e for c in draft.claim_spans[1:] for e in c.get('evidence_ids', [])}:
            if not self.drafting.evidence.resolve(case_id, ref)['current']:
                raise RevisionConflict('Superseded source; redraft before confirmation')
        self.repo.save(s.SectionConfirmation(case_id=case_id, section_id=section_id, draft_id=draft.id,
            input_fingerprint=state.input_fingerprint, editor_revision=state.editor_revision, actor=request.actor))
        return self.repo.save(state.model_copy(update=dict(confirmed_draft_id=draft.id,
            readiness='CA confirmed', editor_revision=state.editor_revision + 1)))
