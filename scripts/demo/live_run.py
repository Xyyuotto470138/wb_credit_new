"""Live end-to-end run of the new-to-bank demo case (Keppel REIT, Ocean Financial Centre).

Makes paid model calls. Every call is recorded in runtime/costs/ledger.jsonl and summarised in docs/cost_log.md.

  .venv/bin/python scripts/demo/live_run.py                 intake, draft every section, export
  .venv/bin/python scripts/demo/live_run.py --sections 2 8  (re)draft only these sections, then export
  .venv/bin/python scripts/demo/live_run.py --export-only   export the saved drafts again, no model calls
  add --fresh to discard the saved case first

The case is kept in runtime/demo_live/case, so the workbench can open it afterwards without further calls.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['WB_CREDIT_LIVE'] = '1'
os.environ.setdefault('LLM_PROVIDER', 'mock')  # the first-generation provider stays on mock; live calls go through the gated route only

import yaml  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.llm import live  # noqa: E402
from backend.app.local import create_demo_app  # noqa: E402

PACK = ROOT / 'demo/synthetic_keppel'
RUNTIME = ROOT / 'runtime/demo_live/case'
OUT = ROOT / 'docs/demo'
ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 14]
CA = dict(actor='Demo Credit Analyst', role='CA')


def cost_log():
    entries = live.read_ledger()
    lines = ['# Live model cost log', '', 'Generated from `runtime/costs/ledger.jsonl` by `scripts/demo/live_run.py`. Costs use each call\'s reported token usage and',
             'the published rates held in `config/models.yaml` (price date shown per model). Calls served by a fallback model are listed as unpriced.', '',
             '## Running totals by model', '', '| Model | Route | Calls | Input tokens | Output tokens | Cost (USD) | Unpriced calls |', '|---|---|---|---|---|---|---|']
    for row in live.totals(entries):
        lines.append(f"| {row['model']} | {row['route']} | {row['calls']} | {row['input_tokens']:,} | {row['output_tokens']:,} | {row['cost_usd']} | {row['unpriced_calls']} |")
    lines += ['', '## Calls', '', '| When (UTC) | Model | Case | Section | Purpose | Input | Output | Cost (USD) | Seconds |', '|---|---|---|---|---|---|---|---|---|']
    for e in entries:
        lines.append(f"| {e['at'][:19]} | {e['model']} | {e['case_id']} | {e['section_id']} | {e['purpose']} | {e['input_tokens']:,} | {e['output_tokens']:,} | {e['cost_usd'] or 'unpriced'} | {e['seconds']} |")
    (ROOT / 'docs/cost_log.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sections', type=int, nargs='*')
    parser.add_argument('--export-only', action='store_true')
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--sense', action='store_true', help='run the model sense check on the saved drafts (all sections, or those named with --sections); no drafting')
    parser.add_argument('--cap', type=float, default=5.0, help='with --sense: stop once this run has spent this many USD')
    args = parser.parse_args()
    if args.fresh and RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    client = TestClient(create_demo_app(RUNTIME, PACK), raise_server_exceptions=False)
    case = client.get('/cases').json()[0]['id']
    base = f'/cases/{case}'
    state = client.get(f'{base}/dashboard').json()
    if not state['documents']:
        for folder in state['intake']['folders'][:1]:  # the deal folder; late_update holds papers that arrive after drafting
            client.post(f'{base}/documents/scan', json=dict(folder_id=folder['id'], metadata_by_path=folder.get('metadata_by_path', {})))
        client.post(f'{base}/public-search', json=CA)
        for doc in client.get(f'{base}/dashboard').json()['documents']:
            if (doc['origin'] == 'public' or doc['catalogue_id'] == 19) and not doc['confirmed_by']:
                client.post(f"{base}/documents/{doc['id']}/confirm", json=CA)
        print('intake done:', client.get(f'{base}/dashboard').json()['counts'])
    if args.sense:
        # The sense check reads saved drafts and records suggestions for a human check. It changes no draft.
        spent = 0.0
        for section in client.get(f'{base}/dashboard').json()['sections']:
            if not section['current_draft_id'] or (args.sections and section['section_id'] not in args.sections):
                continue
            if spent >= args.cap:
                print(f'stopped at the cap of USD {args.cap}'); break
            result = client.post(f"{base}/sections/{section['section_id']}/sense-check", json=dict(actor=CA['actor']))
            if result.status_code != 200:
                print(f"section {section['section_id']}: not run: {result.json().get('detail')}"); continue
            check = next(c for c in result.json() if c['section_id'] == section['section_id'])
            spent += float(check['cost_usd'] or 0)
            print(f"section {section['section_id']}: {check['tables_checked']} tables, {len(check['findings'])} suggested checks, USD {check['cost_usd'] or '0'}")
            for finding in check['findings']:
                print(f"   - {finding['table_title']} / {finding['row_label']} / {finding['column']}: {finding['reason']}")
        cost_log()
        print(f'sense check spend this run: USD {spent:.2f}')
        return
    position = yaml.safe_load((PACK / 'case.yaml').read_text())['demo_ca_position']
    if not args.export_only:
        for number in args.sections or ORDER:
            section = next(s for s in client.get(f'{base}/dashboard').json()['sections'] if s['section_id'] == number)
            body = dict(CA, **({'ca_position': position} if number == 14 else {}))
            if section['current_draft_id']:
                token = dict(expected_draft_id=section['current_draft_id'], expected_revision=section['editor_revision'], expected_input_fingerprint=section['input_fingerprint'])
                response = client.post(f'{base}/sections/{number}/redraft', json=dict(body, **token))
            else:
                response = client.post(f'{base}/drafts/sections/{number}', json=body)
            if response.status_code != 200:
                print(f'section {number}: FAILED {response.status_code} {response.text[:300]}')
                continue
            last = live.read_ledger()[-1]
            draft = response.json()
            draft = draft if 'gaps' in draft else client.get(f"{base}/sections/{number}/history").json()['versions'][-1]
            print(f"section {number}: drafted, {len(draft['gaps'])} gap lines, {last['input_tokens']:,} in / {last['output_tokens']:,} out, USD {last['cost_usd']}, {last['seconds']}s")
            cost_log()
    preview = client.get(f'{base}/exports/preview').json()
    if preview.get('blockers'):
        print('export blocked:', preview['blockers'])
        return
    artifact = client.post(f'{base}/exports', json=dict(CA, expected_preview_token=preview['preview_token'])).json()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'Keppel_REIT_ES_live.docx'
    target.write_bytes(client.get(f"{base}/exports/{artifact['id']}/document.docx").content)
    subprocess.run([str(ROOT / 'scripts/render_docx.sh'), str(target), str(ROOT / 'runtime/demo_live/render')], check=False)
    rendered = ROOT / 'runtime/demo_live/render/Keppel_REIT_ES_live.pdf'
    if rendered.exists():
        shutil.copy(rendered, OUT / 'Keppel_REIT_ES_live.pdf')
    cost_log()
    print('exported', target.relative_to(ROOT), '| total cost USD', sum(float(r['cost_usd']) for r in live.totals()))


if __name__ == '__main__':
    main()
