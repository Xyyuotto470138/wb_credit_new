"""Two ephemeral drafts under one serialized evidence snapshot; no adoption side effect."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .locks import require_working
from .. import schemas as s
from ..llm.registry import load_registry
from ..retrieval.service import identity
from .drafting import DraftRequest, DraftingService
from .readiness import ReadinessService
from .versions import RevisionConflict


class DefaultModelRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    role: Literal['CA'] = 'CA'
    model_id: str
    expected_model_id: str


class CompareRequest(DraftRequest):
    model_ids: list[str] = Field(min_length=2, max_length=2)
    expected_draft_id: str | None
    expected_revision: int = Field(ge=0)
    expected_input_fingerprint: str = Field(min_length=1)


def set_default(repo, case_id, request):
    case = repo.get(s.Case, case_id)
    require_working(repo, case_id)
    if case.default_model_id != request.expected_model_id:
        raise RevisionConflict('Case default changed; reload before choosing a model')
    load_registry().get(request.model_id).require_runnable()
    return repo.save(case.model_copy(update=dict(default_model_id=request.model_id)))


def metrics(draft):
    metadata, *claims = draft['claim_spans']
    # Coverage of displayed claims, including explicit human/case assertions.
    cited = sum(bool(c.get('evidence_ids') or c.get('ca_position') or c['kind'] == 'case_input') for c in claims)
    coverage = str((Decimal(cited) * 100 / len(claims)).quantize(Decimal('0.01'))) if claims else None
    info = metadata['provider']
    return dict(citation_coverage=dict(cited=cited, total=len(claims), percent=coverage,
        basis='Displayed claims with source links or explicit CA/case input; not semantic verification'),
        unsupported_claims_rejected=info['validation']['rejected_claims'],
        malformed_response=info['validation']['malformed_response'], omitted_claims=info['validation']['omitted_claims'],
        gap_markers=draft['gaps'], latency_ms=info['latency_ms'],
        latency_basis='Local provider response and validation only; not a live model benchmark',
        estimated_cost_usd=info['estimated_cost_usd'], cost_basis=info['cost_basis'])


def compare(repo, storage_root, template_root, case_id, section_id, request):
    if request.model_id is not None:
        raise ValueError('Use model_ids for comparison')
    if request.model_ids[0] == request.model_ids[1]:
        raise ValueError('Choose two different registered models')
    registry = load_registry()
    entries = [registry.get(key).require_runnable() for key in request.model_ids]
    case = repo.get(s.Case, case_id)
    require_working(repo, case_id, section_id)
    state = next((v for v in ReadinessService(repo).refresh(case_id)[1] if v.section_id == section_id), None)
    if not state or not state.applicable:
        raise ValueError('Unknown or not applicable section')
    if (state.current_draft_id != request.expected_draft_id or state.editor_revision != request.expected_revision
            or state.input_fingerprint != request.expected_input_fingerprint):
        raise RevisionConflict('Section revision or inputs changed; reload before comparing')
    options = request.model_dump(exclude={'model_ids', 'expected_draft_id', 'expected_revision', 'expected_input_fingerprint'})
    if state.current_draft_id:
        parent = repo.get(s.DraftVersion, state.current_draft_id)
        options['template_version_id'] = parent.template_version_id
    service = DraftingService(repo, storage_root, template_root)
    drafts = []
    for entry in entries:
        options['model_id'] = entry.id
        draft = service.generate(case_id, section_id, DraftRequest(**options), parent_id=state.current_draft_id, preview=True)
        drafts.append(draft)
        # Reuse the exact Python computation, including IDs/operands/citations.
        options['computation_id'] = draft['claim_spans'][0]['computation_id']
    a, b = [draft['claim_spans'][0] for draft in drafts]
    if a['prompt_hash'] != b['prompt_hash'] or a['provider']['evidence_hash'] != b['provider']['evidence_hash']:
        raise RevisionConflict('Comparison inputs diverged; no comparable result returned')
    computed = [{c['computed_value_id']: c['value'] for c in d['claim_spans'][1:] if c.get('computed_value_id')} for d in drafts]
    if a['computed_tables'] != b['computed_tables'] or computed[0] != computed[1]:
        raise RevisionConflict('Python computed tables diverged; comparison withheld')
    return dict(section_id=section_id, saved=False, input_fingerprint=state.input_fingerprint,
        base_draft_id=state.current_draft_id, prompt_hash=a['prompt_hash'], evidence_hash=a['provider']['evidence_hash'],
        computed_tables_identical=True, computed_tables_hash=identity(a['computed_tables']),
        computed_table_count=len(a['computed_tables']), computed_tables=a['computed_tables'],
        computed_values_identical=True, computed_value_count=len(computed[0]), computed_values_hash=identity(computed[0]),
        estimated_cost_usd='0', registry_version=registry.version,
        results=[dict(model=entry.public(), draft=draft, metrics=metrics(draft)) for entry, draft in zip(entries, drafts)])
