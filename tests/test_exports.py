"""B18 offline template exports and repeat-structure preservation."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest

from backend.app import schemas as s
from backend.app.exports import ExportService, ExportRequest, ExportConflict
from backend.app.exports.word import TemplateCopy, repeat_rows, facility_columns, rows, cells, W
from backend.app.services.templates import parse_template
from backend.app.team_config import load_team
from test_drafting import setup, generate, ROOT
from test_synthesis import prerequisites


def service_for(setup, tmp_path):
    drafting,case=setup
    return ExportService(drafting.repo,tmp_path/'blobs',tmp_path/'templates',tmp_path/'exports'),case


def xml(content):
    return ET.fromstring(ZipFile(BytesIO(content)).read('word/document.xml'))


def text(content):
    return '\n'.join(t.text or '' for t in xml(content).iter(W+'t'))


def export(service,case):
    manifest,_=service.prepare(case.id)
    return service.create(case.id,ExportRequest(actor='demo-ca',expected_preview_token=manifest['preview_token']))


@pytest.mark.slow
def test_demo_full_export(setup,tmp_path,database):
    drafting,case=setup
    prerequisites(drafting,case)
    generate(drafting,case,14,ca_position='Support only subject to revised funding and legal evidence. Do not submit yet.')
    service,_=service_for(setup,tmp_path)
    artifact=export(service,case)
    content=service.content(case.id,artifact.id)
    body=text(content)
    for phrase in ['SYNTHETIC','DRAFT','75','46','n.m.','43.4','2.5','6.6','DEMO-G4',
                   'Property-only repayment is insufficient','CA-stated position','Do not submit yet.',
                   'CA confirmation pending','[GAP]','annual-report-2025.pdf','p59',
                   'Existing limit utilisation','maximum delay']:
        assert phrase in body,phrase
    for phrase in ['Borrower A','Borrower B','[Tenant 1]','100.0',"[Moody's]",'DD/MM/YYYY','CAS Approved on MMMYY']:
        assert phrase not in body,phrase
    assert len(artifact.manifest['sections'])==14
    assert 'Date of classification (MMMYY)' in body
    assert 'Prepared by: Credit Analyst' in body
    assert '[GAP: records not supplied]' not in body
    assert set(artifact.manifest['source_markers'].values())==set(artifact.manifest['sources'])
    assert artifact.manifest['template']['content_hash']=='b98f49e5f06ac405036219d7740200c29155cd65969f77bbdad9ce08c7795e30'
    assert artifact.manifest['mapping_gaps'] and not artifact.manifest['blockers']
    fills=artifact.manifest['filled_targets']
    # v0.3 shape: no developments table, so both section 3 updates stay in the narrative;
    # the exposure table's ninth column (limit cap) is an explicit gap; the overview has its own box.
    assert 's3.developments' not in fills
    updates=[c for c in artifact.manifest['sections']['3']['draft']['claim_spans'][1:] if c['id'] in ('disposal','rent-update')]
    assert len(updates)==2 and all(c['text'] in body for c in updates)
    exposure=fills['s2.exposure']['records']
    assert exposure and all(len(r)==9 and r[-1]=='[GAP: not supplied]' for r in exposure)
    assert fills['s4.overview.r1.c0'].startswith('ESR-REIT is a Singapore-listed real estate investment trust')
    template=drafting.templates.content('fig',artifact.manifest['template']['id'])
    with ZipFile(BytesIO(template)) as before,ZipFile(BytesIO(content)) as after:
        assert before.namelist()==after.namelist()
        for name in before.namelist():
            if name!='word/document.xml': assert before.read(name)==after.read(name),name
    assert len(list(xml(content).iter(W+'tbl')))==56
    headings=lambda raw:[ET.tostring(p) for p in xml(raw).find(W+'body').findall(W+'p') if p.find(W+'pPr/'+W+'pStyle') is not None and p.find(W+'pPr/'+W+'pStyle').get(W+'val')=='Heading1']
    assert headings(content)==headings(template) and len(headings(content))==14
    # Leading nested tables need a flow paragraph to survive LibreOffice page
    # boundaries; table count, shapes and owner package parts are unchanged.
    for cell in xml(content).iter(W+'tc'):
        children=[c for c in cell if c.tag!=W+'tcPr']
        assert not children or children[0].tag!=W+'tbl'
    before_case=service.repo.get(s.Case,case.id)
    assert before_case.active_es_version_id is None and before_case.workflow_state=='Draft'
    database.commit();database.expunge_all()
    assert service.content(case.id,artifact.id)==content
    # Save review artifacts in the task-local ignored directory.
    out=ROOT/'runtime/b18/demo';out.mkdir(parents=True,exist_ok=True)
    (out/'draft.docx').write_bytes(content)
    (out/'manifest.json').write_text(json.dumps(artifact.manifest,indent=2))
    (out/'request-list.txt').write_text(artifact.manifest['request_list'])


def test_partial_snapshot_na_and_history(setup,tmp_path,database):
    drafting,case=setup
    generate(drafting,case,1)
    service,_=service_for(setup,tmp_path)
    artifact=export(service,case); content=service.content(case.id,artifact.id)
    assert '[GAP] Section 14: draft not supplied.' in text(content)
    generate(drafting,case,7)
    assert service.content(case.id,artifact.id)==content
    assert service.get(case.id,artifact.id).manifest==artifact.manifest
    with pytest.raises(ValueError,match='append-only'): service.repo.save(artifact)
    with pytest.raises(ValueError,match='case'): service.get('other-case',artifact.id)


def test_preview_conflicts_and_locks(setup,tmp_path):
    drafting,case=setup; service,_=service_for(setup,tmp_path)
    manifest,_=service.prepare(case.id)
    generate(drafting,case,1)
    with pytest.raises(ExportConflict,match='changed'):
        service.create(case.id,ExportRequest(actor='CA',expected_preview_token=manifest['preview_token']))
    assert not service.repo.list_for_case(s.ESVersion,case.id)
    case.workflow_state='Approved';service.repo.save(case)
    with pytest.raises(ExportConflict,match='Draft state'): service.prepare(case.id)


def test_corrupt_template_and_artifact(setup,tmp_path):
    drafting,case=setup; service,_=service_for(setup,tmp_path)
    artifact=export(service,case)
    (tmp_path/'exports'/f'{artifact.content_hash}.docx').write_bytes(b'bad')
    with pytest.raises(ValueError,match='hash'): service.content(case.id,artifact.id)
    template=service.templates.get('fig',artifact.manifest['template']['id'])
    Path(template.storage_path).write_bytes(b'bad')
    with pytest.raises(ValueError,match='hash'): service.prepare(case.id)


@pytest.mark.parametrize('count',[1,2,12])
def test_repeat_rows_preserve_seed_and_total(count):
    content=(ROOT/'templates/ES_Template_FIG_draft_v0.3.docx').read_bytes()
    report=parse_template(content,load_team('fig').template);copy=TemplateCopy(content,report)
    table=copy.bound['s2.exposure'];seed=deepcopy(rows(table)[1]);total=ET.tostring(rows(table)[-1])
    repeat_rows(table,[[str(i)]*9 for i in range(count)],total=True)
    assert len(rows(table))==count+2 and ET.tostring(rows(table)[-1])==total
    for row in rows(table)[1:-1]:
        for old,new in zip(cells(seed),cells(row)):
            assert ET.tostring(old.find(W+'tcPr'))==ET.tostring(new.find(W+'tcPr'))
            assert ET.tostring(old.find(W+'p/'+W+'pPr'))==ET.tostring(new.find(W+'p/'+W+'pPr'))


@pytest.mark.parametrize('count',[1,2,3])
def test_facility_columns_keep_total_width_and_style(count):
    content=(ROOT/'templates/ES_Template_FIG_draft_v0.3.docx').read_bytes()
    copy=TemplateCopy(content,parse_template(content,load_team('fig').template))
    table=copy.bound['s7.facilities'];width=sum(int(c.get(W+'w')) for c in table.find(W+'tblGrid'))
    first=[ET.tostring(cells(row)[0]) for row in rows(table)]
    facility_columns(table,[[f'Facility {n}']+['SYNTHETIC DEMO DATA; test field']*(len(rows(table))-1) for n in range(count)])
    assert sum(int(c.get(W+'w')) for c in table.find(W+'tblGrid'))==width
    assert all(len(cells(row))==count+1 for row in rows(table))
    assert [ET.tostring(cells(row)[0]) for row in rows(table)]==first


def test_column_overflow_is_explicit_and_atomic():
    content=(ROOT/'templates/ES_Template_FIG_draft_v0.3.docx').read_bytes()
    copy=TemplateCopy(content,parse_template(content,load_team('fig').template));table=copy.bound['s7.facilities']
    original=ET.tostring(table)
    with pytest.raises(ValueError,match='owner-reviewed'):facility_columns(table,[['x']*12]*20)
    assert ET.tostring(table)==original


@pytest.mark.parametrize('mode',['missing-heading','duplicate-table','missing-placeholder'])
def test_mapping_failures_named_in_preview_and_block_word(setup,tmp_path,mode):
    from test_templates import mutate, paragraph, nested_table
    drafting,case=setup;service,_=service_for(setup,tmp_path)
    def change(root):
        if mode=='missing-heading':
            body=root.find(W+'body');body.remove(paragraph(root,'14.'))
        elif mode=='duplicate-table':
            table=nested_table(root,'Key terms')
            parent=next(p for p in root.iter() if table in list(p));parent.append(deepcopy(table))
        else:
            p=paragraph(root,'[To provide details of the request]')
            for t in p.iter(W+'t'):t.text='Removed narrative slot'
    candidate=service.templates.register('fig','v0.4','candidate.docx',mutate(change))
    active=service.templates.active('fig')
    service.repo.save(s.TemplateActivation(team_id='fig',template_version_id=candidate.id,expected_previous_id=active.id,actor='fixture',role='template admin'))
    manifest,content=service.prepare(case.id)
    assert manifest['mapping_gaps'] and manifest['blockers'] and content is None
    assert len(manifest['sections'])==14
    with pytest.raises(ExportConflict,match='mapping gaps'):
        service.create(case.id,ExportRequest(actor='CA',expected_preview_token=manifest['preview_token']))
    assert not service.repo.list_for_case(s.ESVersion,case.id)


def test_stale_ca_edits_and_export_bytes_remain_pinned(setup,tmp_path):
    from test_versions import revised_valuation,edit
    drafting,case=setup;service,_=service_for(setup,tmp_path)
    original=generate(drafting,case,8,confirm_unsecured=True)
    edited=edit(drafting,case,8,original)
    artifact=export(service,case);content=service.content(case.id,artifact.id)
    revised_valuation(drafting,case)
    newer=export(service,case);new_content=service.content(case.id,newer.id)
    assert 'STALE DRAFT' in text(new_content)
    assert 'CA-edited wording: CA (Credit Analyst)' in text(new_content)
    assert 'Further legal review is requested by the CA.' in text(new_content)
    assert '112.00' in text(new_content) and '104.00' not in text(new_content)
    assert newer.manifest['sections']['8']['draft']==edited
    assert service.content(case.id,artifact.id)==content
    assert artifact.manifest['sections']['8']['readiness']=='Drafted'


def test_template_pin_survives_activation_and_mixed_pins_block(setup,tmp_path):
    drafting,case=setup;service,_=service_for(setup,tmp_path)
    first=generate(drafting,case,1)
    old=export(service,case)
    active=service.templates.active('fig')
    candidate=service.templates.register('fig','v0.4','candidate.docx',service.templates.content('fig',active.id))
    service.repo.save(s.TemplateActivation(team_id='fig',template_version_id=candidate.id,expected_previous_id=active.id,actor='fixture',role='template admin'))
    assert service.prepare(case.id)[0]['template']['id']==first['template_version_id']
    generate(drafting,case,7)
    with pytest.raises(ExportConflict,match='pins differ'):service.prepare(case.id)
    assert service.content(case.id,old.id)


def test_na_and_nil_require_explicit_case_input(setup,tmp_path):
    drafting,case=setup;service,_=service_for(setup,tmp_path)
    case=case.model_copy(update=dict(case_type='new',existing_client=False,new_to_bank=True))
    service.repo.save(case)
    artifact=export(service,case)
    body=text(service.content(case.id,artifact.id))
    assert artifact.manifest['sections']['13']['na_reason']
    assert 'Not applicable:' in body and 'Nil, new to bank' not in body
    assert 'No adverse' not in body and 'Not recommended' not in body


def test_source_corruption_rejected_before_snapshot(setup,tmp_path):
    drafting,case=setup;service,_=service_for(setup,tmp_path)
    draft=generate(drafting,case,1)
    document=service.repo.get(s.Document,draft['document_ids'][0])
    Path(document.storage_path).write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='hash|integrity'):export(service,case)
    assert not service.repo.list_for_case(s.ExportArtifact,case.id)


def test_api_preview_snapshot_bundle_history_errors(setup,tmp_path,database):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker
    from backend.app.main import create_app
    from test_intake import make_case
    drafting,case=setup
    other=make_case(drafting.repo)
    generate(drafting,case,1);database.commit()
    app=create_app(sessions=sessionmaker(bind=database.get_bind(),expire_on_commit=False),storage_root=tmp_path/'blobs',
        template_storage_root=tmp_path/'templates',export_storage_root=tmp_path/'exports')
    base=f'/cases/{case.id}/exports'
    with TestClient(app) as client:
        preview=client.get(base+'/preview');assert preview.status_code==200
        payload=dict(actor='CA',expected_preview_token=preview.json()['preview_token'])
        assert client.post(base,json=payload|{'role':'Credit Approver'}).status_code==422
        assert client.post(base,json=payload|{'purpose':'approved'}).status_code==422
        assert client.post(base,json=payload|{'actor':' '}).status_code==422
        assert client.post(base,json=payload|{'expected_preview_token':'stale'}).status_code==409
        response=client.post(base,json=payload);assert response.status_code==200,response.text
        artifact=response.json();prefix=base+'/'+artifact['id']
        assert client.get(prefix+'/manifest').json()==artifact['manifest']
        docx=client.get(prefix+'/document.docx');assert docx.status_code==200
        assert sha256(docx.content).hexdigest()==artifact['content_hash']
        bundle=client.get(prefix+'/bundle.zip');assert bundle.status_code==200
        with ZipFile(BytesIO(bundle.content)) as archive:
            assert archive.read('draft.docx')==docx.content
            manifest=json.loads(archive.read('manifest.json'))
            assert manifest==artifact['manifest']
            requests=archive.read('request-list.txt').decode()
            assert requests==client.get(prefix+'/request-list.txt').text
            for phrase in ['RM','client','internal team','ES sections:','Public search:']:
                assert phrase in requests
        assert len(client.get(base).json())==1
        assert client.get(f'/cases/{other.id}/exports/{artifact["id"]}/manifest').status_code==422
        assert client.get('/cases/unknown/exports/preview').status_code==404
    with TestClient(create_app()) as client:
        assert client.get(base+'/preview').status_code==503


def test_zero_records_and_long_repeat_visual_fixture(setup,tmp_path):
    service,case=service_for(setup,tmp_path)
    manifest,content=service.prepare(case.id)
    assert not manifest['blockers']
    out=ROOT/'runtime/b18/fixtures';out.mkdir(parents=True,exist_ok=True)
    (out/'zero.docx').write_bytes(content)
    owner=service.templates.content('fig',manifest['template']['id'])
    report=service.templates.get('fig',manifest['template']['id']).parsed_map
    # Start with sanitized empty export, then resolve its original targets BEFORE
    # row growth by using Mapper on a fresh owner copy.
    from backend.app.exports.mapping import Mapper
    for count in (1,12):
        copy=TemplateCopy(owner,report)
        mapper=Mapper(copy,deepcopy(manifest));mapper.run()
        # v0.3 has no developments table; the section 3 repeat-row table is prior conditions.
        assert 's3.developments' not in copy.bound
        table=copy.bound['s3.prior_conditions']
        records=[[str(i+1),f'SYNTHETIC DEMO DATA row {i+1}: '+
                  ('Long narrative exercises wrapping and page flow. '*8 if i==0 else 'Review item.'),
                  'CA review pending','Synthetic layout fixture, page 1; no approval inferred.'] for i in range(count)]
        repeat_rows(table,records)
        facility_columns(copy.bound['s7.facilities'],[[f'Synthetic facility {i+1}']+['SYNTHETIC DEMO DATA; test value']*11 for i in range(3)])
        (out/f'repeat-{count}.docx').write_bytes(copy.bytes())
        assert all(f'SYNTHETIC DEMO DATA row {i+1}' in text(copy.bytes()) for i in range(count))


def test_b09_currency_conversion_and_source_pins(setup,tmp_path):
    from test_drafting import test_b09_financial_spread_consumed_without_changing_values
    test_b09_financial_spread_consumed_without_changing_values(setup)
    service,case=service_for(setup,tmp_path)
    artifact=export(service,case)
    body=text(service.content(case.id,artifact.id))
    for phrase in ['5,864,836','328,679','FY2025','FY2024','Group figures','CA confirmation pending']:
        assert phrase in body,phrase
    assert artifact.manifest['sections']['10']['draft']['computed_value_ids']


@pytest.mark.parametrize('mode',['claim-text','computed-value','computed-table','cross-case'])
def test_invalid_snapshot_inputs_fail_closed(setup,tmp_path,mode):
    from uuid import uuid4
    from test_intake import make_case
    drafting,case=setup;service,_=service_for(setup,tmp_path)
    draft=generate(drafting,case,2)
    edited=deepcopy(draft);edited['id']=str(uuid4())
    if mode=='claim-text': edited['claim_spans'][1]['text']='Unsupported replacement'
    if mode=='computed-value': edited['claim_spans'][1]['value']['value']='99999'
    if mode=='computed-table': edited['claim_spans'][0]['computed_tables'][0]['rows'][0]['proposed']='99999'
    if mode=='cross-case':
        other=make_case(service.repo)
        # Deliberately corrupt mutable pointers through SQL to exercise service defense.
        from sqlalchemy import update
        from backend.app import models
        _,states=__import__('backend.app.services.readiness',fromlist=['ReadinessService']).ReadinessService(service.repo).refresh(other.id)
        service.repo.session.execute(update(models.Section).where(models.Section.id==next(st.id for st in states if st.section_id==2)).values(current_draft_id=draft['id']))
        service.repo.session.expire_all()
        with pytest.raises(ValueError):service.prepare(other.id)
        return
    record=service.repo.save(s.DraftVersion.model_validate(edited))
    state=next(st for st in service.repo.list_for_case(s.Section,case.id) if st.section_id==2)
    service.repo.save(state.model_copy(update=dict(current_draft_id=record.id)))
    with pytest.raises(ExportConflict):service.prepare(case.id)
    assert not service.repo.list_for_case(s.ESVersion,case.id)


@pytest.mark.slow
def test_ca_presentation_tables_sources_and_repayment(setup, tmp_path):
    import re
    drafting, case = setup
    prerequisites(drafting, case)
    generate(drafting, case,14,ca_position='Defer pending evidence and legal review.')
    service, _ = service_for(setup, tmp_path)
    artifact = export(service, case)
    content = service.content(case.id, artifact.id)
    document = text(content)
    body, appendix = document.split('\nSources\n', 1)
    assert 'MOCK DRAFT' not in body and 'DRAFT — Drafted' not in body
    assert body.count('DRAFT — CA REVIEW REQUIRED') == 1
    assert '.pdf p' not in body and '.xlsx p' not in body and '[S1 ' not in body
    assert 'Found publicly' not in body and 'Read with pinned' not in body
    assert 'generate/review B09' not in body and '[Gap: Total assets' not in body
    assert re.findall(r'\[\d+\]', body)
    for marker, ref in artifact.manifest['source_markers'].items():
        src = artifact.manifest['sources'][ref]
        assert f'[{marker}]' in appendix
        assert src['filename'] in appendix and f"p{src['page']}" in appendix
        if src['origin'] == 'public':
            assert src['url'] in appendix and __import__('backend.app.exports.formatting', fromlist=['human_date']).human_date(src['retrieved_at']) in appendix
    fills = artifact.manifest['filled_targets']
    for target, phrase in [('s4.business.r0.c1','ESR-REIT'), ('s4.business.r1.c1','25 July 2006'),
                          ('s4.business.r2.c1','Singapore Exchange'), ('s4.business.r5.c1','ESR Group'),
                          ('s4.business.r6.c1','Perpetual'), ('s4.business.r4.c1','industrial')]:
        assert phrase in fills[target]
    for target, phrase in [('s5.holders','Tong Jinquan'), ('s6.management','Adrian Chui'),
                          ('s6.stakeholders','Perpetual'), ('s7.facilities','Working capital'),
                          ('s9.tenants','51.7'), ('s9.lease_profile','49.8'),
                          ('s12.external_ratings','BBB'), ('s13.conduct','RCF-01')]:
        assert phrase in str(fills[target])
    assert not any(g.get('anchor','').startswith(('s4.portfolio.r3.', 's5.holders.r4.')) for g in artifact.manifest['mapping_gaps'])
    risks = fills['s11.risks']['records']
    assert all(r[1] != 'Draft context' and 'status' not in r[1].lower() for r in risks)
    for topic in ('refinancing', 'LTV', 'Tenant concentration', 'Interest-rate', 'Regulatory leverage'):
        assert any(topic in r[1] for r in risks)
    # No source worksheet headers or per-cell computation dump in repayment.
    copy = TemplateCopy(content, __import__('backend.app.services.templates', fromlist=['parse_template']).parse_template(content, load_team('fig').template))
    repayment = '\n'.join(t.text or '' for t in copy.bound['s9.wrapper'].iter(W+'t'))
    assert 'scope SYNTHETIC' not in repayment and 'Fictional relationship only' not in repayment
    assert 'Property-only repayment is insufficient' in repayment
    assert 'refinancing is uncommitted' in repayment
    assert 'n.m.' in repayment and '51.7' in repayment
    assert len(repayment) < 3000
    # The revised CAS explicitly supplies classification; it is not inferred.
    classification_table = next(t for t in xml(content).iter(W+'tbl') if rows(t) and cells(rows(t)[0]) and ''.join(n.text or '' for n in cells(rows(t)[0])[0].iter(W+'t')) == 'Borrower/ Group')
    classification = '\n'.join(t.text or '' for t in classification_table.iter(W+'t'))
    assert 'Not applicable' in classification


def test_presentation_does_not_decode_ca_edited_claims(setup, tmp_path):
    from backend.app.exports.mapping import Mapper
    drafting, case = setup
    generate(drafting, case,4)
    service, _ = service_for(setup,tmp_path)
    manifest, _ = service.prepare(case.id)
    claim = next(c for c in manifest['sections']['4']['draft']['claim_spans'][1:] if c['id']=='listing')
    claim['ca_edit'] = {'actor':'CA','recorded_at':'2026-11-11','replacement':claim['text']}
    original = service.templates.content('fig',manifest['template']['id'])
    report = parse_template(original,load_team('fig').template)
    mapper = Mapper(TemplateCopy(original,report),manifest)
    rendered = text(mapper.run())
    assert 's4.business.r1.c1' not in manifest['filled_targets']
    assert claim['text'] in rendered and 'CA-edited wording: CA' in rendered
    risk = dict(claim, id='reviewed-risk', kind='risk_mitigant', text='Concentration risk: CA-reviewed exposure. Mitigant review: verify renewal evidence.')
    mapper.risk_rows([risk])
    assert 'CA-edited wording: CA' in str(manifest['filled_targets']['s11.risks'])


@pytest.mark.slow
def test_explicit_ca_classification_na_and_revised_ltv(setup, tmp_path):
    from test_versions import versions, command, revised_valuation
    from backend.app.services.versions import EditRequest, RedraftRequest
    drafting, case = setup
    reviewed = next(c for c in drafting.fixture['claims'] if c['id'] == 'classification')
    reviewed.pop('numbers')
    reviewed['text'] = 'Classification requires CA assessment.'
    prerequisites(drafting, case)
    state = next(st for st in drafting.repo.list_for_case(s.Section, case.id) if st.section_id == 1)
    original = drafting.repo.get(s.DraftVersion, state.current_draft_id)
    assert any(c['id'] == 'classification' for c in original.claim_spans[1:])
    versions(drafting).save(case.id, 1, command(drafting, case, 1, EditRequest,
        replacements={'classification':'The borrower is not classified as Watchlist or Special Mention.'}))
    revised_valuation(drafting, case)
    for sid in (8, 9, 11):
        versions(drafting).redraft(case.id, sid, command(drafting, case, sid, RedraftRequest, confirm_unsecured=True))
    generate(drafting,case,14,ca_position='Defer pending evidence and legal review.')
    service, _ = service_for(setup, tmp_path)
    artifact = export(service,case)
    content = text(service.content(case.id, artifact.id))
    assert 'Not applicable' in artifact.manifest['filled_targets']['s1.classification.r1.c0']
    risks = artifact.manifest['filled_targets']['s11.risks']['records']
    ltv = next(row for row in risks if row[1] == 'LTV covenant headroom')
    assert '57.7%' in ltv[2] and '-2.7' in ltv[2] and '104.00' in ltv[2]
    assert 'CA-stated position (verbatim):\nDefer pending evidence and legal review.' in content


@pytest.mark.slow
def test_polished_financials_keep_precision_and_source_gaps(setup, tmp_path):
    from decimal import Decimal
    from backend.app.exports.mapping import Mapper
    drafting, case = setup
    prerequisites(drafting, case)
    generate(drafting, case, 14, ca_position='Support renewal subject to the stated conditions.')
    before = {v.id: v.model_dump(mode='json') for v in drafting.repo.list_for_case(s.ComputedValue, case.id)}
    service, _ = service_for(setup, tmp_path)
    artifact = export(service, case)
    content = service.content(case.id, artifact.id)
    body = text(content)
    fills = artifact.manifest['filled_targets']
    assert fills['s0.cover.r1.c1'].startswith('ESR Group [')
    assert fills['s0.cover.r2.c1'].startswith('Singapore [')
    assert fills['s1.sm_dpd.r0.c2'].startswith('No: [x] [')
    # The v0.3 financial table is headed SGD'000: amounts are whole thousands with comma grouping;
    # per-unit, ratio and percentage rows keep their own units.
    assert fills.get('s10.financials.r0.c0') is None and "SGD'000" in body
    for row, value in [(4,'176,076'),(5,'21.914'),(7,'5,013,226'),(9,'2,236,100'),(10,'2,055,640'),(11,'2.55'),(16,'2.0'),(17,'68.4')]:
        assert fills[f's10.financials.r{row}.c2'] == value
    for row, value in [(2,'329,600'),(3,'237,500'),(4,'136,000'),(9,'2,227,100'),(11,'2.43'),(13,'44.1'),(14,'2.60'),(16,'1.9'),(17,'62.9'),(19,'91.7'),(20,'4.8')]:
        assert fills[f's10.financials.r{row}.c4'] == value
    assert 's10.financials.r5.c4' not in fills  # No interim DPU disclosed in this saved update.
    assert all(__import__('re').fullmatch(r'(?:\[\d+\] ?)+', value) for key, value in fills.items() if key.startswith('s10.financials.r') and key.endswith('.c5'))
    assert 'Additional Group figures' not in body and '0.043261' not in body and '4.583333' not in body
    assert 'Leverage increased' in body and 'Reported ICR improved' in body
    assert 'n.m.' in body and 'cash repayment of bullet maturities' in body
    assert not __import__('re').search(r'\d{4}-\d{2}-\d{2}T\d{2}:', body)
    assert 'demo-ca' not in body
    after = {v.id: v.model_dump(mode='json') for v in drafting.repo.list_for_case(s.ComputedValue, case.id)}
    assert before == after
    assert any(v['metric']=='conduct/RCF-01/mean_month_end' and Decimal(v['value']) > Decimal('4.58') for v in after.values())
    assert any(v['metric']=='draft/financial-investment-2025/amount' and v['value']=='5013226' for v in after.values())
    # Missing/edited sources cannot be backfilled with hard-coded demo facts.
    manifest = deepcopy(artifact.manifest)
    manifest['sections']['4']['draft']['claim_spans'] = manifest['sections']['4']['draft']['claim_spans'][:1]
    manifest['sections']['10']['draft']['claim_spans'] = manifest['sections']['10']['draft']['claim_spans'][:1]
    owner = service.templates.content('fig', artifact.manifest['template']['id'])
    Mapper(TemplateCopy(owner, parse_template(owner, load_team('fig').template)), manifest).run()
    assert 's0.cover.r1.c1' not in manifest['filled_targets']
    assert 's10.financials.r7.c2' not in manifest['filled_targets']


def test_inserted_gap_and_checkbox_runs_use_owner_body_font():
    owner = (ROOT/'templates/ES_Template_FIG_draft_v0.3.docx').read_bytes()
    copy = TemplateCopy(owner, parse_template(owner, load_team('fig').template))
    copy.sanitize(lambda *_: '[Gap]')
    copy.status('Draft test')
    copy.appendix('Sources', ['Credit Analyst'])
    rendered = xml(copy.bytes())
    checked = 0
    for run in rendered.iter(W+'r'):
        value = ''.join(t.text or '' for t in run.iter(W+'t'))
        if '[Gap]' in value or 'Pending CA selection' in value or value in ('Draft test','Credit Analyst'):
            fonts = run.find(W+'rPr/'+W+'rFonts')
            assert fonts is not None
            assert all(fonts.get(W+key)=='Arial' for key in ('ascii','hAnsi','eastAsia','cs'))
            checked += 1
        assert 'inserted' not in run.attrib
    assert checked > 100


def test_display_rounding_is_half_up_and_unit_bound():
    from backend.app.exports.formatting import number, prose
    assert number('4.58333333333333333333333') == '4.58'
    assert number('93.3333333333333', 'percent') == '93.3'
    assert number('0.325', 'times') == '0.33'
    assert number('-2.692308', 'percentage points') == '-2.7'
    assert prose('2026-11-10; TL-01; [43]; SGD 4.583333 million; 45.833333 percent; 2.6x') == '2026-11-10; TL-01; [43]; SGD 4.58 million; 45.8 percent; 2.60x'
