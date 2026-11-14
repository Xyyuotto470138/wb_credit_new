"""Specification-driven ES (es2): figure checks, the live-call gate, workbook calculations and template fill.

Everything here is offline. The model is a stub that returns fixed JSON; no network, no paid call."""
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile
import json

import pytest
import yaml

from backend.app import schemas as s
from backend.app.es2 import drafting
from backend.app.es2.numbers import evaluate, figure_in, parse_printed, unsupported_figures
from backend.app.es2.spec import load_spec
from backend.app.llm import client, live
from backend.app.llm.registry import load_registry
from conftest import ROOT


def test_printed_figures_and_expressions():
    assert parse_printed('(117,305)') == Decimal('-117305') and parse_printed('43.4%') == Decimal('43.4')
    assert parse_printed('n.a.') is None
    assert figure_in('5,864,836', 'Total assets 5,864,836 5,741,002') and not figure_in('5,864,837', 'Total assets 5,864,836')
    # Compared by value, never rounded: 50 matches 50.0, 85.2 does not match 85.0.
    assert unsupported_figures('Leverage was 50% in 2025, with 85.2 years left.', 'aggregate leverage 50.0% lease 85.0 years') == ['85.2']
    values = {'Secured facility (SGD m)': Decimal(700), 'Security value (SGD m)': Decimal(2880)}
    names = list(values) + ['LTV covenant (%)']
    assert round(evaluate('Secured facility (SGD m) / Security value (SGD m) * 100', values, names), 2) == Decimal('24.31')
    assert evaluate('LTV covenant (%) - Secured facility (SGD m)', values, names) is None  # a missing operand is never guessed
    with pytest.raises(ValueError):
        evaluate('__import__("os")', {}, [])


def test_live_route_needs_explicit_run_flag_and_key(monkeypatch, tmp_path):
    entry = load_registry().get('fable-5-2-direct')
    assert entry.enabled and entry.model_id == 'claude-fable-5-2' and entry.route == 'direct' and entry.price_input_usd_per_mtok
    monkeypatch.delenv('WB_CREDIT_LIVE', raising=False)
    assert not entry.runnable
    with pytest.raises(client.LiveProviderDisabled):
        entry.require_runnable()
    with pytest.raises(live.LiveCallError):
        live.AnthropicLive(entry, client=object())
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-not-real')
    assert entry.runnable
    # Routes outside the routing rule stay closed even in a live run.
    others = [m for m in load_registry().models if m.route != 'mock' and m.id != entry.id]
    assert others and not any(m.runnable for m in others)


class StubStream:
    def __init__(self, text, stop_reason='end_turn'):
        self.text, self.stop_reason = text, stop_reason

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get_final_message(self):
        usage = SimpleNamespace(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        return SimpleNamespace(usage=usage, model='claude-fable-5-2', stop_reason=self.stop_reason, content=[SimpleNamespace(type='text', text=self.text)])


class StubClient:
    def __init__(self, reply, stop_reason='end_turn'):
        self.reply, self.stop_reason, self.requests = reply, stop_reason, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self.stream))

    def stream(self, **request):
        self.requests.append(request)
        reply = self.reply(request) if callable(self.reply) else self.reply
        return StubStream(reply if isinstance(reply, str) else json.dumps(reply), self.stop_reason)


def test_cost_ledger_uses_reported_usage_and_published_rate(monkeypatch, tmp_path):
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    monkeypatch.setenv('WB_CREDIT_LEDGER', str(tmp_path / 'ledger.jsonl'))
    entry = load_registry().get('fable-5-2-direct')
    stub = StubClient('{"parts": {}}')
    text, call = live.AnthropicLive(entry, client=stub).complete('system', 'user', case_id='c1', section_id=2, purpose='draft')
    assert text == '{"parts": {}}' and 'temperature' not in stub.requests[0] and stub.requests[0]['fallbacks'] == 'default'
    # 1,000 input tokens at USD 8 and 500 output tokens at USD 40 per million.
    assert call['cost_usd'] == '0.028000' and call['model'] == 'claude-fable-5-2' and call['section_id'] == 2 and call['purpose'] == 'draft'
    assert live.totals() == [dict(model='claude-fable-5-2', route='direct', calls=1, input_tokens=1000, output_tokens=500, cost_usd='0.0280', unpriced_calls=0)]
    with pytest.raises(live.LiveCallError, match='cut off'):
        live.AnthropicLive(entry, client=StubClient('{', 'max_tokens')).complete('s', 'u', case_id='c1', section_id=2, purpose='draft')
    assert len(live.read_ledger()) == 2  # a failed call is still recorded


def checker(page_text):
    sources = SimpleNamespace(by_ref={'ref1': dict(text=page_text)})
    return drafting.Checker({'E1': 'ref1'}, sources, {})


def test_copied_figures_must_be_on_the_cited_page():
    check = checker('Total assets 9,978,947 8,457,643\nAggregate leverage 47.9%')
    cell = check.figure_cell(dict(raw='9,978,947', scale='thousand', q='Total assets 9,978,947 8,457,643', c=['E1']), 'Total assets', 'amount')
    assert cell['text'] == '9,978,947' and cell['value'] == '9978947' and cell['cites'] == ['ref1']
    # Amounts are converted to thousands in Python, from the unit the source states.
    million = checker('Market value: SGD 2,880.0 million.').figure_cell(dict(raw='2,880.0', scale='million', q='Market value: SGD 2,880.0 million.', c=['E1']), 'Value', 'amount')
    assert million['text'] == '2,880,000'
    # A column stated in millions is converted in Python too, whatever unit the source line uses.
    in_units = checker('Currency and amount: SGD 600,000,000.').figure_cell(dict(raw='600,000,000', scale='unit', q='Currency and amount: SGD 600,000,000.', c=['E1']), 'Facility', 'amount_m')
    assert in_units['text'] == '600.0' and in_units['value'] == '600'
    assert check.figure_cell(dict(raw='9,978,948', scale='thousand', q='Total assets 9,978,947 8,457,643', c=['E1']), 'x', 'amount') is None
    assert check.figure_cell(dict(raw='9,978,947', scale='thousand', q='Total assets 9,978,947 (restated)', c=['E1']), 'x', 'amount') is None
    assert check.figure_cell(dict(raw='9,978,947', scale='thousand', q='Total assets 9,978,947 8,457,643', c=['E9']), 'x', 'amount') is None
    assert len(check.rejected) == 3
    # Typographic apostrophes and dashes in the PDF text do not defeat an otherwise exact quote.
    curly = checker('Unitholders’ funds 5,123,699 4,891,057')
    assert curly.figure_cell(dict(raw='5,123,699', scale='thousand', q="Unitholders' funds 5,123,699 4,891,057", c=['E1']), 'x', 'amount')['text'] == '5,123,699'
    assert check.text_cell(dict(v='Aggregate leverage was 47.9%.', c=['E1']), 'p')['text'].startswith('Aggregate')
    assert check.text_cell(dict(v='Aggregate leverage was 40.4%.', c=['E1']), 'p') is None  # a figure not on the page is withheld
    assert check.text_cell(dict(v='Leverage is high.', c=[]), 'p') is None  # wording without a citation is withheld


def test_change_is_measured_on_size_and_totals_are_computed():
    part = next(p for p in load_spec('fig_re')['sections'][9]['parts'] if p['key'] == 'pl')
    page = 'Property expenses (59,667) (58,573)\nGross revenue 261,580 274,478'
    cell = lambda raw, line: dict(raw=raw, scale='thousand', q=line, c=['E1'])
    raw = dict(periods=['FY2024', 'FY2025'], rows={
        'Property expenses': {'FY2024': cell('(59,667)', 'Property expenses (59,667) (58,573)'), 'FY2025': cell('(58,573)', 'Property expenses (59,667) (58,573)')},
        'Gross revenue (property income)': {'FY2024': cell('261,580', 'Gross revenue 261,580 274,478'), 'FY2025': cell('274,478', 'Gross revenue 261,580 274,478')}})
    table = drafting.build_table(part, raw, checker(page))
    rows = {row[0]['text']: row for row in table['rows']}
    assert table['columns'][1:3] == ['FY2024', 'FY2025']
    assert rows['Property expenses'][3]['text'] == '-1.8' and rows['Property expenses'][3]['status'] == 'computed'  # costs fell
    assert rows['Gross revenue (property income)'][3]['text'] == '4.9'
    assert rows['Net property income'][1]['status'] == 'gap'  # not supplied: a gap, not a derived figure


@pytest.fixture(scope='module')
def keppel(tmp_path_factory):
    """The new-to-bank case with its synthetic deal papers ingested (no public pack: keeps the fixture quick)."""
    import os
    from fastapi.testclient import TestClient
    from backend.app.local import create_demo_app
    os.environ['LLM_PROVIDER'] = 'mock'
    runtime = tmp_path_factory.mktemp('keppel')
    app = create_demo_app(runtime, 'demo/synthetic_keppel')
    api = TestClient(app)
    board = api.get(f"/cases/{api.get('/cases').json()[0]['id']}/dashboard").json()
    case, folder = board['case'], board['intake']['folders'][0]
    scanned = api.post(f"/cases/{case['id']}/documents/scan", json=dict(folder_id=folder['id'], metadata_by_path=folder['metadata_by_path'])).json()
    assert len(scanned) == 11 and all(r['outcome'] == 'created' and r['document']['conflict_status'] == 'none' for r in scanned)
    return SimpleNamespace(api=api, case=case, runtime=runtime)


def stub_service(keppel, reply, monkeypatch):
    from backend.app.database import create_database
    from backend.app.repository import Repository
    from backend.app.services.drafting import DraftingService
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-not-real')
    monkeypatch.setenv('WB_CREDIT_LEDGER', str(keppel.runtime / 'ledger.jsonl'))
    engine, sessions = create_database(keppel.runtime / 'wb_credit.sqlite')
    session = sessions()
    service = DraftingService(Repository(session), keppel.runtime / 'blobs', keppel.runtime / 'templates')
    service.live_client = StubClient(reply)
    return service, session, engine


def test_new_case_is_new_to_bank_on_the_v1_template(keppel):
    case = keppel.case
    assert case['borrower_name'] == 'Keppel REIT' and case['team_id'] == 'fig_re' and case['new_to_bank'] and not case['existing_client']
    active = keppel.api.get('/templates/fig_re/active').json()
    assert active['display_version'] == 'v1.0' and active['status'] == 'mapped'
    spec = keppel.api.get(f"/cases/{case['id']}/es-spec").json()
    assert [section['id'] for section in spec['sections']] == list(range(1, 15)) and spec['team_label'] == 'FIG'
    assert not any(part.get('hidden') or part['key'] in ('cover_facts', 'covenants') for section in spec['sections'] for part in section['parts'])
    state = {sec['section_id']: sec for sec in keppel.api.get(f"/cases/{case['id']}/dashboard").json()['sections']}
    assert state[13]['readiness'] == 'Not applicable'
    # Without the live-run flag the screens cannot trigger a paid call.
    refused = keppel.api.post(f"/cases/{case['id']}/drafts/sections/9", json=dict(actor='ca', role='CA'))
    assert refused.status_code != 200


@pytest.mark.slow
def test_section_9_is_computed_in_python_and_wording_is_checked(keppel, monkeypatch):
    def reply(request):
        user = request['messages'][0]['content']
        if '"section": "4. Business background"' in user or '"section": "12. ' in user:
            return dict(parts={})  # section 4 is drafted only so that its saved photographs and map are placed
        label = next(line.split(']')[0][1:] for line in user.splitlines() if line.startswith('[E') and 'term_sheet.pdf' in line)
        assert 'Tables computed by the system for this section' in user and '4.17' in user
        return dict(parts=dict(
            primary=dict(paragraphs=[dict(text='Projected interest coverage of the building is 4.17 times in FY2027.', cites=['C']),
                                     dict(text='Interest coverage is projected at 9.99 times.', cites=['C'])]),
            secondary=dict(paragraphs=[dict(text='TL-01 is a bullet due on 30 November 2031, so repayment relies on refinancing.', cites=[label])])), gaps=['Refinancing plan not supplied.'])
    service, session, engine = stub_service(keppel, reply, monkeypatch)
    try:
        from backend.app.services.drafting import DraftRequest
        background = service.generate(keppel.case['id'], 4, DraftRequest(actor='ca'))
        draft = service.generate(keppel.case['id'], 9, DraftRequest(actor='ca'))
        rating = service.generate(keppel.case['id'], 12, DraftRequest(actor='ca'))
        session.commit()
    finally:
        session.close(); engine.dispose()
    images = background['claim_spans'][0]['parts']
    assert len(images['photos']['slots']) == 2 and 'Wikimedia Commons' in images['photos']['slots'][0]['caption']
    assert 'OneMap' in images['map']['slots'][0]['caption']
    # The internal rating line is read from the supplied rating worksheet by Python, with its source cited.
    internal = rating['claim_spans'][0]['parts']['internal_rating']['rows'][0]
    assert [cell['text'] for cell in internal[:4]] == ['Keppel REIT', 'CRR 4', 'None: new to bank', '9 Nov 2026'] and internal[1]['cites'] and internal[1]['status'] == 'ok'
    parts = draft['claim_spans'][0]['parts']
    by_label = lambda key: {row[0]['text']: [c['text'] for c in row[1:4]] for row in parts[key]['rows']}
    # Workbook inputs: revenue 118,500 less expenses 21,900; interest 23,175; capex 3,000. Ratios are Python's.
    assert by_label('debt_service')['Net property income'] == ['96,600', '98,800', '101,100']
    assert by_label('debt_service')['Interest coverage (x)'] == ['4.17', '4.26', '4.36']
    assert by_label('debt_service')['Debt service coverage (x)'] == ['4.04', '4.13', '4.21']
    assert parts['debt_service']['columns'][1] == 'Projected FY2027'
    tenants = parts['tenants']['rows']
    assert [row[0]['text'] for row in tenants][:2] == ['Demo Tenant A', 'Demo Tenant C'] and tenants[0][2]['text'] == '10.9' and tenants[0][3]['text'] == '30 Jun 2030'
    assert parts['lease_profile']['rows'][-1][0]['text'] == 'Vacant' and parts['lease_profile']['rows'][-1][2]['text'] == '4.0'
    claims = draft['claim_spans'][1:]
    assert [c['id'] for c in claims] == ['primary.1', 'secondary.1']  # the 9.99 sentence was withheld
    assert any('9.99' in gap for gap in draft['gaps']) and 'Refinancing plan not supplied.' in draft['gaps']
    assert all(draft['text'][c['start']:c['end']] == c['text'] for c in claims)
    assert draft['model_version'].startswith('live:claude-fable-5-2') and draft['claim_spans'][0]['calls'][0]['cost_usd'] == '0.028000'

    # The Credit Assistant adds the analyst's note under its own heading; the drafted text and tables stay exactly as they were.
    base = f"/cases/{keppel.case['id']}/sections/9"
    state = next(sec for sec in keppel.api.get(f"/cases/{keppel.case['id']}/dashboard").json()['sections'] if sec['section_id'] == 9)
    token = dict(actor='ca', role='CA', expected_draft_id=state['current_draft_id'], expected_revision=state['editor_revision'], expected_input_fingerprint=state['input_fingerprint'])
    proposal = keppel.api.post(f'{base}/chat', json=dict(token, message='The manager expects the refinancing plan before first drawdown.', mode='fact', synthetic=True))
    assert proposal.status_code == 200, proposal.text
    proposed = proposal.json()['proposed_text']
    assert proposed.startswith(draft['text'].rstrip('\n')) and "Credit analyst's notes" in proposed[len(draft['text'].rstrip('\n')):]
    assert keppel.api.post(f"{base}/chat/{proposal.json()['id']}/decision", json=dict(actor='ca', role='CA', action='accept')).status_code == 200
    noted = keppel.api.get(f'{base}/history').json()['versions'][-1]
    assert noted['claim_spans'][0]['parts'] == parts and noted['claim_spans'][-1]['kind'] == 'ca_input'
    assert all(noted['text'][c['start']:c['end']] == c['text'] for c in noted['claim_spans'][1:-1])
    reorder = keppel.api.post(f'{base}/chat', json=dict(token, expected_draft_id=noted['id'], expected_revision=state['editor_revision'] + 1, message='Lead with this.', mode='emphasize', claim_id='primary.1'))
    assert reorder.status_code != 200

    # Export: the draft fills the v1.0 template, with photographs and the location map embedded.
    preview = keppel.api.get(f"/cases/{keppel.case['id']}/exports/preview").json()
    assert preview['blockers'] == []
    artifact = keppel.api.post(f"/cases/{keppel.case['id']}/exports", json=dict(actor='ca', role='CA', expected_preview_token=preview['preview_token'])).json()
    content = keppel.api.get(f"/cases/{keppel.case['id']}/exports/{artifact['id']}/document.docx").content
    with ZipFile(BytesIO(content)) as package:
        names = package.namelist()
        body = package.read('word/document.xml').decode()
    assert len([n for n in names if n.startswith('word/media/es_image')]) == 3 and 'word/media/logo.png' in names
    for expected in ('4.17', 'Demo Tenant A', 'Not applicable: new to bank', 'Ratios, changes, shares and totals are computed by the system', 'SYNTHETIC DEMO DATA', 'Open items for the credit analyst',
                     "Credit analyst's notes", 'The manager expects the refinancing plan before first drawdown.'):
        assert expected in body
    assert 'Interest coverage is projected at 9.99 times' not in body
    assert '[Summarise the request' not in body  # no template guidance left in a filled ES


def test_synthetic_pack_is_labelled_and_matches_its_manifest():
    pack = ROOT / 'demo/synthetic_keppel'
    manifest = yaml.safe_load((pack / 'manifest.yaml').read_text())
    case = yaml.safe_load((pack / 'case.yaml').read_text())
    assert case['app_case']['new_to_bank'] and case['app_case']['team_id'] == 'fig_re' and len(manifest['documents']) == 15
    # Four revised papers arrive after drafting. Each is dated later than the paper it replaces, so intake links them.
    first = {e['id']: e for e in manifest['documents'] if e['file'].startswith('deal_folder/')}
    late = [e for e in manifest['documents'] if e['file'].startswith('late_update/')]
    assert len(first) == 11 and len(late) == 4 and all(e['supersedes'] in first and e['date'] > first[e['supersedes']]['date'] for e in late)
    import fitz
    for entry in manifest['documents']:
        path = pack / entry['file']
        assert path.exists() and entry['synthetic'] and entry['entity'] == 'Keppel REIT'
        if path.suffix == '.pdf':
            with fitz.open(path) as document:
                assert all('SYNTHETIC DEMO DATA' in page.get_text() for page in document)
    for photo in case['assets']['property_photos'] + [dict(file=case['assets']['location_map'])]:
        assert (ROOT / photo['file']).exists()


@pytest.mark.slow
def test_redraft_keeps_notes_and_a_changed_section_marks_its_readers(keppel, monkeypatch):
    """Section 10's headroom table reads section 8. It is marked for update only when what it read changes."""
    case_id = keppel.case['id']

    def reply(request):
        user = request['messages'][0]['content']
        label = lambda name: next((line.split(']')[0][1:] for line in user.splitlines() if line.startswith('[E') and name in line), None)
        terms, value = label('term_sheet.pdf'), label('valuation_report.pdf')
        covenant = dict(raw='45', scale='unit', q='loan to value not exceeding 45%', c=[terms])
        if '"section": "8. ' in user:
            return dict(parts=dict(ltv=dict(rows={'At proposed limit': {
                'Secured facility (SGD m)': dict(raw='600,000,000', scale='unit', q='600,000,000. Purpose: to refinance existing bank borrowings', c=[terms]),
                'Security value (SGD m)': dict(raw='2,880.0', scale='million', q='Market value: SGD 2,880.0 million.', c=[value]),
                'LTV covenant (%)': covenant}})))
        if '"section": "10. ' in user and terms:
            return dict(parts=dict(covenants=dict(rows=[{'Covenant': dict(v='Loan to value', c=[terms]), 'Requirement': dict(v='Loan to value not exceeding 45%', c=[terms]),
                                                         'Threshold': covenant, 'Direction': dict(v='max', c=[terms])}])))
        return dict(parts={})
    service, session, engine = stub_service(keppel, reply, monkeypatch)
    sections = lambda: {sec['section_id']: sec for sec in keppel.api.get(f'/cases/{case_id}/dashboard').json()['sections']}
    token = lambda sec: dict(actor='ca', role='CA', expected_draft_id=sec['current_draft_id'], expected_revision=sec['editor_revision'], expected_input_fingerprint=sec['input_fingerprint'])
    try:
        from backend.app.services.drafting import DraftRequest
        from backend.app.services.versions import RedraftRequest, VersionService
        eight = service.generate(case_id, 8, DraftRequest(actor='ca'))
        ten = service.generate(case_id, 10, DraftRequest(actor='ca'))
        session.commit()
        pin = ten['claim_spans'][0]['freshness_dependencies']['8']
        assert pin['draft_id'] == eight['id'] and pin['basis'] == 'parts'
        headroom = next(row for row in ten['claim_spans'][0]['parts']['headroom']['rows'] if row[0]['text'] == 'Loan to value')
        assert headroom[2]['text'].startswith('20.8%') and headroom[3]['text'] == '24.2 pp' and headroom[4]['text'] == 'Within limit'
        assert sections()[10]['readiness'] == 'Drafted'

        # An accepted note on section 8 is a new version with the same computed content: section 10 stays current.
        base = f'/cases/{case_id}/sections/8'
        proposal = keppel.api.post(f'{base}/chat', json=dict(token(sections()[8]), message='The valuer will reissue the report before drawdown.', mode='fact', synthetic=True))
        assert proposal.status_code == 200, proposal.text
        assert keppel.api.post(f"{base}/chat/{proposal.json()['id']}/decision", json=dict(actor='ca', role='CA', action='accept')).status_code == 200
        state = sections()
        assert state[8]['current_draft_id'] != eight['id'] and state[10]['readiness'] == 'Drafted'

        # A redraft keeps the note. Its content is unchanged here, so section 10 is still current.
        versions = VersionService(service.repo, keppel.runtime / 'blobs', keppel.runtime / 'templates')
        versions.drafting.live_client = service.live_client
        session.expire_all()
        again = versions.redraft(case_id, 8, RedraftRequest(**token(state[8])))
        session.commit()
        assert again['claim_spans'][-1]['kind'] == 'ca_input' and 'The valuer will reissue the report' in again['text']
        note = again['claim_spans'][-1]
        assert again['text'][note['start']:note['end']].startswith(note['text']) and again['ca_input_ids']
        assert sections()[10]['readiness'] == 'Drafted'

        # When the content section 10 read does change, section 10 is marked for update and its wording is kept.
        service.live_client = versions.drafting.live_client = StubClient(lambda request: dict(parts={}))
        session.expire_all()
        versions.redraft(case_id, 8, RedraftRequest(**token(sections()[8])))
        session.commit()
        state = sections()
        assert state[10]['readiness'] == 'Stale' and state[10]['current_draft_id'] == ten['id']
    finally:
        session.close(); engine.dispose()


PNG = ('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8z8DAwMDAxMDAwMDAAAANHQEDasKb6QAAAABJRU5ErkJggg==')


@pytest.mark.slow
def test_analyst_added_blocks_are_versioned_kept_on_redraft_and_exported_in_place(keppel, monkeypatch):
    """The analyst pastes a table, a screenshot and a paragraph into a section; the drafted content is untouched."""
    case_id = keppel.case['id']
    service, session, engine = stub_service(keppel, lambda request: dict(parts={}), monkeypatch)
    section = lambda: next(sec for sec in keppel.api.get(f'/cases/{case_id}/dashboard').json()['sections'] if sec['section_id'] == 5)
    token = lambda: (lambda sec: dict(actor='ca', role='CA', expected_draft_id=sec['current_draft_id'], expected_revision=sec['editor_revision'], expected_input_fingerprint=sec['input_fingerprint']))(section())
    base = f'/cases/{case_id}/sections/5'
    post = lambda **body: keppel.api.post(f'{base}/blocks', json=dict(token(), **body))
    try:
        from backend.app.services.drafting import DraftRequest
        from backend.app.services.versions import RedraftRequest, VersionService
        first = service.generate(case_id, 5, DraftRequest(actor='ca'))
        session.commit()
        spec = keppel.api.get(f'/cases/{case_id}/es-spec').json()
        keys = [part['key'] for part in next(sec for sec in spec['sections'] if sec['id'] == 5)['parts']]

        table = post(op='add', kind='table', after=keys[0], title='Peer comparison', rows=[['Peer', 'Leverage (%)'], ['Demo Peer A', '38.5'], ['Demo Peer B']])
        assert table.status_code == 200, table.text
        blocks = table.json()['claim_spans'][0]['blocks']
        assert blocks[0]['rows'][2] == ['Demo Peer B', ''] and blocks[0]['label'].startswith('Analyst added') and blocks[0]['author'] == 'ca'
        assert table.json()['claim_spans'][0]['parts'] == first['claim_spans'][0]['parts'] and table.json()['text'] == first['text']
        assert post(op='add', kind='image', after=keys[0], title='Site visit', image_data='data:image/png;base64,' + PNG).status_code == 200
        text = post(op='add', kind='text', after='', text='Management met on site.\nNo adverse observations.')
        assert text.status_code == 200 and [b['kind'] for b in text.json()['claim_spans'][0]['blocks']] == ['text', 'table', 'image']
        image = text.json()['claim_spans'][0]['blocks'][2]
        assert keppel.api.get(f"/cases/{case_id}/blocks/{image['image']}").content[:4] == b'\x89PNG'
        assert keppel.api.get(f'/cases/{case_id}/blocks/..%2Fwb_credit.sqlite').status_code == 404

        # Refused: unknown position, an empty table, something that is not an image, a stale version token.
        assert post(op='add', kind='text', after='no-such-part', text='x').status_code == 422
        assert post(op='add', kind='table', after='', rows=[['', '']]).status_code == 422
        assert post(op='add', kind='image', after='', image_data='bm90IGFuIGltYWdl').status_code == 422
        assert keppel.api.post(f'{base}/blocks', json=dict(token(), expected_revision=0, op='delete', block_id=image['id'])).status_code == 409

        # Move the image above the table, edit the text, and every step is a saved version.
        moved = post(op='move', block_id=image['id'], direction='up').json()['claim_spans'][0]['blocks']
        assert [b['kind'] for b in moved] == ['text', 'image', 'table']
        edited = post(op='update', block_id=moved[0]['id'], text='Management met on site on 5 November.').json()
        assert edited['claim_spans'][0]['blocks'][0]['updated_by'] == 'ca'
        history = keppel.api.get(f'{base}/history').json()
        assert len(history['versions']) == 6 and history['section']['readiness'] == 'Drafted'

        # A redraft keeps the blocks.
        versions = VersionService(service.repo, keppel.runtime / 'blobs', keppel.runtime / 'templates')
        versions.drafting.live_client = service.live_client
        session.expire_all()
        again = versions.redraft(case_id, 5, RedraftRequest(**token()))
        session.commit()
        assert [b['kind'] for b in again['claim_spans'][0]['blocks']] == ['text', 'image', 'table']
    finally:
        session.close(); engine.dispose()

    # Export: the blocks sit in section 5 of the Word ES, labelled, with the image embedded.
    preview = keppel.api.get(f'/cases/{case_id}/exports/preview').json()
    assert preview['blockers'] == []
    artifact = keppel.api.post(f'/cases/{case_id}/exports', json=dict(actor='ca', role='CA', expected_preview_token=preview['preview_token'])).json()
    with ZipFile(BytesIO(keppel.api.get(f"/cases/{case_id}/exports/{artifact['id']}/document.docx").content)) as package:
        body = package.read('word/document.xml').decode()
        media = [n for n in package.namelist() if n.startswith('word/media/es_image')]
    assert media and all(text in body for text in ('Peer comparison', 'Demo Peer A', 'Management met on site on 5 November.', 'Site visit', 'Analyst added. Not checked by the system.'))
    top, peer = body.index('Management met on site on 5 November.'), body.index('Demo Peer A')
    assert top < body.index('Site visit') < peer
    import xml.etree.ElementTree as ET
    ET.fromstring(body)  # the document is still well formed
    assert keppel.api.post(f'{base}/blocks', json=dict(token(), op='delete', block_id=image['id'])).status_code == 200


@pytest.mark.slow
def test_model_sense_check_suggests_human_checks_and_changes_nothing(keppel, monkeypatch):
    """Tables that code does not check are read by a model. Its findings are suggestions, validated by Python, never a pass."""
    case_id = keppel.case['id']

    def draft_reply(request):
        user = request['messages'][0]['content']
        label = next((line.split(']')[0][1:] for line in user.splitlines() if line.startswith('[E') and 'term_sheet.pdf' in line), None)
        if '"section": "6. ' in user and label:
            return dict(parts=dict(management=dict(rows=[dict(name=dict(v='Demo Officer', c=[label]))])))
        return dict(parts={})
    service, session, engine = stub_service(keppel, draft_reply, monkeypatch)
    try:
        from backend.app.services.drafting import DraftRequest
        six = service.generate(case_id, 6, DraftRequest(actor='ca'))
        session.commit()
    finally:
        session.close(); engine.dispose()
    section = lambda: next(sec for sec in keppel.api.get(f'/cases/{case_id}/dashboard').json()['sections'] if sec['section_id'] == 6)
    token = lambda: (lambda sec: dict(actor='ca', role='CA', expected_draft_id=sec['current_draft_id'], expected_revision=sec['editor_revision'], expected_input_fingerprint=sec['input_fingerprint']))(section())
    added = keppel.api.post(f'/cases/{case_id}/sections/6/blocks', json=dict(token(), op='add', kind='table', after='', title='Board fees',
                                                                             rows=[['Director', 'Fee (SGD)'], ['Demo Director A', '80,000'], ['Demo Director B', '8,000,000'], ['Total', '88,000']]))
    assert added.status_code == 200, added.text
    block_id = added.json()['claim_spans'][0]['blocks'][0]['id']

    seen = []

    def sense_reply(request):
        seen.append(request)
        user = request['messages'][0]['content']
        table = next(line.split(' ')[0] for line in user.splitlines() if 'Board fees' in line)
        return dict(findings=[
            dict(table=table, row='r2', column='Fee (SGD)', concern='implausible', reason='The fee of 8,000,000 is one hundred times the other director fee; compare it with the source schedule.'),
            dict(table=table, row='r3', column='Fee (SGD)', concern='total', reason=f'The total of 88,000 does not equal the sum of the rows above it in {table} r2.'),
            dict(table=table, row='r9', column='', concern='other', reason='Points at a row that does not exist.'),
            dict(table='T99', row='r1', column='', concern='other', reason='Points at a table that was not sent.'),
            dict(table=table, row='r1', column='', concern='other', reason='This table is verified and the credit can be approved.')])
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-not-real')
    monkeypatch.setenv('WB_CREDIT_LEDGER', str(keppel.runtime / 'ledger.jsonl'))
    keppel.api.app.state.es2.live_client = StubClient(sense_reply)
    try:
        result = keppel.api.post(f'/cases/{case_id}/sections/6/sense-check', json=dict(actor='ca'))
        assert result.status_code == 200, result.text
        check = next(c for c in result.json() if c['section_id'] == 6)
        # Only the two findings that point at a real row are kept; unsafe wording and unknown targets are dropped.
        assert [(f['row_label'], f['concern']) for f in check['findings']] == [('Demo Director B', 'implausible'), ('Total', 'total')]
        assert check['findings'][0]['table'] == f'block:{block_id}' and check['findings'][0]['origin'].startswith('added by the analyst')
        assert check['findings'][1]['reason'].endswith('in the table "Board fees" (row "Demo Director B").')
        assert check['current'] and check['open'] == 2 and 'not a verification' in check['note'] and check['cost_usd'] == '0.028000'
        prompt = seen[0]['messages'][0]['content']
        assert 'Board fees' in prompt and 'r2: Demo Director B | 8,000,000' in prompt and 'Reference tables computed by the system' in prompt
        assert live.read_ledger()[-1]['purpose'] == 'sense_check'
        # The draft is untouched.
        assert section()['current_draft_id'] == added.json()['id'] != six['id']

        # The analyst records having looked at one suggestion; the other stays open and is listed in the Word ES.
        first = check['findings'][0]['id']
        resolved = keppel.api.post(f"/cases/{case_id}/sense-checks/{check['id']}/resolve", json=dict(actor='ca', finding_id=first, note='Typing error in my table, corrected below.'))
        assert resolved.status_code == 200 and next(c for c in resolved.json() if c['section_id'] == 6)['open'] == 1
        assert keppel.api.post(f"/cases/{case_id}/sense-checks/{check['id']}/resolve", json=dict(actor='ca', finding_id='nope')).status_code == 422
        preview = keppel.api.get(f'/cases/{case_id}/exports/preview').json()
        assert len(preview['suggested_checks']) == 1 and 'does not equal the sum' in preview['suggested_checks'][0] and 'Model suggestion for a human check' in preview['suggested_checks'][0]

        # After the section changes, the check is shown as out of date and its suggestions leave the export list.
        assert keppel.api.post(f'/cases/{case_id}/sections/6/blocks', json=dict(token(), op='update', block_id=block_id, title='Board fees FY2025')).status_code == 200
        assert not next(c for c in keppel.api.get(f'/cases/{case_id}/sense-checks').json() if c['section_id'] == 6)['current']
        assert keppel.api.get(f'/cases/{case_id}/exports/preview').json()['suggested_checks'] == []
    finally:
        keppel.api.app.state.es2.live_client = None
    # Without the live-run flag the sense check makes no call.
    monkeypatch.delenv('WB_CREDIT_LIVE')
    assert keppel.api.post(f'/cases/{case_id}/sections/6/sense-check', json=dict(actor='ca')).status_code == 422


def test_papers_list_holds_several_papers_with_their_own_inputs(tmp_path):
    """Two papers for different borrowers share one store; each keeps its own files, stage and progress."""
    import os
    from fastapi.testclient import TestClient
    from backend.app.local import create_demo_app
    os.environ['LLM_PROVIDER'] = 'mock'
    api = TestClient(create_demo_app(tmp_path, 'demo/synthetic_keppel', more=['demo/synthetic']))
    cases = api.get('/cases').json()
    assert [c['borrower_name'] for c in cases] == ['Keppel REIT', 'ESR-REIT']
    keppel, esr = (api.get(f"/cases/{c['id']}/dashboard").json() for c in cases)
    assert [f['id'] for f in keppel['intake']['folders']] != [f['id'] for f in esr['intake']['folders']] and len(esr['intake']['folders']) == 3
    assert esr['demo_spread_available'] and not keppel['demo_spread_available']
    folder = esr['intake']['folders'][0]
    scanned = api.post(f"/cases/{cases[1]['id']}/documents/scan", json=dict(folder_id=folder['id'], metadata_by_path=folder['metadata_by_path']))
    assert scanned.status_code == 200 and scanned.json()
    papers = {p['borrower_name']: p for p in api.get('/papers').json()}
    assert list(papers) == ['Keppel REIT', 'ESR-REIT']
    assert papers['Keppel REIT']['case_type'] == 'new' and papers['ESR-REIT']['case_type'] == 'renewal'
    assert all(p['workflow_state'] == 'Draft' and p['waiting_for'] == 'Credit analyst' and p['drafted'] == 0 and p['suggested_checks'] == 0 for p in papers.values())
    assert papers['Keppel REIT']['sections'] == 13 and papers['ESR-REIT']['sections'] == 14
    # Files scanned into one paper do not appear in the other.
    assert not api.get(f"/cases/{cases[0]['id']}/dashboard").json()['documents'] and api.get(f"/cases/{cases[1]['id']}/dashboard").json()['documents']
    assert papers['ESR-REIT']['inputs_outstanding'] < len(esr['expected_documents'])
