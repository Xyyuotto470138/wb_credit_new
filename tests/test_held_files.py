"""A file the app cannot place is held; the analyst says what it is, and it then counts like any other document."""
import json


def paper(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.local import create_demo_app
    api = TestClient(create_demo_app(tmp_path, 'demo/synthetic_keppel'))
    board = api.get(f"/cases/{api.get('/cases').json()[0]['id']}/dashboard").json()
    case, folder = board['case'], board['intake']['folders'][0]
    api.post(f"/cases/{case['id']}/documents/scan", json=dict(folder_id=folder['id'], metadata_by_path=folder['metadata_by_path']))
    return api, case['id']


def upload(api, case_id, name, text):
    hints = json.dumps(dict(entity='Keppel REIT', scope='default', synthetic=False))
    return api.post(f'/cases/{case_id}/documents', params=dict(filename=name, metadata=hints), content=text.encode(),
                    headers={'Content-Type': 'application/octet-stream'}).json()


def test_a_held_file_counts_once_the_analyst_names_its_type_and_date(tmp_path):
    api, case_id = paper(tmp_path)
    board = lambda: api.get(f'/cases/{case_id}/dashboard').json()
    expected = lambda name: next(e for e in board()['expected_documents'] if e['name'] == name)
    first = next(d for d in board()['documents'] if d['id'] in expected('Term sheet')['document_ids'])
    held = upload(api, case_id, 'final terms v2.txt', 'Agreed terms after the call on Friday.\nFacility A: SGD 650 million.')['document']
    assert held['conflict_status'] == 'pending' and {i.split(':')[0] for i in held['intake']['issues']} == {'unknown_type', 'unknown_period'}
    assert expected('Term sheet')['document_ids'] == [first['id']]  # a held file changes nothing

    route = f"/cases/{case_id}/documents/{held['id']}"
    assert api.post(f'{route}/classify', json=dict(actor='demo-ca', period='2026-11-15')).status_code == 422  # no type given
    assert api.post(f'{route}/classify', json=dict(actor='demo-ca', catalogue_id=999, period='2026-11-15')).status_code == 422
    assert next(d for d in board()['documents'] if d['id'] == held['id'])['conflict_status'] == 'pending'  # a refused attempt leaves it held
    term_sheet = expected('Term sheet')['catalogue_id']
    placed = api.post(f'{route}/classify', json=dict(actor='demo-ca', catalogue_id=term_sheet, period='2026-11-15')).json()
    new = placed['document']
    assert placed['outcome'] == 'created' and new['conflict_status'] == 'none' and new['catalogue_id'] == term_sheet
    assert new['entity'] == 'Keppel REIT' and new['period'] == '2026-11-15' and new['supersedes_id'] == first['id']
    assert new['intake']['review']['by'] == 'demo-ca' and new['intake']['review']['held_document_id'] == held['id']  # who placed it, and from which held record
    documents = {d['id']: d for d in board()['documents']}
    assert documents[held['id']]['conflict_status'] == 'rejected' and documents[new['id']]['current'] and not documents[first['id']]['current']
    assert expected('Term sheet')['document_ids'] == [new['id']]  # the later file is now the term sheet
    assert api.post(f'{route}/classify', json=dict(actor='demo-ca', catalogue_id=term_sheet, period='2026-11-16')).status_code == 422  # no longer held


def test_a_held_file_can_be_set_aside_and_a_same_date_clash_stays_held(tmp_path):
    api, case_id = paper(tmp_path)
    board = lambda: api.get(f'/cases/{case_id}/dashboard').json()
    stray = upload(api, case_id, 'lunch menu.txt', 'Soup of the day.')['document']
    aside = api.post(f"/cases/{case_id}/documents/{stray['id']}/set-aside", json=dict(actor='demo-ca'))
    assert aside.status_code == 200 and aside.json()['conflict_status'] == 'rejected'
    assert not [d for d in board()['documents'] if d['conflict_status'] == 'pending']
    # Naming a held file as a type that already has a file of the same date does not replace that file.
    term = next(e for e in board()['expected_documents'] if e['name'] == 'Term sheet')
    same_day = next(d for d in board()['documents'] if d['id'] in term['document_ids'])['period']
    clash = upload(api, case_id, 'other terms.txt', 'Different terms.')['document']
    again = api.post(f"/cases/{case_id}/documents/{clash['id']}/classify", json=dict(actor='demo-ca', catalogue_id=term['catalogue_id'], period=same_day)).json()
    assert again['document']['conflict_status'] == 'pending' and again['document']['intake']['issues'][0].startswith('same_period_changed')
    assert next(e for e in board()['expected_documents'] if e['name'] == 'Term sheet')['document_ids'] == term['document_ids']
