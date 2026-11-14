"""Typed, reviewable section proposals. Callers own the serialized transaction.

Mock responses select a saved operation; they never author unsupported wording.
Python constructs the candidate from immutable claims and explicit CA inputs.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import re
from typing import Literal
from uuid import uuid4

from sqlalchemy import select

from .locks import require_working
from .. import models
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import schemas as s
from ..analytics.engine import Fact, calculate, normalize, number, VERSION, display
from ..llm import client as llm
from ..retrieval.service import identity
from ..team_config import TeamConfig
from .drafting import source_label
from .versions import VersionService, VersionRequest, RevisionConflict
from .readiness import ReadinessService

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/section_chat.json'


class Operand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: str = Field(min_length=1, max_length=100)
    unit: Literal['currency', 'currency_thousand', 'currency_million', 'currency/unit',
                  'cents/unit', 'units', 'percent', 'fraction', 'times', 'years', 'sqm']
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    item: str | None = Field(default=None, max_length=200)
    maturity: date | None = None


class NumericInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    metric_id: str = Field(min_length=1, max_length=100)
    period: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')
    scope: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    basis: str = Field(min_length=1, max_length=100, pattern=r'.*\S.*')
    synthetic: bool = True
    operands: dict[str, list[Operand]] = Field(default_factory=dict, max_length=20)


class ChatRequest(VersionRequest):
    message: str = Field(min_length=1, max_length=10000, pattern=r'.*\S.*')
    mode: Literal['fact', 'emphasize', 'numeric'] = 'fact'
    synthetic: bool = True
    claim_id: str | None = None
    numeric: NumericInput | None = None

    @model_validator(mode='after')
    def selection(self):
        if (self.mode == 'numeric') != (self.numeric is not None):
            raise ValueError('Numeric mode requires explicit operand inputs')
        if (self.mode == 'emphasize') != (self.claim_id is not None):
            raise ValueError('Emphasis requires an existing claim')
        if self.numeric and any(len(v) > 200 for v in self.numeric.operands.values()):
            raise ValueError('Too many operands')
        return self


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    role: Literal['CA'] = 'CA'
    action: Literal['accept', 'reject']
    accept_numeric_input: bool = False


def proposal_for_message(repo, message_id):
    ref = repo.session.scalar(select(models.SectionProposal.id).where(models.SectionProposal.message_id == message_id))
    return repo.get(s.SectionProposal, ref)


def accepted_inputs(repo, case_id, section_id=None):
    query = select(models.SectionProposal.message_id).where(models.SectionProposal.case_id == case_id,
        models.SectionProposal.status == 'accepted')
    if section_id is not None:
        query = query.where(models.SectionProposal.section_id == section_id)
    messages = set(repo.session.scalars(query))
    records = [v for v in repo.list_for_case(s.CAInput, case_id) if v.message_id in messages]
    superseded = {v.supersedes_id for v in records}
    return sorted([v for v in records if v.id not in superseded], key=lambda v: (v.created_at, v.id))


def numeric_result(config, supplied, evidence_id):
    metric = next((m for m in config.analytics.sets['reit'].metrics if m.id == supplied.metric_id), None)
    if not metric:
        raise ValueError('Unknown metric in pinned configuration')
    inputs = {}
    for key, rows in supplied.operands.items():
        inputs[key] = []
        for row in rows:
            value, unit = normalize(number(row.value), row.unit)
            inputs[key].append(Fact(value, unit, row.currency, supplied.period, supplied.scope,
                supplied.basis, [evidence_id], synthetic=supplied.synthetic, item=row.item, maturity=row.maturity))
    result = calculate(metric, inputs, supplied.period, supplied.scope)
    results = [result]
    for i, threshold in enumerate(result['thresholds']):
        if threshold['headroom'] is not None:
            results.append(dict(result, metric=f'{metric.id}/headroom/{i}', name=metric.name+' headroom',
                value=threshold['headroom'], unit=threshold['headroom_unit'], display=display(number(threshold['headroom'])),
                thresholds=[], currency=None, formula=dict(op='threshold_headroom', rule=threshold)))
    return results


def numeric_claims(repo, source, results, run_id, persist=False):
    claims = []
    for result in results:
        value = s.ComputedValue(id=identity(run_id, result['metric']), case_id=source.case_id, spread_id=run_id,
            metric=result['metric'], formula_version=VERSION, operands=result['operands'],
            operand_evidence_ids=result['operand_evidence_ids'], unit=result['unit'], currency=result['currency'],
            period=result['period'], scope=result['scope'], value=result['value'],
            validated=result['value'] is not None and not result['gaps'], synthetic=result['synthetic'], gaps=result['gaps'])
        # Stable timestamp lets acceptance verify the exact preview payload.
        value.created_at = source.created_at
        if persist:
            repo.save(value)
            for ref in {r for ids in value.operand_evidence_ids.values() for r in ids}:
                repo.save(s.Citation(case_id=source.case_id, evidence_id=ref, computed_value_id=value.id, claim_or_cell=value.metric))
        if not value.validated:
            continue
        claims.append(dict(id=value.id, kind='computed', computed_value_id=value.id,
            evidence_ids=sorted({r for ids in value.operand_evidence_ids.values() for r in ids}),
            text=f"{result['name']}: {result['display']} {value.unit}" + (f' {value.currency}' if value.currency else '') +
                 f'; period {value.period}; scope {value.scope}. Python computation from CA input; not independently verified.',
            value=value.model_dump(mode='json'), definition=result['formula'], thresholds=result['thresholds'], ca_input_id=source.id))
    return claims


def overlay(claims, additions, numeric=None):
    claims = deepcopy(claims)
    if numeric:
        # Only replace this metric in the same scope/period; never modify exposure,
        # conduct, projection cells or original immutable computation snapshots.
        claims = [c for c in claims if not (
            c.get('numeric_key') == [numeric.metric_id, numeric.period, numeric.scope] or
            c.get('value', {}).get('metric', '').split('/headroom/')[0] == numeric.metric_id
            and c['value']['period'] == numeric.period and c['value']['scope'] == numeric.scope)]
    ids = {c['id'] for c in additions}
    return [c for c in claims if c['id'] not in ids] + deepcopy(additions)


def retained_inputs(service, case_id, section_id, claims, sources, gaps):
    """Explicit redrafts retain accepted typed sources and latest Python results."""
    for source in accepted_inputs(service.repo, case_id, section_id):
        proposal = proposal_for_message(service.repo, source.message_id)
        additions = proposal.payload['additions']
        numeric = NumericInput.model_validate(source.numeric_input) if source.numeric_input else None
        claims = overlay(claims, additions, numeric)
        gaps.extend(proposal.payload['numeric_gaps'])
        for ref in {r for c in additions for r in c['evidence_ids']}:
            sources[ref] = service.evidence.resolve(case_id, ref)
    return claims


NOTES_HEADING = "Credit analyst's notes"


def render(parent, claims, sources, gaps):
    """Reuse exact old paragraphs; changed/new spans are emitted with source labels."""
    originals = {c['id']: c for c in parent.claim_spans[1:]}
    if parent.claim_spans[0].get('parts'):
        # A specification-driven section keeps its text and tables exactly; an accepted note is appended under its own heading.
        text = parent.text.rstrip('\n') + '\n'
        for i, claim in enumerate(claims, 1):
            if claim['id'] in originals:
                continue
            if NOTES_HEADING not in text:
                text += f'\n{NOTES_HEADING}\n'
            claim['start'] = len(text)
            text += claim['text'] + '\n' + '\n'.join(f'[CA{i}] {source_label(sources[ref])}' for ref in claim['evidence_ids']) + '\n'
            claim['end'] = len(text)
        return text
    first = min((c['start'] for c in originals.values()), default=len(parent.text))
    text = parent.text[:first] if originals else parent.text.split('\n[GAP]', 1)[0] + '\n'
    for i, claim in enumerate(claims, 1):
        old = originals.get(claim['id'])
        paragraph = parent.text[old['start']:old['end']] if old else claim['text'] + '\n' + '\n'.join(
            f'[CA{i}] {source_label(sources[ref])}' for ref in claim['evidence_ids']) + '\n'
        claim['start'] = len(text)
        text += paragraph + '\n'
        claim['end'] = len(text)
    text += '\n'.join('[GAP] ' + g for g in gaps)
    return text


class SectionChatService:
    def __init__(self, repository, storage_root, template_storage_root=None, provider=None):
        self.repo = repository
        self.versions = VersionService(repository, storage_root, template_storage_root)
        self.drafting = self.versions.drafting
        self.provider = provider

    def check(self, case_id, section_id, request):
        state, draft = self.versions.prepare(case_id, section_id, request)
        if state.readiness == 'Stale':
            raise RevisionConflict('Stale section; explicitly redraft before proposing or accepting chat')
        if not draft.claim_spans or draft.claim_spans[0].get('kind') != 'draft_metadata':
            raise ValueError('Structured draft required')
        for ref in {r for c in draft.claim_spans[1:] for r in c.get('evidence_ids', [])}:
            if not self.drafting.evidence.resolve(case_id, ref)['current']:
                raise RevisionConflict('Source superseded; redraft before chat')
        self.drafting.templates.content(self.repo.get(s.Case, case_id).team_id, draft.template_version_id)
        return state, draft

    def history(self, case_id, section_id):
        state = next((v for v in self.versions.sections(case_id) if v.section_id == section_id), None)
        if not state:
            raise ValueError('Unknown section')
        refs = self.repo.session.scalars(select(models.SectionProposal.id).where(
            models.SectionProposal.case_id == case_id, models.SectionProposal.section_id == section_id))
        proposals = [self.repo.get(s.SectionProposal, ref) for ref in refs]
        for p in proposals:
            if p.status == 'pending' and (not p.payload or p.base_draft_id != state.current_draft_id or
                    p.payload['request']['expected_revision'] != state.editor_revision or
                    p.payload['request']['expected_input_fingerprint'] != state.input_fingerprint or state.readiness == 'Stale'):
                p.status = 'stale'
                self.repo.save(p)
        return dict(proposals=sorted(proposals, key=lambda p: (p.created_at, p.id)),
            messages=[m for m in self.repo.list_for_case(s.ChatMessage, case_id) if m.section_id == section_id])

    def propose(self, case_id, section_id, request):
        state, parent = self.check(case_id, section_id, request)
        config = TeamConfig.model_validate(self.repo.get(s.Case, case_id).config_snapshot)
        if request.numeric and (section_id != 10 or 'reit' not in config.analytics.sets or
                self.repo.get(s.Case, case_id).borrower_type not in config.analytics.sets['reit'].borrower_types):
            raise ValueError('Numeric chat inputs use configured section 10 metrics; source tables require a revised document')
        if request.mode == 'fact' and re.search(r'\d|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion|percent)\b', request.message, re.I):
            raise ValueError('Quantitative facts require explicit numeric operands and Python recomputation')
        claims = deepcopy(parent.claim_spans[1:])
        if parent.claim_spans[0].get('parts') and request.mode == 'emphasize':
            raise ValueError('Reordering is not available for this section; its layout follows the ES template')
        if request.claim_id and request.claim_id not in {c['id'] for c in claims}:
            raise ValueError('Unknown claim; only existing sourced claims may be emphasized')
        fixture = json.loads(FIXTURE.read_text())
        response = fixture['responses'].get(request.mode)
        if not response:
            raise ValueError('Missing chat fixture; no live fallback')
        messages = [dict(role='system', content=fixture['instruction']), dict(role='user', content=json.dumps(dict(
            section_id=section_id, request=request.model_dump(mode='json'), current_text=parent.text,
            claims=claims, gaps=parent.gaps, sources=parent.claim_spans[0]['source_register'],
            computed_values=[self.repo.get(s.ComputedValue, ref).model_dump(mode='json') for ref in parent.computed_value_ids]), sort_keys=True))]
        provider = self.provider or llm.MockProvider({llm.request_key(messages): dict(text=json.dumps(response), stop_reason='end_turn', content=[])})
        if provider.get_provider_info().get('provider') != 'mock':
            raise llm.LiveProviderDisabled('Chat permits offline mock calls only')
        try:
            output = json.loads(llm.clean_json_response(provider.chat(messages)))
        except (llm.MissingFixtureError, ValueError, TypeError) as error:
            raise ValueError('Missing or malformed chat response; no live fallback') from error
        if output != response:
            raise ValueError('Unsupported model text, number, citation or operation rejected')
        message = self.repo.save(s.ChatMessage(case_id=case_id, section_id=section_id, base_draft_id=parent.id,
            actor=request.actor, text=request.message))
        sources = deepcopy(parent.claim_spans[0]['source_register'])
        additions, results, numeric_gaps, ca_input_ids = [], [], [], []
        run_id = str(uuid4())
        if request.mode != 'emphasize':
            supplied = request.numeric.model_dump(mode='json') if request.numeric else None
            previous = next((v for v in reversed(accepted_inputs(self.repo, case_id, section_id)) if v.numeric_input and supplied and
                all(v.numeric_input[k] == supplied[k] for k in ('metric_id', 'period', 'scope'))), None)
            fact = request.message if not supplied else 'CA numeric input (typed operands):\n' + json.dumps(supplied, sort_keys=True)
            source = self.repo.save(s.CAInput(case_id=case_id, message_id=message.id, actor=request.actor, fact=fact,
                numeric_input=supplied, supersedes_id=previous.id if previous else None, revision=previous.revision+1 if previous else 1))
            evidence = self.repo.save(s.Evidence(case_id=case_id, ca_input_id=source.id, excerpt=fact,
                origin='CA input', synthetic=request.numeric.synthetic if supplied else request.synthetic))
            sources[evidence.id] = self.drafting.evidence.resolve(case_id, evidence.id)
            ca_input_ids = [source.id]
            if supplied:
                results = numeric_result(config, request.numeric, evidence.id)
                additions = numeric_claims(self.repo, source, results, run_id)
                numeric_gaps = [g for result in results for g in result['gaps']]
                if not additions:
                    additions = [dict(id='ca-input-'+source.id, kind='ca_input', ca_input_id=source.id,
                        evidence_ids=[evidence.id], text=f"CA numeric input for {results[0]['name']}: incomplete or invalid; "
                        'no calculated result is available. Review the cited CA operands and named gaps; not independently verified.')]
                for addition in additions:
                    addition['numeric_key'] = [request.numeric.metric_id, request.numeric.period, request.numeric.scope]
            else:
                additions = [dict(id='ca-input-'+source.id, kind='ca_input', text='CA input (verbatim; not independently verified):\n'+fact,
                    ca_input_id=source.id, evidence_ids=[evidence.id])]
            claims = overlay(claims, additions, request.numeric)
        else:
            selected = next(c for c in claims if c['id'] == request.claim_id)
            claims.remove(selected)
            # Section 14 always leads with the human position.
            claims.insert(1 if section_id == 14 and claims and claims[0]['kind'] == 'ca_position' else 0, selected)
        replaced_gaps = set()
        if request.numeric and previous:
            replaced_gaps = set(proposal_for_message(self.repo, previous.message_id).payload['numeric_gaps'])
        gaps = list(dict.fromkeys([g for g in parent.gaps if g not in replaced_gaps] + numeric_gaps))
        text = render(parent, claims, sources, gaps)
        meta = deepcopy(parent.claim_spans[0])
        meta.update(source_register=sources, edit_format='b24-chat-v1', chat_fixture=fixture['version'],
                    chat_provider=provider.get_provider_info())
        payload = dict(request=request.model_dump(mode='json'), spans=[meta]+claims, ca_input_ids=ca_input_ids,
            additions=additions, results=results, run_id=run_id, numeric_gaps=numeric_gaps, gaps=gaps,
            fixture_version=fixture['version'], prompt_hash=identity(messages), base_text_hash=identity(parent.text))
        return self.repo.save(s.SectionProposal(case_id=case_id, message_id=message.id, section_id=section_id,
            base_draft_id=parent.id, proposed_text=text, evidence_ids=sorted(sources),
            computed_value_ids=parent.computed_value_ids, model_version=f"mock:{provider.get_provider_info().get('model')}:{fixture['version']}", payload=payload))

    def decide(self, case_id, section_id, proposal_id, decision):
        proposal = self.repo.get(s.SectionProposal, proposal_id)
        if proposal.case_id != case_id or proposal.section_id != section_id:
            raise ValueError('Proposal not found in this section')
        require_working(self.repo, case_id, section_id)
        if proposal.status != 'pending':
            raise RevisionConflict('Proposal already resolved or stale; request a new proposal')
        if decision.action == 'reject':
            proposal.status = 'rejected'
        else:
            command = ChatRequest.model_validate(proposal.payload['request'])
            state, parent = self.check(case_id, section_id, command)
            if identity(parent.text) != proposal.payload['base_text_hash']:
                raise RevisionConflict('Base text changed')
            if command.numeric and not decision.accept_numeric_input:
                raise ValueError('Explicit acceptance of the sourced numeric inputs is required')
            if command.numeric:
                source = self.repo.get(s.CAInput, proposal.payload['ca_input_ids'][0])
                evidence = next(e for e in self.repo.list_for_case(s.Evidence, case_id) if e.ca_input_id == source.id)
                results = numeric_result(TeamConfig.model_validate(self.repo.get(s.Case, case_id).config_snapshot), command.numeric, evidence.id)
                if results != proposal.payload['results']:
                    raise RevisionConflict('Calculation differs from preview; regenerate proposal')
                self.repo.save(s.Spread(id=proposal.payload['run_id'], case_id=case_id, document_ids=[], ca_input_ids=[source.id],
                    version=VERSION, values=dict(chat_proposal_id=proposal.id, results=results, request=source.numeric_input,
                        config_hash=parent.config_hash, arithmetic=VERSION,
                        metrics=[dict(results[0], computed_value_id=identity(proposal.payload['run_id'], results[0]['metric']))],
                        threshold_values=[dict(r, computed_value_id=identity(proposal.payload['run_id'], r['metric'])) for r in results[1:]],
                        tables=[], gaps=proposal.payload['numeric_gaps'],
                        source_register={evidence.id: self.drafting.evidence.resolve(case_id, evidence.id) | {'current': True}}),
                    validation_status='invalid' if proposal.payload['numeric_gaps'] else 'valid', issues=proposal.payload['numeric_gaps']))
                numeric_claims(self.repo, source, results, proposal.payload['run_id'], persist=True)
            new_inputs = [self.repo.get(s.CAInput, ref) for ref in proposal.payload['ca_input_ids']]
            superseded = {v.supersedes_id for v in new_inputs}
            typed = [v for v in accepted_inputs(self.repo, case_id) if v.id not in superseded] + new_inputs
            # Preview the activated fingerprint inside this transaction. The source
            # only becomes current after the final decision and draft both persist.
            state = next(v for v in ReadinessService(self.repo).refresh(case_id, accepted_ca_inputs=typed)[1]
                         if v.section_id == section_id)
            spans = deepcopy(proposal.payload['spans'])
            for ref in proposal.evidence_ids:
                spans[0]['source_register'][ref] = self.drafting.evidence.resolve(case_id, ref)
                if spans[0]['source_register'][ref].get('ca_input_id') in proposal.payload['ca_input_ids']:
                    spans[0]['source_register'][ref]['current'] = True
            computed_ids = sorted({r for c in spans[1:] for r in c.get('computed_value_ids', []) + ([c['computed_value_id']] if c.get('computed_value_id') else [])})
            draft = self.repo.save(s.DraftVersion.model_validate(parent.model_dump() | dict(id=str(uuid4()), created_at=s.utcnow(),
                parent_id=parent.id, text=proposal.proposed_text, claim_spans=spans, ca_edits=True, author=decision.actor,
                model_version=proposal.model_version, prompt_version='b24:'+proposal.payload['prompt_hash'],
                computed_value_ids=computed_ids, ca_input_ids=sorted(set(parent.ca_input_ids + proposal.payload['ca_input_ids'])),
                input_fingerprint=state.input_fingerprint, gaps=proposal.payload['gaps'])))
            for i, claim in enumerate(spans[1:]):
                for ref in claim['evidence_ids']:
                    self.repo.save(s.Citation(case_id=case_id, draft_id=draft.id, evidence_id=ref, claim_or_cell=f'claim:{i}:{claim["id"]}'))
            self.repo.save(state.model_copy(update=dict(current_draft_id=draft.id, confirmed_draft_id=None,
                readiness='Drafted', editor_revision=state.editor_revision+1)))
            proposal.accepted_draft_id = draft.id
            proposal.status = 'accepted'
        proposal.resolved_by, proposal.resolved_at = decision.actor, s.utcnow()
        self.repo.save(proposal)
        self.history(case_id, section_id)
        return proposal
