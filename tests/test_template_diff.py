"""B22 API comparisons of generated, labelled copies of the owner template."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend.app import models, schemas as s
from backend.app.database import create_database
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.templates import TemplateRegistry, W, paragraph_text
from backend.app.team_config import load_team

OWNER = Path(__file__).resolve().parents[1] / 'templates/ES_Template_FIG_draft_v0.3.docx'
OWNER_HASH = 'b98f49e5f06ac405036219d7740200c29155cd65969f77bbdad9ce08c7795e30'


def paragraph(root, value):
    return next(p for p in root.iter(W+'p') if value in paragraph_text(p))


def table(root):
    return next(t for t in root.iter(W+'tbl') if t.find(W+'tr/'+W+'tc/'+W+'p') is not None
                and paragraph_text(t.find(W+'tr/'+W+'tc/'+W+'p')) == 'Key terms')


def mutate(content, change, part='word/document.xml'):
    with ZipFile(BytesIO(content)) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    root = ET.fromstring(parts[part])
    change(root)
    parts[part] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    stream = BytesIO()
    with ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return stream.getvalue()


def font(root):
    run = next(paragraph(root, 'REQUEST / PURPOSE').iter(W+'r'))
    props = run.find(W+'rPr')
    if props is None:
        props = ET.SubElement(run, W+'rPr')
    node = props.find(W+'rFonts')
    if node is None:
        node = ET.SubElement(props, W+'rFonts')
    node.set(W+'ascii', 'Courier New')
    node.set(W+'hAnsi', 'Courier New')


def colour(root):
    run = next(paragraph(root, 'REQUEST / PURPOSE').iter(W+'r'))
    props = run.find(W+'rPr')
    if props is None:
        props = ET.SubElement(run, W+'rPr')
    node = props.find(W+'color')
    if node is None:
        node = ET.SubElement(props, W+'color')
    node.set(W+'val', 'AA3322')


def guidance(root):
    next(paragraph(root, '[To provide details of the request]').iter(W+'t')).text = '[Explain the purpose and borrower context]'


def header(root):
    next(table(root).iter(W+'t')).text = 'Facility terms'


def column(root):
    target = table(root)
    grid = target.find(W+'tblGrid')
    grid.append(deepcopy(grid[-1]))
    for row in target.findall(W+'tr'):
        row.append(deepcopy(row.findall(W+'tc')[-1]))


def added_section(root):
    body = root.find(W+'body')
    heading = deepcopy(paragraph(root, 'REQUEST / PURPOSE'))
    for t in heading.iter(W+'t'):
        t.text = ''
    next(heading.iter(W+'t')).text = '15. SYNTHETIC DEMO DATA: New section'
    body.insert(len(body)-1, heading)


def removed_section(root):
    body = root.find(W+'body')
    p = paragraph(root, 'REQUEST / PURPOSE')
    index = list(body).index(p)
    body.remove(body[index+1])  # section wrapper
    body.remove(p)


def mixed(root):
    font(root)
    guidance(root)
    header(root)


@pytest.fixture
def registry_api(tmp_path):
    folder = tmp_path/'template-fixtures'
    folder.mkdir()
    # Copy then label a header, retaining all configured section/table anchors.
    owner_copy = folder/'owner-copy.docx'
    owner_copy.write_bytes(OWNER.read_bytes())
    with ZipFile(owner_copy) as archive:
        header_part = next(n for n in archive.namelist() if n.startswith('word/header') and n.endswith('.xml'))
    def label(root):
        p = ET.Element(W+'p'); r = ET.SubElement(p, W+'r')
        ET.SubElement(r, W+'t').text = 'SYNTHETIC DEMO DATA'
        root.insert(0, p)
    baseline_bytes = mutate(owner_copy.read_bytes(), label, header_part)
    owner_copy.write_bytes(baseline_bytes)
    engine, sessions = create_database(tmp_path/'db.sqlite')
    storage = tmp_path/'blobs'
    with sessions.begin() as session:
        registry = TemplateRegistry(Repository(session), storage)
        baseline = registry.register('fig', 'v0.1', 'fixture.docx', baseline_bytes)
        registry.repo.save(s.TemplateActivation(team_id='fig', template_version_id=baseline.id,
            actor='synthetic test bootstrap', role='template admin'))
    with TestClient(create_app(sessions=sessions, template_storage_root=storage)) as client:
        yield client, baseline, baseline_bytes, sessions, storage, folder
    engine.dispose()
    assert sha256(OWNER.read_bytes()).hexdigest() == OWNER_HASH


def upload_compare(fixture, change, version='v0.2', part='word/document.xml'):
    client, baseline, content, _, _, folder = fixture
    path = folder/f'{version}.docx'
    path.write_bytes(mutate(content, change, part))
    response = client.post('/templates/fig', params={'display_version': version, 'filename': path.name,
                           'parent_id': baseline.id}, content=path.read_bytes())
    assert response.status_code == 200, response.text
    candidate = response.json()
    response = client.post(f'/templates/fig/{candidate["id"]}/compare', params={'expected_active_id': baseline.id})
    assert response.status_code == 200, response.text
    comparison = response.json()
    assert client.get('/templates/fig/active').json()['id'] == baseline.id
    assert client.get(f'/templates/fig/{baseline.id}/source').content == content
    assert client.get(f'/templates/fig/{candidate["id"]}/source').content == path.read_bytes()
    assert client.post(f'/templates/fig/{candidate["id"]}/activate').status_code == 404
    return candidate, comparison


@pytest.mark.parametrize('change,category', [(font,'formatting'), (colour,'formatting'),
    (guidance,'prompt'), (header,'code'), (column,'code'), (added_section,'code'), (removed_section,'code'), (mixed,'code')])
def test_required_variants_and_it_export(registry_api, change, category):
    client, baseline, _, _, _, _ = registry_api
    candidate, comparison = upload_compare(registry_api, change)
    report = comparison['report']
    assert report['category'] == category
    assert report['formatting_only'] == (category == 'formatting')
    assert report['requires_it'] == (category != 'formatting')
    assert not report['activation_available']
    assert report['changes'] and all(c['reason'] and c['anchor'] for c in report['changes'])
    if change == mixed:
        assert all(report['counts'][c] > 0 for c in ('formatting','prompt','code'))
    if change == header:
        item = next(c for c in report['changes'] if c['before'] == 'Key terms')
        assert item['after'] == 'Facility terms' and item['section_id'] == 7
        assert item['anchor'] == 's7.facilities'
    if change == added_section:
        assert any(c['section_id'] == 15 for c in report['changes'])
    if change == removed_section:
        assert all(c['section_id'] == 1 for c in report['changes'])
    if change == guidance:
        assert report['candidate']['parse_gaps']  # changing the configured anchor also requires review
        assert any('prompts.yaml' in f for c in report['changes'] for f in c['affected_files'])
    base = f'/templates/fig/{candidate["id"]}/comparisons/{comparison["id"]}'
    assert client.get(base).json() == comparison
    export = client.get(base+'/it-change-list')
    assert export.status_code == 200 and 'attachment;' in export.headers['content-disposition']
    assert comparison['id'] in export.text and baseline.content_hash in export.text
    assert candidate['content_hash'] in export.text and 'candidate remains inactive' in export.text
    for c in report['changes']:
        if c['category'] != 'formatting':
            assert c['reason'] in export.text
            assert json.dumps(c['before'], ensure_ascii=False) in export.text
            assert json.dumps(c['after'], ensure_ascii=False) in export.text
            assert all(f in export.text for f in c['affected_files'])
        else:
            assert c['reason'] not in export.text


def test_styles_font_and_colour_are_formatting(registry_api):
    def style(root):
        props = root.find(W+'docDefaults/'+W+'rPrDefault/'+W+'rPr')
        node = props.find(W+'color')
        if node is None:
            node = ET.SubElement(props, W+'color')
        node.set(W+'val', 'AA3322')
    _, result = upload_compare(registry_api, style, part='word/styles.xml')
    assert result['report']['category'] == 'formatting'
    assert result['report']['formatting_only']


@pytest.mark.parametrize('kind', ['formula','duplicate','merge','italic','relationship','sample','unknown_property'])
def test_ambiguous_semantic_and_unsupported_changes_require_code(registry_api, kind):
    part = 'word/document.xml'
    def change(root):
        if kind == 'formula':
            next(paragraph(root, '[To provide details of the request]').iter(W+'t')).text = '[Calculate DSCR = income / debt service]'
        elif kind == 'duplicate':
            root.find(W+'body').append(deepcopy(paragraph(root, 'REQUEST / PURPOSE')))
        elif kind == 'merge':
            cell = table(root).find(W+'tr/'+W+'tc')
            props = cell.find(W+'tcPr')
            node = props.find(W+'gridSpan')
            if node is None:
                node = ET.SubElement(props, W+'gridSpan')
            node.set(W+'val', '2')
        elif kind == 'italic':
            for i in paragraph(root, '[To provide details of the request]').iter(W+'i'):
                i.set(W+'val', '0')
        elif kind == 'relationship':
            root[0].set('Target', 'https://example.invalid/never-fetched')
        elif kind == 'sample':
            next(paragraph(root, '100.0').iter(W+'t')).text = '99.0'
        else:
            ET.SubElement(next(root.iter(W+'rPr')), W+'vanish')
    if kind == 'relationship':
        part = 'word/_rels/document.xml.rels'
    _, result = upload_compare(registry_api, change, part=part)
    assert result['report']['category'] == 'code'
    assert result['report']['requires_it'] and not result['report']['formatting_only']


def test_unchanged_reserialization_and_no_active(registry_api, tmp_path):
    _, result = upload_compare(registry_api, lambda root: None)
    assert result['report']['category'] == 'unchanged' and result['report']['changes'] == []
    engine, sessions = create_database(tmp_path/'empty.sqlite')
    try:
        with TestClient(create_app(sessions=sessions, template_storage_root=tmp_path/'empty')) as client:
            version = client.post('/templates/fig', params={'display_version':'v0.1','filename':'x.docx'}, content=OWNER.read_bytes()).json()
            assert client.post(f'/templates/fig/{version["id"]}/compare').status_code == 409
    finally:
        engine.dispose()


def test_comparisons_dedup_restart_immutable_and_scoped(registry_api):
    client, baseline, _, sessions, storage, _ = registry_api
    candidate, comparison = upload_compare(registry_api, header)
    endpoint = f'/templates/fig/{candidate["id"]}/compare'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(endpoint), range(2)))
    assert all(r.status_code == 200 and r.json() == comparison for r in results)
    assert client.post(endpoint, params={'expected_active_id':'stale'}).status_code == 409
    assert client.post(f'/templates/fig/{baseline.id}/compare').status_code == 422
    assert client.post('/templates/fig/missing/compare').status_code == 404
    assert client.post(f'/templates/other/{candidate["id"]}/compare').status_code == 404
    path = f'/templates/fig/{candidate["id"]}/comparisons/{comparison["id"]}'
    assert client.get(path.replace(candidate['id'], baseline.id)).status_code == 404
    assert client.get(path.replace('/fig/', '/other/')).status_code == 404
    assert client.get(path.replace(comparison['id'], 'missing')).status_code == 404
    with sessions() as session:
        registry = TemplateRegistry(Repository(session), storage)
        saved = registry.comparison('fig', candidate['id'], comparison['id'])
        assert len(list(session.scalars(select(models.TemplateComparison)))) == 1
        with pytest.raises(ValueError, match='append-only'):
            registry.repo.save(saved)
        with pytest.raises(IntegrityError, match='immutable'):
            session.execute(text('DELETE FROM template_comparison WHERE id=:id'), {'id':saved.id})
    with TestClient(create_app(sessions=sessions, template_storage_root=storage)) as restarted:
        assert restarted.get(path).json() == comparison
        old_export = restarted.get(path+'/it-change-list').content
        Path(candidate['storage_path']).write_bytes(b'corrupt')
        assert restarted.post(endpoint).status_code == 409
        # Historical report is still readable; creating another diff verifies bytes.
        assert restarted.get(path+'/it-change-list').content == old_export


def test_baseline_is_current_active_not_candidate_parent_and_old_report_preserved(registry_api):
    client, baseline, content, sessions, storage, _ = registry_api
    candidate, original = upload_compare(registry_api, header)
    assert candidate['parent_id'] == baseline.id
    with sessions.begin() as session:
        registry = TemplateRegistry(Repository(session), storage)
        other = registry.register('fig','v0.3','x.docx',mutate(content, colour), baseline.id)
        registry.repo.save(s.TemplateActivation(team_id='fig', template_version_id=other.id,
            expected_previous_id=baseline.id, actor='synthetic test setup', role='template admin'))
    endpoint = f'/templates/fig/{candidate["id"]}/compare'
    assert client.post(endpoint, params={'expected_active_id':baseline.id}).status_code == 409
    current = client.post(endpoint).json()
    assert current['baseline_version_id'] == other.id and current['id'] != original['id']
    assert current['report']['counts']['formatting'] > 0
    historical = client.get(f'/templates/fig/{candidate["id"]}/comparisons/{original["id"]}').json()
    assert historical == original
    assert client.get('/templates/fig/active').json()['id'] == other.id


def test_changed_configuration_is_explicit_review_and_does_not_rewrite_maps(registry_api):
    _, baseline, _, sessions, storage, _ = registry_api
    candidate, _ = upload_compare(registry_api, font)
    def config_loader(team):
        config = load_team(team).model_copy(deep=True)
        config.template.version = 'v0.9'
        return config
    with sessions.begin() as session:
        registry = TemplateRegistry(Repository(session, config_loader), storage)
        comparison = registry.compare('fig', candidate['id'])
        assert comparison.report['category'] == 'code'
        assert any('different parser/mapping rules' in c['reason'] for c in comparison.report['changes'])
        assert registry.get('fig', baseline.id).parsed_map == baseline.parsed_map


def test_no_activation_eligibility_with_inherited_mapping_gaps(registry_api):
    _, baseline, content, sessions, storage, _ = registry_api
    with sessions.begin() as session:
        registry = TemplateRegistry(Repository(session), storage)
        broken = registry.register('fig', 'v0.3', 'x.docx', mutate(content, header))
        registry.repo.save(s.TemplateActivation(team_id='fig', template_version_id=broken.id,
            expected_previous_id=baseline.id, actor='synthetic test setup', role='template admin'))
        candidate = registry.register('fig', 'v0.4', 'x.docx', mutate(mutate(content, header), font))
        report = registry.compare('fig', candidate.id).report
        assert report['category'] == 'formatting'
        assert report['candidate']['parse_gaps'] and report['baseline']['parse_gaps']
        assert not report['formatting_only'] and report['requires_it']


def test_corrupt_baseline_is_rejected_and_persistence_required(registry_api):
    client, baseline, _, _, _, _ = registry_api
    candidate, _ = upload_compare(registry_api, font)
    Path(baseline.storage_path).write_bytes(b'corrupt baseline')
    assert client.post(f'/templates/fig/{candidate["id"]}/compare').status_code == 409
    with TestClient(create_app()) as empty:
        assert empty.post('/templates/fig/missing/compare').status_code == 503


def test_historical_comparison_sql_update_is_blocked(registry_api):
    _, _, _, sessions, _, _ = registry_api
    _, comparison = upload_compare(registry_api, guidance)
    with sessions() as session:
        with pytest.raises(IntegrityError, match='immutable'):
            session.execute(text("UPDATE template_comparison SET report='{}' WHERE id=:id"), {'id':comparison['id']})
