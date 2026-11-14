"""Build B03 source-document fixtures offline; no production analytics or API calls.

Run with the project's Python environment. Workbook authoring is a separate
artifact-tool step; --manifest runs after that step. All arithmetic uses Decimal.
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date
from decimal import Decimal as D
from email.message import EmailMessage
from email.policy import SMTP
import hashlib
import json
from pathlib import Path
import textwrap

import fitz
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'demo/synthetic'
QA = ROOT / 'runtime/b03'
LABEL = 'SYNTHETIC DEMO DATA, not a real record'
DISCLAIMER = 'Fictional scenario only. No real lending relationship is stated or implied.'
TEMPLATE = ROOT / 'templates/ES_Template_FIG_draft_v0.1.docx'
TEMPLATE_HASH = '9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21'


def load_case():
    return yaml.safe_load((PACK / 'case.yaml').read_text())


def money(value):
    return f'{D(str(value)):,.2f}'


def calculations(c):
    fs = c['facilities']
    p = c['property']
    total = lambda key: sum(D(f[key]) for f in fs)
    rents = sum(D(l['monthly_rent_sgd']) for l in c['leases']) * 12 / D(1000000)
    npi = rents - D(p['operating_cost_annual'])
    available = npi - D(p['reserve_annual']) - D(p['capex_reserve_annual'])
    occupied = sum(l['area_sqm'] for l in c['leases'] if l['monthly_rent_sgd'] > 0)
    return dict(existing=total('existing_limit'), outstanding=total('outstanding'),
                proposed=total('proposed_limit'), change=total('proposed_limit')-total('existing_limit'),
                rental=rents, npi=npi, available=available, occupied=occupied,
                occupancy=D(occupied)/D(p['nla_sqm'])*100,
                ltv=D(fs[0]['proposed_limit'])/D(p['initial_value'])*100,
                revised_ltv=D(fs[0]['proposed_limit'])/D(p['revised_value'])*100,
                current_ltv=D(fs[0]['outstanding'])/D(p['initial_value'])*100)


def pdf(path, title, c, pages):
    """Simple paginated textual source reports, with searchable text and stable pages."""
    target = PACK / path
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for number, paragraphs in enumerate(pages, 1):
        page = doc.new_page(width=595, height=842)
        page.insert_text((42, 38), LABEL, fontsize=10, fontname='hebo', color=(0.55, 0.08, 0.08))
        page.insert_text((42, 68), title, fontsize=16, fontname='hebo')
        y = 93
        for paragraph in [f"Borrower: {c['borrower']['name']} | Lender: {c['lender']}", DISCLAIMER, *paragraphs]:
            for line in textwrap.wrap(paragraph, width=92, break_long_words=False, break_on_hyphens=False):
                if y > 770:
                    raise ValueError(f'Explicit page capacity exceeded: {path}')
                page.insert_text((42, y), line, fontsize=10.5)
                y += 15
            y += 10
        page.insert_text((42, 812), f'{target.name} | Page {number} of {len(pages)}', fontsize=8)
    doc.set_metadata({'title': title, 'author': 'WB Credit synthetic fixture builder', 'subject': LABEL})
    doc.save(target, garbage=4, deflate=True, no_new_id=True)
    doc.close()


def public_reference(c, doc_id):
    manifest = yaml.safe_load((ROOT / c['borrower']['public_manifest']).read_text())
    return next(d for d in manifest['documents'] if d['id'] == doc_id)


def reports(c):
    v = calculations(c)
    history = c['public_property']
    property_ref = public_reference(c, history['document_id'])
    prop = c['borrower']['property']
    fs = c['facilities']
    terms = [f"Proposal dated {c['proposal_date']}. Renewal and upsize, subject to human credit review.",
             f"TL-01: existing SGD {money(fs[0]['existing_limit'])}m; proposed SGD {money(fs[0]['proposed_limit'])}m. RCF-01: existing SGD {money(fs[1]['existing_limit'])}m; proposed SGD {money(fs[1]['proposed_limit'])}m.",
             f"Total proposed SGD {money(v['proposed'])}m; increase SGD {money(v['change'])}m. All exposures are fictional and solely to the Bank.",
             f"TL-01: first mortgage over {prop} and assignment of rents. No corporate guarantee is assumed. Security terms are fictional; public property facts are cited in valuation_v1.pdf page 2.",
             'RCF-01: expressly unsecured, negative pledge and pari passu undertaking. CA confirmation is required before adopting this description.',
             f"TL-01 matures {fs[0]['proposed_maturity']}, bullet principal; RCF-01 matures {fs[1]['proposed_maturity']}, renewable only by a fresh human decision. No automatic extension.",
             'Purpose: refinance the existing term loan and fund property capital expenditure; revolving facility for working capital. TL availability: 90 days from execution; RCF drawings up to its maturity.',
             f"Pricing: TL-01 3-month SORA + {fs[0]['margin_bps']} bp, upfront fee {fs[0]['upfront_fee_pct']}%; RCF-01 3-month SORA + {fs[1]['margin_bps']} bp, upfront fee {fs[1]['upfront_fee_pct']}%. Interest quarterly. RCF undrawn fee 0.40% p.a.",
             f"Synthetic contractual covenants: aggregate leverage <= {c['covenants']['leverage_max_pct']}%; reported group ICR >= {c['covenants']['icr_min_x']}x; TL drawn LTV <= {c['covenants']['ltv_max_pct']}%. Test quarterly and before drawings. Contractual thresholds are not regulatory guidance.",
             'Before drawdown: CA review of valuation, insurance and security evidence; required documents and human approvals. Legal perfection is an assumption requiring evidence, not established by this pack.']
    pdf('tranche_1/term_sheet.pdf', 'Indicative term sheet', c, [terms])
    pdf('tranche_2/cas.pdf', 'Credit application summary', c, [[
        f"CAS DEMO-CAS-002 dated {c['proposal_date']}; renewal and upsize of the fictional existing relationship.",
        f"Existing limits SGD {money(v['existing'])}m; outstanding SGD {money(v['outstanding'])}m at {c['as_of']}; proposed SGD {money(v['proposed'])}m; increase SGD {money(v['change'])}m.",
        *[f"{f['id']}: {f['type']}. Existing {money(f['existing_limit'])}, outstanding {money(f['outstanding'])}, proposed {money(f['proposed_limit'])} (SGD million)." for f in fs],
        'Source: limits_utilisation.xlsx, Exposure rows 6-7, synthetic. No other obligors or currencies are included in this scenario. No FX conversion is used.',
        'Requested purpose and terms: term_sheet.pdf page 1. Rationale: stagger maturities and provide a capital expenditure buffer. This is an RM request; current CA position is not supplied.',
        'Prior synthetic approval: DEMO-CAS-001 on 2026-05-01, term limit 45.00 and RCF limit 10.00 (SGD million); maturity 2027-04-30. Source: prior_es.docx sections 2 and 7.',
        'Property security brings valuation and insurance into scope. Property income brings rent roll, leases and projections into scope. Financial covenants require compliance and monitoring reports.',
        'Review current conduct and internal rating when supplied in tranche 3. Historical excerpts in the prior ES do not satisfy current-period reports. Industry code remains a CA-confirmation step.',
        'Current classification: Pass; not on Watchlist or Special Mention. Current days past due (DPD): 0. Current recommendation remains for the CA. A missing input is a document gap, not a factual conclusion.'
    ]])
    pdf('tranche_2/prior_conditions.pdf', 'Prior approval conditions and credit comments', c, [[
        'Prior synthetic decision DEMO-CAS-001 dated 2026-05-01. Source: prior_es.docx section 14.',
        'C01: provide an updated secured-property valuation before renewal. Status: document supplied for review. Evidence: valuation_v1.pdf pages 1-2. Acceptance is a human review step.',
        'C02: provide renewed insurance noting the Bank as mortgagee/loss payee. Status: document supplied for review. Evidence: insurance.pdf page 1. No inference of legal perfection.',
        'C03: quarterly certificate and covenant monitoring. Status: current certificate supplied for review. Evidence: compliance_certificate.pdf page 1; covenant_monitoring.xlsx Tests rows 6-8.',
        'Outstanding action: verify the proposed fully drawn TL against the latest valuation before any drawdown. An updated report must trigger re-review of security and dependent analysis.',
        'No waiver is recorded by this fixture. Current recommendation and submission exceptions require an explicit CA entry.'
    ]])
    ref = public_reference(c, c['public_observations'][0]['document_id'])
    obs = {o['metric']: o['value'] for o in c['public_observations']}
    pdf('tranche_2/compliance_certificate.pdf', 'Compliance certificate', c, [[
        f"Fictional certificate issued 2026-11-04, testing exposures as of {c['as_of']}, signed by Demo Authorised Signatory. It does not represent an actual client attestation.",
        f"Public group observations at 2026-09-30: reported aggregate leverage {obs['aggregate_leverage_pct']}%; reported interest coverage {obs['interest_coverage_x']}x. These are quoted public figures, not synthetic consolidated totals or a newly calculated regulatory ratio.",
        f"Public source: {ref['title']}, physical PDF page 2; retrieved {ref['retrieved_at']}. URL: {ref['url']}",
        f"Fictional contractual tests: leverage maximum {c['covenants']['leverage_max_pct']}%; ICR minimum {c['covenants']['icr_min_x']}x. Headroom: {money(D(c['covenants']['leverage_max_pct'])-D(obs['aggregate_leverage_pct']))} percentage points and {money(D(obs['interest_coverage_x'])-D(c['covenants']['icr_min_x']))}x respectively. Source thresholds: term_sheet.pdf page 1.",
        f"Current TL drawn LTV at {c['as_of']}: SGD {money(fs[0]['outstanding'])}m / SGD {money(c['property']['initial_value'])}m = {money(v['current_ltv'])}%. This is property/facility data only. Sources: limits_utilisation.xlsx Exposure row 6; valuation_v1.pdf page 1.",
        f"Fully drawn proposed TL LTV: {money(v['ltv'])}%; contractual maximum {c['covenants']['ltv_max_pct']}%. Proposed and current exposures are separate tests.",
        'This certificate is dated before the revised valuation. It must not be reused as a fresh assessment after that update. No group portfolio total is adjusted for this fictional deal.'
    ]])
    pdf('tranche_2/pricing.pdf', 'Pricing report', c, [[
        f"Proposed terms dated {c['proposal_date']}; source: term_sheet.pdf page 1.",
        *[f"{f['id']}: margin {f['margin_bps']} basis points over 3-month SORA; upfront fee {f['upfront_fee_pct']}% of proposed SGD {money(f['proposed_limit'])}m = SGD {money(D(f['proposed_limit'])*D(f['upfront_fee_pct'])*10000)} (computed in Python)." for f in fs],
        'RCF undrawn commitment fee: 0.40% p.a. on daily undrawn amount. No daily fee forecast is represented here.',
        'No live SORA fixing, RAROC, funding cost or profitability hurdle is supplied. These are named gaps; no commercial approval is implied.',
        'The RM supports review of the request; the CA must state the current position independently.'
    ]])
    for rev in (False, True):
        value = c['property']['revised_value' if rev else 'initial_value']
        date_ = c['late_valuation_date'] if rev else c['as_of']
        name = 'late_update/valuation_v2.pdf' if rev else 'tranche_2/valuation_v1.pdf'
        ltv = v['revised_ltv' if rev else 'ltv']
        pdf(name, 'Revised property valuation' if rev else 'Property valuation report', c, [[
            f"Report {'DEMO-VAL-002' if rev else 'DEMO-VAL-001'} issued {date_ if rev else '2026-11-04'}, valuation effective {date_}. Property: {prop}. Fictional valuer: Demo Valuer. Market value: SGD {money(value)} million.",
            ('Supersedes DEMO-VAL-001, effective 2026-10-31 and issued 2026-11-04. '+c['property']['revision_reason'] if rev else 'Initial valuation in the fictional scenario. This is a complete demo property-report input, not the public annual-report summary and not a professional appraisal.'),
            'Scope: the named property only. Public facts and their historical date are on page 2. Later valuations, tenant details and security terms are fictional; published group accounts are unchanged.',
            f"Public net lettable area {c['property']['nla_sqm']:,} sqm. Synthetic rent roll at {c['as_of']}: leased area {v['occupied']:,} sqm; occupancy {money(v['occupancy'])}%. Source: rent_roll.xlsx Leases rows 6-9. Annual rent SGD {money(v['rental'])}m, property NPI SGD {money(v['npi'])}m after SGD {money(c['property']['operating_cost_annual'])}m costs. No claim about real tenants.",
            f"Fully drawn proposed term loan SGD {money(fs[0]['proposed_limit'])}m / value SGD {money(value)}m = {money(ltv)}% LTV. RCF is unsecured and excluded from this numerator. Source: term_sheet.pdf page 1.",
            f"Contractual maximum {c['covenants']['ltv_max_pct']}%. Headroom {money(D(c['covenants']['ltv_max_pct'])-ltv)} percentage points. {'Proposed draw exceeds this limit; human reassessment is required.' if rev else 'Proposed draw is within this fictional limit, subject to other checks and human approval.'}",
        ], [
            'Valuation assumptions and inspection scope',
            f"Public property facts at {history['as_of']}: {history['property_type']}; {history['lease_type']}. GFA {history['gfa_sqm']:,} sqm; NLA {history['nla_sqm']:,} sqm. Land tenure {history['land_tenure_years']} years; expiry {history['land_lease_expiry']}; remaining land lease {history['remaining_land_lease_years']} years at that public date.",
            f"Acquired {history['acquisition_date']}; purchase price/development cost SGD {history['purchase_price_or_development_cost']}m. Public occupancy {history['occupancy_pct']}%; valuation SGD {history['valuation']}m at {history['as_of']}; FY2025 rental income SGD {history['rental_income_fy2025']}m.",
            f"Public source: {property_ref['title']}, physical PDF pages 72-73 (printed 70-71), property row 5. Retrieved {property_ref['retrieved_at']}. URL: {property_ref['url']}",
            'Synthetic income approach with reletting assumptions. No cadastral search, inspection or independent comparable transactions were conducted.',
            f"Income check: annual rent {money(v['rental'])} less operating costs {money(c['property']['operating_cost_annual'])} = NPI {money(v['npi'])} (SGD million). Implied NPI/value yield {money(v['npi']/D(value)*100)}%. This is an arithmetic yield, not a public valuation capitalisation rate.",
            'Assume continued lettability and no contamination for scenario modelling only. Title, enforceability, ranking, environmental and legal due diligence require separate evidence.',
            'No actual valuer, signature, seal, registration number or bank record is represented. Sources for scenario operands: rent_roll.xlsx Leases rows 6-9; projections.xlsx Forecast rows 6-8; term_sheet.pdf page 1.',
            ('The 31 October rent roll is a pre-notice snapshot, not a new occupancy assessment. Projections dated 2 November assume renewals and require reassessment after this notice; no revised cash flow is supplied.' if rev else 'Synthetic occupancy is held near the public 50.2% baseline; tenant areas are rounded to whole sqm. Later fictional values do not update the published valuation.')
        ]])
    pdf('tranche_2/insurance.pdf', 'Property insurance report', c, [[
        f"Policy DEMO-INS-001 for {prop}; fictional insurer Demo Insurer. Report dated {c['as_of']}.",
        f"Reinstatement sum insured SGD {money(c['property']['insured_reinstatement_value'])}m. This is not market value and is not the LTV denominator.",
        'Period: 2026-11-01 to 2027-10-31. Scenario coverage: property damage, fire and business interruption for 12 months. Deductible SGD 0.05m per event.',
        'The Bank is named as mortgagee and loss payee in this fictional policy summary. This does not establish an actual insurance contract or perfected security.',
        'Exclusions: wear and tear, gradual contamination and uninsured tenant liabilities. Review adequacy, coverage and renewal before drawdown. No real insurer, broker or policy reference is used.'
    ]])
    pdf('tranche_3/internal_rating.pdf', 'Internal credit rating report', c, [[
        f"Input-only fictional rating, supplied by Demo Rating Officer on {c['internal_rating']['current_date']}: {c['internal_rating']['grade']}. Previous rating {c['internal_rating']['grade']} dated {c['internal_rating']['prior_date']}.",
        'DEMO-G4 is a made-up grade on a demo scale. No probability of default, bank scale or mapping to a public agency rating is asserted.',
        'Fictional analyst rationale: retain grade for this scenario, while reviewing refinancing, concentration and valuation sensitivity. This is supplied source wording, not an AI-inferred rating.',
        'Rating validity for this exercise: to 2027-10-31, subject to earlier review following material evidence changes. Proposed structure and credit approval remain separate human decisions.',
        'External agency releases in the public pack remain separate public sources and cannot satisfy this internal-rating requirement.'
    ]])
    msg = EmailMessage(policy=SMTP)
    msg['X-Synthetic-Data'] = LABEL
    msg['From'] = 'Demo RM <rm@example.invalid>'
    msg['To'] = 'Demo CA <ca@example.invalid>'
    msg['Date'] = 'Mon, 02 Nov 2026 09:00:00 +0800'
    msg['Subject'] = f"{LABEL}: renewal and upsize review"
    msg.set_content(f"{LABEL}\n{DISCLAIMER}\n\nBorrower: {c['borrower']['name']}\nLender: {c['lender']}\n\nPlease review the attached indicative term sheet dated {c['proposal_date']}. "
                    f"The synthetic request is SGD {money(v['proposed'])}m total limits, up from SGD {money(v['existing'])}m: term loan 60.00m and RCF 15.00m. "
                    f"The term loan is secured against {prop}; the RCF is expressly unsecured.\n\n"
                    'I support review of the request for refinancing, capital expenditure and working capital. Source: term_sheet.pdf page 1. '
                    'This RM view does not supply the CA recommendation or grant credit approval. Please obtain the remaining client and internal documents.\n\nDemo RM\n')
    (PACK / 'tranche_1/rm_support.eml').write_bytes(msg.as_bytes())


def workbook_specs(c):
    """Values-only bank-style source extracts; Python owns computed snapshots."""
    v = calculations(c)
    specs = []

    def sheet(name, title, note, columns, rows, formats=None, widths=None):
        return dict(name=name, title=title, note=note, columns=columns, rows=rows,
                    formats=formats or {}, widths=widths or {})

    def book(file, sheets):
        specs.append(dict(file=file, borrower=c['borrower']['name'], label=LABEL,
                          disclaimer=DISCLAIMER, sheets=sheets))

    book('tranche_2/limits_utilisation.xlsx', [sheet('Exposure', 'Limits and utilisation at 31 Oct 2026',
         'SGD million. Synthetic exposure to the Bank only. Renewal proposal: term_sheet.pdf p1.',
         ['Facility', 'Existing limit', 'Outstanding', 'Proposed limit', 'Change', 'Existing maturity', 'Proposed maturity', 'Security'],
         [[f['id'], float(f['existing_limit']), float(f['outstanding']), float(f['proposed_limit']),
           float(D(f['proposed_limit'])-D(f['existing_limit'])), f['existing_maturity'], f['proposed_maturity'],
           'Secured' if i == 0 else 'Unsecured'] for i, f in enumerate(c['facilities'])] +
         [['Total', *[float(v[k]) for k in ('existing', 'outstanding', 'proposed', 'change')], None, None, None]],
         {'B:E': '#,##0.00', 'F:G': 'yyyy-mm-dd'})])
    ref = public_reference(c, c['public_observations'][0]['document_id'])
    obs = {o['metric']: D(o['value']) for o in c['public_observations']}
    book('tranche_2/covenant_monitoring.xlsx', [sheet('Tests', 'Covenant monitoring at 31 Oct 2026',
         'Contractual limits are fictional. Group actuals: public 3Q2026 update p2 at 30 Sep. LTV: synthetic drawn TL.',
         ['Metric', 'Actual', 'Limit', 'Direction', 'Headroom', 'Unit', 'Test date', 'Source'],
         [['Aggregate leverage', float(obs['aggregate_leverage_pct']), 45, 'maximum', float(D(45)-obs['aggregate_leverage_pct']), 'percentage points', '2026-09-30', 'Public update p2'],
          ['Group ICR', float(obs['interest_coverage_x']), 2, 'minimum', float(obs['interest_coverage_x']-2), 'times', '2026-09-30', 'Public update p2'],
          ['Drawn TL LTV', float(v['current_ltv']), 55, 'maximum', float(55-v['current_ltv']), 'percentage points', c['as_of'], 'Limits row 6; valuation v1 p1']],
         {'B:C': '0.00', 'E:E': '0.00', 'G:G': 'yyyy-mm-dd'}, {'A': 25, 'F': 24, 'H': 30}),
         sheet('Sources', 'Covenant source register', 'Public figures remain public in a synthetic certificate. No group totals are invented.',
               ['Source', 'Page or range', 'Date', 'URL or path'],
               [[ref['title'], 'PDF page 2', ref['retrieved_at'], ref['url']],
                ['Contractual limits', 'PDF page 1', c['proposal_date'], 'tranche_1/term_sheet.pdf'],
                ['Drawn loan', 'Exposure row 6', c['as_of'], 'tranche_2/limits_utilisation.xlsx'],
                ['Property value', 'PDF page 1', c['as_of'], 'tranche_2/valuation_v1.pdf']],
               {'C:C': 'yyyy-mm-dd'}, {'A': 35, 'D': 85})])
    leases = c['leases']
    history = c['public_property']
    property_ref = public_reference(c, history['document_id'])
    book('tranche_2/rent_roll.xlsx', [sheet('Leases', f"Rent roll for {c['borrower']['property']}",
         'At 31 Oct 2026. Fictional tenant split/rents; public NLA and occupancy baseline in Sources. SGD rent excludes taxes/service charge.',
         ['Tenant', 'Sector', 'Area sqm', 'Monthly rent SGD', 'Annual rent SGD', 'Lease expiry'],
         [[l['tenant'], l['sector'], l['area_sqm'], l['monthly_rent_sgd'], l['monthly_rent_sgd']*12, l['expiry']] for l in leases],
         {'C:E': '#,##0', 'F:F': 'yyyy-mm-dd'}, {'A': 25, 'B': 24}),
         sheet('Sources', 'Property source and scenario basis', 'Public facts retain FY2025 dates. Tenant allocations and later cash flows are fictional.',
               ['Source or assumption', 'Value', 'Date', 'Reference'],
               [['Public NLA sqm', history['nla_sqm'], history['as_of'], 'Annual report physical p72, row 5'],
                ['Public occupancy %', float(history['occupancy_pct']), history['as_of'], 'Annual report physical p73, row 5'],
                ['Public FY2025 rent SGD m', float(history['rental_income_fy2025']), history['as_of'], 'Annual report physical p73, row 5'],
                ['Synthetic leased sqm', v['occupied'], c['as_of'], 'Whole-sqm allocation holds occupancy near public 50.2%'],
                ['Synthetic annual rent SGD m', float(v['rental']), c['as_of'], 'Fictional run rate near public FY2025 rent; not reported FY2026 income'],
                [property_ref['title'], 'PDF pp72-73; printed pp70-71', property_ref['retrieved_at'], property_ref['url']]],
               {'C:C': 'yyyy-mm-dd'}, {'A': 35, 'B': 30, 'D': 85})])
    annual = v['rental'] * 1000000
    profile_rows = []
    for year in (2027, 2028, 2029, 2030):
        subset = [l for l in leases if l['expiry'] and date.fromisoformat(l['expiry']).year == year]
        rent = sum(D(l['monthly_rent_sgd'])*12 for l in subset)
        area = sum(l['area_sqm'] for l in subset)
        profile_rows.append([year, int(rent), area, float(rent/annual), float(D(area)/D(c['property']['nla_sqm']))])
    vacant = sum(l['area_sqm'] for l in leases if not l['expiry'])
    profile_rows.append(['Vacant', 0, vacant, 0, float(D(vacant)/D(c['property']['nla_sqm']))])
    profile_rows.append(['Total', int(annual), c['property']['nla_sqm'], 1, 1])
    book('tranche_2/lease_profile.xlsx', [sheet('Expiry', f"Lease expiry profile for {c['borrower']['property']}",
         'At 31 Oct 2026. Source: rent_roll.xlsx Leases rows 6-9. Area share uses total NLA, including vacancy.',
         ['Expiry year', 'Annual rent SGD', 'Area sqm', 'Share of rent', 'Share of total NLA'], profile_rows,
         {'B:C': '#,##0', 'D:E': '0.00%'}, {'A': 23, 'E': 26})])
    forecasts = []
    for yr in (2027, 2028, 2029):
        # Constant scenario assumptions, including full draw from the start.
        interest = D(60)*D('0.04') + D(15)*D('0.042')
        principal = D(15) if yr == 2027 else D(60) if yr == 2029 else D(0)
        debt_service = interest+principal
        forecasts.append([yr, float(v['rental']), 1.8, float(v['npi']), 0.6, 0.3,
                          float(v['available']), float(interest), float(principal), float(debt_service),
                          float(v['available']/debt_service)])
    book('tranche_2/projections.xlsx', [sheet('Forecast', 'Property cash flow and facility debt service',
         'SGD million; fictional full draw: TL 60 at 4.0%, RCF 15 at 4.2%. RCF repaid end 2027; no interest thereafter.',
         ['Year', 'Rent', 'Operating costs', 'NPI', 'Other reserve', 'Capex reserve', 'Cash for debt service', 'Interest', 'Bullet principal', 'Debt service', 'DSCR x'],
         # Replace later interest to reflect the RCF contractual bullet repayment.
         [row if row[0] == 2027 else row[:7]+[2.4, row[8], 2.4+row[8], float(v['available']/(D('2.4')+D(str(row[8]))))] for row in forecasts],
         {'B:K': '0.00'}, {'A': 12, 'G': 25, 'I': 23}),
         sheet('Assumptions', 'Projection assumptions', 'Scenario only. No group financial forecast; published portfolio totals are unchanged.',
         ['Assumption', 'Value', 'Unit or source'],
         [['Rent roll unchanged through 2029', float(v['rental']), 'SGD m per year; Leases rows 6-9'],
          ['Operating cost', 1.8, 'SGD m per year; fictional input'],
          ['Other reserve', 0.6, 'SGD m per year; fictional input'],
          ['Capex reserve', 0.3, 'SGD m per year; fictional input'],
          ['TL all-in interest', 0.04, 'decimal p.a.; scenario, not live SORA'],
          ['RCF all-in interest', 0.042, 'decimal p.a.; scenario, not live SORA'],
          ['TL full draw', 60, 'SGD m; term_sheet.pdf p1'],
          ['RCF full draw', 15, 'SGD m; term_sheet.pdf p1'],
          ['TL bullet', '2029-11-30', 'Annual model assumes year-end service; conservative full-year interest'],
          ['RCF bullet', '2027-11-30', 'Annual model assumes year-end service; conservative full-year interest'],
          ['Refinancing at maturity', 'Not committed', 'Cash deficit must remain visible; no refinance receipt assumed'],
          ['Lease renewals', 'Assumed at same rents', 'Forecast assumption only; no renewals are committed']],
         {'B:B': '0.000'}, {'A': 38, 'B': 24, 'C': 75})])
    months = [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]
    rows = []
    for i, (yr, mo) in enumerate(months):
        last = date(yr, mo, calendar.monthrange(yr, mo)[1]).isoformat()
        for f, series, peaks in [('TL-01', c['conduct']['month_end_tl'], c['conduct']['month_end_tl']),
                                 ('RCF-01', c['conduct']['month_end_rcf'], c['conduct']['monthly_peak_rcf'])]:
            rows.append([last, f, 45 if f == 'TL-01' else 10, series[i], peaks[i]])
    book('tranche_3/account_conduct.xlsx', [sheet('Monthly', 'Account conduct from Nov 2025 to Oct 2026',
         'SGD million. Month-end samples and independently supplied monthly peaks; averages are not daily averages. Fictional relationship only.',
         ['Month end', 'Facility', 'Limit', 'Month-end outstanding', 'Monthly peak outstanding'], rows,
         {'A:A': 'yyyy-mm-dd', 'C:E': '0.00'}, {'D': 31, 'E': 34}),
         sheet('Events', 'Account excess and payment events',
         'Complete synthetic event register for 1 Nov 2025 to 31 Oct 2026. Excess days inclusive; DPD = paid date minus due date.',
         ['Event', 'Facility', 'Start or due date', 'End or paid date', 'Amount SGD m', 'Cured date', 'Description'],
         [['Excess', 'RCF-01', '2026-06-14', '2026-06-15', 0.5, '2026-06-16', 'Peak 10.5 versus limit 10.0; two calendar days'],
          ['Past due', 'TL-01', '2026-03-31', '2026-04-03', 0.12, '2026-04-03', 'Quarterly interest paid three calendar days late']],
         {'C:D': 'yyyy-mm-dd', 'F:F': 'yyyy-mm-dd', 'E:E': '0.00'}, {'G': 62})])
    QA.mkdir(parents=True, exist_ok=True)
    (QA / 'workbooks.json').write_text(json.dumps(specs, indent=2))
    (QA / 'case.json').write_text(json.dumps(c, indent=2))


DOCUMENTS = [
    ('term-sheet', 'tranche_1/term_sheet.pdf', 2, 1, '2026-11-02'),
    ('rm-support', 'tranche_1/rm_support.eml', 12, 1, '2026-11-02'),
    ('cas', 'tranche_2/cas.pdf', 1, 2, '2026-11-02'),
    ('prior-es', 'tranche_2/prior_es.docx', 3, 2, '2026-05-01'),
    ('prior-conditions', 'tranche_2/prior_conditions.pdf', 22, 2, '2026-11-04'),
    ('monitoring', 'tranche_2/covenant_monitoring.xlsx', 21, 2, '2026-10-31'),
    ('compliance', 'tranche_2/compliance_certificate.pdf', 8, 2, '2026-11-04'),
    ('pricing', 'tranche_2/pricing.pdf', 11, 2, '2026-11-02'),
    ('valuation-v1', 'tranche_2/valuation_v1.pdf', 9, 2, '2026-11-04'),
    ('insurance', 'tranche_2/insurance.pdf', 13, 2, '2026-10-31'),
    ('rent-roll', 'tranche_2/rent_roll.xlsx', 15, 2, '2026-10-31'),
    ('lease-profile', 'tranche_2/lease_profile.xlsx', 16, 2, '2026-10-31'),
    ('projections', 'tranche_2/projections.xlsx', 14, 2, '2026-11-02'),
    ('limits', 'tranche_2/limits_utilisation.xlsx', None, 2, '2026-10-31'),
    ('conduct', 'tranche_3/account_conduct.xlsx', 17, 3, '2026-10-31'),
    ('internal-rating', 'tranche_3/internal_rating.pdf', 10, 3, '2026-10-31'),
    ('valuation-v2', 'late_update/valuation_v2.pdf', 9, 'late_update', '2026-11-09'),
]


def manifest(c):
    from openpyxl import load_workbook
    docs = []
    for id_, file, catalogue, tranche, date_ in DOCUMENTS:
        path = PACK / file
        row = dict(id=id_, file=file, catalogue_id=catalogue, tranche=tranche,
                   entity=c['borrower']['name'], date=date_, synthetic=True, origin='generated',
                   ca_confirmed=False, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
        if id_ == 'limits':
            row['suggestion_id'] = 'limits_utilisation'
        if path.suffix == '.pdf':
            with fitz.open(path) as doc:
                row['pages'] = len(doc)
                row['citation_locator'] = 'One-based physical PDF page'
        elif path.suffix == '.xlsx':
            wb = load_workbook(path)
            row['sheets'] = {s.title: {'header_row': 5, 'first_data_row': 6, 'last_data_row': s.max_row} for s in wb}
            row['citation_locator'] = 'Worksheet and Excel row/cell; data begins at row 6'
            wb.close()
        elif path.suffix == '.docx':
            row['template_sha256'] = TEMPLATE_HASH
            row['citation_locator'] = 'Numbered section and table; physical pages from latest render'
        else:
            row['citation_locator'] = 'Decoded message body, normalized page 1'
        if id_ == 'valuation-v2':
            row.update(supersedes='valuation-v1', revision=2, expected_stale_sections=[8, 9, 11, 14])
        else:
            row['revision'] = 1
        if id_ in {'valuation-v1', 'compliance', 'monitoring', 'conduct', 'limits', 'rent-roll', 'lease-profile'}:
            row['period_end'] = c['as_of']
        if id_ in {'prior-es', 'internal-rating', 'conduct'}:
            row['period_scope'] = 'historical_approval_only' if id_ == 'prior-es' else 'current_review'
        docs.append(row)
    data = dict(schema_version=1, task='0005', case_config='case.yaml', label=LABEL,
                borrower=c['borrower'], lender=c['lender'], documents=docs,
                public_sources=[dict(id=d['id'], file=str(Path(c['borrower']['public_manifest']).parent / d['file']),
                                     url=d['url'], retrieved_at=d['retrieved_at'], sha256=d['sha256'])
                                for d in [public_reference(c, c['public_historical']['document_id']),
                                          public_reference(c, c['public_observations'][0]['document_id'])]],
                boundaries=['Never treat synthetic facility exposures as public group borrowings.',
                            'Public portfolio evidence remains in its original saved pack with date and URL.',
                            'Current internal rating and conduct remain tranche 3 inputs despite historical prior ES.',
                            'Industry mapping, generated spread and CA position are later app/demo steps.',
                            'Late update is a scenario input, not implemented Stale behavior.'])
    (PACK / 'manifest.yaml').write_text('# '+LABEL+'\n'+yaml.safe_dump(data, sort_keys=False))


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--manifest', action='store_true')
    opts = args.parse_args()
    case = load_case()
    if opts.manifest:
        manifest(case)
    else:
        reports(case)
        workbook_specs(case)
        print('Built source PDFs/email and workbook specifications; fill prior ES and author workbooks next.')
