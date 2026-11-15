"""Review threads: comments between the roles. They change nothing in the ES and are open at every stage."""


def paper(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.local import create_demo_app
    api = TestClient(create_demo_app(tmp_path, 'demo/synthetic_keppel'))
    return api, api.get('/cases').json()[0]['id']


def test_a_thread_is_opened_answered_resolved_with_a_conclusion_and_reopened(tmp_path):
    api, case_id = paper(tmp_path)
    base = f'/cases/{case_id}/threads'
    assert api.get(base).json() == [] and api.get('/papers').json()[0]['open_comments'] == 0
    opened = api.post(base, json=dict(actor='demo-credit-head', role='Credit Head', section_id=8, part_key='security',
                                      quote='first legal mortgage', text='Is the mortgage shared with the other lenders?'))
    assert opened.status_code == 201
    thread = opened.json()
    assert thread['status'] == 'open' and thread['part_title'] and thread['comments'][0]['author'] == 'demo-credit-head'
    route = f"{base}/{thread['id']}"
    replied = api.post(f'{route}/replies', json=dict(actor='demo-ca', role='CA', text='Yes, pari passu. I will add that.')).json()
    assert [c['role'] for c in replied['comments']] == ['Credit Head', 'CA']
    assert api.get('/papers').json()[0]['open_comments'] == 1
    # A conclusion is required to resolve, and a resolved thread takes no replies.
    assert api.post(f'{route}/resolve', json=dict(actor='demo-credit-head', role='Credit Head', conclusion='  ')).status_code == 422
    resolved = api.post(f'{route}/resolve', json=dict(actor='demo-credit-head', role='Credit Head', conclusion='State that the mortgage ranks pari passu.')).json()
    assert resolved['status'] == 'resolved' and resolved['resolved_by'] == 'demo-credit-head' and resolved['conclusion'].startswith('State that')
    assert api.post(f'{route}/replies', json=dict(actor='demo-ca', role='CA', text='Done.')).status_code == 422
    assert api.post(f'{route}/resolve', json=dict(actor='demo-ca', role='CA', conclusion='Again.')).status_code == 422
    assert api.get('/papers').json()[0]['open_comments'] == 0
    reopened = api.post(f'{route}/reopen', json=dict(actor='demo-ca', role='CA')).json()
    assert reopened['status'] == 'open' and reopened['conclusion'] is None and 'Earlier conclusion' in reopened['comments'][-1]['text']
    assert len(api.get(base).json()) == 1


def test_a_thread_needs_a_real_section_part_and_role_and_does_not_touch_the_es(tmp_path):
    api, case_id = paper(tmp_path)
    base = f'/cases/{case_id}/threads'
    said = dict(actor='demo-ca', role='CA', text='A question.')
    assert api.post(base, json=said | dict(section_id=99)).status_code == 422
    assert api.post(base, json=said | dict(section_id=8, part_key='no-such-part')).status_code == 422
    assert api.post(base, json=said | dict(section_id=8, role='template admin')).status_code == 422
    assert api.post('/cases/unknown/threads', json=said | dict(section_id=8)).status_code == 404
    before = api.get(f'/cases/{case_id}/dashboard').json()
    whole = api.post(base, json=said | dict(section_id=8)).json()  # a thread on the whole section
    assert whole['part_key'] is None
    assert api.post(f'/cases/{case_id}/threads/unknown/replies', json=said).status_code == 422
    after = api.get(f'/cases/{case_id}/dashboard').json()
    assert after['sections'] == before['sections'] and after['case']['workflow_state'] == before['case']['workflow_state']
