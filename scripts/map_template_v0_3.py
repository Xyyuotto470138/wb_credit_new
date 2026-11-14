"""One-off: update config/teams/fig/template.yaml for the v0.3 FIG template.

Table shapes (headers, row labels, cell spans) are read from the template itself,
so the mapping cannot drift from the file. Run once, on the v0.1 mapping, after
scripts/build_template_v0_3.py.
"""
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.templates import parse_template  # noqa: E402
from backend.app.team_config import load_team  # noqa: E402

CONFIG = ROOT / 'config/teams/fig/template.yaml'
TEMPLATE = 'templates/ES_Template_FIG_draft_v0.3.docx'
NEW_S10_POLICY = 'CA or Python sourced values only; guidance rows and sample labels are not facts.'
# (section, first header) -> (id, kind, repeat, source policy); None keeps the existing entry's settings.
TABLES = {
    (2, 'Borrower'): ('exposure', None, None, None),
    (3, ''): ('update_matrix', 'records', 'rows', 'CA-confirmed Y/N per borrower; never inferred from the absence of evidence.'),
    (4, 'Overview'): ('overview', 'records', 'none', 'Cited business description.'),
    (4, 'Industry/peer comparison'): ('peer_comparison', 'records', 'none', 'Cited peer and industry data only.'),
    (4, 'Business updates & recent developments'): ('business_updates', 'records', 'none', 'Cited updates since the last review.'),
    (4, 'Key tenant names'): ('key_tenants', 'records', 'rows', 'Cited tenant records from the rent roll or lease profile.'),
    (4, 'Concentration risk (if any)'): ('concentration', 'records', 'rows', 'Cited concentration data; mitigation is CA wording.'),
    (10, "SGD'000"): ('financials', None, None, None),
    (10, 'Line item'): ('major_changes', 'matrix', 'none', NEW_S10_POLICY),
    (10, 'Segment'): ('segmental', 'records', 'rows', NEW_S10_POLICY),
    (10, 'Country / region'): ('geographic', 'records', 'rows', NEW_S10_POLICY),
    (10, 'Scenario/Stress applied'): ('stress_cases', 'matrix', 'none', NEW_S10_POLICY),
    (10, 'Assumption'): ('assumptions', 'matrix', 'none', NEW_S10_POLICY),
    (10, 'Any inter-company debts?'): ('intercompany', 'records', 'rows', 'CA-confirmed answer and comments; never inferred.'),
    (10, 'FX risk check'): ('fx_checklist', 'matrix', 'none', 'CA-confirmed answers; never inferred.'),
}
BASE_CASE = ('cashflow_base', 'matrix', 'none', NEW_S10_POLICY)
RENAMED = {'developments': 'update_matrix'}

data = yaml.safe_load(CONFIG.read_text())
data['default_template'] = TEMPLATE
data['version'] = 'fig-2026-11-12-v2'
report = parse_template((ROOT / TEMPLATE).read_bytes(), load_team('fig').template)
existing = {t['id']: t for t in data['table_anchors']}
order = [RENAMED.get(t['id'], t['id']) for t in data['table_anchors']]
for table in report['tables']:
    if table.get('anchor') or table['parent_table'] is None or table['section_id'] not in (2, 3, 4, 10):
        continue
    headers = [c['text'].strip() for c in table['rows'][0]]
    key = (table['section_id'], headers[0])
    if key == (10, "SGD'000") and headers[1].startswith('Projected'):
        spec = BASE_CASE
    elif key == (10, 'Scenario'):
        spec = TABLES[(10, 'Scenario/Stress applied')]
    else:
        spec = TABLES[key]
    name, kind, repeat, policy = spec
    old = existing.get(name) or existing.get({v: k for k, v in RENAMED.items()}.get(name), {})
    entry = dict(id=name, section_id=table['section_id'], headers=headers,
                 row_labels=[row[0]['text'].strip() for row in table['rows'][1:]],
                 repeat=repeat or old['repeat'], source_policy=policy or old['source_policy'],
                 cell_spans=[[c['grid_span'] for c in row] for row in table['rows']], kind=kind or old['kind'])
    existing[name] = entry
    if name not in order:
        # Keep section order: insert after the last table of the same section.
        last = max(i for i, n in enumerate(order) if existing[n]['section_id'] <= table['section_id'])
        order.insert(last + 1, name)
data['table_anchors'] = [existing[name] for name in order]

anchors = [a for a in data['narrative_anchors'] if not a['text'].startswith('[Brief description of the business model')]
for a in anchors:
    a['text'] = a['text'].replace('Amounts in S$m unless stated. Rows follow', "Amounts in SGD'000 unless stated. Rows follow")
new = [
    '[Highlight the major profit and loss and balance sheet items and compare them with prior years. Explain each significant movement.]',
    '[If applicable. Revenue or net property income by business segment or asset class. State "Not applicable" with the reason if the borrower has a single segment.]',
    '[If applicable. Revenue or net property income by country or region. State "Not applicable" with the reason if operations are in one country.]',
    '[Analysis of profitability, balance sheet strength, leverage, liquidity and debt maturity, with the reasons for the main movements over the periods shown.]',
    '[Detailed projection over the facility tenor. Base case assumes stable cash flow. State every assumption and the basis for it.]',
]
at = max(i for i, a in enumerate(anchors) if a['section_id'] == 10)  # before the Commentary anchor
anchors[at:at] = [dict(section_id=10, text=t) for t in new if not any(a['text'] == t for a in anchors)]
data['narrative_anchors'] = anchors
CONFIG.write_text(yaml.safe_dump(data, sort_keys=False, width=100, allow_unicode=True))

check = parse_template((ROOT / TEMPLATE).read_bytes(), load_team('fig').template)
print('complete', check['complete'], 'tables', len(check['tables']), 'fill points', len(check['fill_points']), 'gaps', len(check['gaps']))
for gap in check['gaps']:
    print('  ', gap)
