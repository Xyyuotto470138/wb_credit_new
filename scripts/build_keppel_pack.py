"""Build the synthetic deal papers for the new-to-bank demo case (Keppel REIT, Ocean Financial Centre).

Output: demo/synthetic_keppel/ (case.yaml, manifest.yaml, deal_folder/*). Every file is labelled
SYNTHETIC DEMO DATA. The borrower and building are real and described only from the saved public
pack (demo/public_pack/keppel-reit); the facility, the bank papers, the tenants, rents, insurance
and projections are fictional. No real lending relationship is implied.

Run: .venv/bin/python scripts/build_keppel_pack.py [--late]
--late rebuilds only late_update/ and the manifest. Use it when the deal folder is already built: a rebuilt
workbook has different bytes, so a full rebuild changes the hashes that saved demo cases hold.
"""
from datetime import date
from decimal import Decimal as D
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path
import hashlib
import textwrap

import fitz
import yaml
from openpyxl import Workbook
from openpyxl.styles import Font

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'demo/synthetic_keppel'
FOLDER = PACK / 'deal_folder'
LABEL = 'SYNTHETIC DEMO DATA, not a real record'
BORROWER = 'Keppel REIT'
PROPERTY = 'Ocean Financial Centre, 10 Collyer Quay, Singapore 049315'
FIXED = date(2026, 11, 10)  # fixed document date, so rebuilt files are byte-stable

# Fictional rent roll: tenant, trade sector, leased area (sq ft), rent (SGD per sq ft per month), lease expiry.
NLA = 871000  # public figure: approximately 871,000 sq ft of office space at 100%
TENANTS = [
    ('Demo Tenant A', 'Legal services', 92000, '11.60', '2030-06-30'), ('Demo Tenant B', 'Banking', 84000, '11.90', '2028-03-31'),
    ('Demo Tenant C', 'Flexible workspace', 96000, '10.80', '2027-09-30'), ('Demo Tenant D', 'Commodities trading', 46000, '12.20', '2027-12-31'),
    ('Demo Tenant E', 'Banking', 52000, '12.00', '2029-08-31'), ('Demo Tenant F', 'Insurance', 61000, '11.40', '2028-04-30'),
    ('Demo Tenant G', 'Asset management', 48000, '12.40', '2031-01-31'), ('Demo Tenant H', 'Technology', 57000, '11.00', '2027-06-30'),
    ('Demo Tenant I', 'Professional services', 66000, '11.30', '2030-10-31'), ('Demo Tenant J', 'Energy', 44000, '11.80', '2032-03-31'),
    ('Demo Tenant K', 'Banking', 58000, '12.10', '2027-11-30'), ('Demo Tenant L', 'Legal services', 39000, '11.70', '2029-05-31'),
    ('Demo Tenant M', 'Retail and food and beverage', 28000, '14.50', '2028-07-31'), ('Other tenants (below 3% each)', 'Various', 65000, '11.50', '2028-12-31'),
]
YEARS = ['FY2027', 'FY2028', 'FY2029']
# Fictional projection inputs for the building at 100%, SGD'000. Ratios are computed by the system, not stored here.
BASE = {'Gross revenue': [118500, 121200, 124000], 'Property expenses': [21900, 22400, 22900], 'Capital expenditure': [3000, 3000, 3500],
        'Interest expense': [23175, 23175, 23175], 'Scheduled debt repayment': [0, 0, 0]}
STRESS = [
    ('Stress 1', 'Occupancy and rent stress', 'Gross revenue 15% below the base case in every year; costs and interest as in the base case.',
     {'Gross revenue': [100725, 103020, 105400]}),
    ('Stress 2', 'Interest rate stress', 'All-in interest cost 200 basis points above the base case on SGD 650 million drawn; income as in the base case.',
     {'Interest expense': [36175, 36175, 36175]}),
    ('Stress 3', 'Combined stress', 'Gross revenue 15% below the base case and interest cost 200 basis points above it.',
     {'Gross revenue': [100725, 103020, 105400], 'Interest expense': [36175, 36175, 36175]}),
]
ASSUMPTIONS = [
    ('Revenue and rental growth', 'About 2.3% a year from contracted rent steps and renewals at prevailing rents', '15% below the base case in every year',
     'Fictional rent roll at 31 October 2026 and the lease expiry profile; no new letting of vacant space is assumed.'),
    ('Occupancy', '96% committed occupancy held', 'Equivalent to occupancy near 82% at unchanged rents', 'Committed occupancy in the rent roll; the stress removes the largest tenant and one further floor.'),
    ('Operating costs', 'Property expenses at about 18.5% of gross revenue', 'Unchanged in absolute terms', 'FY2025 cost ratio of the building in the public annual report.'),
    ('Interest rate', '3.55% all-in on the term loan; 3.75% on SGD 50 million drawn under the revolving facility', '200 basis points higher on SGD 650 million drawn',
     'Indicative pricing in the term sheet and pricing report; hedging is not assumed.'),
    ('Capital expenditure', 'SGD 3.0 million to SGD 3.5 million a year', 'Unchanged', 'Manager\'s asset plan as summarised in the credit application summary.'),
    ('Refinancing', 'None in the projection period; the term loan is a bullet due on 30 November 2031', 'None assumed', 'Final maturity in the term sheet. Repayment at maturity relies on refinancing or sale.'),
]


def pdf(name, title, paragraphs, folder=None, when=None):
    when = when or FIXED
    target = (folder or FOLDER) / name
    doc = fitz.open()
    lines = []
    for paragraph in paragraphs:
        lines += textwrap.wrap(paragraph, 92) or ['']
        lines.append('')
    # The intake check reads the borrower from a line of its own.
    lines = [f'Borrower: {BORROWER}', ''] + lines
    pages = [lines[i:i + 58] for i in range(0, len(lines), 58)]
    for number, chunk in enumerate(pages, 1):
        page = doc.new_page(width=595, height=842)
        page.insert_text((42, 38), LABEL, fontsize=10, fontname='hebo', color=(0.55, 0.08, 0.08))
        page.insert_text((42, 66), title, fontsize=15, fontname='hebo')
        page.insert_text((42, 84), f'{BORROWER} | the Bank | Fictional relationship only | {when.isoformat()}', fontsize=9, color=(0.35, 0.35, 0.35))
        y = 112
        for line in chunk:
            page.insert_text((42, y), line, fontsize=10.5)
            y += 12.2
        page.insert_text((42, 812), f'{name} | Page {number} of {len(pages)}', fontsize=8)
    stamp = f'D:{when:%Y%m%d}000000'
    doc.set_metadata({'title': title, 'creationDate': stamp, 'modDate': stamp, 'producer': 'WB Credit synthetic pack'})
    doc.save(target, garbage=4, deflate=True, no_new_id=True)
    doc.close()


def workbook(name, sheets, folder=None, when=None):
    """Each sheet: label, title, borrower line, period line, note, header in row 6, data from row 7."""
    book = Workbook()
    book.remove(book.active)
    for title, note, header, rows in sheets:
        sheet = book.create_sheet(title[:31])
        sheet['A1'], sheet['A2'], sheet['A3'] = LABEL, title, f'{BORROWER} | the Bank | Fictional relationship only'
        sheet['A4'], sheet['A5'] = f'Period: {(when or date(2026, 10, 31)).isoformat()}', note
        sheet['A1'].font, sheet['A2'].font = Font(bold=True, color='8B2020'), Font(bold=True, size=14)
        for column, value in enumerate(header, 1):
            sheet.cell(6, column, value).font = Font(bold=True)
        for r, row in enumerate(rows, 7):
            for column, value in enumerate(row, 1):
                sheet.cell(r, column, value)
        for column in range(1, len(header) + 1):
            sheet.column_dimensions[chr(64 + column)].width = 34 if column == 1 else 22
    stamp = when or FIXED
    book.properties.created = book.properties.modified = __import__('datetime').datetime(stamp.year, stamp.month, stamp.day)
    book.save((folder or FOLDER) / name)


def documents():
    pdf('cas.pdf', 'Credit application summary (CAS)', [
        'CAS number: CAS-2026-FIG-0417 (fictional). Paper type: Standalone. Review type: New. Booking office: Singapore.',
        f'Borrower: {BORROWER}, acting through its trustee. Obligor group: Keppel REIT group. Country of risk: Singapore. '
        'Industry: Real estate investment trusts (office). Relationship manager: Demo Relationship Manager (fictional).',
        'Relationship: the borrower is new to the Bank. There are no existing limits, no outstanding exposure, no account history and no prior approval conditions.',
        'Request: (1) a new secured term loan facility TL-01 of SGD 600,000,000 for five years, and (2) a new secured committed revolving credit facility RCF-01 '
        'of SGD 100,000,000 for three years. Total proposed limits: SGD 700,000,000.',
        f'Purpose: TL-01 refinances existing bank borrowings associated with {PROPERTY} and funds asset enhancement works at the building. '
        'RCF-01 is for working capital and general corporate purposes of the borrower.',
        'Justification: the request establishes a first relationship with a Singapore listed office REIT sponsored by Keppel. The financing object is a Grade A office '
        'building in the Raffles Place and Marina Bay area with a diversified tenant base. The secured structure, a loan to value covenant of 45% and an interest '
        'coverage covenant of 2.0 times at the building support the request. The Bank expects ancillary business in hedging, cash management and deposits.',
        'Account classification: not applicable, new to the Bank. No Watchlist or Special Mention classification applies. There are no days past due.',
        'Asset plan: the manager plans capital expenditure of about SGD 3.0 million to SGD 3.5 million a year at the building for lobby, lift and sustainability works.',
        'Know your customer: onboarding checks are in progress and are a condition precedent to first drawdown.',
        'Single borrower limit cap: the Bank\'s internal limit cap for the obligor group is SGD 1,000,000,000 (fictional).',
    ])
    pdf('term_sheet.pdf', 'Indicative term sheet', [
        f'Borrower: {BORROWER}, acting through its trustee. Lender: the Bank. Status: indicative terms, subject to credit approval and documentation.',
        'Facility TL-01. Facility type: secured term loan facility. Currency and amount: SGD 600,000,000. Purpose: to refinance existing bank borrowings associated with '
        f'{PROPERTY} and to fund asset enhancement works at the building. Tenor and final maturity: five years from first drawdown; final maturity 30 November 2031. '
        'Availability period: three months from the date of the facility agreement. Repayment: bullet repayment in full on the final maturity date. '
        'Pricing: margin of 1.05% a year over three-month compounded SORA; upfront fee of 0.30% of the facility amount.',
        'Facility RCF-01. Facility type: secured committed revolving credit facility. Currency and amount: SGD 100,000,000. Purpose: working capital and general corporate '
        'purposes of the borrower. Tenor and final maturity: three years from the date of the facility agreement; final maturity 30 November 2029. '
        'Availability period: until one month before the final maturity date. Repayment: each loan is repaid at the end of its interest period and may be redrawn; '
        'all amounts are repaid on the final maturity date. Pricing: margin of 1.25% a year over three-month compounded SORA; commitment fee of 0.35% a year on undrawn amounts; '
        'upfront fee of 0.20% of the facility amount.',
        f'Security for both facilities: first legal mortgage over {PROPERTY}, granted by the property holding entity; assignment of rental proceeds and tenancy agreements; '
        'assignment of insurances with the Bank named as mortgagee and loss payee; charge over the rental collection account. The facilities rank pari passu under the same security.',
        'Financial covenants, tested half-yearly: (a) loan to value not exceeding 45%, being total secured facilities over the market value of the security property; '
        '(b) interest coverage of the security property not less than 2.0 times, being net property income over interest expense on the facilities; '
        '(c) aggregate leverage of the borrower group not exceeding 50%, in line with the regulatory limit for Singapore REITs.',
        'Other key terms: negative pledge over the security property; no disposal of the security property without the Bank\'s consent; change of manager or sponsor is a '
        'review event; annual valuation by a valuer acceptable to the Bank; cross default to other financial indebtedness of the borrower group.',
        'Conditions precedent: valuation report addressed to the Bank; consent of the other partners of the property holding entity to the security; registration of the mortgage; '
        'legal opinions; insurance endorsement naming the Bank; completion of know your customer checks.',
        'Conditions subsequent: perfection of the assignment of rental proceeds within 30 days of first drawdown; interest rate hedging of at least 50% of TL-01 within 90 days of first drawdown.',
    ])
    pdf('valuation_report.pdf', 'Valuation report: Ocean Financial Centre', [
        f'Valuer: Demo Valuer Pte. Ltd. (fictional). Addressed to: the Bank. Property: {PROPERTY}. Interest valued: 100% of the property.',
        'Market value: SGD 2,880.0 million. Effective date of valuation: 31 October 2026. Basis: market value, subject to existing tenancies and occupational arrangements.',
        'Approach: income capitalisation and discounted cash flow, cross-checked against comparable sales. Capitalisation rate adopted: 3.40%.',
        'Description: a Grade A office tower in the Raffles Place and Marina Bay financial district with about 871,000 square feet of net lettable area. '
        'Land tenure: 99-year leasehold expiring on 13 December 2110.',
        'Tenancy: committed occupancy of 96.0% at the effective date, based on the rent roll supplied. The valuer has relied on the rent roll without audit.',
        'This fictional valuation adopts the same value as the independent valuation at 31 December 2025 disclosed in the public annual report. It is not a new valuation of the real building.',
        'Limiting conditions: no structural survey was carried out; title was not investigated; the valuation is for mortgage security purposes only.',
    ])
    pdf('insurance_report.pdf', 'Insurance report: Ocean Financial Centre', [
        f'Insured property: {PROPERTY}. Insurer: Demo Insurer Pte. Ltd. (fictional). Broker: Demo Broker Pte. Ltd. (fictional).',
        'Policy: industrial all risks, including fire, flood, explosion and machinery breakdown. Sum insured: SGD 1,150.0 million on a reinstatement basis.',
        'Business interruption: loss of rent cover of SGD 240.0 million for an indemnity period of 24 months. Public liability: SGD 50.0 million any one occurrence.',
        'Period of insurance: 1 January 2026 to 31 December 2026, renewable annually.',
        'Bank\'s interest: the Bank is to be noted as mortgagee and loss payee by endorsement before first drawdown. The endorsement has not yet been issued.',
        'Exclusions include wear and tear, gradual pollution, war and terrorism. Terrorism cover is arranged under a separate policy with a limit of SGD 500.0 million.',
    ])
    pdf('pricing_report.pdf', 'Pricing report', [
        'Facilities: TL-01 SGD 600,000,000 secured term loan and RCF-01 SGD 100,000,000 secured revolving credit facility.',
        'TL-01: margin 1.05% a year over three-month compounded SORA; upfront fee 0.30%. Indicative all-in interest cost to the borrower of 3.55% a year at current rates.',
        'RCF-01: margin 1.25% a year over three-month compounded SORA; commitment fee 0.35% a year; upfront fee 0.20%. Indicative all-in cost on drawn amounts of 3.75% a year.',
        'Return: the relationship return on risk-adjusted capital is 14.2% against a hurdle of 12.0% (fictional figures), including expected ancillary income.',
        'The pricing is within the delegated pricing grid for secured lending to investment grade equivalent real estate borrowers (fictional).',
    ])
    pdf('industry_code_mapping.pdf', 'Industry code mapping', [
        f'Borrower: {BORROWER}. Industry code: FIG-RE-01 (fictional demonstration code). Description: Real estate investment trusts, office.',
        'Basis: the borrower is a Singapore listed real estate investment trust whose principal activity is investment in income-producing commercial office property.',
        'Confirmed by: Demo Credit Analyst (fictional), 10 November 2026.',
    ])
    message = EmailMessage(policy=SMTP)
    message['From'], message['To'] = 'Demo Relationship Manager <rm@example.invalid>', 'Demo Credit Analyst <ca@example.invalid>'
    message['Subject'], message['Date'] = f'{LABEL}: business support for Keppel REIT new facilities', 'Tue, 10 Nov 2026 09:30:00 +0800'
    message.set_content(
        f'{LABEL}\n\nBorrower: {BORROWER}\n\nI support the request for TL-01 (SGD 600,000,000 secured term loan) and RCF-01 (SGD 100,000,000 secured revolving credit facility).\n\n'
        'Relationship rationale: this is a first relationship with a Keppel sponsored office REIT. The manager has asked the Bank to refinance borrowings on Ocean Financial Centre '
        'and has indicated that interest rate hedging and cash management for the building would follow.\n\n'
        'Client feedback: the manager wants a five-year tenor to lengthen its debt maturity profile and has accepted a loan to value covenant of 45%.\n\n'
        'I am not aware of any adverse information on the borrower, its manager or its sponsor.\n\nDemo Relationship Manager (fictional)\n')
    (FOLDER / 'rm_support.eml').write_bytes(message.as_bytes())

    rent_rows = [[name, sector, area, float(D(area) * D(psf) * 12 / 1000), expiry] for name, sector, area, psf, expiry in TENANTS]
    occupied = sum(row[2] for row in rent_rows)
    workbook('rent_roll.xlsx', [
        ('Rent roll', f'Rent roll at 31 October 2026. Net lettable area (sq ft): {NLA}. Annual rent is contracted gross rent.',
         ['Tenant', 'Trade sector', 'Leased area (sq ft)', "Annual rent (SGD'000)", 'Lease expiry'], rent_rows),
        ('Summary', 'Totals as supplied by the manager (fictional).', ['Item', 'Value'],
         [['Net lettable area (sq ft)', NLA], ['Leased area (sq ft)', occupied], ['Vacant area (sq ft)', NLA - occupied]]),
    ])
    workbook('lease_profile.xlsx', [
        ('Leases', 'Lease expiry schedule at 31 October 2026, one line per lease as in the rent roll.',
         ['Tenant', 'Lease expiry', 'Leased area (sq ft)', "Annual rent (SGD'000)"], [[r[0], r[4], r[2], r[3]] for r in rent_rows]),
    ])
    lines = list(BASE)
    sheets = [('Base case', 'Base case: stable cash flow. Building at 100%. Amounts in SGD\'000.', ['Line item'] + YEARS, [[line] + BASE[line] for line in lines])]
    for sheet, title, description, changes in STRESS:
        sheets.append((sheet, f'{title}. {description}', ['Line item'] + YEARS, [[line] + changes.get(line, BASE[line]) for line in lines]))
    sheets.append(('Assumptions', 'Assumptions and the basis for each.', ['Assumption', 'Base case', 'Stress case', 'Basis for assumption'], [list(a) for a in ASSUMPTIONS]))
    workbook('financial_projections.xlsx', sheets)
    workbook('internal_rating_worksheet.xlsx', [
        ('Internal rating', 'Internal rating assigned by the rating unit (fictional). Fictional scale of 1 to 10; 1 is the strongest.', ['Item', 'Value'],
         [['Internal rating (CRR)', 'CRR 4'], ['Previous rating', 'None: new to bank'], ['Rating date', '2026-11-09'],
          ['Rating model', 'Real estate investment trust scorecard (fictional)'], ['Assigned by', 'Demo Rating Unit (fictional)'],
          ['Change and reason', 'First-time rating assigned on onboarding. Drivers recorded by the rating unit: Grade A office portfolio, sponsorship by Keppel and '
                                'aggregate leverage within the regulatory limit; constrained by reliance on refinancing at maturity and the absence of a current public rating.']]),
    ])


# ---- Late update: papers that arrive after the ES is drafted (the "new information" scenario) ----
LATE = PACK / 'late_update'
LATE_DATE = date(2026, 11, 13)
LATE_BASE = dict(BASE, **{'Interest expense': [24950, 24950, 24950]})  # 650m at 3.55% plus 50m at 3.75%
LATE_STRESS = [
    STRESS[0],
    ('Stress 2', 'Interest rate stress', 'All-in interest cost 200 basis points above the base case on SGD 700 million drawn; income as in the base case.',
     {'Interest expense': [38950, 38950, 38950]}),
    ('Stress 3', 'Combined stress', 'Gross revenue 15% below the base case and interest cost 200 basis points above it.',
     {'Gross revenue': [100725, 103020, 105400], 'Interest expense': [38950, 38950, 38950]}),
]
LATE_FILES = {'cas_rev2.pdf': (1, '2026-11-13', 'cas'), 'term_sheet_rev2.pdf': (2, '2026-11-13', 'term-sheet'),
              'valuation_report_nov2026.pdf': (9, '2026-11-12', 'valuation-report'), 'financial_projections_rev2.xlsx': (14, '2026-11-13', 'financial-projections')}


def late_update():
    """Revised papers: a larger term loan (CAS, term sheet, projections) and a lower valuation. All fictional."""
    LATE.mkdir(parents=True, exist_ok=True)
    pdf('cas_rev2.pdf', 'Credit application summary (CAS)', [
        'CAS number: CAS-2026-FIG-0417 (fictional). Paper type: Standalone. Review type: New. Booking office: Singapore. '
        'This is revision 2 of the CAS, issued on 13 November 2026. It replaces the CAS issued on 10 November 2026.',
        f'Borrower: {BORROWER}, acting through its trustee. Obligor group: Keppel REIT group. Country of risk: Singapore. '
        'Industry: Real estate investment trusts (office). Relationship manager: Demo Relationship Manager (fictional).',
        'Relationship: the borrower is new to the Bank. There are no existing limits, no outstanding exposure, no account history and no prior approval conditions.',
        'Request: (1) a new secured term loan facility TL-01 of SGD 650,000,000 for five years, and (2) a new secured committed revolving credit facility RCF-01 '
        'of SGD 100,000,000 for three years. Total proposed limits: SGD 750,000,000.',
        'Change since the first CAS: TL-01 is increased from SGD 600,000,000 to SGD 650,000,000 because the manager has widened the asset enhancement works '
        'at the building to include the chilled water plant and the facade lighting (fictional). RCF-01 is unchanged. Tenors, security and covenants are unchanged.',
        f'Purpose: TL-01 refinances existing bank borrowings associated with {PROPERTY} and funds asset enhancement works at the building. '
        'RCF-01 is for working capital and general corporate purposes of the borrower.',
        'Justification: the request establishes a first relationship with a Singapore listed office REIT sponsored by Keppel. The financing object is a Grade A office '
        'building in the Raffles Place and Marina Bay area with a diversified tenant base. The secured structure, a loan to value covenant of 45% and an interest '
        'coverage covenant of 2.0 times at the building support the request. The Bank expects ancillary business in hedging, cash management and deposits.',
        'Valuation: a revised valuation report with an effective date of 12 November 2026 states a market value of SGD 2,750.0 million for the building, '
        'against SGD 2,880.0 million in the report with an effective date of 31 October 2026.',
        'Related papers: the revised term sheet and the revised financial projections issued on 13 November 2026 reflect the increased amount. The pricing report and the '
        'relationship manager\'s support email of 10 November 2026 still state the first amount of TL-01. Margins and fees are unchanged. A revised pricing report is to follow.',
        'Account classification: not applicable, new to the Bank. No Watchlist or Special Mention classification applies. There are no days past due.',
        'Asset plan: the manager plans capital expenditure of about SGD 3.0 million to SGD 3.5 million a year at the building for lobby, lift and sustainability works. '
        'The widened works funded by the increase in TL-01 are in addition to this plan.',
        'Know your customer: onboarding checks are in progress and are a condition precedent to first drawdown.',
        'Single borrower limit cap: the Bank\'s internal limit cap for the obligor group is SGD 1,000,000,000 (fictional).',
    ], LATE, LATE_DATE)
    pdf('term_sheet_rev2.pdf', 'Indicative term sheet', [
        f'Borrower: {BORROWER}, acting through its trustee. Lender: the Bank. Status: indicative terms, subject to credit approval and documentation. '
        'This is revision 2 of the term sheet, issued on 13 November 2026. It replaces the term sheet issued on 10 November 2026. Only the amount of TL-01 has changed.',
        'Facility TL-01. Facility type: secured term loan facility. Currency and amount: SGD 650,000,000. Purpose: to refinance existing bank borrowings associated with '
        f'{PROPERTY} and to fund asset enhancement works at the building. Tenor and final maturity: five years from first drawdown; final maturity 30 November 2031. '
        'Availability period: three months from the date of the facility agreement. Repayment: bullet repayment in full on the final maturity date. '
        'Pricing: margin of 1.05% a year over three-month compounded SORA; upfront fee of 0.30% of the facility amount.',
        'Facility RCF-01. Facility type: secured committed revolving credit facility. Currency and amount: SGD 100,000,000. Purpose: working capital and general corporate '
        'purposes of the borrower. Tenor and final maturity: three years from the date of the facility agreement; final maturity 30 November 2029. '
        'Availability period: until one month before the final maturity date. Repayment: each loan is repaid at the end of its interest period and may be redrawn; '
        'all amounts are repaid on the final maturity date. Pricing: margin of 1.25% a year over three-month compounded SORA; commitment fee of 0.35% a year on undrawn amounts; '
        'upfront fee of 0.20% of the facility amount.',
        f'Security for both facilities: first legal mortgage over {PROPERTY}, granted by the property holding entity; assignment of rental proceeds and tenancy agreements; '
        'assignment of insurances with the Bank named as mortgagee and loss payee; charge over the rental collection account. The facilities rank pari passu under the same security.',
        'Financial covenants, tested half-yearly: (a) loan to value not exceeding 45%, being total secured facilities over the market value of the security property; '
        '(b) interest coverage of the security property not less than 2.0 times, being net property income over interest expense on the facilities; '
        '(c) aggregate leverage of the borrower group not exceeding 50%, in line with the regulatory limit for Singapore REITs.',
        'Other key terms: negative pledge over the security property; no disposal of the security property without the Bank\'s consent; change of manager or sponsor is a '
        'review event; annual valuation by a valuer acceptable to the Bank; cross default to other financial indebtedness of the borrower group.',
        'Conditions precedent: valuation report addressed to the Bank; consent of the other partners of the property holding entity to the security; registration of the mortgage; '
        'legal opinions; insurance endorsement naming the Bank; completion of know your customer checks.',
        'Conditions subsequent: perfection of the assignment of rental proceeds within 30 days of first drawdown; interest rate hedging of at least 50% of TL-01 within 90 days of first drawdown.',
    ], LATE, LATE_DATE)
    pdf('valuation_report_nov2026.pdf', 'Valuation report: Ocean Financial Centre', [
        f'Valuer: Demo Valuer Pte. Ltd. (fictional). Addressed to: the Bank. Property: {PROPERTY}. Interest valued: 100% of the property. '
        'This revised report replaces the valuation report with an effective date of 31 October 2026.',
        'Market value: SGD 2,750.0 million. Effective date of valuation: 12 November 2026. Basis: market value, subject to existing tenancies and occupational arrangements.',
        'Approach: income capitalisation and discounted cash flow, cross-checked against comparable sales. Capitalisation rate adopted: 3.55%.',
        'Reason for the revision: the manager has received notice that Demo Tenant C will not renew its lease expiring on 30 September 2027 (fictional). The valuer has allowed '
        'for a letting void and reletting costs on that space and has adopted a higher capitalisation rate than in the earlier report.',
        'Description: a Grade A office tower in the Raffles Place and Marina Bay financial district with about 871,000 square feet of net lettable area. '
        'Land tenure: 99-year leasehold expiring on 13 December 2110.',
        'Tenancy: committed occupancy of 96.0% at the effective date, based on the rent roll supplied. The valuer has relied on the rent roll without audit.',
        'This is a fictional revised valuation prepared for this demonstration. It is not a valuation of the real building and no real tenant event is implied.',
        'Limiting conditions: no structural survey was carried out; title was not investigated; the valuation is for mortgage security purposes only.',
    ], LATE, date(2026, 11, 12))
    lines = list(LATE_BASE)
    sheets = [('Base case', 'Base case: stable cash flow. Building at 100%. Amounts in SGD\'000. Revision 2: interest on TL-01 of SGD 650 million.',
               ['Line item'] + YEARS, [[line] + LATE_BASE[line] for line in lines])]
    for sheet, title, description, changes in LATE_STRESS:
        sheets.append((sheet, f'{title}. {description}', ['Line item'] + YEARS, [[line] + changes.get(line, LATE_BASE[line]) for line in lines]))
    assumptions = [list(a) for a in ASSUMPTIONS]
    assumptions[3][2] = '200 basis points higher on SGD 700 million drawn'
    sheets.append(('Assumptions', 'Assumptions and the basis for each.', ['Assumption', 'Base case', 'Stress case', 'Basis for assumption'], assumptions))
    workbook('financial_projections_rev2.xlsx', sheets, LATE, LATE_DATE)


CATALOGUE = {'cas.pdf': (1, '2026-11-10'), 'term_sheet.pdf': (2, '2026-11-10'), 'valuation_report.pdf': (9, '2026-10-31'), 'insurance_report.pdf': (13, '2026-10-31'),
             'pricing_report.pdf': (11, '2026-11-10'), 'industry_code_mapping.pdf': (19, '2026-11-10'), 'rm_support.eml': (12, '2026-11-10'),
             'rent_roll.xlsx': (15, '2026-10-31'), 'lease_profile.xlsx': (16, '2026-10-31'), 'financial_projections.xlsx': (14, '2026-10-31'),
             'internal_rating_worksheet.xlsx': (10, '2026-10-31')}


def manifest():
    entries = []
    for name, (catalogue_id, when) in CATALOGUE.items():
        data = (FOLDER / name).read_bytes()
        entries.append(dict(id=name.rsplit('.', 1)[0].replace('_', '-'), file=f'deal_folder/{name}', catalogue_id=catalogue_id, tranche=1, entity=BORROWER,
                            date=when, synthetic=True, origin='generated', ca_confirmed=False, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), revision=1))
    for name, (catalogue_id, when, replaces) in LATE_FILES.items():
        data = (LATE / name).read_bytes()
        entries.append(dict(id=name.rsplit('.', 1)[0].replace('_', '-'), file=f'late_update/{name}', catalogue_id=catalogue_id, tranche=2, entity=BORROWER,
                            date=when, synthetic=True, origin='generated', ca_confirmed=False, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), revision=2,
                            supersedes=replaces))
    (PACK / 'manifest.yaml').write_text('# ' + LABEL + '\n' + yaml.safe_dump(dict(schema_version=1, case_id='demo-new-001', documents=entries), sort_keys=False))
    case = dict(
        schema_version=1, case_id='demo-new-001', lender='the Bank', as_of='2026-10-31', proposal_date='2026-11-10', unit='SGD_thousand',
        borrower=dict(name=BORROWER, sgx_code='K71U', public_manifest='demo/public_pack/keppel-reit/manifest.yaml', property='Ocean Financial Centre'),
        assets=dict(property_photos=[dict(file='demo/public_pack/keppel-reit/photos/ofc-exterior-collyer-quay-2026.jpg'),
                                     dict(file='demo/public_pack/keppel-reit/photos/ofc-exterior-ground-level-2025.jpg')],
                    credits='demo/public_pack/keppel-reit/photos/credits.yaml', location_map='demo/public_pack/keppel-reit/map/location_map.png',
                    location='demo/public_pack/keppel-reit/map/location.yaml', financing_object='Ocean Financial Centre'),
        demo_ca_position=('Recommended with conditions. Support the new secured term loan and revolving credit facility for Keppel REIT, subject to the valuation report being '
                          'addressed to the Bank, the consent of the other partners to the security and perfection of the mortgage and assignments before first drawdown.'),
        app_case=dict(team_id='fig_re', case_type='new', borrower_type='reit', facility_types=['term', 'revolving'], existing_client=False, new_to_bank=True,
                      property_or_asset_security=True, insured_security_or_assets=True, financial_covenants=True, covenants=True, new_money=True,
                      property_income_repayment=True, bureau_covered=False, has_information_memorandum=False, public_entity=True, ca_position=None,
                      default_model_id='fable-5-2-direct'))
    (PACK / 'case.yaml').write_text('# ' + LABEL + '\n' + yaml.safe_dump(case, sort_keys=False, width=110))
    (PACK / 'README.md').write_text(
        f'# Synthetic deal papers: {BORROWER}, new to bank\n\n{LABEL}.\n\nBuilt by `scripts/build_keppel_pack.py`. The borrower and Ocean Financial Centre are real and are '
        'described from the saved public pack in `demo/public_pack/keppel-reit/`. Everything in `deal_folder/` is fictional: the facilities, the bank papers, the valuer, '
        'insurer, tenants, rents and projections. No real lending relationship is implied. The fictional valuation adopts the publicly disclosed value at 31 December 2025.\n\n'
        '`late_update/` holds papers that arrive after the ES is drafted, for the new information scenario: a revised CAS and term sheet (TL-01 raised from '
        'SGD 600 million to SGD 650 million), revised projections on the higher loan, and a revised valuation of SGD 2,750.0 million (was SGD 2,880.0 million). '
        'They are fictional too. No published figure of the real trust is changed. Load them only after the first draft: scan the deal folder first.\n')


if __name__ == '__main__':
    import sys
    FOLDER.mkdir(parents=True, exist_ok=True)
    if '--late' not in sys.argv:
        documents()
    late_update()
    manifest()
    print(f'wrote {len(CATALOGUE)} files to {FOLDER.relative_to(ROOT)} and {len(LATE_FILES)} to {LATE.relative_to(ROOT)}')
