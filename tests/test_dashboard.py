"""Gate 1 acceptance through the HTTP contracts used by the dashboard, offline."""
import asyncio
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode

import pytest

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.local import demo_settings, seed_case
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.search import SavedPublicPackProvider
from test_intake import request

ROOT = Path(__file__).resolve().parents[1]
CA = json.dumps({'actor': 'gate1-ca', 'role': 'CA'}).encode()


def raw_request(app, path, query=None):
    messages = []
    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}
    async def send(message):
        messages.append(message)
    asyncio.run(app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
        'method': 'GET', 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
        'query_string': urlencode(query or {}).encode(), 'headers': [],
        'server': ('test', 80), 'client': ('test', 1), 'root_path': ''}, receive, send))
    return messages[0]['status'], dict(messages[0]['headers']), b''.join(m.get('body', b'') for m in messages[1:])


@pytest.fixture
def dashboard_app(tmp_path):
    engine, sessions = create_database(tmp_path / 'dashboard.sqlite')
    case = seed_case(sessions)
    _, folders, options, presets = demo_settings()
    def app():
        return create_app(sessions=sessions, storage_root=tmp_path / 'blobs', intake_folders=folders,
            search_provider=SavedPublicPackProvider(), dashboard_folders=options,
            intake_presets=presets, demo_case_ids=(case.id,))
    try:
        yield app(), sessions, case, app
    finally:
        engine.dispose()


def get_snapshot(app, case):
    status, data = request(app, 'GET', f'/cases/{case.id}/dashboard')
    assert status == 200
    assert len(data['sections']) == 14
    assert all(section['name'] for section in data['sections'])
    assert len([e for e in data['expected_documents'] if e['catalogue_id']]) == 22
    assert not any('storage_path' in doc for doc in data['documents'])
    return data


def section_states(data):
    return {s['section_id']: s['readiness'] for s in data['sections']}


def input_row(data, catalogue_id):
    return next(e for e in data['expected_documents'] if e['catalogue_id'] == catalogue_id)


def ingest_tranche(app, case, data, tranche, route):
    prefix = f'/cases/{case.id}'
    if route == 'scan':
        folder = next(f for f in data['intake']['folders'] if f['id'] == f'tranche_{tranche}')
        status, results = request(app, 'POST', prefix + '/documents/scan', json.dumps({
            'folder_id': folder['id'], 'metadata_by_path': folder['metadata_by_path']}).encode())
        assert status == 200
        return results
    results = []
    for preset in data['intake']['presets']:
        if preset['tranche'] != tranche:
            continue
        content = (ROOT / 'demo/synthetic' / f'tranche_{tranche}' / preset['filename']).read_bytes()
        assert sha256(content).hexdigest() == preset['sha256']
        status, result = request(app, 'POST', prefix + '/documents', content,
            query={'filename': preset['filename'], 'metadata': json.dumps(preset['metadata'])})
        assert status == 200
        results.append(result)
    return results


@pytest.mark.parametrize('route', ['upload', 'scan'])
def test_dashboard_three_tranches_real_services_and_restart(dashboard_app, route, tmp_path):
    app, sessions, case, restart = dashboard_app
    prefix = f'/cases/{case.id}'
    status, cases = request(app, 'GET', '/cases')
    assert status == 200 and cases[0]['id'] == case.id
    data = get_snapshot(app, case)
    assert data['synthetic_demo'] and data['search_mode'] == 'saved-pack'
    assert not data['documents'] and data['counts']['draftable'] == 0
    for tranche, count in ((1, 2), (2, 12), (3, 2)):
        results = ingest_tranche(app, case, data, tranche, route)
        assert len(results) == count
        assert all(r['outcome'] == 'created' and r['document']['conflict_status'] == 'none' for r in results)
        assert all(r['document']['synthetic'] for r in results)
        duplicates = ingest_tranche(app, case, data, tranche, route)
        assert all(r['outcome'] == 'duplicate' for r in duplicates)
        if tranche == 1:
            status, result = request(app, 'POST', prefix + '/public-search', CA)
            assert status == 200 and result['search']['outcome'] == 'found'
            data = get_snapshot(app, case)
            assert data['counts']['documents']['Provided'] == 2
            assert data['counts']['documents']['Found publicly'] == 6
            assert {4, 5, 6, 7, 10} <= {n for n, state in section_states(data).items() if state.startswith('Can draft')}
            assert section_states(data)[8] == section_states(data)[9] == 'Can draft (partial)'
            for doc in data['documents']:
                if doc['origin'] == 'public':
                    assert doc['url'] and doc['retrieved_at'] and doc['intake']['cached']
                    assert not doc['confirmed_by']
                    assert request(app, 'POST', prefix + f"/documents/{doc['id']}/confirm", CA)[0] == 200
            data = get_snapshot(app, case)
            assert section_states(data)[5] == section_states(data)[6] == 'Can draft (full)'
            assert all(not input_row(data, i)['satisfied'] for i in (7, 9, 10, 16, 19))
            assert all(not offer['execution_available'] for offer in data['generation_offers'])
        data = get_snapshot(app, case)
        states = section_states(data)
        if tranche >= 2:
            assert all(states[i] == 'Can draft (full)' for i in (1, 2, 3, 7, 8))
            assert states[9] == states[10] == states[11] == 'Can draft (partial)'
        if tranche < 3:
            assert states[12] == states[13] == 'Waiting for input'
            assert not input_row(data, 10)['satisfied']
        else:
            assert states[12] == states[13] == 'Can draft (full)'
            assert input_row(data, 10)['status'] == 'Provided' and input_row(data, 10)['satisfied']
        assert states[14] == 'Waiting for input'
        # Capture the response for optional rendered UI checks without an invented spread.
        (tmp_path / f'tranche-{tranche}.json').write_text(json.dumps(data))
        assert get_snapshot(restart(), case) == data
    with sessions() as session:
        repo = Repository(session)
        assert not repo.list_for_case(s.Spread, case.id)
        assert not repo.list_for_case(s.DraftVersion, case.id)
        assert repo.get(s.Case, case.id).ca_position is None
    status, headers, body = raw_request(app, prefix + '/request-list')
    assert status == 200 and b'attachment' in headers[b'content-disposition']
    assert all(owner.encode() in body for owner in ('RM', 'client', 'internal team'))
    assert b'Financial spread' in body and b'Industry code' in body
    assert seed_case(sessions).id == case.id
    assert get_snapshot(app, case) == data  # Restart/seed does not reset a working case.


def test_dashboard_dismiss_restore_and_pending_inputs(dashboard_app):
    app, _, case, _ = dashboard_app
    data = get_snapshot(app, case)
    item = input_row(data, 1)
    prefix = f'/cases/{case.id}'
    for action in ('dismiss', 'restore'):
        status, _ = request(app, 'POST', prefix + f"/expected-documents/{item['id']}/{action}",
            json.dumps(dict(actor='gate1-ca', role='CA', reason='Requested from RM for demo')).encode())
        assert status == 200
        data = get_snapshot(app, case)
        assert input_row(data, 1)['status'] == ('Dismissed' if action == 'dismiss' else 'Missing')
        assert not input_row(data, 1)['satisfied']
        assert any(e['catalogue_id'] == 1 for e in data['gaps']['RM'])
    bad = b'SYNTHETIC DEMO DATA\nTerm sheet for Other Company\n2026-11-02'
    status, result = request(app, 'POST', prefix + '/documents', bad, query={
        'filename': 'term_sheet.txt', 'metadata': json.dumps(dict(catalogue_id=2, entity='Other Company', period='2026-11-02'))})
    assert status == 200 and result['document']['conflict_status'] == 'pending'
    data = get_snapshot(app, case)
    assert not data['documents'][0]['current'] and data['documents'][0]['intake']['issues']
    assert input_row(data, 2)['status'] == 'Missing'
    assert any('Manual review' in detail for detail in input_row(data, 2)['details'])


def test_content_exact_bytes_cross_case_hash_and_format_guards(dashboard_app, tmp_path):
    app, sessions, case, _ = dashboard_app
    data = get_snapshot(app, case)
    results = ingest_tranche(app, case, data, 1, 'upload')
    pdf = next(r['document'] for r in results if r['filename'].endswith('.pdf'))
    eml = next(r['document'] for r in results if r['filename'].endswith('.eml'))
    path = f"/cases/{case.id}/documents/{pdf['id']}/content"
    status, headers, body = raw_request(app, path, {'preview': 'true'})
    assert status == 200 and headers[b'content-type'] == b'application/pdf'
    assert headers[b'x-content-type-options'] == b'nosniff' and headers[b'cache-control'] == b'no-store'
    assert sha256(body).hexdigest() == pdf['content_hash']
    status, headers, body = raw_request(app, path)
    assert status == 200 and b'attachment' in headers[b'content-disposition']
    assert raw_request(app, f"/cases/{case.id}/documents/{eml['id']}/content", {'preview': 'true'})[0] == 415
    assert raw_request(app, f"/cases/{case.id}/documents/unknown/content")[0] == 404
    with sessions.begin() as session:
        repo = Repository(session)
        other = repo.save(case.model_copy(update={'id': 'other-case'}))
    assert raw_request(app, path.replace(case.id, other.id))[0] == 404
    assert not get_snapshot(app, other)['synthetic_demo']
    assert raw_request(app, path.replace(case.id, 'missing-case'))[0] == 404
    stored = Path(pdf['storage_path'])
    stored.write_bytes(b'corrupt')
    assert raw_request(app, path)[0] == 409
    # A valid hash alone must not authorize a path outside configured storage.
    outside = tmp_path / 'outside.txt'
    outside.write_bytes(b'SYNTHETIC DEMO DATA\nNot in blob storage')
    with sessions.begin() as session:
        doc = Repository(session).save(s.Document(case_id=case.id, catalogue_id=1, entity=case.borrower_name,
            content_hash=sha256(outside.read_bytes()).hexdigest(), storage_path=str(outside),
            original_filename='outside.txt', origin='upload', synthetic=True))
    assert raw_request(app, f'/cases/{case.id}/documents/{doc.id}/content')[0] == 409


def test_dashboard_not_configured_and_unknown_case(dashboard_app):
    app, _, _, _ = dashboard_app
    assert request(create_app(), 'GET', '/cases')[0] == 503
    assert request(create_app(), 'GET', '/cases/x/dashboard')[0] == 503
    assert request(app, 'GET', '/cases/missing/dashboard')[0] == 404
