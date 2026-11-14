"""B15 three-tranche dashboard, history/chat/Stale/export integration, offline."""
import pytest
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from backend.app import schemas as s
from backend.app.local import create_demo_app, seed_case
from backend.app.repository import Repository
from backend.app.database import create_database
from test_dashboard import get_snapshot, ingest_tranche, raw_request
from test_intake import request

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_gate2_three_tranches_chat_history_stale_and_pinned_export(tmp_path):
    app = create_demo_app(tmp_path)
    engine, sessions = create_database(tmp_path / 'wb_credit.sqlite')
    case = seed_case(sessions)
    prefix = f'/cases/{case.id}'
    actor = dict(actor='gate2-ca', role='CA')

    def get(path):
        status, body = request(app, 'GET', prefix + path)
        assert status == 200, body
        return body

    def post(path, body=None, expected=200):
        status, result = request(app, 'POST', prefix + path, json.dumps(body or actor).encode())
        assert status == expected, result
        return result

    def history(sid):
        return get(f'/sections/{sid}/history')

    def token(sid):
        sec = history(sid)['section']
        return actor | dict(expected_draft_id=sec['current_draft_id'], expected_revision=sec['editor_revision'],
                            expected_input_fingerprint=sec['input_fingerprint'])

    def draft(sid, **kw):
        state = history(sid)['section']
        if state['current_draft_id']:
            return post(f'/sections/{sid}/redraft', token(sid) | kw)
        return post(f'/drafts/sections/{sid}', actor | kw)

    def snapshot(name):
        value = get_snapshot(app, case)
        (tmp_path / f'{name}.json').write_text(json.dumps(value))
        return value

    try:
        data = snapshot('empty')
        assert data['demo_spread_available']
        post('/demo/spread', expected=422)
        ingest_tranche(app, case, data, 1, 'scan')
        post('/public-search')
        post('/demo/spread', expected=422)  # Never silently confirm public evidence.
        for doc in get('/dashboard')['documents']:
            if doc['origin'] == 'public':
                post(f"/documents/{doc['id']}/confirm")
        spread = post('/demo/spread')
        assert spread['spread']['validation_status'] == 'valid'
        assert next(v for v in spread['computed_values'] if v['metric'] == 'npi' and v['period'] == '2025')['value'] == '328679000'
        post('/demo/spread', dict(actor='head', role='Credit Head'), expected=403)
        assert request(app, 'POST', '/cases/other/demo/spread', json.dumps(actor).encode())[0] == 404
        for sid in (4, 5, 6, 7, 10, 8, 9):
            draft(sid, **({'confirm_unsecured': True} if sid in (7, 8) else {}))
        data = snapshot('tranche-1')
        assert sum(bool(s['current_draft_id']) for s in data['sections']) == 7
        assert all(not s['current_draft_id'] for s in data['sections'] if s['section_id'] in (12, 13, 14))
        assert any(e['catalogue_id'] == 19 and not e['satisfied'] for e in data['expected_documents'])
        ingest_tranche(app, case, data, 2, 'scan')
        for sid in (1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11):
            draft(sid, **({'confirm_unsecured': True} if sid in (7, 8) else {}))
        data = snapshot('tranche-2')
        assert sum(bool(s['current_draft_id']) for s in data['sections']) == 11
        # A proposal has no effect until accepted; rejection preserves the saved draft.
        before = history(8)
        proposal = post('/sections/8/chat', token(8) | dict(message='Legal review remains pending.', mode='fact', synthetic=True))
        assert history(8)['section']['current_draft_id'] == before['section']['current_draft_id']
        post(f"/sections/8/chat/{proposal['id']}/decision", actor | dict(action='reject'))
        assert history(8)['section']['current_draft_id'] == before['section']['current_draft_id']
        proposal = post('/sections/8/chat', token(8) | dict(message='Legal review remains pending.', mode='fact', synthetic=True))
        accepted = post(f"/sections/8/chat/{proposal['id']}/decision", actor | dict(action='accept'))
        assert history(8)['section']['current_draft_id'] == accepted['accepted_draft_id']
        assert history(9)['section']['readiness'] == 'Stale'
        ingest_tranche(app, case, data, 3, 'scan')
        # Refresh all affected prerequisites in order, preserving accepted chat input.
        for sid in (1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 13):
            if history(sid)['section']['readiness'] == 'Stale' or not history(sid)['section']['current_draft_id']:
                draft(sid, **({'confirm_unsecured': True} if sid in (7, 8) else {}))
        post('/drafts/sections/14', expected=422)
        draft(14, ca_position='Defer pending evidence and legal review.')
        data = snapshot('tranche-3')
        assert all(s['current_draft_id'] for s in data['sections'])
        assert not any(s['readiness'] == 'Stale' for s in data['sections'])
        # Confirm the exact draft but keep mandatory industry-mapping and content gaps.
        post('/sections/8/confirm', token(8))
        saved = history(8)
        assert 'Legal review remains pending.' in saved['versions'][-1]['text']
        preview = get('/exports/preview')
        assert len(preview['sections']) == 14 and preview['mapping_gaps']
        (tmp_path / 'export-preview.json').write_text(json.dumps(preview))
        artifact = post('/exports', actor | dict(expected_preview_token=preview['preview_token']))
        status, _, bundle = raw_request(app, prefix + f"/exports/{artifact['id']}/bundle.zip")
        assert status == 200
        with ZipFile(BytesIO(bundle)) as z:
            assert set(z.namelist()) == {'draft.docx', 'manifest.json', 'request-list.txt'}
            manifest = json.loads(z.read('manifest.json'))
            assert 'Defer pending evidence and legal review.' in manifest['sections']['14']['draft']['text']
            assert any(v['origin'] == 'CA input' for v in manifest['sources'].values())
            assert len(manifest['sections']) == 14
        # Keep historical wording/confirmation/export intact after real revised source intake.
        preset = next(p for p in data['intake']['presets'] if p['tranche'] not in (1, 2, 3))
        source = next((ROOT / 'demo/synthetic').rglob(preset['filename']))
        status, result = request(app, 'POST', prefix + '/documents', source.read_bytes(),
            query={'filename': source.name, 'metadata': json.dumps(preset['metadata'])})
        assert status == 200, result
        late = snapshot('stale')
        assert {s['section_id'] for s in late['sections'] if s['readiness'] == 'Stale'} == {8, 9, 11, 14}
        post('/exports', actor | dict(expected_preview_token=preview['preview_token']), expected=409)
        assert history(8)['versions'] == saved['versions']
        assert history(8)['confirmations'] == saved['confirmations']
        (tmp_path / 'history-stale.json').write_text(json.dumps(history(8)))
        post('/sections/8/confirm', token(8), expected=409)
        for sid in (8, 9, 11, 14):
            fresh = draft(sid, **({'ca_position': 'Defer pending evidence and legal review.'} if sid == 14 else {'confirm_unsecured': True} if sid == 8 else {}))
            assert fresh['parent_id']
        assert '104' in history(8)['versions'][-1]['text']
        assert not any(s['readiness'] == 'Stale' for s in snapshot('redrafted')['sections'])
        later_bundle = raw_request(app, prefix + f"/exports/{artifact['id']}/bundle.zip")[2]
        with ZipFile(BytesIO(bundle)) as original, ZipFile(BytesIO(later_bundle)) as later:
            assert {n: original.read(n) for n in original.namelist()} == {n: later.read(n) for n in later.namelist()}
        # Persistence after rebuilding the app, plus explicit workflow lock on demo action.
        app = create_demo_app(tmp_path)
        assert get('/exports')[0]['id'] == artifact['id']
        with sessions.begin() as session:
            repo = Repository(session)
            current = repo.get(s.Case, case.id)
            assert current.workflow_state == 'Draft' and current.active_es_version_id is None
            repo.save(current.model_copy(update={'workflow_state': 'Submitted to Credit Head'}))
        post('/demo/spread', expected=409)
    finally:
        engine.dispose()
