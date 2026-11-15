"""Lending type: chosen when a paper is started, kept on the case, and given to the drafting model as emphasis.

Offline: the model is the stub from test_es2; no network, no paid call."""
import sqlite3
from types import SimpleNamespace

from backend.app.es2.spec import lending_note, lending_types
from test_es2 import StubClient


def test_every_lending_type_has_an_id_a_label_and_a_focus():
    types = lending_types()
    assert len(types) == 9 and len({t['id'] for t in types}) == 9
    assert all(t['label'].strip() and len(t['focus'].split()) > 10 for t in types)


def test_note_is_empty_without_a_lending_type_and_names_the_focus_with_one():
    assert lending_note(SimpleNamespace(lending_type=None)) == '' and lending_note(SimpleNamespace(lending_type='not-a-type')) == ''
    note = lending_note(SimpleNamespace(lending_type='subscription_line'))
    assert 'Lending type: Subscription line financing' in note and 'uncalled capital commitments' in note
    assert 'do not fill it from general knowledge' in note  # a point the documents do not cover is left out, not invented


def test_a_new_paper_keeps_its_lending_type_and_an_older_store_gains_the_column(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.database import create_database
    from backend.app.main import create_app
    path = tmp_path / 'store.sqlite'
    engine, sessions = create_database(path)
    engine.dispose()
    with sqlite3.connect(path) as raw:  # a store made before lending types existed
        raw.execute('ALTER TABLE "case" DROP COLUMN lending_type')
    engine, sessions = create_database(path)
    try:
        api = TestClient(create_app(sessions=sessions))
        assert [t['id'] for t in api.get('/lending-types').json()][:2] == ['property_ipre', 'data_centre']
        made = api.post('/papers', json=dict(borrower_name='Sample Fund', case_type='new', lending_type='nav_fund_level'))
        assert made.status_code == 201 and made.json()['lending_type'] == 'nav_fund_level'
        listed = next(p for p in api.get('/papers').json() if p['id'] == made.json()['id'])
        assert listed['lending_type'] == 'NAV / fund-level financing'
        assert api.post('/papers', json=dict(borrower_name='X', case_type='new', lending_type='made-up')).status_code == 422
        assert api.post('/papers', json=dict(borrower_name='X', case_type='new')).status_code == 422
    finally:
        engine.dispose()


def test_the_drafting_request_carries_the_focus_only_for_a_paper_with_a_lending_type(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.database import create_database
    from backend.app.local import create_demo_app
    from backend.app.repository import Repository
    from backend.app.services.drafting import DraftingService, DraftRequest
    api = TestClient(create_demo_app(tmp_path, 'demo/synthetic_keppel'))
    board = api.get(f"/cases/{api.get('/cases').json()[0]['id']}/dashboard").json()
    case_id, folder = board['case']['id'], board['intake']['folders'][0]
    api.post(f'/cases/{case_id}/documents/scan', json=dict(folder_id=folder['id'], metadata_by_path=folder['metadata_by_path']))
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-not-real')
    monkeypatch.setenv('WB_CREDIT_LEDGER', str(tmp_path / 'ledger.jsonl'))
    engine, sessions = create_database(tmp_path / 'wb_credit.sqlite')
    prompts = []
    for chosen in (None, 'data_centre'):
        with sessions() as session:
            session.connection().exec_driver_sql('UPDATE "case" SET lending_type = ? WHERE id = ?', (chosen, case_id))
            session.commit()
        with sessions() as session:
            service = DraftingService(Repository(session), tmp_path / 'blobs', tmp_path / 'templates')
            service.live_client = StubClient(dict(parts={}))
            service.generate(case_id, 1, DraftRequest(actor='ca'), preview=True)
            prompts.append(service.live_client.requests[0]['messages'][0]['content'])
    engine.dispose()
    assert 'Lending type' not in prompts[0]
    assert 'Lending type: Data centre financing' in prompts[1] and 'construction and completion risk' in prompts[1]
    assert prompts[1].index('Lending type') < prompts[1].index('Parts to draft')
