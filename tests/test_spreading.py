"""B09 offline regressions, using saved public PDFs and labelled synthetic tables."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

import fitz
import pdfplumber
import pytest

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.extraction_agent.contracts import Extraction, SpreadProfile
from backend.app.extraction_agent.orchestrator import messages, run_extraction_agent
from backend.app.extraction_agent.pdf_quality import apply_text_quality_gate
from backend.app.extraction_agent.validator import number, validate_extraction
from backend.app.llm.client import MockProvider, request_key
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.gaps import GapService
from backend.app.services.spreading import SpreadRequest, SpreadingService
from backend.app.team_config import load_team, TeamConfig
from test_intake import make_case, request

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests/fixtures/spreading'


def register(provider, action, sources, profile, response, current=None, targets=None, issues=None, stop='end_turn'):
    key = request_key(messages(action, sources, profile, current, targets, issues), 12000, 0, 60)
    provider.fixtures[key] = dict(text=json.dumps(response), stop_reason=stop, content=[])


def bind(response, ids):
    data = deepcopy(response)
    for table in data['tables']:
        table['evidence_id'] = ids[table['evidence_id']]
        table['currency_evidence_id'] = ids[table['currency_evidence_id']]
    return data


def store(service, case, content, filename, **changes):
    digest = sha256(content).hexdigest()
    path = service.storage_root / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return service.repo.save(s.Document(**(dict(case_id=case.id, entity=case.borrower_name,
        catalogue_id=4, period='FY2025', original_filename=filename, content_hash=digest,
        storage_path=str(path), origin='upload', synthetic=True) | changes)))


@pytest.fixture
def synthetic(database, tmp_path):
    repo = Repository(database)
    case = make_case(repo)
    provider = MockProvider()
    service = SpreadingService(repo, tmp_path / 'blobs', provider)
    # Independently balanced, signed values. Every source page carries the label.
    values = dict(total_assets=['1000','900'],total_liabilities=['600','550'],net_assets=['400','350'],
        property_income=['100','90'],property_expenses=['(30)','(20)'],npi=['70','70'],
        profit_before_tax=['50','40'],tax=['(5)','(4)'],profit_after_tax=['45','36'],
        cf_profit_before_tax=['50','40'],cf_operating=['60','50'],cf_investing=['(10)','(20)'],
        cf_financing=['(20)','(10)'],cf_change=['30','20'],cf_open=['100','80'],cf_fx=['(2)','0'],cf_close=['128','100'])
    profile = load_team('fig').analytics.spreading['reit_core']
    tables, pages = [], []
    for stmt in ['balance_sheet','income_statement','cash_flow']:
        rows = [dict(label=a.aliases[0],note='',values=values[code],quote=' '.join([a.aliases[0],*values[code]]))
                for code,a in profile.accounts.items() if a.statement==stmt]
        pages.append('SYNTHETIC DEMO DATA\nDemo REIT financial statements\nGroup\n2025 2024\nSGD thousands\n' + '\n'.join(r['quote'] for r in rows))
        tables.append(dict(statement=stmt,evidence_id=f'page:{len(pages)}',columns=[dict(period=p,scope='Group') for p in ['2025','2024']],header_quote='2025 2024',scope_quote='Group',unit_quote='SGD thousands',unit='SGD thousands',currency='SGD',currency_evidence_id=f'page:{len(pages)}',currency_quote='SGD thousands',rows=rows))
    doc = store(service,case,'\f'.join(pages).encode(),'financial-statements.txt')
    index = service.evidence.index_document(case.id,doc.id)
    ids = {f'page:{repo.get(s.Evidence,e).page}':e for e in index.evidence_ids}
    response = bind(dict(tables=tables),ids)
    req = SpreadRequest(profile='reit_core',evidence_ids=list(ids.values()),periods=['2025','2024'],scope='Group')
    _,profile,sources,_ = service.prepare(case.id,req)
    return service,case,doc,req,profile,sources,response


def set_full(env, response=None, missing=None):
    service,case,doc,req,profile,sources,good = env
    full = response if response is not None else good
    register(service.provider,'full',sources,profile,full)
    register(service.provider,'missing_rows',sources,profile,missing or {'tables':[]},full)


def set_repair(env, current, repair):
    service,_,_,req,profile,sources,_ = env
    report = validate_extraction(Extraction.model_validate(current),sources,profile,req.periods,req.scope)
    from backend.app.extraction_agent.orchestrator import targets_for
    register(service.provider,'targeted_fix',sources,profile,repair,current,targets_for(report),report['issues'])


def test_valid_round_trip_citations_exact_decimal_and_readiness(synthetic, database):
    service,case,doc,req,profile,sources,good = synthetic
    set_full(synthetic)
    result = service.generate(case.id,req)
    spread = result['spread']
    assert spread['validation_status']=='valid'
    assert spread['values']['result']['iterations']==1
    values=result['computed_values']
    assert len(values)==34 and all(v['validated'] and v['synthetic'] for v in values)
    assert next(v['value'] for v in values if v['metric']=='npi' and v['period']=='2025')=='70000'
    assert len(spread['values']['result']['validation']['checks_passed'])==12
    for citation in service.repo.list_for_case(s.Citation,case.id):
        resolved=service.evidence.resolve_citation(case.id,citation.id)
        assert resolved['source']['document_id']==doc.id
        assert resolved['source']['synthetic']
    assert GapService(service.repo).refresh(case.id).support[7].full
    database.commit(); database.expunge_all()
    assert service.get(case.id,spread['id'])==result
    with pytest.raises(ValueError,match='append-only'):
        service.repo.save(service.repo.get(s.Spread,spread['id']))


def test_missing_rows_are_added_then_revalidated(synthetic):
    service,case,_,req,_,_,good=synthetic
    incomplete=deepcopy(good)
    removed=incomplete['tables'][0]['rows'].pop()
    additions={'tables':[dict(deepcopy(incomplete['tables'][0]),rows=[removed])]}
    set_full(synthetic,incomplete,additions)
    result=service.generate(case.id,req)
    assert result['spread']['validation_status']=='valid'
    assert result['spread']['values']['result']['iterations']==1


def test_targeted_fix_only_failed_statement(synthetic):
    service,case,_,req,_,_,good=synthetic
    bad=deepcopy(good);bad['tables'][0]['rows'][0]['values'][0]='999'
    set_full(synthetic,bad)
    set_repair(synthetic,bad,{'tables':[good['tables'][0]]})
    result=service.generate(case.id,req)['spread']
    assert result['validation_status']=='valid'
    history=result['values']['result']['history']
    assert len(history)==2 and history[1]['targets']==['balance_sheet']
    assert history[0]['tables'][1:]==history[1]['tables'][:2]


def test_third_iteration_deterministic_fallback(synthetic):
    service,case,_,req,_,_,good=synthetic
    bad=deepcopy(good);bad['tables'][0]['rows'].pop()
    set_full(synthetic,bad);set_repair(synthetic,bad,{'tables':[]})
    result=service.generate(case.id,req)['spread']
    assert result['validation_status']=='valid'
    assert result['values']['result']['iterations']==3
    assert len(service.provider.usage)==3  # full, missing rows, targeted; fallback is Python.


def test_bad_source_arithmetic_never_repaired_by_model_or_accepted(synthetic):
    service,case,doc,req,profile,sources,good=synthetic
    # Alter source and indexed fixture together: the arithmetic must catch a real source inconsistency.
    for source in sources.values():
        source['excerpt']=source['excerpt'].replace('Total assets 1000 900','Total assets 998 900')
    bad=deepcopy(good);row=bad['tables'][0]['rows'][0]
    row['values'][0]='998';row['quote']='Total assets 998 900'
    register(service.provider,'full',sources,profile,bad)
    register(service.provider,'missing_rows',sources,profile,{'tables':[]},bad)
    report=validate_extraction(Extraction.model_validate(bad),sources,profile,req.periods,req.scope)
    assert any(i.get('residual')=='-2000' for i in report['issues'])
    from backend.app.extraction_agent.orchestrator import targets_for
    register(service.provider,'targeted_fix',sources,profile,{'tables':[]},bad,targets_for(report),report['issues'])
    result=run_extraction_agent(service.provider,sources,profile,req.periods,req.scope)
    assert result['iterations']==3 and result['validation']['status']=='invalid'


@pytest.mark.parametrize('mutation', ['number','period','scope','unit','currency','unknown_source','quote','duplicate','unknown_mapping','dash','wrong_sign'])
def test_validation_rejects_bad_or_incomplete_evidence(synthetic,mutation):
    _,_,_,req,profile,sources,good=synthetic
    bad=deepcopy(good);table=bad['tables'][0];row=table['rows'][0]
    if mutation=='number':row['values'][0]='123456'
    elif mutation=='period':table['columns'][0]['period']='2024'
    elif mutation=='scope':table['columns'][0]['scope']='Trust'
    elif mutation=='unit':table['unit']='SGD'
    elif mutation=='currency':table['currency']='USD'
    elif mutation=='unknown_source':table['evidence_id']='unknown'
    elif mutation=='quote':row['quote']='invented quote'
    elif mutation=='duplicate':table['rows'].append(deepcopy(row))
    elif mutation=='unknown_mapping':row['label']='AI-approved capacity'
    elif mutation=='dash':
        source=sources[table['evidence_id']];source['excerpt']=source['excerpt'].replace(row['quote'],'Total assets – 900')
        row['quote']='Total assets – 900';row['values'][0]='–'
    else:row['values'][0]='(1000)'
    report=validate_extraction(Extraction.model_validate(bad),sources,profile,req.periods,req.scope)
    assert report['status']!='valid' and report['issues']


def test_missing_fixture_is_persisted_invalid_not_live_fallback(synthetic):
    service,case,_,req,_,_,_=synthetic
    result=service.generate(case.id,req)
    assert result['spread']['validation_status']=='invalid'
    assert any('missing mock fixture' in i for i in result['spread']['issues'])
    assert result['computed_values']==[]
    assert not GapService(service.repo).refresh(case.id).support[7].usable


def test_missing_completeness_fixture_invalidates_even_balanced_tables(synthetic):
    service,case,_,req,profile,sources,good=synthetic
    register(service.provider,'full',sources,profile,good)
    result=service.generate(case.id,req)
    assert result['spread']['validation_status']=='invalid'
    assert all(not v['validated'] for v in result['computed_values'])


def test_targeted_response_cannot_overwrite_passing_statements(synthetic):
    service,case,_,req,_,_,good=synthetic
    bad=deepcopy(good);bad['tables'][0]['rows'].pop()
    set_full(synthetic,bad);set_repair(synthetic,bad,good)
    result=service.generate(case.id,req)['spread']
    assert result['validation_status']=='invalid'
    assert any('response rejected' in i for i in result['issues'])


def test_source_selection_boundaries(synthetic):
    service,case,doc,req,_,_,_=synthetic
    other=make_case(service.repo)
    with pytest.raises(ValueError):service.prepare(other.id,req)
    with pytest.raises(ValueError):service.prepare(case.id,req.model_copy(update={'periods':['2026']}))
    with pytest.raises(ValueError):service.prepare(case.id,req.model_copy(update={'periods':['2025','2025']}))
    with pytest.raises(ValueError):service.prepare(case.id,req.model_copy(update={'profile':'unknown'}))
    with pytest.raises(ValueError):service.prepare(case.id,req.model_copy(update={'scope':'Secured property'}))
    service.repo.save(doc.model_copy(update={'conflict_status':'pending'}))
    with pytest.raises(ValueError,match='current'):service.prepare(case.id,req)


def test_newer_source_removes_old_spread_readiness_but_keeps_history(synthetic):
    service,case,doc,req,_,_,_=synthetic
    set_full(synthetic);result=service.generate(case.id,req)
    store(service,case,b'SYNTHETIC DEMO DATA\nnew report','new.txt',period='FY2026',revision=2,supersedes_id=doc.id)
    assert not GapService(service.repo).refresh(case.id).support[7].usable
    assert service.get(case.id,result['spread']['id'])==result
    with pytest.raises(ValueError,match='current'):service.generate(case.id,req)


def test_corrupt_source_blocks_generation(synthetic):
    service,case,doc,req,_,_,_=synthetic
    set_full(synthetic);Path(doc.storage_path).write_bytes(b'changed')
    with pytest.raises(ValueError,match='integrity'):service.generate(case.id,req)
    assert not service.repo.list_for_case(s.Spread,case.id)


def test_live_provider_rejected_before_any_call(synthetic):
    service,case,_,req,_,_,_=synthetic
    class Live:
        def get_provider_info(self):return {'provider':'live'}
        def chat_raw(self,*a,**k):raise AssertionError('must never call live')
    service.provider=Live()
    with pytest.raises(ValueError,match='mock providers only'):service.generate(case.id,req)


@pytest.mark.parametrize('raw,expected',[('1,234.50','1234.50'),('(0.25)','-0.25'),('0','0'),('–',None)])
def test_numeric_tokens(raw,expected):
    result=number(raw)
    assert (str(result) if result is not None else None)==expected


@pytest.mark.parametrize('raw',['1,23','NaN','Infinity','1e4','--1','(-2)','1.2.3'])
def test_invalid_numeric_tokens(raw):
    with pytest.raises(ValueError):number(raw)


def test_actual_esr_saved_report_public_confirmation_and_group_columns(database,tmp_path):
    repo=Repository(database);case=make_case(repo,borrower_name='ESR-REIT')
    provider=MockProvider();service=SpreadingService(repo,tmp_path/'blobs',provider)
    import yaml
    manifest=yaml.safe_load((ROOT/'demo/public_pack/esr-reit/manifest.yaml').read_text())
    entry=next(e for e in manifest['documents'] if e['file']=='annual-report-2025.pdf')
    # Same saved public document and provenance; no network or synthetic relabelling.
    doc=store(service,case,(ROOT/'demo/public_pack/esr-reit/annual-report-2025.pdf').read_bytes(),'annual-report-2025.pdf',
        origin='public',synthetic=False,url=entry['url'],retrieved_at=datetime.fromisoformat(str(entry['retrieved_at']).replace('Z','+00:00')).replace(tzinfo=timezone.utc))
    index=service.evidence.index_document(case.id,doc.id)
    ids={f'page:{repo.get(s.Evidence,e).page}':e for e in index.evidence_ids}
    response=bind(json.loads((FIX/'esr-core-response.json').read_text()),ids)
    req=SpreadRequest(profile='reit_core',evidence_ids=[ids[f'page:{p}'] for p in [127,128,155,156,162]],periods=['2025','2024'],scope='Group')
    _,profile,sources,_=service.prepare(case.id,req)
    register(provider,'full',sources,profile,response)
    register(provider,'missing_rows',sources,profile,{'tables':[]},response)
    result=service.generate(case.id,req)
    assert result['spread']['validation_status']=='valid',result['spread']['issues']
    values={(v['metric'],v['period']):v for v in result['computed_values']}
    assert values['total_assets','2025']['value']=='5864836000'
    assert values['npi','2025']['value']=='328679000'
    assert values['cf_close','2025']['value']=='45928000'
    assert all(not v['synthetic'] and v['scope']=='Group' for v in values.values())
    assert not GapService(repo).refresh(case.id).support[7].full
    repo.save(doc.model_copy(update={'confirmed_by':'CA','confirmed_at':datetime.now(timezone.utc)}))
    assert GapService(repo).refresh(case.id).support[7].full
    assert all(src['url']==doc.url and src['retrieved_at'] for src in result['spread']['values']['source_register'].values())


def test_dbs_actual_pdfplumber_loss_and_original_region_mapping(database,tmp_path):
    path=FIX/'dbs-annual-report-2025.pdf';content=path.read_bytes()
    assert sha256(content).hexdigest()=='062223b76be563833610f1f14232c6f754e8ec9931c9e2ad1650d1218180665f'
    with pdfplumber.open(path) as pdf:bad=pdf.pages[58].extract_text()
    assert '897,488' not in bad
    result=apply_text_quality_gate(content,59,bad)
    assert result['method']=='pymupdf' and result['pymupdf_count']>=2*result['candidate_count']
    assert '897,488' in result['text'] and result['page']==59
    repo=Repository(database);case=make_case(repo,borrower_name='DBS Group Holdings Ltd')
    service=SpreadingService(repo,tmp_path/'blobs',MockProvider())
    doc=store(service,case,content,path.name,synthetic=False,
        intake={'page_references':[{'pdf_pages':[59],'printed_pages':['114–115']}]})
    index=service.evidence.index_document(case.id,doc.id)
    evidence=next(repo.get(s.Evidence,e) for e in index.evidence_ids if repo.get(s.Evidence,e).page==59)
    with fitz.open(path) as pdf:bounds=pdf[58].rect; bbox=[0,0,bounds.width/2,bounds.height]
    region=service.evidence.cite_pdf_region(case.id,evidence.id,bbox)
    assert region['page']==59 and region['parent_evidence_id']==evidence.id
    assert region['printed_page']=='114–115'
    assert '897,488' in region['excerpt'] and '828,572' in region['excerpt']
    assert 'Consolidated statement' not in region['excerpt']
    assert service.evidence.resolve(case.id,region['evidence_id'])==region


def test_profile_validation_and_legacy_pin(synthetic):
    service,case,_,_,_,_,_=synthetic
    old=deepcopy(case.config_snapshot);old['analytics'].pop('spreading')
    legacy=TeamConfig.model_validate(old)
    assert 'spreading' not in legacy.model_dump(exclude_unset=True)['analytics']
    assert not legacy.analytics.spreading
    bad=deepcopy(case.config_snapshot);bad['analytics']['spreading']['reit_core']['equations'][0]['terms']['invented']=1
    with pytest.raises(ValueError):TeamConfig.model_validate(bad)
    bad=deepcopy(case.config_snapshot);bad['analytics']['spreading']['reit_core']['units']['SGD']='NaN'
    with pytest.raises(ValueError):TeamConfig.model_validate(bad)


def test_api_persistence_and_failure_contract(tmp_path):
    engine,sessions=create_database(tmp_path/'api.sqlite')
    provider=MockProvider()
    with sessions() as session:
        repo=Repository(session);case=make_case(repo)
        service=SpreadingService(repo,tmp_path/'blobs',provider)
        doc=store(service,case,b'SYNTHETIC DEMO DATA\nGroup\n2025 2024\nSGD thousands','report.txt')
        index=service.evidence.index_document(case.id,doc.id);session.commit()
    app=create_app(sessions=sessions,storage_root=tmp_path/'blobs',provider=provider)
    payload=dict(profile='reit_core',evidence_ids=index.evidence_ids,periods=['2025'],scope='Group')
    response=request(app,'POST',f'/cases/{case.id}/spreads',json.dumps(payload).encode())
    assert response[0]==200,response
    result=response[1];sid=result['spread']['id']
    assert result['spread']['validation_status']=='invalid'
    assert request(app,'GET',f'/cases/{case.id}/spreads/{sid}')[0]==200
    assert len(request(app,'GET',f'/cases/{case.id}/spreads')[1])==1
    engine.dispose()


def test_comparative_only_spread_does_not_close_current_gap(synthetic):
    service,case,_,req,_,_,_=synthetic
    set_full(synthetic)
    result=service.generate(case.id,req.model_copy(update={'periods':['2024']}))
    assert result['spread']['validation_status']=='valid'
    assert not GapService(service.repo).refresh(case.id).support[7].usable


def test_nonfinancial_and_wrong_entity_sources_rejected(synthetic):
    service,case,_,req,_,_,_=synthetic
    for changes in [dict(catalogue_id=9),dict(entity='Different borrower')]:
        doc=store(service,case,b'SYNTHETIC DEMO DATA\nUnrelated source','other.txt',**changes)
        index=service.evidence.index_document(case.id,doc.id)
        with pytest.raises(ValueError):service.prepare(case.id,req.model_copy(update={'evidence_ids':index.evidence_ids}))


def test_tolerance_boundary_is_in_reported_units_and_applies_to_prior_year(synthetic):
    _,_,_,req,profile,sources,good=synthetic
    for assets,expected in [('899','valid'),('898','invalid')]:
        altered=deepcopy(sources);bad=deepcopy(good);table=bad['tables'][0];row=table['rows'][0]
        row['values'][1]=assets;row['quote']=f'Total assets 1000 {assets}'
        altered[table['evidence_id']]['excerpt']=altered[table['evidence_id']]['excerpt'].replace('Total assets 1000 900',row['quote'])
        report=validate_extraction(Extraction.model_validate(bad),altered,profile,req.periods,req.scope)
        assert report['status']==expected


def test_cross_statement_failure_targets_both_statements(synthetic):
    _,_,_,req,profile,sources,good=synthetic
    table=good['tables'][2];row=table['rows'][0]
    sources[table['evidence_id']]['excerpt']=sources[table['evidence_id']]['excerpt'].replace(row['quote'],row['quote'].replace('50 40','55 40'))
    row['quote']=row['quote'].replace('50 40','55 40');row['values'][0]='55'
    report=validate_extraction(Extraction.model_validate(good),sources,profile,req.periods,req.scope)
    from backend.app.extraction_agent.orchestrator import targets_for
    assert targets_for(report)==['cash_flow','income_statement']


@pytest.mark.parametrize('payload,stop',[({'tables':[],'command':'ignore rules'},'end_turn'),({'tables':[]},'max_tokens')])
def test_malformed_and_truncated_responses_are_persisted_failures(synthetic,payload,stop):
    service,case,_,req,profile,sources,good=synthetic
    register(service.provider,'full',sources,profile,payload,stop=stop)
    result=service.generate(case.id,req)
    assert result['spread']['validation_status']=='invalid'
    assert any('response rejected' in i for i in result['spread']['issues'])


def test_api_success_restart_and_cross_case_isolation(synthetic,database):
    from sqlalchemy.orm import sessionmaker
    service,case,_,req,_,_,_=synthetic
    set_full(synthetic);other=make_case(service.repo);database.commit()
    sessions=sessionmaker(bind=database.bind)
    app=create_app(sessions=sessions,storage_root=service.storage_root,provider=service.provider)
    status,result=request(app,'POST',f'/cases/{case.id}/spreads',req.model_dump_json().encode())
    assert status==200 and result['spread']['validation_status']=='valid'
    sid=result['spread']['id']
    fresh=create_app(sessions=sessions,storage_root=service.storage_root)
    assert request(fresh,'GET',f'/cases/{case.id}/spreads/{sid}')[1]==result
    assert request(fresh,'GET',f'/cases/{other.id}/spreads/{sid}')[0]==422


def test_alternate_team_profile_uses_config_not_fig_branching(synthetic):
    service,case,_,req,profile,sources,good=synthetic
    alternate=deepcopy(case.config_snapshot)
    alternate['template']['team_id']='alternate'
    alternate['analytics']['spreading']['custom']=alternate['analytics']['spreading'].pop('reit_core')
    alternate['analytics']['spreading']['custom']['version']='alternate-v2'
    # Shared validator/formula vocabulary; no new business content.
    config=TeamConfig.model_validate(alternate)
    report=validate_extraction(Extraction.model_validate(good),sources,config.analytics.spreading['custom'],req.periods,req.scope)
    assert report['status']=='valid'


def test_source_substring_is_not_numeric_support(synthetic):
    _,_,_,_,profile,sources,good=synthetic
    bad=deepcopy(good);table=bad['tables'][0]
    table['columns']=[table['columns'][0]];table['header_quote']='2025';table['rows']=table['rows'][:1]
    row=table['rows'][0];row['values']=['100'];row['quote']='Total assets 100'
    report=validate_extraction(Extraction.model_validate(bad),sources,profile,['2025'],'Group')
    assert any(i['check']=='source_row' for i in report['issues'])


def test_partial_row_cannot_mislabel_group_column_as_trust(synthetic):
    _,_,_,_,profile,sources,good=synthetic
    bad=deepcopy(good);table=bad['tables'][0]
    source=sources[table['evidence_id']]
    source['excerpt']=source['excerpt'].replace('Group','Group Trust').replace('2025 2024','2025 2024 2025 2024')
    for row in table['rows']:
        source['excerpt']=source['excerpt'].replace(row['quote'],row['quote']+' 500 400')
    table['scope_quote']='Trust'
    for col in table['columns']:col['scope']='Trust'
    report=validate_extraction(Extraction.model_validate(bad),sources,profile,['2025','2024'],'Trust')
    assert report['status']!='valid'
    assert any(i['check']=='source_row' for i in report['issues'])


def test_cross_statement_mixed_currency_is_not_summed(synthetic):
    _,_,_,req,profile,sources,good=synthetic
    profile=profile.model_copy(deep=True)
    profile.currencies['USD']=['USD']
    table=good['tables'][2]
    sources[table['currency_evidence_id']]['excerpt']+='\nUSD\n'
    table['currency']='USD';table['currency_quote']='USD'
    report=validate_extraction(Extraction.model_validate(good),sources,profile,req.periods,req.scope)
    assert report['status']=='invalid'
    assert any('Mixed currencies' in i['message'] for i in report['issues'])
