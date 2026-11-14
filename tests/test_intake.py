import asyncio
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode

import fitz
import pytest
import yaml
from sqlalchemy import text

from backend.app import schemas
from backend.app.database import create_database
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.intake import IntakeError, IntakeService, Metadata, period_key
from backend.app.team_config import load_team

ROOT = Path(__file__).resolve().parents[1]


def make_case(repo, **changes):
    config = load_team('fig')
    return repo.save(schemas.Case(**(dict(borrower_name='Demo REIT', team_id='fig',
        config_version=config.template.version, config_hash=config.content_hash,
        case_type='renewal', borrower_type='reit', existing_client=True, new_to_bank=False) | changes)))


def source(period='2026-10-31', entity='Demo REIT', extra=''):
    return f'SYNTHETIC DEMO DATA\nValuation report\nBorrower: {entity}\nPeriod: {period}\n{extra}'.encode()


@pytest.fixture
def intake(database, tmp_path):
    repo = Repository(database)
    case = make_case(repo)
    folder = tmp_path / 'inbox'
    folder.mkdir()
    service = IntakeService(repo, tmp_path / 'blobs', {'demo': folder})
    return service, case, folder


def test_upload_scan_dedup_case_isolation_and_restart(intake, database):
    service, case, folder = intake
    content = source()
    result = service.ingest(case.id, 'valuation.txt', content)
    doc = result.document
    assert result.outcome == 'created'
    assert (doc.catalogue_id, doc.entity, doc.period, doc.synthetic, doc.conflict_status) == (9, 'Demo REIT', '2026-10-31', True, 'none')
    assert Path(doc.storage_path).read_bytes() == content
    assert doc.content_hash == sha256(content).hexdigest()
    assert doc.confirmed_by is None
    assert service.repository.get(schemas.Case, case.id).first_upload_at == doc.created_at
    (folder / 'renamed.txt').write_bytes(content)
    assert service.scan(case.id, 'demo')[0].document == doc
    assert service.scan(case.id, 'demo')[0].outcome == 'duplicate'
    assert service.ingest(case.id, 'again.txt', content, metadata={'entity': 'Other'}).document == doc
    other = make_case(service.repository)
    other_doc = service.scan(other.id, 'demo')[0].document
    assert other_doc.origin == 'folder' and other_doc.id != doc.id
    assert other_doc.storage_path == doc.storage_path
    database.commit()
    database.expunge_all()
    fresh = IntakeService(Repository(database), service.storage_root, service.folders)
    assert fresh.scan(case.id, 'demo')[0].document == doc
    assert len(fresh.repository.list_for_case(schemas.Document, case.id)) == 1


def test_newer_revision_old_and_wrong_entity_never_replace(intake):
    service, case, _ = intake
    first = service.ingest(case.id, 'valuation.txt', source()).document
    # CA confirmation remains on the historical version, not inherited by v2.
    first = service.repository.save(first.model_copy(update={'confirmed_by': 'demo-ca', 'confirmed_at': schemas.utcnow()}))
    newer = service.ingest(case.id, 'valuation_v2.txt', source('2026-11-09')).document
    assert newer.supersedes_id == first.id and newer.revision == 2
    assert newer.confirmed_by is None and newer.conflict_status == 'none'
    old = service.ingest(case.id, 'old.txt', source('2025-10-31')).document
    wrong = service.ingest(case.id, 'wrong.txt', source(entity='Other REIT')).document
    same = service.ingest(case.id, 'amended.txt', source('2026-11-09', extra='New text')).document
    for doc, reason in [(old, 'older_period'), (wrong, 'wrong_entity'), (same, 'same_period_changed')]:
        assert doc.conflict_status == 'pending' and doc.supersedes_id is None
        assert any(reason in issue for issue in doc.intake['issues'])
    assert service.repository.get(schemas.Document, first.id) == first
    assert service.repository.get(schemas.Document, newer.id) == newer
    final = service.ingest(case.id, 'newest.txt', source('2026-12-31')).document
    assert final.supersedes_id == newer.id
    # Independent property reports can explicitly use distinct scopes.
    separate = service.ingest(case.id, 'property_b.txt', source('2026-11-09', extra='Property B'), metadata={'scope': 'property B'}).document
    assert separate.revision == 1 and separate.supersedes_id is None


def test_classification_hints_do_not_override_observed_conflicts(intake):
    service, case, _ = intake
    doc = service.ingest(case.id, 'valuation.txt', source(entity='Other REIT'), metadata={
        'catalogue_id': 2, 'entity': 'Demo REIT', 'period': '2025-01-01'}).document
    assert doc.entity == 'Other REIT'
    for code in ('type_mismatch', 'entity_mismatch', 'wrong_entity', 'period_mismatch'):
        assert any(code in issue for issue in doc.intake['issues'])
    with pytest.raises(IntakeError, match='catalogue'):
        service.ingest(case.id, 'x.txt', source(), metadata={'catalogue_id': 99})
    with pytest.raises(IntakeError, match='suggestion'):
        service.ingest(case.id, 'x.txt', source(), metadata={'suggestion_id': 'invented'})


@pytest.mark.parametrize('name,content,code', [
    ('scan.pdf', None, 'no_text'), ('broken.pdf', b'not a pdf', 'unreadable'),
    ('broken.docx', b'PKbroken', 'unreadable'), ('broken.xlsx', b'PKbroken', 'unreadable'),
    ('opaque.bin', b'bytes', 'unsupported_format'), ('binary.txt', b'\x00', 'unreadable'),
])
def test_unreadable_files_are_persisted_review_gaps(intake, name, content, code):
    service, case, _ = intake
    if content is None:
        with fitz.open() as pdf:
            pdf.new_page()
            content = pdf.tobytes()
    doc = service.ingest(case.id, name, content, metadata={'catalogue_id': 9, 'entity': 'Demo REIT', 'period': '2026'}).document
    assert doc.conflict_status == 'pending'
    assert any(code in issue for issue in doc.intake['issues'])
    assert Path(doc.storage_path).read_bytes() == content
    assert service.ingest(case.id, name, content).outcome == 'duplicate'


def test_limits_traversal_and_folder_boundaries(intake):
    service, case, folder = intake
    for name in ('../x.txt', '/x.txt', 'x\\y.txt', 'x\x00.txt'):
        with pytest.raises(IntakeError, match='filename'):
            service.ingest(case.id, name, source())
    with pytest.raises(IntakeError, match='empty'):
        service.ingest(case.id, 'empty.txt', b'')
    service.max_bytes = 200
    with pytest.raises(IntakeError, match='limit'):
        service.ingest(case.id, 'large.txt', b'x' * 201)
    with pytest.raises(IntakeError, match='folder ID'):
        service.scan(case.id, '../')
    outside = folder.parent / 'outside.txt'
    outside.write_bytes(source())
    (folder / 'link.txt').symlink_to(outside)
    (folder / 'ok.txt').write_bytes(source())
    (folder / 'large.txt').write_bytes(b'x' * 201)
    (folder / 'sub').mkdir()
    (folder / 'sub' / 'copy.txt').write_bytes(source())
    results = service.scan(case.id, 'demo')
    assert [(r.filename, r.outcome) for r in results] == [
        ('large.txt', 'rejected'), ('link.txt', 'rejected'), ('ok.txt', 'created'), ('sub/copy.txt', 'duplicate')]
    assert len(service.repository.list_for_case(schemas.Document, case.id)) == 1


def test_actual_synthetic_pack_all_formats_match_both_routes(intake):
    service, _, folder = intake
    upload_case = make_case(service.repository, borrower_name='ESR-REIT')
    scan_case = make_case(service.repository, borrower_name='ESR-REIT')
    pack = ROOT / 'demo/synthetic'
    manifest = yaml.safe_load((pack / 'manifest.yaml').read_text())
    hints_by_path = {}
    uploads = {}
    # Preserve tranche order so late valuation follows its original.
    for entry in sorted(manifest['documents'], key=lambda e: (e.get('revision', 1), str(e.get('tranche', 4)))):
        path = pack / entry['file']
        hint = {'entity': entry['entity'], 'period': entry.get('period_end', entry['date']), 'synthetic': True}
        if entry.get('catalogue_id'):
            hint['catalogue_id'] = entry['catalogue_id']
        else:
            hint['suggestion_id'] = entry['suggestion_id']
        document = service.ingest(upload_case.id, path.name, path.read_bytes(), metadata=hint).document
        assert document.synthetic and 'unreadable' not in ' '.join(document.intake['issues'])
        assert document.catalogue_id == entry.get('catalogue_id')
        uploads[path.name] = document
        target = folder / entry['file']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        hints_by_path[entry['file']] = hint
    scanned = service.scan(scan_case.id, 'demo', hints_by_path)
    assert len(scanned) == 17
    for result in scanned:
        assert result.outcome == 'created'
        actual = result.document
        expected = uploads[Path(result.filename).name]
        for field in ('content_hash', 'catalogue_id', 'suggestion_id', 'entity', 'period', 'synthetic'):
            assert getattr(actual, field) == getattr(expected, field)
    assert all(r.outcome == 'duplicate' for r in service.scan(scan_case.id, 'demo', hints_by_path))
    assert uploads['valuation_v2.pdf'].supersedes_id == uploads['valuation_v1.pdf'].id


def test_existing_b01_database_additive_upgrade_and_immutability(tmp_path):
    path = tmp_path / 'old.sqlite'
    engine, sessions = create_database(path)
    with sessions.begin() as session:
        service = IntakeService(Repository(session), tmp_path / 'blobs')
        case = make_case(service.repository)
        doc = service.ingest(case.id, 'valuation.txt', source()).document
    with engine.begin() as connection:
        connection.exec_driver_sql('DROP TRIGGER immutable_document_content')
        connection.exec_driver_sql('ALTER TABLE document DROP COLUMN intake')
    engine.dispose()
    engine, sessions = create_database(path)
    try:
        with sessions.begin() as session:
            repo = Repository(session)
            old = repo.get(schemas.Document, doc.id)
            assert old.intake == {} and old.content_hash == doc.content_hash
            with pytest.raises(ValueError, match='immutable'):
                repo.save(old.model_copy(update={'intake': {'changed': True}}))
        with engine.begin() as connection:
            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError, match='immutable'):
                connection.execute(text('UPDATE document SET intake = :data'), {'data': '{"changed":true}'})
    finally:
        engine.dispose()


def request(app, method, path, body=b'', query=None):
    messages = []
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    async def send(message):
        messages.append(message)
    asyncio.run(app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
        'method': method, 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
        'query_string': urlencode(query or {}).encode(), 'headers': [(b'content-type', b'application/json')],
        'server': ('test', 80), 'client': ('test', 1), 'root_path': ''}, receive, send))
    return messages[0]['status'], json.loads(b''.join(m.get('body', b'') for m in messages[1:]))


def test_api_upload_scan_list_and_failures(tmp_path):
    engine, sessions = create_database(tmp_path / 'api.sqlite')
    try:
        with sessions.begin() as session:
            case = make_case(Repository(session))
        folder = tmp_path / 'inbox'
        folder.mkdir()
        (folder / 'valuation.txt').write_bytes(source())
        app = create_app(sessions=sessions, storage_root=tmp_path / 'blobs', intake_folders={'inbox': folder})
        path = f'/cases/{case.id}/documents'
        status, result = request(app, 'POST', path, source(), {'filename': 'valuation.txt'})
        assert status == 200 and result['outcome'] == 'created'
        status, result = request(app, 'POST', path + '/scan', json.dumps({'folder_id': 'inbox'}).encode())
        assert status == 200 and result[0]['outcome'] == 'duplicate'
        status, result = request(app, 'GET', path)
        assert status == 200 and len(result) == 1
        assert request(app, 'POST', path, source(), {'filename': '../bad.txt'})[0] == 422
        assert request(app, 'POST', path, source(), {'filename': 'x.txt', 'metadata': '{bad'})[0] == 422
        assert request(app, 'POST', path + '/scan', b'{"folder_id":"/etc"}')[0] == 422
        assert request(app, 'GET', '/cases/unknown/documents')[0] == 404
        assert request(create_app(), 'GET', path)[0] == 503
        assert request(app, 'GET', path)[1][0]['origin'] == 'upload'
    finally:
        engine.dispose()


def test_period_comparisons_are_dates_not_lexical():
    assert period_key('FY2025') == period_key('2025-12-31')
    assert period_key('2026-Q1') < period_key('2026-Q3') < period_key('2026')
    assert period_key('2026-99-42') is None
    with pytest.raises(ValueError, match='Period'):
        Metadata(period='recent')


def test_corrupt_stored_duplicate_fails_closed(intake):
    service, case, _ = intake
    doc = service.ingest(case.id, 'valuation.txt', source()).document
    Path(doc.storage_path).write_bytes(b'corrupt')
    with pytest.raises(IntakeError, match='integrity'):
        service.ingest(case.id, 'renamed.txt', source())
    assert len(service.repository.list_for_case(schemas.Document, case.id)) == 1


def test_entity_mentions_and_external_rating_require_review(intake):
    service, case, _ = intake
    content = b'SYNTHETIC DEMO DATA\nExternal credit rating report\nBorrower: Demo REIT\nPeriod: 2026\nAgency opinion'
    doc = service.ingest(case.id, 'rating.txt', content).document
    assert doc.conflict_status == 'pending'
    assert any('rating_scope' in issue for issue in doc.intake['issues'])
    other = service.ingest(case.id, 'annual_report.txt', b'SYNTHETIC DEMO DATA\nAnnual report\nOther issuer\nPeriod: 2026\nA reference to Demo REIT as a competitor.').document
    assert other.catalogue_id == 4
    assert other.entity == '' and any('unknown_entity' in issue for issue in other.intake['issues'])


def test_folder_revisions_match_upload_when_files_arrive_progressively(intake):
    service, case, folder = intake
    upload = make_case(service.repository)
    prior_folder = prior_upload = None
    for period in ('2026-10-31', '2026-11-09'):
        (folder / 'valuation.txt').write_bytes(source(period))
        folder_doc = service.scan(case.id, 'demo')[0].document
        upload_doc = service.ingest(upload.id, 'valuation.txt', source(period)).document
        assert folder_doc.revision == upload_doc.revision
        assert folder_doc.conflict_status == upload_doc.conflict_status == 'none'
        assert folder_doc.supersedes_id == prior_folder
        assert upload_doc.supersedes_id == prior_upload
        prior_folder, prior_upload = folder_doc.id, upload_doc.id
    assert service.scan(case.id, 'demo')[0].outcome == 'duplicate'


def test_concurrent_api_uploads_create_one_version(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    engine, sessions = create_database(tmp_path / 'concurrent.sqlite')
    try:
        with sessions.begin() as session:
            case = make_case(Repository(session))
        app = create_app(sessions=sessions, storage_root=tmp_path / 'blobs')
        def upload(_):
            return request(app, 'POST', f'/cases/{case.id}/documents', source(), {'filename': 'valuation.txt'})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(upload, range(2)))
        assert all(status == 200 for status, _ in results)
        assert sorted(result['outcome'] for _, result in results) == ['created', 'duplicate']
        assert len({result['document']['id'] for _, result in results}) == 1
    finally:
        engine.dispose()
