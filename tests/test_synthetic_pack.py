"""Independent, offline reconciliation of delivered B03 files, not generator output."""
from collections import Counter
from datetime import date, datetime
from decimal import Decimal as D, ROUND_HALF_UP
from email import policy
from email.parser import BytesParser
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import fitz
from openpyxl import load_workbook
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'demo/synthetic'
CASE = yaml.safe_load((PACK / 'case.yaml').read_text())
MANIFEST = yaml.safe_load((PACK / 'manifest.yaml').read_text())
GOLD = yaml.safe_load((ROOT / 'tests/fixtures/synthetic_gold.yaml').read_text())
LABEL = 'SYNTHETIC DEMO DATA, not a real record'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def decimal(x):
    return D(str(x))


def rounded(x):
    return decimal(x).quantize(D('0.000001'), rounding=ROUND_HALF_UP)


def book(file):
    return load_workbook(PACK / file, data_only=True)


def pdf_text(file, page=1):
    with fitz.open(PACK / file) as doc:
        return doc[page-1].get_text()


def docx_root(file):
    with ZipFile(file) as archive:
        return ET.fromstring(archive.read('word/document.xml'))


def xml_text(root):
    return ' '.join(t.text or '' for t in root.findall('.//w:t', NS))


@pytest.mark.parametrize('item', MANIFEST['documents'], ids=lambda x: x['id'])
def test_manifest_and_source_labels(item):
    path = PACK / item['file']
    assert path.resolve().is_relative_to(PACK.resolve())
    assert item['synthetic'] is True and item['ca_confirmed'] is False
    assert item['entity'] == CASE['borrower']['name']
    assert item['origin'] == 'generated'
    assert date.fromisoformat(item['date']) <= date(2026, 11, 10)
    assert item['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert item['bytes'] == path.stat().st_size
    assert item['citation_locator']
    if path.suffix == '.pdf':
        with fitz.open(path) as doc:
            assert len(doc) == item['pages']
            for page in doc:
                text = page.get_text()
                assert text.splitlines()[0] == LABEL
                assert CASE['borrower']['name'] in text and 'the Bank' in text
                assert 'No real lending relationship' in text
                # Source text must stay within the printable page, including long URLs.
                for x0, y0, x1, y1, *_ in page.get_text('blocks'):
                    assert 35 <= x0 < x1 <= page.rect.width-35
                    assert 20 <= y0 < y1 <= page.rect.height-15
    elif path.suffix == '.xlsx':
        wb = book(item['file'])
        assert set(item['sheets']) == set(wb.sheetnames)
        for sheet in wb:
            assert sheet['A1'].value == LABEL
            assert CASE['borrower']['name'] in sheet['A3'].value
            assert item['sheets'][sheet.title]['last_data_row'] == sheet.max_row
            assert sheet.max_row >= 7
            assert all(cell.data_type != 'e' for row in sheet for cell in row)
        # These are received source extracts, not live spreadsheet models.
        formulas = load_workbook(path, data_only=False)
        assert not any(c.data_type == 'f' for s in formulas for row in s for c in row)
    elif path.suffix == '.docx':
        with ZipFile(path) as archive:
            headers = [xml_text(ET.fromstring(archive.read(n))) for n in archive.namelist() if n.startswith('word/header') and n.endswith('.xml')]
            assert headers and all(LABEL in h for h in headers)
        assert CASE['borrower']['name'] in xml_text(docx_root(path))
    else:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        assert str(message['X-Synthetic-Data']) == LABEL
        assert message.get_content().splitlines()[0] == LABEL
        assert 'example.invalid' in message['To'] and 'example.invalid' in message['From']
        assert CASE['borrower']['name'] in message.get_content()


def test_tranche_inventory_formats_and_late_revision():
    docs = MANIFEST['documents']
    assert len(docs) == len({d['id'] for d in docs}) == 17
    assert Counter(d['tranche'] for d in docs) == {1: 2, 2: 12, 3: 2, 'late_update': 1}
    assert {d['catalogue_id'] for d in docs if d['tranche'] == 1} == {2, 12}
    assert {d['catalogue_id'] for d in docs if d['tranche'] == 2} == {1, 3, 22, 21, 8, 11, 9, 13, 15, 16, 14, None}
    assert {d['catalogue_id'] for d in docs if d['tranche'] == 3} == {17, 10}
    expected_formats = {1: '.pdf', 2: '.pdf', 3: '.docx', 8: '.pdf', 9: '.pdf', 10: '.pdf',
                        12: '.eml', 13: '.pdf', 14: '.xlsx', 15: '.xlsx', 16: '.xlsx', 17: '.xlsx', 21: '.xlsx', None: '.xlsx'}
    for d in docs:
        if d['catalogue_id'] in expected_formats:
            assert Path(d['file']).suffix == expected_formats[d['catalogue_id']]
    late = next(d for d in docs if d['id'] == 'valuation-v2')
    old = next(d for d in docs if d['id'] == late['supersedes'])
    assert late['revision'] == 2 and old['revision'] == 1
    assert late['date'] > old['date'] and late['sha256'] != old['sha256']
    assert late['expected_stale_sections'] == [8, 9, 11, 14]
    actual = {p.relative_to(PACK).as_posix() for p in PACK.rglob('*') if p.suffix in {'.pdf', '.xlsx', '.docx', '.eml'}}
    assert actual == {d['file'] for d in docs}


def test_exposure_gold_and_cross_document_consistency():
    s = book('tranche_2/limits_utilisation.xlsx')['Exposure']
    totals = [sum(decimal(s.cell(r, col).value) for r in (6, 7)) for col in range(2, 6)]
    g = GOLD['exposure']
    assert totals == [D(g[k]) for k in ('existing', 'outstanding', 'proposed', 'increase')]
    assert totals == [decimal(s.cell(8, col).value) for col in range(2, 6)]
    assert totals[0]-totals[1] == D(g['undrawn_existing'])
    assert rounded(totals[1]/totals[0]*100) == D(g['existing_utilisation_pct'])
    for r, f in zip((6, 7), CASE['facilities']):
        assert s.cell(r, 1).value == f['id']
        assert [decimal(s.cell(r, col).value) for col in (2, 3, 4)] == [D(f[k]) for k in ('existing_limit', 'outstanding', 'proposed_limit')]
        assert decimal(s.cell(r, 4).value)-decimal(s.cell(r, 2).value) == decimal(s.cell(r, 5).value)
        assert isinstance(s.cell(r, 6).value, datetime)
    cas = pdf_text('tranche_2/cas.pdf')
    for n in ('55.00', '46.00', '75.00', '20.00'):
        assert n in cas
    terms = pdf_text('tranche_1/term_sheet.pdf')
    assert '60.00m' in terms and '15.00m' in terms and 'expressly unsecured' in terms


def test_ltv_gold_from_pdf_values_not_builder():
    values = []
    for file in ('tranche_2/valuation_v1.pdf', 'late_update/valuation_v2.pdf'):
        text = ' '.join(pdf_text(file).split())
        values.append(D(re.search(r'Market value: SGD ([\d,.]+) million', text)[1].replace(',', '')))
    s = book('tranche_2/limits_utilisation.xlsx')['Exposure']
    drawn, proposed = decimal(s['C6'].value), decimal(s['D6'].value)
    cap = D(CASE['covenants']['ltv_max_pct'])
    g = GOLD['ltv']
    assert rounded(drawn/values[0]*100) == D(g['drawn_initial_pct'])
    assert rounded(proposed/values[0]*100) == D(g['proposed_initial_pct'])
    assert rounded(proposed/values[1]*100) == D(g['proposed_revised_pct'])
    assert rounded(drawn/values[1]*100) == D(g['drawn_revised_pct'])
    assert rounded(cap-proposed/values[0]*100) == D(g['initial_headroom_pp'])
    assert rounded(cap-proposed/values[1]*100) == D(g['revised_headroom_pp'])
    assert values[1]*cap/100 == D(g['revised_max_loan'])
    assert proposed-values[1]*cap/100 == D(g['proposed_paydown_to_limit'])
    assert 'RCF is unsecured and excluded' in ' '.join(pdf_text('late_update/valuation_v2.pdf').split())
    assert proposed/values[0]*100 < cap < proposed/values[1]*100
    assert values == [D('112'), D('104')]


def test_property_facts_match_public_row_and_scenario_is_separate():
    public = CASE['public_property']
    ref = next(s for s in MANIFEST['public_sources'] if s['id'] == public['document_id'])
    with fitz.open(ROOT / ref['file']) as doc:
        left = ' '.join(doc[71].get_text().split())
        right = ' '.join(doc[72].get_text().split())
    # Match the property row across the facing pages, not unrelated nearby values.
    assert '5 16 Tai Seng Street Multi-tenanted 22,798 19,187 30+30 03 July 2067' in left
    assert '41.5 29 May 2012 100.5 50.2 109.0 3.5' in right
    assert public == dict(document_id='esr-ar2025', pdf_pages=[72, 73], printed_pages=[70, 71],
        as_of='2025-12-31', property_type='High-specifications industrial', lease_type='Multi-tenanted',
        gfa_sqm=22798, nla_sqm=19187, land_tenure_years='30+30', land_lease_expiry='2067-07-03',
        remaining_land_lease_years='41.5', acquisition_date='2012-05-29',
        purchase_price_or_development_cost='100.5', occupancy_pct='50.2', valuation='109.0',
        rental_income_fy2025='3.5')
    assert CASE['property']['nla_sqm'] == public['nla_sqm'] == GOLD['property']['nla_sqm']
    assert abs(D(GOLD['property']['occupancy_pct'])-D(public['occupancy_pct'])) < D('.001')
    assert abs(D(GOLD['property']['annual_rent_sgd'])/1000000-D(public['rental_income_fy2025'])) < D('.1')
    for file in ('tranche_2/valuation_v1.pdf', 'late_update/valuation_v2.pdf'):
        page = ' '.join(pdf_text(file, 2).split())
        for expected in ('22,798', '19,187', '30+30', '2067-07-03', '41.5', '2012-05-29',
                         '100.5', '50.2%', '109.0m', '3.5m', '2025-12-31', ref['url'], ref['retrieved_at']):
            assert expected in page
    late = ' '.join(pdf_text('late_update/valuation_v2.pdf').split())
    assert CASE['property']['revision_reason'] in late
    tenant = CASE['leases'][0]
    assert tenant['tenant'] in late and tenant['expiry'] in late
    assert 'require reassessment' in pdf_text('late_update/valuation_v2.pdf', 2)
    rent = book('tranche_2/rent_roll.xlsx')
    assert rent['Sources']['D11'].value == ref['url']
    prior = xml_text(docx_root(PACK / 'tranche_2/prior_es.docx'))
    assert '109.0' in prior and '38.53 drawn' in prior and '120.0' not in prior


def test_covenants_reconcile_and_public_figures_keep_provenance():
    wb = book('tranche_2/covenant_monitoring.xlsx')
    s = wb['Tests']
    for r, key in zip((6, 7, 8), ('leverage_headroom_pp', 'icr_headroom_x', 'drawn_ltv_headroom_pp')):
        actual, limit = decimal(s.cell(r, 2).value), decimal(s.cell(r, 3).value)
        headroom = limit-actual if s.cell(r, 4).value == 'maximum' else actual-limit
        assert headroom == D(GOLD['covenants'][key]) == decimal(s.cell(r, 5).value)
    public = yaml.safe_load((ROOT / CASE['borrower']['public_manifest']).read_text())
    ref = next(d for d in public['documents'] if d['id'] == CASE['public_observations'][0]['document_id'])
    assert wb['Sources']['D6'].value == ref['url']
    assert wb['Sources']['C6'].value.date().isoformat() == ref['retrieved_at']
    assert [s['B6'].value, s['B7'].value] == [float(o['value']) for o in CASE['public_observations']]
    with fitz.open(ROOT / Path(CASE['borrower']['public_manifest']).parent / ref['file']) as doc:
        text = doc[1].get_text()
        assert '44.1%' in text and '2.6x' in text
    cert = ' '.join(pdf_text('tranche_2/compliance_certificate.pdf').split())
    assert '0.90 percentage points' in cert and '0.60x' in cert
    assert 'not synthetic consolidated totals' in cert


def test_conduct_gold_events_days_and_period():
    wb = book('tranche_3/account_conduct.xlsx')
    monthly = list(wb['Monthly'].iter_rows(min_row=6, values_only=True))
    events = list(wb['Events'].iter_rows(min_row=6, values_only=True))
    assert len(monthly) == 24 and len(events) == 2
    assert min(r[0] for r in monthly).date() == date(2025, 11, 30)
    assert max(r[0] for r in monthly).date() == date(2026, 10, 31)
    exposure = book('tranche_2/limits_utilisation.xlsx')['Exposure']
    for rownum, facility in [(6, 'TL-01'), (7, 'RCF-01')]:
        rows = [r for r in monthly if r[1] == facility]
        g = GOLD['conduct'][facility]
        assert len(rows) == len({r[0] for r in rows}) == 12
        mean = sum(decimal(r[3]) for r in rows)/12
        assert rounded(mean) == rounded(g['mean_month_end'])
        assert rounded(mean/decimal(rows[0][2])*100) == D(g['mean_utilisation_pct'])
        assert max(decimal(r[4]) for r in rows) == D(g['peak'])
        assert rows[-1][3] == exposure.cell(rownum, 3).value
        assert all(r[4] >= r[3] for r in rows)
        excess = [r for r in events if r[0] == 'Excess' and r[1] == facility]
        late = [r for r in events if r[0] == 'Past due' and r[1] == facility]
        assert len(excess) == g['excess_count']
        assert sum((r[3]-r[2]).days+1 for r in excess) == g['excess_days']
        assert max((decimal(r[4]) for r in excess), default=D(0)) == D(g['max_excess'])
        assert len(late) == g['past_due_count']
        assert max(((r[3]-r[2]).days for r in late), default=0) == g['max_dpd']
        assert max((decimal(r[4]) for r in late), default=D(0)) == D(g['max_past_due'])
    assert max(decimal(r[4])-decimal(r[2]) for r in monthly if r[1] == 'RCF-01') == D('0.5')


def test_rent_lease_and_projection_gold():
    rent = list(book('tranche_2/rent_roll.xlsx')['Leases'].iter_rows(min_row=6, values_only=True))
    g = GOLD['property']
    assert sum(decimal(r[4]) for r in rent) == D(g['annual_rent_sgd'])
    assert all(decimal(r[3])*12 == decimal(r[4]) for r in rent)
    assert sum(r[2] for r in rent) == g['nla_sqm']
    occupied = sum(r[2] for r in rent if r[3] > 0)
    assert occupied == g['occupied_sqm']
    assert rounded(D(occupied)/D(g['nla_sqm'])*100) == D(g['occupancy_pct'])
    expiry = list(book('tranche_2/lease_profile.xlsx')['Expiry'].iter_rows(min_row=6, max_row=10, values_only=True))
    for year, annual, area, rent_share, area_share in expiry:
        subset = [r for r in rent if (r[5] is None if year == 'Vacant' else r[5] and r[5].year == year)]
        assert sum(r[4] for r in subset) == annual
        assert sum(r[2] for r in subset) == area
        assert rounded(decimal(annual)/D(g['annual_rent_sgd'])) == rounded(rent_share)
        assert rounded(decimal(area)/D(g['nla_sqm'])) == rounded(area_share)
    wb = book('tranche_2/projections.xlsx')
    assert isinstance(wb['Assumptions']['B14'].value, datetime)
    assert isinstance(wb['Assumptions']['B15'].value, datetime)
    for row in wb['Forecast'].iter_rows(min_row=6, values_only=True):
        year, *vals = row
        revenue, costs, npi, reserve, capex, available, interest, principal, service, dscr = map(decimal, vals)
        assert revenue*1000000 == D(g['annual_rent_sgd'])
        assert revenue-costs == npi == D(g['annual_npi'])
        assert npi-reserve-capex == available == D(g['cash_for_debt_service'])
        assert service == interest+principal
        expected = GOLD['projections'][str(year)]
        assert [interest, principal, service] == [D(expected[k]) for k in ('interest', 'principal', 'debt_service')]
        assert rounded(available/service) == rounded(dscr) == D(expected['dscr'])
        if year in (2027, 2029):
            assert dscr < 1  # Maturity risk remains visible; no fabricated refinancing receipt.


def test_prior_es_preserves_template_and_historical_period():
    template = ROOT / 'templates/ES_Template_FIG_draft_v0.1.docx'
    filled = PACK / 'tranche_2/prior_es.docx'
    assert hashlib.sha256(template.read_bytes()).hexdigest() == '9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21'
    a, b = docx_root(template), docx_root(filled)
    for tag in ('tbl', 'tr', 'tc', 'sectPr', 'tblGrid', 'tcPr', 'pPr', 'rPr'):
        assert len(a.findall('.//w:'+tag, NS)) == len(b.findall('.//w:'+tag, NS))
    headings = lambda root: [xml_text(p) for p in root.findall('.//w:p', NS)
                            if p.find('w:pPr/w:pStyle[@w:val="Heading1"]', NS) is not None]
    assert len(headings(a)) == 14 and headings(a) == headings(b)
    with ZipFile(template) as x, ZipFile(filled) as y:
        assert set(x.namelist()) == set(y.namelist())
        changes = {n for n in x.namelist() if x.read(n) != y.read(n)}
        assert changes <= {'word/document.xml', 'word/settings.xml', 'word/header1.xml'}
        for part in changes:
            raw = y.read(part).decode()
            for prefix in re.search(r'Ignorable="([^"]+)"', raw)[1].split() if 'Ignorable=' in raw else []:
                assert 'xmlns:'+prefix+'=' in raw
    text = xml_text(b)
    for sample in ('Borrower A', 'Borrower B', '[Tenant', '[Property', 'DD/MM/YYYY', 'FY['):
        assert sample not in text
    assert 'DEMO-CAS-001' in text and 'DEMO-G4' in text and '1 May 2026' in text
    assert 'Approved with conditions; fictional' in text
    assert 'not the current CA recommendation' in text
    # Historical RCF balance uses April, not the October exposure snapshot.
    assert '47,000' in text and '5,000' in text
    assert '44.1' not in text and '2026-09-30' not in text


def test_historical_public_context_is_dated_and_sourced():
    context = CASE['public_historical']
    ref = next(s for s in MANIFEST['public_sources'] if s['id'] == context['document_id'])
    assert ref['url'].startswith('https://') and ref['retrieved_at'] == '2026-11-10'
    with fitz.open(ROOT / ref['file']) as doc:
        for key in ('leverage_pct', 'icr_x', 'debt', 'cost_of_debt_pct', 'debt_maturity_years', 'fixed_rate_pct'):
            assert context[key].replace(',', '') in doc[58].get_text().replace(',', '')
        for person in context['management']:
            assert person[0] in doc[34].get_text()
        assert context['portfolio_valuation'] in doc[49].get_text().replace(',', '')
    text = xml_text(docx_root(PACK / 'tranche_2/prior_es.docx'))
    assert 'AR p59' in text and '31 Dec 2025' in text
    assert 'Public values are not adjusted for the fictional deal' in text
    assert '1.6 pp' in text and '0.5x' in text


def test_borrower_swap_has_one_configuration_point():
    # Read only assertion: sources do not embed the current name/property in builders.
    for script in ('build_synthetic_pack.py', 'fill_demo_prior_es.py', 'build_synthetic_workbooks.mjs'):
        source = (ROOT / 'scripts' / script).read_text()
        assert CASE['borrower']['name'] not in source
        assert CASE['borrower']['property'] not in source
    assert MANIFEST['borrower'] == CASE['borrower']


def test_pack_maps_to_b01_case_and_document_contracts():
    from backend.app.schemas import Case, Document
    from backend.app.team_config import load_team
    config = load_team(CASE['app_case']['team_id'])
    case = Case(id=CASE['case_id'], borrower_name=CASE['borrower']['name'],
                public_identifiers={k: CASE['borrower'][k] for k in ('sgx_code', 'isin')},
                config_version=config.template.version, config_hash=config.content_hash,
                **CASE['app_case'])
    assert case.ca_position is None and case.financial_covenants and case.property_or_asset_security
    assert case.public_entity and case.existing_client and not case.new_to_bank
    for item in MANIFEST['documents']:
        document = Document(id=item['id'], case_id=case.id, catalogue_id=item['catalogue_id'],
                            suggestion_id=item.get('suggestion_id'), entity=item['entity'],
                            period=item.get('period_end', item['date']), content_hash=item['sha256'],
                            storage_path=str(PACK / item['file']), revision=item['revision'],
                            supersedes_id=item.get('supersedes'), origin=item['origin'],
                            synthetic=item['synthetic'], original_filename=Path(item['file']).name)
        assert document.synthetic and document.confirmed_by is None
        if document.catalogue_id is not None:
            assert document.catalogue_id in {d.id for d in config.catalogue.items}
