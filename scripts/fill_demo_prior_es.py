"""Fill one historical demo ES by patching the owner's template package in place.

This deliberately narrow fixture builder is not the B18/B22 export/parser.
All non-text layout and all untouched ZIP members are retained byte for byte.
"""
import hashlib
from decimal import Decimal as D
from io import BytesIO
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{'+NS['w']+'}'
LABEL = 'SYNTHETIC DEMO DATA, not a real record'
TEMPLATE = ROOT / 'templates/ES_Template_FIG_draft_v0.1.docx'


def set_text(element, value):
    """Keep the existing paragraph/run properties, including italic slot styling."""
    nodes = element.findall('.//w:t', NS)
    if not nodes:
        p = element if element.tag == W+'p' else element.find('w:p', NS)
        if p is None:
            p = ET.SubElement(element, W+'p')
        run = ET.SubElement(p, W+'r')
        nodes = [ET.SubElement(run, W+'t')]
    nodes[0].text = str(value)
    nodes[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    for n in nodes[1:]:
        n.text = ''


def text(e):
    return ''.join(n.text or '' for n in e.findall('.//w:t', NS))


def serialize(root, original):
    # QName values such as mc:Ignorable need declarations even for unused namespaces.
    namespaces = dict(pair for _, pair in ET.iterparse(BytesIO(original), events=['start-ns']))
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    used = ET.tostring(root, encoding='unicode')
    for prefix, uri in namespaces.items():
        declaration = 'xmlns:'+prefix if prefix else 'xmlns'
        if declaration+'=' not in used:
            root.set(declaration, uri)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def fill():
    c = json.loads((ROOT / 'runtime/b03/case.json').read_text())
    name, prop = c['borrower']['name'], c['borrower']['property']
    public = c['public_historical']
    property_history = c['public_property']
    rental = sum(D(l['monthly_rent_sgd']) for l in c['leases'])*12/D(1000000)
    npi = rental-D(c['property']['operating_cost_annual'])
    cash = dict(rental=rental, npi=npi,
                available=npi-D(c['property']['reserve_annual'])-D(c['property']['capex_reserve_annual']))
    historical_ltv = D(c['facilities'][0]['outstanding'])/D(property_history['valuation'])*100
    assert hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() == '9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21'
    with ZipFile(TEMPLATE) as z:
        originals = {n: z.read(n) for n in z.namelist()}
    root = ET.fromstring(originals['word/document.xml'])
    outer = root.find('w:body', NS).findall('w:tbl', NS)
    assert len(outer) == 15
    tables = {i: outer[i].findall('.//w:tbl', NS) for i in range(1, 15)}

    def row(section, table, index, values):
        cells = tables[section][table].findall('w:tr', NS)[index].findall('w:tc', NS)
        assert len(cells) == len(values), (section, table, index, len(cells), values)
        for cell, value in zip(cells, values):
            set_text(cell, value)

    # Name every omitted historical field instead of leaving apparent sample facts.
    for i in range(1, 15):
        for table in tables[i]:
            for tr in table.findall('w:tr', NS)[1:]:
                for cell in tr.findall('w:tc', NS):
                    if not text(cell) or '[' in text(cell) or 'DD/MM/YYYY' in text(cell) or '☐' in text(cell):
                        set_text(cell, 'Not reproduced')
    cover = outer[0].findall('w:tr', NS)
    set_text(cover[0].findall('w:tc', NS)[1], f'{name} - DEMO-CAS-001; DEMO-G4\nSingle borrower; fictional prior approval')
    set_text(cover[0].findall('w:tc', NS)[2], 'Standalone demo. Watchlist and AML classifications not reproduced; no negative finding inferred.')
    set_text(cover[1].findall('w:tc', NS)[1], name)
    set_text(cover[2].findall('w:tc', NS)[1], 'Singapore')

    replacements = {
        1: ['Prior approval dated 1 May 2026. Fictional historical record only.',
            'Approve TL-01 SGD 45m and RCF-01 SGD 10m until 30 April 2027. Source: section 7 terms below.',
            'Historical classification detail not reproduced. This demo copy records an exception, not a conclusion about watchlist status.',
            'DEMO-CAS-001 approved 1 May 2026 by fictional human signatories in section 14.',
            'Current review requires fresh classification evidence.'],
        2: ["Synthetic exposures at 30 April 2026, SGD'000. Source: historical facility schedule embedded below.",
            'Only these two facilities are in the fictional obligor group. Current conduct must be obtained separately.'],
        3: ['Historical conditions are recorded below. Current developments belong to the new review and are not backdated into this record.'],
        4: ['Industrial property REIT with assets in Singapore, Australia and Japan. Public source: annual-report-2025.pdf (AR), physical p2. Public source URL and retrieval date are recorded in manifest.yaml public_sources.',
            'Property: high-specifications industrial; public 31 Dec 2025 data, AR pp72-73. Portfolio: AR p50; WALE: AR p53. Scopes are separate.'],
        5: ['Public sponsor and other unitholder interests at 31 Dec 2025, AR p10. Approximate percentages as reported; do not substitute the later March 2026 register.'],
        6: ['Public historical management roles from AR p35. These are not current-period confirmations.'],
        7: ['Historical approved terms, 1 May 2026. These are the source assumptions for this fictional prior approval.'],
        8: ['RCF expressly unsecured with negative pledge; TL secured by assumed mortgage and rents. Source: section 7.'],
        9: [f"Primary: fictional rent SGD {cash['rental']:.2f}m less costs 1.80m and reserves 0.90m: cash for service {cash['available']:.2f}m. Run rate near public FY2025 rent {property_history['rental_income_fy2025']}m (AR p73). Current review needs fresh inputs.",
            'Secondary: refinancing or sale, uncommitted. No sponsor guarantee or refinancing receipt is assumed.',
            'Historical lease details not reproduced; do not substitute this table for the current property schedule.'],
        10: ['Public FY2025 observations: annual-report-2025.pdf (AR) physical pp50, 53 and 59. Other periods and untranscribed fields are marked Gap. Public values are not adjusted for the fictional deal.',
             'Public metrics retain their reported definitions (AR p59 footnotes), including share of JV debt and FRS 116 exclusions. No new regulatory compliance conclusion. Historical gaps accepted only for this fictional archival copy. Source URL/retrieval: manifest.yaml public_sources.'],
        12: ['Historical internal grade only. It cannot satisfy the current internal-rating report requirement.'],
        13: ['Synthetic six-month excerpt, Nov 2025-Apr 2026, SGD m. Mean uses month-end samples. Embedded historical data; it cannot satisfy the current 12-month conduct requirement.'],
        14: ['Fictional historical CA position: support the limits in section 7 subject to conditions below. Human sign-offs are synthetic. This is not the current CA recommendation. Historical omissions in sections 1 and 4-6 and 9-13 are acknowledged for this demo archival copy only, not waived in the current review.']
    }
    # Replace narrative instructions in their existing slots; preserve headings/labels.
    for i in range(1, 15):
        paragraphs = outer[i].find('w:tr/w:tc', NS).findall('w:p', NS)
        pending = iter(replacements.get(i, []))
        for p in paragraphs:
            value = text(p)
            if '[' in value or value.startswith(('Please ', 'CAS Approved on')):
                set_text(p, next(pending, 'Historical detail not reproduced in this demo copy.'))
    row(1, 0, 1, [name, 'Not reproduced', 'Apr26', 'Not reproduced'])
    row(1, 0, 4, ['Account Strategy/Action Plan', 'Obtain fresh evidence for renewal; historical classification omitted.'])
    row(1, 0, 5, ['Timeline for Action Plan', 'Before renewal'])
    row(1, 1, 0, ['SM status and DPD test: historical detail not reproduced', 'Not assessed', 'Not assessed'])
    row(1, 1, 1, ['LOD assessment requires classification evidence', 'Not assessed', 'Not assessed'])
    row(2, 0, 1, [name, 'TL-01', '45,000', '42,000', '45,000', '0', '30 Apr 2027', 'Secured'])
    row(2, 0, 2, [name, 'RCF-01', '10,000', '5,000', '10,000', '0', '30 Apr 2027', 'Unsecured'])
    row(2, 0, 3, ['Not used', '-', '-', '-', '-', '-', '-', '-'])
    row(2, 0, 4, ['Total obligor group', '55,000', '47,000', '55,000', '0', '-', '-'])
    row(3, 0, 1, ['1 May 2026', 'Prior demo approval', 'Section 14', 'Historical', 'Renewal needs fresh review'])
    row(3, 0, 2, ['Not used', '-', '-', '-', '-'])
    row(3, 1, 1, ['C01', 'Updated valuation and insurance before renewal', 'Due at renewal', 'Section 14 conditions'])
    row(3, 1, 2, ['C03', 'Quarterly certificate and monitoring', 'Ongoing', 'Current evidence required'])
    row(4, 0, 0, ['Borrower', name])
    row(4, 0, 1, ['Date of incorporation / listing', public['listing_date']+' (listing; AR p2)'])
    row(4, 0, 2, ['Listing exchange', 'SGX (AR p2)'])
    row(4, 0, 3, ['Industry code', 'Current CA confirmation required'])
    row(4, 0, 4, ['Principal activities', 'Income-producing industrial properties (AR p2)'])
    row(4, 0, 5, ['Manager / sponsor', public['manager']+' / '+public['sponsor']+' (AR p2)'])
    row(4, 1, 1, [prop, 'Singapore', 'Industrial', property_history['valuation'], '31 Dec 2025', property_history['occupancy_pct'], 'Gap'])
    row(4, 1, 2, ['Not used', '-', '-', '-', '-', '-', '-'])
    row(4, 1, 3, ['Total portfolio', public['portfolio_valuation'], '31 Dec 2025', public['occupancy_pct'], public['wale_years']])
    row(5, 0, 1, [public['sponsor'], public['sponsor_holding_pct'], 'Approximate; AR p10'])
    row(5, 0, 2, ['Other unitholders', public['other_holding_pct'], 'Approximate; AR p10'])
    row(5, 0, 3, ['Not used', '-', '-'])
    row(5, 0, 4, ['Total', str(D(public['sponsor_holding_pct'])+D(public['other_holding_pct'])), 'Public approximate interests'])
    set_text(tables[5][1].find('w:tr/w:tc', NS), 'Sponsor and other unitholders hold the REIT; manager provides management services. Public structure: AR p10. No corporate guarantee follows from ownership.')
    for j, person in enumerate(public['management'], 1):
        row(6, 0, j, [*person, 'AR p35'])
    row(6, 0, 3, ['Not used', '-', '-', '-'])
    row(6, 1, 1, [public['sponsor'], 'Sponsor', 'AR p2; no support commitment inferred'])
    row(6, 1, 2, [public['manager'], 'Manager', 'AR p2'])
    row(6, 1, 3, ['Trustee', 'Acts for unitholders', 'AR p10; legal name not transcribed'])
    terms = [
        [name, name], ['Secured term loan', 'Unsecured RCF'], ['SGD 45m', 'SGD 10m'],
        ['Property financing', 'Working capital'], ['30 Apr 2027', '30 Apr 2027'],
        ['90 days from approval', 'Until maturity'], ['Bullet at maturity', 'Bullet at maturity'],
        ['SORA + 160 bp', 'SORA + 180 bp'], [f'Mortgage: {prop}; rents', 'Negative pledge; pari passu'],
        ['LTV <=55%; group leverage <=45%; ICR >=2x', 'Group leverage <=45%; ICR >=2x'],
        ['Evidence of security required', 'No guarantee assumed']]
    for j, values in enumerate(terms, 1):
        old = tables[7][0].findall('w:tr', NS)[j].findall('w:tc', NS)[0]
        row(7, 0, j, [text(old), *values])
    row(8, 0, 1, ['Mortgage', prop, property_history['valuation'], 'AR pp72-73; 31 Dec 2025', 'Public value; fictional charge', f'{historical_ltv:.2f} drawn', f"42 / {property_history['valuation']} x 100; section 2"])
    row(8, 0, 2, ['Assignment of rents', 'Assumed property rents', 'Not separately valued', '-', '-', '-', 'No double count'])
    row(8, 0, 3, ['No guarantee assumed', '-', '-', '-', '-', '-', 'Section 7'])
    for j, value in enumerate(['Demo Insurer', 'SGD 90m reinstatement', 'Fictional fire and damage cover', '31 Oct 2026', 'The Bank; fictional assumption']):
        cell = tables[8][1].findall('w:tr', NS)[j].findall('w:tc', NS)[0]
        row(8, 1, j, [text(cell), value])
    row(9, 0, 0, ['Measure', 'FY2024', 'FY2025', 'Projected FY2027', 'Remarks'])
    old_interest = D('45')*D('.04')+D('10')*D('.042')
    row(9, 0, 1, ['Net property income / EBITDA (S$m)', 'Gap', 'Gap', str(cash['npi']), 'Synthetic property, not group'])
    row(9, 0, 2, ['Interest expense (S$m)', 'Gap', 'Gap', str(old_interest), '45 at 4%; 10 at 4.2%'])
    row(9, 0, 3, ['Interest coverage (x)', 'Gap', 'Gap', format(cash['npi']/old_interest, '.2f'), 'Property NPI/interest; not MAS ICR'])
    row(9, 0, 4, ['Debt service coverage (x)', 'Gap', 'Gap', format(cash['available']/(old_interest+D(55)), '.2f'), 'Includes 55m bullet; no committed refinance'])
    # Preserve template metric names and periods, marking absent inputs clearly.
    row(10, 0, 0, ['S$m', 'FY2023', 'FY2024', 'FY2025', 'Interim', 'Remarks'])
    for idx, key, source in [(9, 'debt', 'AR p59; gross debt basis'), (13, 'leverage_pct', 'AR p59'),
                             (14, 'icr_x', 'AR p59; MAS ICR'), (15, 'cost_of_debt_pct', 'AR p59'),
                             (16, 'debt_maturity_years', 'AR p59'), (17, 'fixed_rate_pct', 'AR p59'),
                             (19, 'occupancy_pct', 'AR p50'), (20, 'wale_years', 'AR p53; rent weighted')]:
        metric = text(tables[10][0].findall('w:tr', NS)[idx].findall('w:tc', NS)[0])
        row(10, 0, idx, [metric, 'Gap', 'Gap', public[key], 'Gap', source])
    for i, table in enumerate(tables[10]):
        if i == 1:
            row(10, 1, 3, ['Contractual group leverage', '<=45%', public['leverage_pct'], str(D(45)-D(public['leverage_pct']))+' pp', 'Within fictional limit'])
            row(10, 1, 4, ['Contractual group ICR', '>=2x', public['icr_x'], str(D(public['icr_x'])-D(2))+'x', 'Within fictional limit'])
    risks = [('Refinancing', 'Bullet maturity in 2027', 'Fresh renewal review; no committed refinancing'),
             ('Leasing', 'Rents may fall or tenants leave', 'Obtain current leases and projections'),
             ('Valuation', 'Security value may decline', 'LTV cap and updated valuation'),
             ('Interest rate', 'Floating SORA pricing', 'Review stressed service capacity')]
    for j, (risk, description, mitigation) in enumerate(risks, 1):
        row(11, 0, j, [str(j), risk, description+' (scenario; section 7)', mitigation])
    row(12, 0, 1, [name, 'DEMO-G4', 'Not reproduced', '30 Apr 2026', 'Fictional supplied historical grade'])
    row(12, 0, 2, ['Not used', '-', '-', '-', '-'])
    for idx, facility in enumerate(['TL-01', 'RCF-01'], 1):
        series = c['conduct']['month_end_tl' if idx == 1 else 'month_end_rcf'][:6]
        peaks = c['conduct']['month_end_tl' if idx == 1 else 'monthly_peak_rcf'][:6]
        mean = sum(D(str(x)) for x in series)/len(series)
        row(13, 0, idx, [facility, '45' if idx == 1 else '10', str(max(peaks)), format(mean, '.2f'),
                        '0 / 0 / 0', '1 / 3 DPD' if idx == 1 else '0 / 0 DPD', 'Synthetic six-month excerpt'])
    row(13, 1, 1, ['Group leverage', '<=45%', '31 Dec 2025', public['leverage_pct']+'%', 'Within; AR p59'])
    row(13, 1, 2, ['Group ICR', '>=2x', '31 Dec 2025', public['icr_x']+'x', 'Within; AR p59'])
    row(13, 2, 0, ['Historical bureau and conduct details not reproduced', 'Not assessed', 'Not assessed'])
    row(14, 0, 1, ['C01/C02', 'Updated valuation and insurance', 'Before renewal'])
    row(14, 0, 2, ['C03', 'Quarterly certificate and covenant monitoring', 'Quarterly'])
    for j, (person, decision, date_) in enumerate([
        ('Demo CA', 'Submitted; fictional', '29 Apr 2026'),
        ('Demo Credit Head', 'Supported; fictional', '30 Apr 2026'),
        ('Demo Approver', 'Approved with conditions; fictional', '1 May 2026')], 1):
        role = tables[14][1].findall('w:tr', NS)[j].findall('w:tc', NS)[0]
        row(14, 1, j, [text(role), person, decision, date_])
    # Remove leftover instructional/sample strings without changing layout.
    for p in root.findall('.//w:p', NS):
        value = text(p)
        if '☐ Secured' in value:
            set_text(p, 'Partially secured: secured TL and unsecured RCF (section 7).')
        elif '☐ Recommended for approval' in value:
            set_text(p, 'Historical CA position: recommended with conditions; fictional (section 14).')
        elif '[' in value or 'DD/MM/YYYY' in value:
            set_text(p, re.sub(r'\[[^\]]*\]', 'Not reproduced', value).replace('DD/MM/YYYY', 'Not reproduced'))
        elif value == 'Not reproduced':
            set_text(p, 'Gap')
    patches = {'word/document.xml': serialize(root, originals['word/document.xml'])}
    for name_ in originals:
        if name_.startswith('word/header') and name_.endswith('.xml'):
            h = ET.fromstring(originals[name_])
            set_text(h.find('w:p', NS), LABEL)
            patches[name_] = serialize(h, originals[name_])
    settings = ET.fromstring(originals['word/settings.xml'])
    field = settings.find('w:updateFields', NS)
    if field is None:
        field = ET.SubElement(settings, W+'updateFields')
    field.set(W+'val', 'true')
    patches['word/settings.xml'] = serialize(settings, originals['word/settings.xml'])
    out = ROOT / 'demo/synthetic/tranche_2/prior_es.docx'
    with ZipFile(TEMPLATE) as source, ZipFile(out, 'w') as dest:
        for info in source.infolist():
            dest.writestr(info, patches.get(info.filename, originals[info.filename]))
    print(out.relative_to(ROOT))


if __name__ == '__main__':
    fill()
