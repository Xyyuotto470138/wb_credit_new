"""Deterministic B25 checks. Callers own transactions and SQLite write locks.

A recorded check is evidence of a review at one instant, never a reusable permit
for a later workflow transition. B16 must rerun require_passed in its transaction.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .. import schemas as s
from ..retrieval import EvidenceService
from ..retrieval.service import ContentIntegrityError, identity
from .readiness import ReadinessService
from .locks import require_working
from .templates import TemplateRegistry

MASTER_LABEL = 'Not connected: assumed consistent for this prototype'
Nonblank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    role: Literal['CA'] = 'CA'
    expected_preview_token: str = Field(min_length=1)
    mandatory_gap_reasons: dict[str, Nonblank] = Field(default_factory=dict)


class SubmissionConflict(ValueError):
    def __init__(self, message, report=None):
        super().__init__(message)
        self.report = report


def section_result(state, name, draft, confirmations, source_issues):
    """One configured section; neither document reasons nor draft completeness waive it."""
    issues = list(source_issues)
    confirmation = None
    fresh = False
    if not state.applicable:
        if state.readiness != 'Not applicable' or not (state.na_reason and state.na_reason.strip()):
            issues.append('Not applicable requires a recorded nonblank reason.')
        fresh = not issues
    else:
        if not draft:
            issues.append('A current draft and CA confirmation are required.')
        else:
            fresh = draft.input_fingerprint == state.input_fingerprint and state.readiness != 'Stale' and not issues
            if not fresh:
                issues.append('Current inputs or sources require re-review and a fresh confirmation.')
            confirmation = next((c for c in reversed(confirmations)
                if c.section_id == state.section_id and c.draft_id == draft.id
                and c.input_fingerprint == state.input_fingerprint
                and c.editor_revision == state.editor_revision - 1), None)
            if (state.readiness != 'CA confirmed' or state.confirmed_draft_id != draft.id
                    or not confirmation):
                issues.append('The current draft needs CA confirmation.')
    return dict(section_id=state.section_id, name=name, applicable=state.applicable,
        na_reason=state.na_reason, readiness=state.readiness, draft_id=state.current_draft_id,
        confirmed_draft_id=state.confirmed_draft_id, input_fingerprint=state.input_fingerprint,
        editor_revision=state.editor_revision, fresh=fresh,
        confirmation=confirmation.model_dump(mode='json') if confirmation else None,
        status='open' if issues else 'passed', issues=issues, content_gaps=state.gaps)


class SubmissionChecksService:
    def __init__(self, repo, storage_root, template_storage_root):
        self.repo = repo
        self.evidence = EvidenceService(repo, storage_root)
        self.templates = TemplateRegistry(repo, template_storage_root)

    def preview(self, case_id):
        gaps, states = ReadinessService(self.repo).refresh(case_id)
        case = gaps.case
        confirmations = sorted(self.repo.list_for_case(s.SectionConfirmation, case_id),
                               key=lambda c: (c.created_at, c.id))
        drafts, sections, sources = {}, [], {}
        names = {d.id: d.name for d in gaps.config.template.sections}
        for state in states:
            draft = self.repo.get(s.DraftVersion, state.current_draft_id) if state.current_draft_id and state.applicable else None
            issues = []
            if draft:
                if draft.case_id != case_id or draft.section_id != state.section_id or draft.config_hash != case.config_hash:
                    raise SubmissionConflict('Draft ownership, section or configuration mismatch')
                drafts[state.section_id] = draft
                refs = set(draft.claim_spans[0].get('source_register', {})) if draft.claim_spans else set()
                refs.update(ref for claim in draft.claim_spans[1:] for ref in claim.get('evidence_ids', []))
                for ref in sorted(refs):
                    if ref not in sources:
                        try:
                            sources[ref] = self.evidence.resolve(case_id, ref)
                        except (ValueError, ContentIntegrityError) as error:
                            sources[ref] = dict(current=False, issue=str(error))
                    if not sources[ref]['current']:
                        issues.append(f'Source {ref} requires review: ' + sources[ref].get('issue', 'superseded evidence.'))
            sections.append(section_result(state, names[state.section_id], draft, confirmations, issues))
        mandatory = [item | dict(recorded_reason=None, status_check='open')
                     for group in gaps.groups.values() for item in group if item['mandatory']]
        mandatory.sort(key=lambda item: item['catalogue_id'])
        pins = {d.template_version_id for d in drafts.values()}
        blockers = []
        template = None
        if len(pins) > 1:
            blockers.append('Section template versions differ; select a consistent working version.')
        else:
            template = self.templates.get(case.team_id, next(iter(pins))) if pins else self.templates.active(case.team_id)
            if template is None:
                blockers.append('An active or draft-pinned template is required to record an ES snapshot.')
        report = dict(format_version='submission-checks-v1', case_id=case_id,
            config_hash=case.config_hash, workflow_state=case.workflow_state,
            template_version_id=template.id if template else None,
            sections=sections, mandatory_gaps=mandatory, blockers=blockers,
            future_credit_master=self._master_panel(drafts.get(2), sections, sources),
            scope='Pre-submission checks only; no credit decision or workflow transition.')
        self._summarize(report)
        report['preview_token'] = identity(report)
        return report

    @staticmethod
    def _summarize(report):
        statuses = [v['status'] for v in report['sections']] + [v['status_check'] for v in report['mandatory_gaps']]
        report['summary'] = dict(total=len(statuses), passed=statuses.count('passed'), open=statuses.count('open'))
        report['passed'] = not report['summary']['open'] and not report['blockers']
        report['can_submit'] = report['passed'] and report['workflow_state'] in {'Draft', 'Returned to CA'}

    def _master_panel(self, draft, sections, sources):
        panel = dict(label=MASTER_LABEL, status='not connected', included_in_pass_count=False,
            section_id=2, draft_id=draft.id if draft else None,
            section_readiness=next((v['readiness'] for v in sections if v['section_id'] == 2), None),
            figures_to_compare=['Existing limit', 'Outstanding', 'Proposed limit'],
            facilities=[], gaps=[])
        if not draft:
            panel['gaps'].append('Section 2 has no saved exposure figures yet.')
            return panel
        meta = draft.claim_spans[0] if draft.claim_spans else {}
        tables = [t for t in meta.get('computed_tables', []) if t.get('kind') == 'exposure']
        if len(tables) != 1:
            panel['gaps'].append('Section 2 has no single supported exposure table; figures are not inferred.')
            return panel
        table = tables[0]
        run = self.repo.get(s.Spread, meta['computation_id'])
        if run.case_id != draft.case_id or table not in run.values.get('tables', []):
            raise SubmissionConflict('Section 2 exposure table differs from its saved Python computation')
        if table.get('case_input'):
            panel['case_input'] = table['case_input']
            panel['exposure_note'] = table['status']
        for row in table['rows']:
            figures = {}
            for key, label in [('existing', 'Existing limit'), ('outstanding', 'Outstanding'), ('proposed', 'Proposed limit')]:
                metric = f'exposure/{row["facility"]}/{key}'
                cells = [c for c in table['cells'] if c['metric'] == metric]
                if len(cells) != 1:
                    raise SubmissionConflict('Exposure figure has no unique computed cell')
                cell = cells[0]
                value = self.repo.get(s.ComputedValue, cell['computed_value_id'])
                refs = sorted({r for group in value.operand_evidence_ids.values() for r in group})
                if (value.case_id != draft.case_id or value.spread_id != run.id or value.id not in draft.computed_value_ids
                        or not value.validated or value.gaps or value.value is None
                        or str(value.value) != row[key] or not refs
                        or any(ref not in sources or sources[ref].get('issue') for ref in refs)):
                    panel['gaps'].append(f'{row["facility"]}: {label} source/value unavailable; figure withheld.')
                    continue
                figures[key] = dict(label=label, value=str(value.value), unit=value.unit, currency=value.currency,
                    period=value.period, synthetic=value.synthetic, computed_value_id=value.id,
                    operand_evidence_ids=value.operand_evidence_ids,
                    sources={ref: sources[ref] for ref in refs})
            panel['facilities'].append(dict(facility=row['facility'], entity=row['entity'],
                currency=row['currency'], period=row['period'], figures=figures))
        return panel

    def evaluate(self, case_id, request, *, allowed_states=None):
        if allowed_states is None:
            require_working(self.repo, case_id)
        report = self.preview(case_id)
        if report['workflow_state'] not in (allowed_states or {'Draft', 'Returned to CA'}):
            raise SubmissionConflict('Recording pre-submission checks requires a working Draft or Returned to CA state')
        if request.expected_preview_token != report['preview_token']:
            raise SubmissionConflict('Inputs, confirmations or gaps changed; reload the checks before recording reasons')
        gap_ids = {item['id'] for item in report['mandatory_gaps']}
        if not set(request.mandatory_gap_reasons) <= gap_ids:
            raise ValueError('Reasons must name current open mandatory gaps in this case')
        for item in report['mandatory_gaps']:
            reason = request.mandatory_gap_reasons.get(item['id'])
            item.update(recorded_reason=reason, status_check='passed' if reason else 'open')
        self._summarize(report)
        return report

    def require_passed(self, case_id, request, *, allowed_states=None):
        """B16 integration seam: rerun inside the same transaction as submission."""
        report = self.evaluate(case_id, request, allowed_states=allowed_states)
        if not report['passed']:
            raise SubmissionConflict('Pre-submission checks remain open', report)
        return report

    def record(self, case_id, request, *, require_passed=False):
        report = self.require_passed(case_id, request) if require_passed else self.evaluate(case_id, request)
        return self.record_report(case_id, request, report, purpose='submission' if require_passed else 'working')

    def record_report(self, case_id, request, report, *, purpose, parent_id=None):
        if report['blockers']:
            raise SubmissionConflict('ES snapshot cannot be recorded', report)
        reasons = {item['id']: item['recorded_reason'] for item in report['mandatory_gaps'] if item['recorded_reason']}
        es = self.repo.save(s.ESVersion(case_id=case_id, parent_id=parent_id,
            section_versions={v['section_id']: v['draft_id'] for v in report['sections'] if v['applicable'] and v['draft_id']},
            config_hash=report['config_hash'], template_version_id=report['template_version_id'],
            author=request.actor, purpose=purpose, gap_reasons=reasons))
        return self.repo.save(s.SubmissionCheck(case_id=case_id, es_version_id=es.id,
            section_results={v['section_id']: v for v in report['sections']},
            mandatory_gap_reasons=reasons, freshness_results={v['section_id']: v['fresh'] for v in report['sections']},
            passed=report['passed'], checked_by=request.actor, report=report))

    def get(self, case_id, check_id):
        check = self.repo.get(s.SubmissionCheck, check_id)
        if check.case_id != case_id:
            raise ValueError('Submission check not found in this case')
        return check
