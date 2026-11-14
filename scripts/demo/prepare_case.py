"""Bring a running local demo case to "sections drafted" through the same API the screens use.

Usage: .venv/bin/python scripts/demo/prepare_case.py http://127.0.0.1:18200 [borrower name]
Mock provider and saved public pack only. Skips steps that are already done.
"""
import json
import sys
import urllib.error
import urllib.request

API = sys.argv[1].rstrip('/')
CA = dict(actor='demo-ca', role='CA')


def call(path, body=None):
    request = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'}, method='GET' if body is None else 'POST')
    with urllib.request.urlopen(request) as response:
        return json.load(response)


# An optional second argument names the borrower to prepare, when the store holds several papers.
case = next(c for c in call('/cases') if len(sys.argv) < 3 or c['borrower_name'] == sys.argv[2])['id']
base = f'/cases/{case}'
state = call(f'{base}/dashboard')
if not state['documents']:
    for folder in state['intake']['folders'][:2]:  # tranche 3 stays out, so the demo still has inputs pending
        call(f'{base}/documents/scan', dict(folder_id=folder['id'], metadata_by_path=folder.get('metadata_by_path', {})))
    call(f'{base}/public-search', CA)
    for doc in call(f'{base}/dashboard')['documents']:
        if doc['origin'] == 'public' and not doc['confirmed_by']:
            call(f"{base}/documents/{doc['id']}/confirm", CA)
    call(f'{base}/demo/spread', CA)
sections = {s['section_id']: s for s in call(f'{base}/dashboard')['sections']}
for number in (1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11):
    section = sections[number]
    if section['current_draft_id'] or not section['readiness'].startswith('Can draft'):
        continue
    try:
        call(f'{base}/drafts/sections/{number}', dict(CA, confirm_unsecured=True))
        print(f'drafted section {number}')
    except urllib.error.HTTPError as error:
        print(f'section {number} not drafted: {error.read().decode()[:200]}')
print('case ready')
