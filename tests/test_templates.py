"""G2 uses real owner bytes plus in-memory structural mutations; no authoring output."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.templates import (TemplateRegistry, TemplateIntegrityError,
    TemplateNotFound, parse_template, W, paragraph_text, Styles)
from backend.app.team_config import load_team, TeamConfig

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / 'templates/ES_Template_FIG_draft_v0.3.docx'
OWNER_HASH = 'b98f49e5f06ac405036219d7740200c29155cd65969f77bbdad9ce08c7795e30'


def mutate(change, part='word/document.xml'):
    with ZipFile(BytesIO(OWNER.read_bytes())) as source:
        parts = {name: source.read(name) for name in source.namelist()}
    root = ET.fromstring(parts[part])
    change(root)
    parts[part] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    stream = BytesIO()
    with ZipFile(stream, 'w', ZIP_DEFLATED) as target:
        for name, content in parts.items():
            target.writestr(name, content)
    return stream.getvalue()


def parse(content=None, config=None):
    return parse_template(content or OWNER.read_bytes(), config or load_team('fig').template)


def paragraph(root, contains):
    return next(p for p in root.iter(W+'p') if contains in paragraph_text(p))


def nested_table(root, first_header):
    return next(t for t in root.iter(W+'tbl') if t.find(W+'tr/'+W+'tc/'+W+'p') is not None
                and paragraph_text(t.find(W+'tr/'+W+'tc/'+W+'p')) == first_header)


def resolve(root, locator):
    element = root.find(W+'body')
    for index in locator['path']:
        element = element[index]
    return element


def test_actual_inventory_complete_and_locations():
    content = OWNER.read_bytes()
    report = parse(content)
    assert sha256(content).hexdigest() == OWNER_HASH
    assert report['complete'] and report['gaps'] == []
    assert len(report['sections']) == 14
    assert len(report['tables']) == 56
    assert sum(t['parent_table'] is not None for t in report['tables']) == 41
    assert len(report['bindings']) == 56
    assert len(report['fill_points']) == 187
    assert all(f['mapped'] for f in report['fill_points'])
    assert {f['kind'] for f in report['fill_points']} == {'placeholder', 'period', 'date', 'checkbox'}
    assert len({f['id'] for f in report['fill_points']}) == 187
    with ZipFile(BytesIO(content)) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    for table in report['tables']:
        assert resolve(root, table['locator']).tag == W+'tbl'
        for row in table['rows']:
            for cell in row:
                assert resolve(root, cell['locator']).tag == W+'tc'
    for fill in report['fill_points']:
        p = resolve(root, fill['locator'])
        assert paragraph_text(p)[fill['start']:fill['end']] == fill['text']
        runs = list(p.iter(W+'r'))
        assert ''.join(paragraph_text(r)[o['start']:o['end']] for o in fill['runs'] for r in [runs[o['run']]]) == fill['text']
    mapped = {t.get('anchor'):t for t in report['tables'] if t.get('anchor')}
    assert mapped['s7.facilities']['repeat'] == 'facility_columns'
    assert mapped['s10.headroom']['repeat'] == 'covenant_rows'
    assert any(c['text'] == '' and c['requires_sourced_value'] for row in mapped['s10.financials']['rows'][1:] for c in row)
    assert any(c['grid_span'] > 1 for t in report['tables'] for row in t['rows'] for c in row)
    assert report == parse(content)  # deterministic, no timestamps/random IDs


@pytest.mark.parametrize('mode', ['missing', 'duplicate', 'title', 'style', 'unknown'])
def test_heading_failures_keep_all_canonical_sections(mode):
    def change(root):
        body = root.find(W+'body')
        p = paragraph(root, 'REQUEST / PURPOSE')
        if mode == 'missing': body.remove(p)
        elif mode == 'duplicate': body.insert(list(body).index(p), deepcopy(p))
        elif mode == 'style': p.find(W+'pPr/'+W+'pStyle').set(W+'val', 'Normal')
        else:
            target = next(t for t in p.iter(W+'t') if 'REQUEST' in (t.text or ''))
            target.text = target.text.replace('REQUEST', 'DIFFERENT') if mode == 'title' else '99. UNKNOWN SECTION'
    report = parse(mutate(change))
    assert not report['complete']
    assert len(report['sections']) == 14
    assert any('Section 1 / heading' in g for g in report['gaps'])
    assert 's1.classification' not in report['bindings']


@pytest.mark.parametrize('mode', ['missing', 'duplicate', 'header', 'row'])
def test_table_ambiguity_and_missing_rows(mode):
    def change(root):
        t = nested_table(root, 'Key terms')
        parent = next(p for p in root.iter() if t in list(p))
        if mode == 'missing': parent.remove(t)
        elif mode == 'duplicate': parent.append(deepcopy(t))
        elif mode == 'header': next(t.iter(W+'t')).text = 'Changed key terms'
        else: t.remove(t.findall(W+'tr')[2])
    report = parse(mutate(change))
    assert any('Section 7 / facilities' in g for g in report['gaps'])
    assert 's7.facilities' not in report['bindings']
    assert len(report['sections']) == 14


def test_split_runs_inherited_italics_and_repeated_placeholder_identity():
    def change(root):
        p = paragraph(root, '[To provide details of the request]')
        run = next(r for r in p.findall(W+'r') if '[' in paragraph_text(r))
        value = paragraph_text(run)
        run.find(W+'t').text = value[:10]
        other = deepcopy(run)
        other.find(W+'t').text = value[10:]
        p.insert(list(p).index(run)+1, other)
    report = parse(mutate(change))
    f = next(f for f in report['fill_points'] if f['text']=='[To provide details of the request]')
    assert len(f['runs']) == 2 and f['mapped']
    assert report['complete']
    refs = [f for f in report['fill_points'] if f['text']=='[CAS no.]']
    assert len(refs)==2 and refs[0]['id'] != refs[1]['id']
    xml = f'<w:styles xmlns:w="{W[1:-1]}"><w:style w:styleId="Base"><w:rPr><w:i/></w:rPr></w:style><w:style w:styleId="Derived"><w:basedOn w:val="Base"/></w:style></w:styles>'
    styles = Styles(ET.fromstring(xml))
    p = ET.fromstring(f'<w:p xmlns:w="{W[1:-1]}"><w:pPr><w:pStyle w:val="Derived"/></w:pPr><w:r><w:t>[value]</w:t></w:r></w:p>')
    assert styles.italic(p,p.find(W+'r'))
    ET.SubElement(ET.SubElement(p.find(W+'r'),W+'rPr'),W+'i',{W+'val':'0'})
    assert not styles.italic(p,p.find(W+'r'))


def test_removed_nonitalic_and_new_narrative_are_named_gaps():
    def change(root):
        p=paragraph(root,'[To provide details of the request]')
        for r in p.findall(W+'r'):
            pr=r.find(W+'rPr')
            if pr is None: pr=ET.SubElement(r,W+'rPr')
            italic=pr.find(W+'i')
            if italic is None: italic=ET.SubElement(pr,W+'i')
            italic.set(W+'val','0')
    report=parse(mutate(change))
    assert any('not effectively italic' in g for g in report['gaps'])
    assert any('missing or duplicate narrative' in g for g in report['gaps'])
    def new(root):
        p=paragraph(root,'[To provide details of the request]')
        next(p.iter(W+'t')).text='[New unsupported guidance]'
    report=parse(mutate(new))
    assert any('missing or duplicate narrative' in g for g in report['gaps'])
    assert not next(f for f in report['fill_points'] if f['text']=='[New unsupported guidance]')['mapped']


def test_decorations_and_case_normalization_preserve_display_text():
    def change(root):
        p=paragraph(root,'REQUEST / PURPOSE')
        for t in p.iter(W+'t'):
            t.text=t.text.lower().replace('ⓘ','')
    report=parse(mutate(change))
    assert report['complete']
    assert 'request / purpose' in report['sections'][0]['headings'][0]['text']


@pytest.mark.parametrize('content', [b'not zip', b'', b'PKfake'])
def test_malformed_package_rejected(content):
    with pytest.raises(ValueError): parse_template(content, load_team('fig').template)


def test_xml_entity_macro_and_duplicate_parts_rejected():
    with ZipFile(BytesIO(OWNER.read_bytes())) as z: parts={n:z.read(n) for n in z.namelist()}
    for mutation in ('entity','macro','duplicate','xml'):
        stream=BytesIO()
        with ZipFile(stream,'w') as z:
            for name,data in parts.items():
                if name=='word/document.xml' and mutation=='entity': data=b'<!DOCTYPE x [<!ENTITY e "bad">]>'+data
                if name=='word/document.xml' and mutation=='xml': data=b'<malformed'
                z.writestr(name,data)
            if mutation=='macro': z.writestr('word/vbaProject.bin',b'fake')
            if mutation=='duplicate':
                with pytest.warns(UserWarning): z.writestr('word/document.xml',parts['word/document.xml'])
        with pytest.raises(ValueError): parse(stream.getvalue())


def test_unsupported_content_and_header_fill_report_gaps():
    def change(root):
        ET.SubElement(root.find(W+'body'),W+'altChunk')
    assert any('unsupported content' in g for g in parse(mutate(change))['gaps'])
    def header(root):
        p=ET.SubElement(root,W+'p');r=ET.SubElement(p,W+'r');ET.SubElement(r,W+'t').text='[Unmapped header]'
    with ZipFile(OWNER) as z: part=next(n for n in z.namelist() if n.startswith('word/header') and n.endswith('.xml'))
    assert any('header/footer fill' in g for g in parse(mutate(header,part))['gaps'])


def test_registry_seed_restart_immutable_and_integrity(tmp_path):
    engine,sessions=create_database(tmp_path/'db.sqlite')
    try:
        with sessions.begin() as session:
            registry=TemplateRegistry(Repository(session),tmp_path/'blobs')
            versions=registry.seed_owner_templates('fig',ROOT)
            active=registry.active('fig')
            # Every versioned owner file is registered in numeric order; the configured
            # default (v0.3) is the highest, so it ends active. Older files keep their gaps.
            assert [v.display_version for v in versions]==['v0.1','v0.2','v0.3']
            assert active.id==versions[-1].id
            assert [v.status for v in versions]==['review required','review required','mapped']
            assert versions[0].parse_gaps and versions[1].parse_gaps and not active.parse_gaps
            assert [v.parent_id for v in versions]==[None,versions[0].id,versions[1].id]
            assert active.status=='mapped' and active.content_hash==OWNER_HASH
            assert registry.content('fig',active.id)==OWNER.read_bytes()
        with sessions.begin() as session:
            registry=TemplateRegistry(Repository(session),tmp_path/'blobs')
            assert [v.id for v in registry.seed_owner_templates('fig',ROOT)]==[v.id for v in versions]
            assert len(registry.versions('fig'))==3
            assert registry.active('fig').id==active.id
            candidate=registry.register('fig','v0.4','candidate.docx',OWNER.read_bytes(),active.id)
            assert candidate.parent_id==active.id and candidate.id!=active.id
            assert registry.active('fig').id==active.id
            with pytest.raises(ValueError,match='append-only'): registry.repo.save(active)
            with pytest.raises(TemplateNotFound): registry.get('another-team',active.id)
            with pytest.raises(ValueError,match='different bytes'):
                registry.register('fig','v0.3','candidate.docx',b'different')
        with sessions.begin() as session:
            with pytest.raises(IntegrityError,match='immutable'):
                session.execute(text("UPDATE template_version SET display_version='changed' WHERE id=:id"),{'id':active.id})
        Path(active.storage_path).write_bytes(b'corrupted')
        with sessions() as session:
            with pytest.raises(TemplateIntegrityError,match='hash mismatch'):
                TemplateRegistry(Repository(session),tmp_path/'blobs').content('fig',active.id)
    finally:engine.dispose()
    assert sha256(OWNER.read_bytes()).hexdigest()==OWNER_HASH


def test_owner_newer_versions_seed_numerically_and_restart_preserves_active(tmp_path):
    owner=tmp_path/'project/templates';owner.mkdir(parents=True)
    for v in ('0.1','0.3','0.10'):(owner/f'ES_Template_FIG_draft_v{v}.docx').write_bytes(OWNER.read_bytes())
    engine,sessions=create_database(tmp_path/'db.sqlite')
    try:
        with sessions.begin() as session:
            registry=TemplateRegistry(Repository(session),tmp_path/'blobs')
            versions=registry.seed_owner_templates('fig',tmp_path/'project')
            assert [v.display_version for v in versions]==['v0.1','v0.3','v0.10']
            assert registry.active('fig').id==versions[-1].id
        (owner/'ES_Template_FIG_draft_v0.11.docx').write_bytes(OWNER.read_bytes())
        with sessions.begin() as session:
            registry=TemplateRegistry(Repository(session),tmp_path/'blobs')
            assert len(registry.seed_owner_templates('fig',tmp_path/'project'))==4
            assert registry.active('fig').id==versions[-1].id
            assert registry.content('fig',versions[0].id)==OWNER.read_bytes()
    finally:engine.dispose()


def test_invalid_template_preserves_named_gaps_and_never_activates(database,tmp_path):
    registry=TemplateRegistry(Repository(database),tmp_path/'blobs')
    def change(root):
        body=root.find(W+'body');body.remove(paragraph(root,'REQUEST / PURPOSE'))
    candidate=registry.register('fig','v0.2','candidate.docx',mutate(change))
    assert candidate.status=='review required'
    assert candidate.parse_gaps
    assert len(candidate.parsed_map['sections'])==14
    assert registry.active('fig') is None
    with pytest.raises(ValueError):registry.register('fig','v0.3','../bad.docx',OWNER.read_bytes())
    with pytest.raises(ValueError):registry.register('fig','v0.3','bad.doc',OWNER.read_bytes())


def test_storage_boundary_and_symlinks(database,tmp_path):
    registry=TemplateRegistry(Repository(database),tmp_path/'blobs')
    version=registry.register('fig','v0.1','template.docx',OWNER.read_bytes())
    other=tmp_path/'other.docx';other.write_bytes(OWNER.read_bytes())
    Path(version.storage_path).unlink();Path(version.storage_path).symlink_to(other)
    with pytest.raises(TemplateIntegrityError):registry.content('fig',version.id)
    with pytest.raises(TemplateIntegrityError):registry.register('fig','v0.2','template.docx',OWNER.read_bytes())
    with pytest.raises(TemplateIntegrityError):TemplateRegistry(Repository(database),tmp_path/'otherroot').content('fig',version.id)


def test_old_config_pin_and_alternate_team():
    config=load_team('fig')
    old=config.model_dump(mode='json',exclude_unset=True)
    old['template'].pop('table_anchors');old['template'].pop('narrative_anchors')
    restored=TeamConfig.model_validate(old)
    assert restored.model_dump(mode='json',exclude_unset=True)==old
    assert restored.template.table_anchors==[]
    alternate=config.template.model_copy(deep=True)
    alternate.team_id='test-team'
    alternate.sections[0].name='Test-only purpose'
    report=parse(config=alternate)
    assert any('Test-only purpose' in g for g in report['gaps'])
    assert report['mapping_hash']!=parse()['mapping_hash']


def test_api_and_concurrent_dedup(tmp_path):
    engine,sessions=create_database(tmp_path/'db.sqlite')
    app=create_app(sessions=sessions,template_storage_root=tmp_path/'blobs')
    try:
        with TestClient(app) as client:
            assert client.get('/templates/fig/active').json() is None
            def upload(_):
                return client.post('/templates/fig',params={'display_version':'v0.1','filename':'template.docx'},content=OWNER.read_bytes())
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(upload,range(2)))
            assert all(r.status_code==200 for r in results)
            version=results[0].json();assert results[1].json()['id']==version['id']
            assert len(client.get('/templates/fig').json())==1
            assert client.get(f"/templates/fig/{version['id']}").json()['parsed_map']['complete']
            assert client.get(f"/templates/fig/{version['id']}/source").content==OWNER.read_bytes()
            assert client.get(f"/templates/other/{version['id']}").status_code==404
            assert client.get('/templates/fig/unknown').status_code==404
            assert client.get('/templates/fig/active').json() is None
            assert client.post('/templates/fig',params={'display_version':'v0.2','filename':'x.docx'},content=b'bad').status_code==422
            assert client.post(f"/templates/fig/{version['id']}/activate").status_code==404
            Path(version['storage_path']).write_bytes(b'corrupted')
            assert client.get(f"/templates/fig/{version['id']}/source").status_code==409
        with TestClient(create_app()) as client:assert client.get('/templates/fig').status_code==503
    finally:engine.dispose()


def test_changed_blank_cell_geometry_withholds_mapping():
    def change(root):
        t=nested_table(root,'Key terms')
        row=t.findall(W+'tr')[1]
        row.remove(row.findall(W+'tc')[-1])
    report=parse(mutate(change))
    assert 's7.facilities' not in report['bindings']
    assert any('changed cell count' in g for g in report['gaps'])


def test_key_value_first_row_and_sample_values_are_explicit_targets():
    report=parse()
    tables={t.get('anchor'):t for t in report['tables']}
    assert tables['s8.insurance']['rows'][0][1]['requires_sourced_value']
    assert tables['s4.business']['rows'][0][1]['requires_sourced_value']
    assert tables['s5.holders']['rows'][-1][1]['text']=='100.0'
    assert tables['s5.holders']['rows'][-1][1]['requires_sourced_value']
    assert tables['s14.signoff']['rows'][1][2]['text']=='Submitted'
    assert tables['s14.signoff']['rows'][1][2]['requires_sourced_value']


def test_mapping_config_rejects_unknown_duplicate_anchors():
    config=load_team('fig').model_dump(mode='json')
    config['template']['table_anchors'][0]['section_id']=99
    with pytest.raises(ValueError):TeamConfig.model_validate(config)
    config=load_team('fig').model_dump(mode='json')
    config['template']['table_anchors'].append(config['template']['table_anchors'][0])
    with pytest.raises(ValueError):TeamConfig.model_validate(config)
