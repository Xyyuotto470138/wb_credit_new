"""Hand a running demo paper from the maker to the checker, through the same API the screens use.

Usage: .venv/bin/python scripts/demo/submit_for_review.py http://127.0.0.1:18200 [borrower name]
Confirms every drafted section as the credit analyst and submits the ES to the Credit Head, so the checker has a
paper waiting for review. Does nothing if the paper is already with a reviewer. Makes no model call.
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
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f'{path}: {error.code} {error.read().decode()[:400]}')


case = next(c for c in call('/cases') if len(sys.argv) < 3 or c['borrower_name'] == sys.argv[2])
base = f"/cases/{case['id']}"
review = call(f'{base}/review')
if review['state'] not in ('Draft', 'Returned to CA'):
    sys.exit(f"{case['borrower_name']} is already at: {review['state']}. Nothing to do.")
for section in call(f'{base}/dashboard')['sections']:
    if section['current_draft_id'] and section['readiness'] != 'CA confirmed':
        call(f"{base}/sections/{section['section_id']}/confirm", dict(CA, expected_draft_id=section['current_draft_id'],
             expected_revision=section['editor_revision'], expected_input_fingerprint=section['input_fingerprint']))
        print(f"confirmed section {section['section_id']}")
report = call(f'{base}/submission-checks/preview')
still_open = [s for s in report['sections'] if s['status'] != 'passed']
if still_open or report['blockers']:
    sys.exit('Cannot submit yet. ' + '; '.join([f"section {s['section_id']} is not confirmed" for s in still_open] + report['blockers']))
review = call(f'{base}/review')
call(f'{base}/workflow/transitions', dict(CA, action='submit', expected_state=review['state'], expected_event_id=review['latest_event_id'],
     expected_es_version_id=review['active_es_version_id'], expected_preview_token=report['preview_token'],
     mandatory_gap_reasons={gap['id']: 'Demo submission: this input is still to come and is listed as an open item.' for gap in report['mandatory_gaps']},
     comment='Submitted for review by the demo set-up script.'))
print(f"{case['borrower_name']} submitted to the Credit Head")
