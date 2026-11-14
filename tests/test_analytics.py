"""B10 independent offline gold, definition, source-boundary and persistence tests."""
from copy import deepcopy
from datetime import date
from decimal import Decimal as D
from pathlib import Path
import pytest
import yaml

from backend.app import schemas as s
from backend.app.analytics import AnalyticsService, AnalyticsRequest
from backend.app.analytics.contracts import Binding
from backend.app.analytics.engine import Fact, calculate, display, normalize
from backend.app.analytics.tables import compute_table
from backend.app.repository import Repository
from backend.app.team_config import load_team, TeamConfig
from backend.app.main import create_app
from test_intake import make_case, request as http_request
from test_spreading import store, synthetic, set_full

ROOT=Path(__file__).resolve().parents[1]
GOLD=yaml.safe_load((ROOT/'tests/fixtures/synthetic_gold.yaml').read_text())
METRICS={m.id:m for m in load_team('fig').analytics.sets['reit'].metrics}


def fact(value,unit='currency',currency='SGD',period='2026-10-31',scope='Group',basis='financial statements',**kw):
    return Fact(D(str(value)),unit,currency,period,scope,basis,['evidence'],**kw)


def calc(id,**inputs):
    return calculate(METRICS[id],inputs,'2026-10-31','Group')


@pytest.mark.parametrize('metric,operand,unit,actual,headroom,status',[
 ('aggregate_leverage','regulatory_leverage','percent','49.999','0.001','within'),
 ('aggregate_leverage','regulatory_leverage','percent','50','0','within'),
 ('aggregate_leverage','regulatory_leverage','percent','50.001','-0.001','outside'),
 ('interest_coverage','regulatory_icr','times','1.499','-0.001','outside'),
 ('interest_coverage','regulatory_icr','times','1.5','0.0','within'),
 ('interest_coverage','regulatory_icr','times','1.501','0.001','within'),
])
def test_mas_boundaries(metric,operand,unit,actual,headroom,status):
    result=calc(metric,**{operand:[fact(actual,unit,None,basis='MAS Appendix 6 reported')]})
    assert result['value']==actual and not result['gaps']
    assert D(result['thresholds'][0]['headroom'])==D(headroom)
    assert result['thresholds'][0]['status'].startswith(status)
    assert result['thresholds'][0]['effective_date']=='2024-11-28'
    assert 'mas.gov.sg' in result['thresholds'][0]['source']
    assert 'capacity' not in str(result)


@pytest.mark.parametrize('icr,flag',[('1.799',True),('1.8',False),('1.801',False)])
def test_improvement_boundary(icr,flag):
    result=calc('interest_coverage',regulatory_icr=[fact(icr,'times',None,basis='MAS Appendix 6 reported')])
    assert (result['thresholds'][1]['status']=='improvement plan expected') is flag


@pytest.mark.parametrize('change',[{'proxy':True},{'basis':'NPI / finance costs'},{'period':'2025-10-31'},{'scope':'Trust'},{'unit':'percent'}])
def test_regulatory_rejects_proxy_definition_date_scope_units(change):
    f=fact('2.6','times',None,basis='MAS Appendix 6 reported')
    for k,v in change.items(): setattr(f,k,v)
    result=calc('interest_coverage',regulatory_icr=[f])
    assert result['value'] is None and result['gaps'] and not result['thresholds']


def test_all_ten_measures_missing_remain_named_gaps():
    for m in list(METRICS.values())[:10]:
        result=calculate(m,{},'2026-10-31','Group')
        assert result['value'] is None and result['gaps'][0].startswith(m.name) and result['thresholds']==[]


def test_units_normalization_and_precision():
    assert normalize(D('2.7'),'cents/unit')==(D('.027'),'currency/unit')
    assert normalize(D('1.25'),'currency_million')==(D('1250000'),'currency')
    assert normalize(D('.9'),'fraction')==(D('90'),'percent')
    result=calc('dpu',distributions=[fact('1')],eligible_units=[fact('3','units',None)])
    assert result['value'].startswith('0.3333333333333333333333333') and result['display']=='0.333333'
    assert result['currency']=='SGD'


def test_npi_sign_reconciliation_and_synthetic_flags():
    inputs=dict(property_income=[fact(100,synthetic=True)],property_expenses=[fact(30)],reported_npi=[fact(70)])
    result=calc('npi',**inputs)
    assert result['value']=='70' and result['synthetic']
    inputs['property_expenses'][0].value=D(-30)
    assert calc('npi',**inputs)['value'] is None
    inputs['property_expenses'][0].value=D(31)
    assert 'reconcile' in calc('npi',**inputs)['gaps'][0]


@pytest.mark.parametrize('denominator',['0','-1'])
def test_zero_negative_denominators(denominator):
    assert calc('dpu',distributions=[fact(5)],eligible_units=[fact(denominator,'units',None)])['value'] is None


def test_occupancy_fixed_share_and_weights():
    basis='comparable lettable area'
    result=calc('occupancy',occupied_area=[fact(9632,'sqm',None,basis=basis)],lettable_area=[fact(19187,'sqm',None,basis=basis)])
    assert result['display']==GOLD['property']['occupancy_pct']
    basis='fixed or hedged, non-overlapping'
    assert calc('fixed_rate_share',fixed_or_hedged_debt=[fact(60,basis=basis)],total_debt=[fact(100,basis=basis)])['value']=='60.0'
    assert calc('fixed_rate_share',fixed_or_hedged_debt=[fact(110,basis=basis)],total_debt=[fact(100,basis=basis)])['value'] is None
    basis='rental-income weights'
    a=[fact(2,'years',None,basis=basis,item='A'),fact(5,'years',None,basis=basis,item='B')]
    b=[fact(80,'percent',None,basis=basis,item='A'),fact(20,'percent',None,basis=basis,item='B')]
    assert calc('wale',remaining_lease_years=a,weights=b)['value']=='2.6'
    b[1].item='A'
    assert calc('wale',remaining_lease_years=a,weights=b)['value'] is None


def test_maturity_reconciles_and_keeps_bucket_dates():
    a=[fact(30,item='TL',maturity=date(2027,1,1)),fact(70,item='RCF',maturity=date(2028,1,1))]
    result=calc('debt_maturity',debt_amounts=a,total_debt=[fact(100)])
    assert result['value']=='100' and result['details']['buckets']=={'2027':'30','2028':'70'}
    assert calc('debt_maturity',debt_amounts=a,total_debt=[fact(99)])['value'] is None
    a[1].item='TL'
    assert calc('debt_maturity',debt_amounts=a,total_debt=[fact(100)])['value'] is None


def test_portfolio_currency_date_and_duplicate_assets():
    a=[fact(120,basis='portfolio attributable valuation',item='A'),fact(80,basis='portfolio attributable valuation',item='B')]
    assert calc('portfolio_valuation',asset_values=a)['value']=='200'
    a[1].currency='USD'
    assert 'currency' in calc('portfolio_valuation',asset_values=a)['gaps'][0]
    a[1].currency='SGD';a[1].item='A'
    assert calc('portfolio_valuation',asset_values=a)['value'] is None


def test_capitalisation_is_not_property_yield():
    a=fact(5,'percent',None,basis='disclosed valuation capitalisation rate')
    assert calc('capitalisation_rates',disclosed_valuation_rates=[a])['value']=='5'
    a.proxy=True
    assert calc('capitalisation_rates',disclosed_valuation_rates=[a])['value'] is None


def test_sensitivity_requires_complete_basis_and_all_debt():
    basis='MAS TTM complete sensitivity'
    values=dict(regulatory_ebitda=[fact(25,basis=basis)],regulatory_interest=[fact(10,basis=basis)])
    assert calc('icr_ebitda_down_10',**values)['value']=='2.25'
    assert calc('icr_rates_up_100bp',**values)['value'] is None
    values['total_debt']=[fact(100,basis=basis)]
    result=calc('icr_rates_up_100bp',**values)
    assert D(result['value'])==D(25)/D(11) or display(D(result['value']))==display(D(25)/D(11))
    assert 'fixed/hedged' in METRICS['icr_rates_up_100bp'].definition
    values['total_debt'][0].basis='floating debt only'
    assert calc('icr_rates_up_100bp',**values)['value'] is None


@pytest.fixture
def pack(database,tmp_path):
    repo=Repository(database);case=make_case(repo,borrower_name='ESR-REIT')
    service=AnalyticsService(repo,tmp_path/'blobs')
    # store helper expects the service's storage root.
    service.storage_root=tmp_path/'blobs'
    files=[('tranche_2/limits_utilisation.xlsx',None,'limits_utilisation'),('tranche_2/covenant_monitoring.xlsx',21,None),
           ('tranche_3/account_conduct.xlsx',17,None),('tranche_2/projections.xlsx',14,None)]
    selected={};documents={}
    for file,cat,suggestion in files:
        path=ROOT/'demo/synthetic'/file
        doc=store(service,case,path.read_bytes(),path.name,catalogue_id=cat,suggestion_id=suggestion,period='2026-10-31')
        documents[path.stem]=doc
        index=service.evidence.index_document(case.id,doc.id)
        selected[path.stem]=[service.evidence.resolve(case.id,r) for r in index.evidence_ids]
    return service,case,selected,documents


def selections(pack):
    service,case,selected,_=pack
    by_sheet=lambda name,sheet: next(s['evidence_id'] for s in selected[name] if s['locator']['sheet']==sheet)
    return [dict(kind='exposure',evidence_ids=[by_sheet('limits_utilisation','Exposure')]),
            dict(kind='covenants',evidence_ids=[by_sheet('covenant_monitoring','Tests')]),
            dict(kind='conduct',evidence_ids=[by_sheet('account_conduct',s) for s in ['Monthly','Events']]),
            dict(kind='projections',evidence_ids=[by_sheet('projections','Forecast')])]


def req(**kw):
    return AnalyticsRequest(period='2026-10-31',scope='Group',reviewed_by='demo-ca',review_note='Offline reviewed fixture mappings',**kw)


def test_actual_pack_gold_persistence_and_citations(pack,database):
    service,case,_,_=pack
    result=service.generate(case.id,req(tables=selections(pack)))
    report=result['computation']['values'];tables={t['kind']:t for t in report['tables']}
    assert all(not t['gaps'] for t in tables.values()),tables
    exp=tables['exposure'];g=GOLD['exposure']
    for k in ('existing','outstanding','proposed','increase','undrawn_existing','existing_utilisation_pct'):
        assert display(D(exp['totals'][k]))==display(D(g[k]))
    assert [D(r['headroom']) for r in tables['covenants']['rows']]==[D(GOLD['covenants'][k]) for k in ('leverage_headroom_pp','icr_headroom_x','drawn_ltv_headroom_pp')]
    for row in tables['conduct']['rows']:
        for key,value in GOLD['conduct'][row['facility']].items(): assert display(D(row[key]))==display(D(str(value)))
        assert row['period_start']==GOLD['conduct']['period_start'] and row['period_end']==GOLD['conduct']['period_end']
        assert row['average_basis']==GOLD['conduct']['average_basis']
    for row in tables['projections']['rows']:
        for key,val in GOLD['projections'][row['year']].items(): assert display(D(row[key]))==display(D(val))
    assert result['computation']['validation_status']=='manual review'
    assert all(v['synthetic'] for v in result['computed_values'] if v['validated'])
    citations=service.repo.list_for_case(s.Citation,case.id)
    assert citations
    for c in citations:
        source=service.evidence.resolve_citation(case.id,c.id)['source']
        assert source['synthetic'] and source['locator']['page_basis']=='normalized worksheet'
    database.commit();database.expunge_all()
    assert service.get(case.id,result['computation']['id'])==result
    with pytest.raises(ValueError,match='append-only'): service.repo.save(service.repo.get(s.Spread,result['computation']['id']))
    other=make_case(service.repo)
    with pytest.raises(ValueError): service.get(other.id,result['computation']['id'])


@pytest.mark.parametrize('kind,workbook,sheet,column,new_value',[
 ('exposure','limits_utilisation','Exposure',4,'999'),
 ('covenants','covenant_monitoring','Tests',4,'999'),
 ('projections','projections','Forecast',3,'999'),
])
def test_source_controls_cannot_replace_computation(pack,kind,workbook,sheet,column,new_value):
    _,case,selected,_=pack
    source=deepcopy(next(s for s in selected[workbook] if s['locator']['sheet']==sheet))
    source['locator']['rows'][5][column]=new_value
    result=compute_table(kind,[source],case)
    assert result['gaps'] and not result['cells']


@pytest.mark.parametrize('mutation',['duplicate','missing_month','missing_events','overlap','bad_date','coverage','cure_date'])
def test_conduct_missing_duplicate_dates_and_overlap(pack,mutation):
    _,case,selected,_=pack
    sources=deepcopy([s for s in selected['account_conduct'] if s['locator']['sheet'] in ('Monthly','Events')])
    monthly=next(s for s in sources if s['locator']['sheet']=='Monthly')['locator']['rows']
    events=next(s for s in sources if s['locator']['sheet']=='Events')['locator']['rows']
    if mutation=='duplicate': monthly.append(monthly[5])
    if mutation=='missing_month': monthly.pop(5)
    if mutation=='missing_events': sources=[s for s in sources if s['locator']['sheet']=='Monthly']
    if mutation=='overlap':
        row=deepcopy(events[5]);row[2]='2026-06-15 00:00:00';row[3]='2026-06-16 00:00:00';row[6]='Separate overlapping excess';events.append(row)
    if mutation=='bad_date': events[5][3]='2026-06-13 00:00:00'
    if mutation=='coverage': events[3][0]=events[3][0].replace('1 Nov 2025','1 Dec 2025')
    if mutation=='cure_date': events[5][5]='2026-06-01 00:00:00'
    result=compute_table('conduct',sources,case)
    if mutation=='overlap':
        assert not result['gaps'];row=next(r for r in result['rows'] if r['facility']=='RCF-01')
        assert row['excess_count']=='2' and row['excess_days']=='3'
    else: assert result['gaps'] and not result['cells']


def test_missing_source_not_nil_or_satisfactory(pack):
    service,case,_,_=pack
    result=service.generate(case.id,req())['computation']['values']
    assert all(t['gaps'] for t in result['tables'])
    new=make_case(service.repo,case_type='new',existing_client=False,new_to_bank=True)
    result=service.generate(new.id,req())['computation']['values']
    tables={t['kind']:t for t in result['tables']}
    assert tables['exposure']['case_input']['new_to_bank'] and tables['conduct']['status'].startswith('Not applicable')
    assert tables['covenants']['gaps']


def test_source_binding_token_context_case_and_integrity(pack):
    service,case,_,_=pack
    text='SYNTHETIC DEMO DATA\nGroup 2026-10-31 MAS Appendix 6 reported\nMAS Interest Coverage Ratio 2.6 times\n'
    doc=store(service,case,text.encode(),'operational.txt',catalogue_id=4,period='2026-10-31')
    index=service.evidence.index_document(case.id,doc.id)
    binding=Binding(evidence_id=index.evidence_ids[0],quote='MAS Interest Coverage Ratio 2.6 times',token='2.6',unit='times',
                    period='2026-10-31',scope='Group',basis='MAS Appendix 6 reported',context_quote='Group 2026-10-31 MAS Appendix 6 reported')
    inp=dict(interest_coverage=dict(bindings={'regulatory_icr':[binding.model_dump(mode='json')]}))
    result=service.generate(case.id,req(metrics=inp))
    icr=next(m for m in result['computation']['values']['metrics'] if m['metric']=='interest_coverage')
    assert icr['value']=='2.6' and icr['synthetic'] and icr['thresholds'][0]['headroom']=='1.1'
    for changes in [dict(token='6'),dict(quote='ICR 99'),dict(period='2024-10-31'),dict(scope='Trust')]:
        with pytest.raises(ValueError): service.binding(case.id,binding.model_copy(update=changes),{})
    other=make_case(service.repo)
    with pytest.raises(ValueError): service.binding(other.id,binding,{})
    Path(doc.storage_path).write_text('tampered')
    with pytest.raises(ValueError,match='integrity'):service.binding(case.id,binding,{})


def test_validated_b09_consumption_and_proxy_boundary(synthetic):
    spreading,case,_,request,_,_,_=synthetic
    set_full(synthetic)
    spread=spreading.generate(case.id,request)
    service=AnalyticsService(spreading.repo,spreading.storage_root)
    asset=next(v for v in spread['computed_values'] if v['metric']=='total_assets' and v['period']=='2025')
    request=AnalyticsRequest(period='2025',scope='Group',reviewed_by='ca',review_note='Verified B09 mappings',metrics={
        'total_assets':{'spread_value_ids':{'total_assets':[asset['id']]}}})
    result=service.generate(case.id,request)
    assert next(m for m in result['computation']['values']['metrics'] if m['metric']=='total_assets')['value']=='1000000'
    result=service.generate(case.id,request.model_copy(update={'metrics':{'interest_coverage':request.metrics['total_assets']}}))
    assert next(m for m in result['computation']['values']['metrics'] if m['metric']=='interest_coverage')['value'] is None


def test_old_pin_unchanged_and_unverified_rules_fail_closed():
    raw=load_team('fig').model_dump(mode='json',exclude_unset=True)
    raw['analytics']['sets']['reit']['metrics'][0]['thresholds'][0]['verification']='pending B10'
    config=TeamConfig.model_validate(raw)
    assert config.content_hash==TeamConfig.model_validate(config.model_dump(mode='json',exclude_unset=True)).content_hash
    result=calculate(config.analytics.sets['reit'].metrics[0],{'regulatory_leverage':[fact(50,'percent',None,basis='MAS Appendix 6 reported')]},'2026-10-31','Group')
    assert result['value'] is None and result['thresholds']==[]


def test_analytics_api(pack,database):
    service,case,_,_=pack
    database.commit()
    from sqlalchemy.orm import sessionmaker
    sessions=sessionmaker(bind=database.bind,expire_on_commit=False)
    app=create_app(sessions=sessions,storage_root=service.storage_root)
    status,body=http_request(app,'POST',f'/cases/{case.id}/analytics',req(tables=selections(pack)).model_dump_json().encode())
    assert status==200,body
    status,saved=http_request(app,'GET',f'/cases/{case.id}/analytics/{body["computation"]["id"]}')
    assert status==200 and saved==body
    status,listing=http_request(app,'GET',f'/cases/{case.id}/analytics')
    assert status==200 and len(listing)==1
    status,listing=http_request(app,'GET',f'/cases/{case.id}/spreads')
    assert status==200 and listing==[]
    status,_=http_request(app,'GET',f'/cases/{case.id}/spreads/{body["computation"]["id"]}')
    assert status==422


def test_actual_public_disclosures_keep_url_date_scope_and_no_synthetic(pack):
    from datetime import datetime, timezone
    service,case,_,_=pack
    manifest=yaml.safe_load((ROOT/'demo/public_pack/esr-reit/manifest.yaml').read_text())
    item=next(d for d in manifest['documents'] if d['id']=='esr-ar2025')
    path=ROOT/'demo/public_pack/esr-reit'/item['file']
    doc=store(service,case,path.read_bytes(),path.name,catalogue_id=4,period='FY2025',synthetic=False,origin='public',url=item['url'],
        retrieved_at=datetime(2026,11,10,tzinfo=timezone.utc),intake={'cached':True})
    index=service.evidence.index_document(case.id,doc.id)
    ref=next(r for r in index.evidence_ids if service.repo.get(s.Evidence,r).page==59)
    source=service.evidence.resolve(case.id,ref)
    context=' '.join(source['excerpt'].split())
    assert len(context)<10000
    bindings={
      'aggregate_leverage':('regulatory_leverage','43.4','percent','MAS Appendix 6 reported'),
      'interest_coverage':('regulatory_icr','2.5','times','MAS Appendix 6 reported'),
      'fixed_rate_share':('reported','68.4','percent','fixed or hedged, non-overlapping'),
      'average_cost_of_debt':('average_cost_of_debt','3.35','percent','reported weighted cost of debt'),
      'weighted_debt_maturity':('weighted_debt_maturity','2.0','years','reported debt maturity'),
    }
    inputs={}
    for metric,(operand,token,unit,basis) in bindings.items():
        inputs[metric]={'bindings':{operand:[dict(evidence_id=ref,quote=context,token=token,unit=unit,
                  period='2025-12-31',scope='ESR-REIT',basis=basis,context_quote=context)]}}
    request=AnalyticsRequest(period='2025-12-31',scope='ESR-REIT',reviewed_by='fixture-review',review_note='Reviewed FY2025 first-column values and source footnotes; comparative/pro-forma excluded',metrics=inputs)
    result=service.generate(case.id,request)
    metrics={m['metric']:m for m in result['computation']['values']['metrics']}
    assert metrics['aggregate_leverage']['value']=='43.4'
    assert metrics['aggregate_leverage']['thresholds'][0]['headroom']=='6.6'
    assert metrics['interest_coverage']['thresholds'][0]['headroom']=='1.0'
    persisted={v['id']:v for v in result['computed_values']}
    headrooms=result['computation']['values']['threshold_values']
    assert len(headrooms)==2
    assert {persisted[v['computed_value_id']]['value'] for v in headrooms}=={'6.6','1.0'}
    assert metrics['fixed_rate_share']['value']=='68.4'
    for metric in inputs:
        assert not metrics[metric]['gaps'] and not metrics[metric]['synthetic']
        provenance=next(iter(metrics[metric]['sources'].values()))['provenance']
        assert provenance['url']==item['url'] and provenance['retrieved_at'].startswith('2026-11-10')
        assert provenance['cached'] and provenance['confirmed_by'] is None and provenance['page']==59
    # Persisted numeric results do not confirm a public document or close financial spread readiness.
    assert service.repo.get(s.Document,doc.id).confirmed_by is None
    from backend.app.services.gaps import GapService
    assert not GapService(service.repo).refresh(case.id).support[7].full


def test_npi_reported_fallback_and_ltv():
    result=calc('npi',reported=[fact('328679000')])
    assert result['value']=='328679000' and result['formula']['op']=='reported'
    basis='secured property LTV'
    result=calc('ltv',secured_debt=[fact(60,basis=basis,synthetic=True)],secured_property_value=[fact(112,basis=basis,synthetic=True)])
    assert result['display']==GOLD['ltv']['proposed_initial_pct'] and result['synthetic']
    assert D(result['value']) < 55
    result=calc('ltv',secured_debt=[fact(60,basis=basis,synthetic=True)],secured_property_value=[fact(104,basis=basis,synthetic=True)])
    assert result['display']==GOLD['ltv']['proposed_revised_pct'] and result['synthetic']
    assert D(result['value']) > 55


def test_all_template_financial_rows_mapped():
    config=load_team('fig')
    # Actual YAML anchors are the exporter contract; category headings carry no values.
    raw=yaml.safe_load((ROOT/'config/teams/fig/template.yaml').read_text())
    mappings=next(v for v in raw.values() if isinstance(v,list) and any(isinstance(x,dict) and x.get('id')=='financials' for x in v))
    labels=next(t['row_labels'] for t in mappings if t['id']=='financials')
    slots={r for m in METRICS.values() for r in m.template_rows}
    assert set(labels)-{'Income','Balance sheet','Capital management','Portfolio'} <= slots


def test_empty_complete_events_proves_zero_only_with_consistent_monthly_peaks(pack):
    _,case,selected,_=pack
    sources=deepcopy([s for s in selected['account_conduct'] if s['locator']['sheet'] in ('Monthly','Events')])
    events=next(s for s in sources if s['locator']['sheet']=='Events')
    events['locator']['rows']=events['locator']['rows'][:5]
    assert compute_table('conduct',sources,case)['gaps']  # RCF monthly peak still has excess.
    monthly=next(s for s in sources if s['locator']['sheet']=='Monthly')
    for row in monthly['locator']['rows'][5:]: row[4]=row[3]
    result=compute_table('conduct',sources,case)
    assert not result['gaps']
    assert all(r['excess_count']=='0' and r['past_due_count']=='0' for r in result['rows'])


def test_changed_source_version_rejected_historical_snapshot_retained(pack):
    service,case,selected,documents=pack
    result=service.generate(case.id,req(tables=selections(pack)))
    old=documents['limits_utilisation']
    newer=store(service,case,Path(old.storage_path).read_bytes(),'new.xlsx',catalogue_id=None,suggestion_id='limits_utilisation',
                period='2026-11-30',supersedes_id=old.id,revision=2)
    with pytest.raises(ValueError,match='current'):
        service.generate(case.id,req(tables=selections(pack)))
    assert service.get(case.id,result['computation']['id'])==result


def test_bad_mapping_rolls_back_api_and_cross_case(pack,database):
    service,case,selected,_=pack
    database.commit()
    from sqlalchemy.orm import sessionmaker
    sessions=sessionmaker(bind=database.bind,expire_on_commit=False)
    app=create_app(sessions=sessions,storage_root=service.storage_root)
    status,_=http_request(app,'POST',f'/cases/{case.id}/analytics',req(tables=[{'kind':'conduct','evidence_ids':[selected['limits_utilisation'][0]['evidence_id']]}]).model_dump_json().encode())
    assert status==422 and service.repo.list_for_case(s.Spread,case.id)==[]
    other=make_case(service.repo);database.commit()
    status,_=http_request(app,'POST',f'/cases/{other.id}/analytics',req(tables=selections(pack)).model_dump_json().encode())
    assert status==404


def test_old_case_hash_without_b10_fields_is_stable():
    config=load_team('fig');raw=config.model_dump(mode='json',exclude_unset=True)
    old_fields={'id','name','unit','formula','reported_fallback','definition','thresholds'}
    raw['analytics']['sets']['reit']['metrics']=raw['analytics']['sets']['reit']['metrics'][:10]
    for m in raw['analytics']['sets']['reit']['metrics']:
        for key in list(m):
            if key not in old_fields: m.pop(key)
    old=TeamConfig.model_validate(raw)
    assert old.model_dump(mode='json',exclude_unset=True)==raw
    assert old.content_hash==TeamConfig.model_validate(old.model_dump(mode='json',exclude_unset=True)).content_hash


def test_alternate_config_uses_same_engine():
    metric=METRICS['dpu'].model_copy(update={'id':'alternate_ratio','name':'Alternate measure','multiplier':'10','template_rows':[]})
    result=calculate(metric,{'distributions':[fact(2)],'eligible_units':[fact(4,'units',None)]},'2026-10-31','Group')
    assert result['metric']=='alternate_ratio' and result['value']=='5.0'


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity','-','1e99','abc','1234567890123456789012345678901'])
def test_nonnumeric_or_nonfinite_source_is_not_zero(value):
    from backend.app.analytics.engine import number
    with pytest.raises(ValueError):number(value)


def test_adverse_reported_values_are_outside_not_missing():
    result=calc('interest_coverage',regulatory_icr=[fact('-1','times',None,basis='MAS Appendix 6 reported')])
    assert result['value']=='-1' and result['thresholds'][0]['headroom']=='-2.5'
    result=calc('aggregate_leverage',regulatory_leverage=[fact('110','percent',None,basis='MAS Appendix 6 reported')])
    assert result['value']=='110' and result['thresholds'][0]['headroom']=='-60'


def test_ratio_unit_suffix_is_not_a_numeric_substring(pack):
    service,case,_,_=pack
    doc=store(service,case,b'SYNTHETIC DEMO DATA\nGroup 2026-10-31\nMAS Interest Coverage Ratio 2.6x', 'ratio.txt',catalogue_id=4,period='2026-10-31')
    index=service.evidence.index_document(case.id,doc.id)
    b=Binding(evidence_id=index.evidence_ids[0],quote='MAS Interest Coverage Ratio 2.6x',token='2.6',unit='times',period='2026-10-31',scope='Group',basis='MAS Appendix 6 reported',context_quote='Group 2026-10-31')
    assert service.binding(case.id,b,{}).value==D('2.6')
    with pytest.raises(ValueError):service.binding(case.id,b.model_copy(update={'token':'6'}),{})
