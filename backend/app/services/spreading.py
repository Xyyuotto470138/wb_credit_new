"""Case-scoped B09 generation; callers own the transaction and serialize writes.

Immutable spread/figure/citation records reference B08 source versions. No runtime
Phase 1 imports, background threads, live model calls, ratios or recommendation.
"""
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .locks import require_working
from .. import schemas as s
from ..extraction_agent.orchestrator import run_extraction_agent, VERSION
from ..extraction_agent.validator import number
from ..retrieval import EvidenceService
from ..retrieval.service import identity
from ..team_config import TeamConfig
from .gaps import coverage
from .intake import period_key
from .readiness import ReadinessService


class SpreadRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile: str = Field(min_length=1, max_length=100)
    evidence_ids: list[str] = Field(min_length=1, max_length=40)
    periods: list[str] = Field(min_length=1, max_length=5)
    scope: str = Field(min_length=1, max_length=80)


class SpreadingService:
    def __init__(self, repository, storage_root, provider):
        self.repo, self.storage_root, self.provider = repository, Path(storage_root), provider
        self.evidence = EvidenceService(repository, storage_root)

    def prepare(self, case_id, request):
        case = self.repo.get(s.Case, case_id)
        config = TeamConfig.model_validate(case.config_snapshot)
        profile = config.analytics.spreading.get(request.profile)
        if not profile or case.borrower_type not in profile.borrower_types:
            raise ValueError('No applicable spreading profile in pinned case configuration')
        if request.scope not in profile.scopes:
            raise ValueError('Unknown spreading scope')
        if (len(set(request.periods)) != len(request.periods)
                or any(len(p) != 4 or not p.isdigit() or not 2000 <= int(p) <= 2099 for p in request.periods)):
            raise ValueError('Use unique four-digit reporting years')
        if len(set(request.evidence_ids)) != len(request.evidence_ids):
            raise ValueError('Duplicate source selection')
        allowed = {i for item in config.catalogue.items if item.generation == 'spread'
                   and item.applicable_when.matches(case) for i in item.generation_inputs}
        sources, documents = {}, {}
        for ref in sorted(request.evidence_ids):
            source = self.evidence.resolve(case_id, ref)
            doc = self.repo.get(s.Document, source['document_id'])
            if not source['current']:
                raise ValueError('Spreading requires current, usable case/entity evidence')
            eligible = False
            for item in config.catalogue.items:
                if item.id not in allowed or not coverage(doc, item):
                    continue
                if doc.origin == 'public' and item.public_support == 'none':
                    continue
                if doc.catalogue_id != item.id and not any(m.get('id') == item.id and source['page'] in m.get('pages', [])
                                                          for m in doc.intake.get('catalogue_support', [])):
                    continue
                eligible = True
            if not eligible:
                raise ValueError('Selected page is not a configured financial spread source')
            key = period_key(doc.period)
            if key is None or max(int(p) for p in request.periods) > key.year:
                raise ValueError('Requested period is newer than or incompatible with source report period')
            sources[ref] = source
            documents[doc.id] = doc
        if sum(len(v['excerpt']) for v in sources.values()) > 250_000:
            raise ValueError('Selected source text exceeds spreading budget; narrow the selection')
        return case, profile, sources, documents

    def generate(self, case_id, request):
        require_working(self.repo, case_id)
        case, profile, sources, documents = self.prepare(case_id, request)
        result = run_extraction_agent(self.provider, sources, profile, request.periods, request.scope)
        report = result['validation']
        spread = s.Spread(case_id=case_id, document_ids=sorted(documents), version=VERSION,
            validation_status=report['status'], issues=[i['message'] for i in report['issues']],
            values=dict(result=result, request=request.model_dump(mode='json'), config_hash=case.config_hash,
                profile=profile.model_dump(mode='json'), source_register=sources,
                coverage='Configured core financial rows only; not a complete line-by-line financial statement or regulatory analytics.'))
        self.repo.save(spread)
        for fact in report['facts']:
            ref = identity(spread.id, fact['metric'], fact['period'], fact['scope'])
            computed = self.repo.save(s.ComputedValue(id=ref, case_id=case_id, spread_id=spread.id,
                metric=fact['metric'], formula_version='reported-times-scale-v1',
                operands={'reported': str(number(fact['raw_value'])), 'scale': fact['scale']},
                operand_evidence_ids={'reported': fact['evidence_ids'], 'scale': fact['evidence_ids']},
                unit=fact['unit'], currency=fact['currency'], period=fact['period'], scope=fact['scope'],
                value=fact['value'], validated=spread.validation_status == 'valid', synthetic=fact['synthetic'],
                gaps=[] if spread.validation_status == 'valid' else ['Spread has unresolved validation issues; do not use as validated input.']))
            for evidence_id in fact['evidence_ids']:
                self.repo.save(s.Citation(id=identity(ref, evidence_id), case_id=case_id,
                    evidence_id=evidence_id, computed_value_id=computed.id,
                    claim_or_cell=f"{fact['metric']}/{fact['period']}/{fact['scope']}"))
        ReadinessService(self.repo).refresh(case_id)
        return self.get(case_id, spread.id)

    def get(self, case_id, spread_id):
        spread = self.repo.get(s.Spread, spread_id)
        if spread.case_id != case_id or spread.version != VERSION:
            raise ValueError('Spread not found in this case')
        values = [v for v in self.repo.list_for_case(s.ComputedValue, case_id) if v.spread_id == spread.id]
        return dict(spread=spread.model_dump(mode='json'), computed_values=[v.model_dump(mode='json') for v in values])
