"""Immutable case-scoped computation snapshots and reviewed operand mappings."""
import re
from ..services.locks import require_working
from .. import schemas as s
from ..retrieval import EvidenceService
from ..retrieval.service import identity
from ..team_config import TeamConfig
from .engine import Fact, VERSION, number, normalize, calculate, display
from .tables import compute_table
from uuid import uuid4


class AnalyticsService:
    def __init__(self, repository, storage_root):
        self.repo = repository
        self.evidence = EvidenceService(repository, storage_root)

    def source(self, case_id, evidence_id):
        source = self.evidence.resolve(case_id, evidence_id)
        if not source['current']:
            raise ValueError('Computation requires current case/entity evidence')
        return source

    def binding(self, case_id, binding, register):
        if binding.evidence_id not in register:
            register[binding.evidence_id] = self.source(case_id, binding.evidence_id)
        source = register[binding.evidence_id]
        compact = lambda text: ' '.join(text.split())
        excerpt, quote, context = map(compact, (source['excerpt'], binding.quote, binding.context_quote))
        if quote not in excerpt or context not in excerpt:
            raise ValueError('Source quote/context does not match evidence')
        # Numeric boundaries prevent selecting 50 from 150, or 2.5 from 12.5.
        pattern = r'(?<![\d.,\w])' + re.escape(binding.token) + r'(?:(?![\d.,\w])|(?=x\b))'
        if len(list(re.finditer(pattern, quote))) <= binding.occurrence:
            raise ValueError('Numeric token/occurrence not present in source quote')
        if binding.period not in context:
            # Explicit reviewed period mappings may use a human-readable source date.
            from datetime import date
            try:
                dt=date.fromisoformat(binding.period)
                variants=[dt.strftime('%d %B %Y').lstrip('0'),dt.strftime('%d %b %Y').lstrip('0')]
            except ValueError:
                variants=[]
            if not any(v in context for v in variants):
                raise ValueError('Period is not supported by source context')
        value, unit = normalize(number(binding.token), binding.unit)
        if unit.startswith('currency') and not binding.currency:
            raise ValueError('Currency is required')
        if binding.scope not in context:
            raise ValueError('Scope must occur in reviewed source context')
        if binding.item and binding.item not in context:
            raise ValueError('Item identity must occur in source context')
        if binding.maturity and binding.maturity.isoformat() not in context:
            raise ValueError('Maturity date must occur in source context')
        return Fact(value,unit,binding.currency,binding.period,binding.scope,binding.basis,[binding.evidence_id],
                    synthetic=source['synthetic'],proxy=binding.proxy,item=binding.item,maturity=binding.maturity,
                    source=dict(binding=binding.model_dump(mode='json'),provenance=source))

    def spread_fact(self, case_id, value_id, register, expected_metric):
        value=self.repo.get(s.ComputedValue,value_id)
        if value.case_id!=case_id or not value.validated or value.value is None or value.gaps or not value.spread_id:
            raise ValueError('Spread operand is not a validated value in this case')
        spread=self.repo.get(s.Spread,value.spread_id)
        if spread.validation_status!='valid' or 'result' not in spread.values:
            raise ValueError('Expected a validated B09 financial spread')
        if value.metric != expected_metric:
            raise ValueError('Spread account does not match mapped operand')
        refs=sorted({r for ids in value.operand_evidence_ids.values() for r in ids})
        if not refs: raise ValueError('Spread operand has no evidence')
        for ref in refs: register[ref]=self.source(case_id,ref)
        return Fact(value.value,value.unit,value.currency,value.period,value.scope,'financial statements',refs,
                    value.synthetic,value.proxy,source=dict(computed_value_id=value.id,spread_id=spread.id))

    def generate(self, case_id, request):
        require_working(self.repo, case_id)
        case=self.repo.get(s.Case,case_id)
        config=TeamConfig.model_validate(case.config_snapshot)
        selected=config.analytics.sets.get(request.set_id)
        if not selected or case.borrower_type not in selected.borrower_types:
            raise ValueError('No applicable analytics set in pinned configuration')
        if len({t.kind for t in request.tables})!=len(request.tables):
            raise ValueError('Duplicate table selection')
        if set(request.metrics)-{m.id for m in selected.metrics}:
            raise ValueError('Unknown metric in pinned analytics set')
        register={}; values=[]
        for metric in selected.metrics:
            mapped=request.metrics.get(metric.id)
            inputs={}
            if mapped:
                for bindings in mapped.bindings.values():
                    for binding in bindings:
                        if metric.source_labels and not any(label.casefold() in ' '.join(binding.quote.split()).casefold() for label in metric.source_labels):
                            raise ValueError(f'{metric.name}: quote must identify the disclosed metric')
                inputs={key:[self.binding(case_id,b,register) for b in bindings] for key,bindings in mapped.bindings.items()}
                inputs.update({key:[self.spread_fact(case_id,ref,register,metric.id if key=='reported' else 'npi' if key=='reported_npi' else key) for ref in refs] for key,refs in mapped.spread_value_ids.items()})
            values.append(calculate(metric,inputs,request.period,request.scope))
        tables=[]
        for selection in request.tables:
            sources=[self.source(case_id,ref) for ref in selection.evidence_ids]
            register.update({src['evidence_id']:src for src in sources})
            # Table source policy prevents routing unrelated evidence into financial tables.
            allowed={'exposure':{1,3},'covenants':{8,21},'conduct':{17},'projections':{14}}
            for src in sources:
                doc=self.repo.get(s.Document,src['document_id'])
                if doc.catalogue_id not in allowed[selection.kind] and not (selection.kind=='exposure' and doc.suggestion_id=='limits_utilisation'):
                    raise ValueError('Worksheet is not a configured source type for this table')
            tables.append(compute_table(selection.kind,sources,case))
        present={t['kind'] for t in tables}
        for kind,section in [('exposure',2),('conduct',13),('covenants',13),('projections',9)]:
            if kind not in present:
                if kind=='exposure' and case.new_to_bank:
                    tables.append(dict(kind=kind,section_id=section,rows=[],cells=[],gaps=[],
                        status='Nil existing exposure: explicit new-to-bank case input',case_input=dict(case_id=case.id,new_to_bank=True),
                        note='Proposed facilities still require sourced inputs.'))
                elif kind=='conduct' and case.new_to_bank:
                    tables.append(dict(kind=kind,section_id=section,rows=[],cells=[],gaps=[],status='Not applicable: new-to-bank case input'))
                else:
                    tables.append(dict(kind=kind,section_id=section,rows=[],cells=[],gaps=[f'{kind}: required source extract not provided']))
        gaps=[gap for v in values for gap in v['gaps']]+[gap for t in tables for gap in t['gaps']]+[gap for t in tables for c in t['cells'] for gap in c['gaps']]
        threshold_values=[]
        for result in values:
            for i,threshold in enumerate(result['thresholds']):
                if threshold['headroom'] is not None:
                    threshold_values.append(dict(result,metric=f'{result["metric"]}/headroom/{i}',
                        name=result['name']+' headroom',value=threshold['headroom'],unit=threshold['headroom_unit'],
                        display=display(number(threshold['headroom'])),thresholds=[],formula={'op':'threshold_headroom','rule':threshold},currency=None))
        run_id=str(uuid4())
        all_values=values+threshold_values+[cell for table in tables for cell in table['cells']]
        for i,result in enumerate(all_values):
            result['computed_value_id']=identity(run_id,str(i),result['metric'])
        report=dict(metrics=values,threshold_values=threshold_values,tables=tables,gaps=gaps,source_register=register,request=request.model_dump(mode='json'),
                    config_hash=case.config_hash,arithmetic=VERSION,
                    mapping_review='Source mapping reviewed by caller; arithmetic validation is not independent semantic extraction validation.')
        # A computation report is not a financial-statement spread. Keep it out of B05's spread-readiness gate.
        run=self.repo.save(s.Spread(id=run_id,case_id=case_id,document_ids=sorted({src['document_id'] for src in register.values()}),
            version=VERSION,values=report,validation_status='manual review',issues=gaps))
        for result in all_values:
            ref=result['computed_value_id']
            value=self.repo.save(s.ComputedValue(id=ref,case_id=case_id,spread_id=run.id,metric=result['metric'],formula_version=VERSION,
                operands=result['operands'],operand_evidence_ids=result['operand_evidence_ids'],unit=result['unit'],currency=result['currency'],
                period=result['period'],scope=result['scope'],value=result['value'],validated=result['value'] is not None and not result['gaps'],
                proxy=result['proxy'],synthetic=result['synthetic'],gaps=result['gaps']))
            for evidence_id in sorted({ref for refs in value.operand_evidence_ids.values() for ref in refs}):
                self.repo.save(s.Citation(id=identity(value.id,evidence_id),case_id=case_id,evidence_id=evidence_id,
                    computed_value_id=value.id,claim_or_cell=value.metric))
        return self.get(case_id,run.id)

    def get(self,case_id,run_id):
        run=self.repo.get(s.Spread,run_id)
        if run.case_id!=case_id or run.version!=VERSION:
            raise ValueError('Computation not found in this case')
        values=[v.model_dump(mode='json') for v in self.repo.list_for_case(s.ComputedValue,case_id) if v.spread_id==run.id]
        return dict(computation=run.model_dump(mode='json'),computed_values=values)
