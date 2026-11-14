"""Parts of the ES that Python fills: tables computed from structured workbooks and from figures already
checked in this or another section, case inputs, and saved image assets. No model output is used here."""
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re

import yaml
from openpyxl import load_workbook

from .. import schemas as s
from ..retrieval.service import read_content
from ..services.gaps import current_documents
from .numbers import fmt
from .spec import column_names

ROOT = Path(__file__).resolve().parents[3]
RENT_ROLL, PROJECTIONS, RATING = 15, 14, 10


class Context:
    def __init__(self, service, case, sources, content, other_section):
        self.service, self.case, self.sources, self.content, self.other_section = service, case, sources, content, other_section

    def workbook(self, catalogue_id):
        """The current document of a catalogue type as (sheets, citation refs by sheet name), or (None, {})."""
        docs = [d for d in current_documents(self.service.repo.list_for_case(s.Document, self.case.id), self.case)
                if d.catalogue_id == catalogue_id and d.original_filename.lower().endswith('.xlsx')]
        if not docs:
            return None, {}
        doc = docs[-1]
        book = load_workbook(BytesIO(read_content(doc, self.service.storage_root)), data_only=True)
        pages = [p for p in self.sources.pages if p['document_id'] == doc.id]
        refs = {}
        for index, sheet in enumerate(book.worksheets):
            match = next((p for p in pages if str(sheet['A2'].value or sheet.title) in p['text']), pages[index] if index < len(pages) else (pages[0] if pages else None))
            refs[sheet.title] = [match['ref']] if match else []
        return book, refs


def table_rows(sheet):
    """Rows under the header in row 6, as dicts keyed by header text. Row 5 holds the sheet's note."""
    header = [str(c.value).strip() for c in sheet[6] if c.value is not None]
    rows = []
    for row in sheet.iter_rows(min_row=7, max_col=len(header), values_only=True):
        if row[0] is None:
            break
        rows.append(dict(zip(header, row)))
    return header, rows


def cell(text, cites=(), status='computed', value=None):
    return dict(text=str(text), cites=list(cites), sections=[], status=status, **({'value': str(value)} if value is not None else {}))


def label(text):
    return cell(text, status='label')


def missing(part, reason):
    return dict(status='gap', note=reason, columns=column_names(part), rows=[])


def day(value):
    """An ISO date shown as 30 Jun 2030. Display only."""
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').strftime('%d %b %Y').lstrip('0')
    except ValueError:
        return str(value)


def number(value):
    return Decimal(str(value))


def rent_roll(ctx):
    book, refs = ctx.workbook(RENT_ROLL)
    if book is None or 'Rent roll' not in book.sheetnames:
        return None
    _, rows = table_rows(book['Rent roll'])
    _, summary = table_rows(book['Summary']) if 'Summary' in book.sheetnames else ([], [])
    nla = next((number(r['Value']) for r in summary if str(r['Item']).lower().startswith('net lettable')), None)
    leases = [dict(tenant=r['Tenant'], sector=r['Trade sector'], area=number(r['Leased area (sq ft)']), rent=number(r["Annual rent (SGD'000)"]),
                   expiry=str(r['Lease expiry'])[:10]) for r in rows]
    return dict(leases=leases, nla=nla, rent=sum(l['rent'] for l in leases), cites=refs.get('Rent roll', []) + refs.get('Summary', []))


def named(leases):
    """Single named tenants, largest rent first. Grouped lines such as 'Other tenants' are not a tenant."""
    return sorted((l for l in leases if not l['tenant'].lower().startswith('other')), key=lambda l: -l['rent'])


def key_tenants(part, ctx):
    data = rent_roll(ctx)
    if not data or not data['nla']:
        return missing(part, 'Rent roll not provided: the key tenants cannot be listed.')
    rows = [[cell(l['tenant'], data['cites'], 'ok'), cell(fmt(l['area'], 'amount'), data['cites'], 'ok'), cell(fmt(l['area'] / data['nla'] * 100, 'percent')),
             cell(fmt(l['rent'] / data['rent'] * 100, 'percent')), cell(day(l['expiry']), data['cites'], 'ok')] for l in named(data['leases'])[:5]]
    return dict(columns=column_names(part), rows=rows)


def top_tenants(part, ctx):
    data = rent_roll(ctx)
    if not data:
        return missing(part, 'Rent roll not provided: the top tenants cannot be listed.')
    rows = [[cell(l['tenant'], data['cites'], 'ok'), cell(l['sector'], data['cites'], 'ok'), cell(fmt(l['rent'] / data['rent'] * 100, 'percent')),
             cell(day(l['expiry']), data['cites'], 'ok')] for l in named(data['leases'])[:5]]
    return dict(columns=column_names(part), rows=rows)


def lease_profile(part, ctx):
    data = rent_roll(ctx)
    if not data or not data['nla']:
        return missing(part, 'Rent roll not provided: the lease expiry profile cannot be computed.')
    years = {}
    for lease in data['leases']:
        bucket = years.setdefault(lease['expiry'][:4], [Decimal(0), Decimal(0)])
        bucket[0] += lease['rent']; bucket[1] += lease['area']
    rows = [[cell(year, data['cites'], 'ok'), cell(fmt(rent / data['rent'] * 100, 'percent')), cell(fmt(area / data['nla'] * 100, 'percent'))]
            for year, (rent, area) in sorted(years.items())]
    vacant = data['nla'] - sum(l['area'] for l in data['leases'])
    rows.append([label('Vacant'), cell('n.a.', status='na'), cell(fmt(vacant / data['nla'] * 100, 'percent'))])
    return dict(columns=column_names(part), rows=rows)


def projection(ctx, sheet_name):
    """One projection sheet as {years, lines, cites, note}, with the ratios computed here."""
    book, refs = ctx.workbook(PROJECTIONS)
    if book is None or sheet_name not in book.sheetnames:
        return None
    sheet = book[sheet_name]
    header, rows = table_rows(sheet)
    years = header[1:]
    lines = {str(r['Line item']): [number(r[y]) for y in years] for r in rows}
    need = ('Gross revenue', 'Property expenses', 'Capital expenditure', 'Interest expense', 'Scheduled debt repayment')
    if any(line not in lines for line in need):
        return None
    npi = [a - b for a, b in zip(lines['Gross revenue'], lines['Property expenses'])]
    cads = [a - b for a, b in zip(npi, lines['Capital expenditure'])]
    service = [a + b for a, b in zip(lines['Interest expense'], lines['Scheduled debt repayment'])]
    lines.update({'Net property income': npi, 'Cash available for debt service': cads,
                  'Debt service coverage (x)': [c / d if d else None for c, d in zip(cads, service)],
                  'Interest coverage (x)': [n / i if i else None for n, i in zip(npi, lines['Interest expense'])],
                  'Scheduled principal': lines['Scheduled debt repayment']})
    return dict(years=years, lines=lines, cites=refs.get(sheet_name, []), title=str(sheet['A2'].value or sheet_name), note=str(sheet['A5'].value or ''))


def projection_table(part, ctx, remark):
    data = projection(ctx, 'Base case')
    if not data:
        return missing(part, 'Financial projections not provided: the projection cannot be shown.')
    rows = []
    for line in part['rows']:
        ratio = line.endswith('(x)')
        values = data['lines'][line]
        input_line = line in ('Gross revenue', 'Capital expenditure', 'Interest expense', 'Scheduled debt repayment', 'Scheduled principal')
        cells = [cell(fmt(v, 'number' if ratio else 'amount') if v is not None else 'n.m.', data['cites'] if input_line else (), 'ok' if input_line else 'computed') for v in values]
        rows.append([label(line)] + cells + [cell(remark if line == part['rows'][0] else '', data['cites'], 'ok')])
    columns = [column_names(part)[0]] + [f'Projected {y}' for y in data['years']] + ['Remarks']
    return dict(columns=columns, rows=rows)


def debt_service(part, ctx):
    return projection_table(part, ctx, 'Base case of the financial projections; building at 100%.')


def cashflow_base(part, ctx):
    return projection_table(part, ctx, 'Inputs from the financial projections. Net property income, cash available for debt service and the coverage ratios are computed by the system.')


def covenant_threshold(ctx, words):
    for row in (ctx.content.get('covenants') or {}).get('rows', []):
        if all(word in row[0]['text'].lower() for word in words) and row[2].get('value'):
            return Decimal(row[2]['value'])
    return None


def stress_cases(part, ctx):
    book, _ = ctx.workbook(PROJECTIONS)
    if book is None:
        return missing(part, 'Financial projections not provided: the stress cases cannot be shown.')
    floor = covenant_threshold(ctx, ('interest coverage', 'property'))
    rows = []
    for name in [n for n in book.sheetnames if n == 'Base case' or n.lower().startswith('stress')]:
        data = projection(ctx, name)
        if not data:
            continue
        dscr = [v for v in data['lines']['Debt service coverage (x)'] if v is not None]
        icr = [v for v in data['lines']['Interest coverage (x)'] if v is not None]
        low_dscr, low_icr = min(dscr), min(icr)
        year = data['years'][data['lines']['Debt service coverage (x)'].index(low_dscr)]
        outcome = (f'Debt service is covered in every year; the lowest coverage is in {year}.' if low_dscr >= 1
                   else f'Debt service is not covered in {year}.')
        if floor is not None:
            outcome += f' Interest coverage {"stays at or above" if low_icr >= floor else "falls below"} the {fmt(floor, "number", 1)} times covenant.'
        applied = 'None: stable cash flow.' if name == 'Base case' else data['note'].split('. ', 1)[-1]
        scenario = 'Base case' if name == 'Base case' else data['note'].split('.', 1)[0]
        rows.append([cell(scenario, data['cites'], 'ok'), cell(applied, data['cites'], 'ok'), cell(fmt(low_dscr)), cell(fmt(low_icr)), cell(outcome)])
    return dict(columns=column_names(part), rows=rows) if rows else missing(part, 'No projection sheets could be read.')


def assumptions(part, ctx):
    book, refs = ctx.workbook(PROJECTIONS)
    if book is None or 'Assumptions' not in book.sheetnames:
        return missing(part, 'Financial projections not provided: assumptions and their basis are not available.')
    names = column_names(part)
    _, rows = table_rows(book['Assumptions'])
    return dict(columns=names, rows=[[cell(str(r.get(n) or ''), refs.get('Assumptions', []), 'ok') for n in names] for r in rows])


def latest_value(table, row_label):
    """Latest checked figure in a period table row: the interim column if filled, else the latest year."""
    for row in (table or {}).get('rows', []):
        if row[0]['text'] == row_label:
            filled = [(c, table['columns'][i]) for i, c in enumerate(row) if i and c.get('value') and c['status'] == 'ok']
            return (Decimal(filled[-1][0]['value']), filled[-1][1], filled[-1][0]['cites']) if filled else None
    return None


def headroom(part, ctx):
    rows = []

    def add(measure, requirement, limit, direction, actual, unit, basis, cites):
        if actual is None:
            rows.append([label(measure), cell(requirement, status='ok'), cell('', status='gap'), cell('', status='gap'), cell('Not assessed: no actual figure held', status='gap')])
            return
        room = limit - actual if direction == 'max' else actual - limit
        suffix = ' pp' if unit == '%' else ' x'
        shown = fmt(actual, 'number', 1 if unit == '%' else 2) + ('%' if unit == '%' else 'x')
        rows.append([label(measure), cell(requirement, status='ok'), cell(f'{shown} ({basis})', cites, 'ok'), cell(fmt(room, 'number', 1 if unit == '%' else 2) + suffix),
                     cell('Within limit' if room >= 0 else 'Outside limit')])

    for rule in part.get('regulatory', []):
        found = latest_value(ctx.content.get('ratios'), rule['row'])
        limit = Decimal(rule['limit'])
        requirement = f"Not more than {rule['limit']}%" if rule['direction'] == 'max' else f"At least {rule['limit']} times"
        add(rule['measure'], requirement, limit, rule['direction'], found[0] if found else None, rule['unit'], found[1] if found else '', found[2] if found else [])
    for row in (ctx.content.get('covenants') or {}).get('rows', []):
        name, requirement, threshold, direction, actual = (row + [None] * 5)[:5]
        if not threshold or not threshold.get('value'):
            continue
        limit, text = Decimal(threshold['value']), name['text'].lower()
        way = 'max' if 'max' in (direction or {}).get('text', '').lower() or 'not exceed' in (requirement or {}).get('text', '').lower() else 'min'
        unit = '%' if 'leverage' in text or 'loan to value' in text or '%' in (requirement or {}).get('text', '') else 'x'
        value, basis, cites = None, '', []
        if 'loan to value' in text:
            ltv = next((r for r in (ctx.other_section(8).get('ltv') or {}).get('rows', [])), None)
            if ltv and ltv[3].get('value'):
                value, basis = Decimal(ltv[3]['value']), 'at proposed limits, section 8'
        elif 'interest coverage' in text and 'property' in text:
            base = projection(ctx, 'Base case')
            if base:
                value, basis, cites = base['lines']['Interest coverage (x)'][0], f"projected {base['years'][0]}, base case", base['cites']
        elif 'aggregate leverage' in text:
            found = latest_value(ctx.content.get('ratios'), 'Aggregate leverage (%)')
            if found:
                value, basis, cites = found
        elif actual and actual.get('value'):
            value, basis, cites = Decimal(actual['value']), 'latest reported', actual['cites']
        add(name['text'], (requirement or {}).get('text', ''), limit, way, value, unit, basis, cites + threshold.get('cites', []))
    return dict(columns=column_names(part), rows=rows)


COMPUTE = dict(key_tenants=key_tenants, top_tenants=top_tenants, lease_profile=lease_profile, debt_service=debt_service,
               cashflow_base=cashflow_base, stress_cases=stress_cases, assumptions=assumptions, headroom=headroom)


def run(part, ctx):
    function = COMPUTE.get(part.get('compute'))
    if function is None:
        return missing(part, 'No calculation is configured for this part.')
    try:
        return function(part, ctx)
    except Exception as error:  # a workbook in an unexpected layout is a named gap, never a guess
        return missing(part, f'The source workbook could not be read as expected ({type(error).__name__}); nothing was computed.')


def internal_rating(part, ctx):
    """The internal rating line, copied from the supplied rating worksheet. Without one the rating stays an open item."""
    case = ctx.case
    book, refs = ctx.workbook(RATING)
    if book is None or 'Internal rating' not in book.sheetnames:
        return dict(columns=column_names(part), rows=[[
            cell(case.borrower_name, status='ok'), cell('Not yet assigned', status='open'), cell('None: new to bank' if case.new_to_bank else '', status='ok'),
            cell('n.a.', status='na'), cell('To be assigned by the rating unit before submission. External ratings are shown for reference and do not replace the internal rating.', status='open')]])
    cites = refs.get('Internal rating', [])
    items = {str(row['Item']).strip(): row['Value'] for row in table_rows(book['Internal rating'])[1]}
    held = lambda name, show=str: cell(show(items[name]), cites, 'ok') if items.get(name) not in (None, '') else cell('', status='gap')
    return dict(columns=column_names(part), rows=[[
        cell(case.borrower_name, status='ok'), held('Internal rating (CRR)'), held('Previous rating'), held('Rating date', day), held('Change and reason')]])


COMPUTE['internal_rating'] = internal_rating


def case_part(part, case):
    return dict(status='gap', note='Case input not available.')


@lru_cache(maxsize=None)
def case_assets(case_id):
    """Saved image assets declared for a demo case in its case.yaml (photographs, map). {} when none."""
    for path in sorted((ROOT / 'demo').glob('*/case.yaml')):
        data = yaml.safe_load(path.read_text())
        if data.get('case_id') == case_id:
            return data.get('assets') or {}
    return {}


def structure_chart(case, content, storage_root):
    """Draw the ownership chart from the checked unitholders table of the same section. Returns a slot or None."""
    holders = [(row[0]['text'], row[1]['text']) for row in (content.get('holders') or {}).get('rows', [])
               if row[0].get('status') == 'ok' and row[1].get('status') == 'ok'][:3]
    if not holders:
        return None
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 26)
        bold = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 28)
    except OSError:
        font = bold = ImageFont.load_default()
    width, height, navy = 1500, 620, (0, 32, 96)
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)

    def box(x, y, w, h, lines, fill):
        draw.rectangle([x, y, x + w, y + h], fill=fill, outline=navy, width=3)
        for i, (text, face) in enumerate(lines):
            colour = 'white' if fill == navy else navy
            draw.text((x + w / 2, y + h / 2 + (i - (len(lines) - 1) / 2) * 34), text, font=face, fill=colour, anchor='mm')

    gap, w = 40, (width - 80 - 40 * (len(holders) - 1)) // len(holders)
    centre = width // 2
    for i, (name, share) in enumerate(holders):
        x = 40 + i * (w + gap)
        label = name if len(name) <= 34 else name[:33] + '…'
        box(x, 30, w, 110, [(label, font), (f'{share}%', bold)], (238, 241, 246))
        draw.line([x + w / 2, 140, x + w / 2, 190], fill=navy, width=3)
    draw.line([40 + w / 2, 190, 40 + (len(holders) - 1) * (w + gap) + w / 2, 190], fill=navy, width=3)
    draw.line([centre, 190, centre, 250], fill=navy, width=3)
    box(centre - 330, 250, 660, 110, [(case.borrower_name, bold), ('Borrower', font)], navy)
    assets = case_assets(case.id)
    target = (assets.get('financing_object') or 'Financing object')
    draw.line([centre, 360, centre, 430], fill=navy, width=3)
    box(centre - 330, 430, 660, 110, [(target, bold), ('Financing object', font)], (238, 241, 246))
    folder = Path(storage_root) / 'assets'
    folder.mkdir(parents=True, exist_ok=True)
    name = 'structure_' + __import__('hashlib').sha256(repr((case.id, holders, target)).encode()).hexdigest()[:16] + '.png'
    image.save(folder / name)
    return dict(path=f'generated/{name}', caption='Drawn by the system from the unitholders table above. Holdings include deemed interests, which can overlap, so they are not additive.')


def asset_path(path, storage_root):
    """Resolve a slot path: generated/<name> is under the case's storage; anything else is a project file."""
    return Path(storage_root) / 'assets' / Path(path).name if str(path).startswith('generated/') else ROOT / path


def asset_part(part, case, content=None, storage_root=None):
    assets = case_assets(case.id)
    slots = []
    if part['asset'] == 'structure_chart' and storage_root:
        slot = structure_chart(case, content or {}, storage_root)
        return dict(slots=[slot]) if slot else dict(status='gap', note='The chart is drawn from the unitholders table, which has no checked rows yet.', slots=[])
    if part['asset'] == 'property_photos':
        credits = {c['file']: c for c in yaml.safe_load((ROOT / assets['credits']).read_text())['photos']} if assets.get('credits') else {}
        for photo in (assets.get('property_photos') or [])[:part['slots']]:
            info = credits.get(Path(photo['file']).name, {})
            shows = re.split(r'[:.;]', str(info.get('shows', 'Exterior of the building')))[0].strip()
            slots.append(dict(path=photo['file'], caption=f"{shows}. Photograph: {info.get('author', 'author not recorded')}, {info.get('licence', 'licence not recorded')}, Wikimedia Commons."))
    elif part['asset'] == 'location_map' and assets.get('location_map'):
        place = yaml.safe_load((ROOT / assets['location']).read_text()) if assets.get('location') else {}
        address = (place.get('geocode', {}).get('result', {}) or {}).get('address', '').title()
        slots.append(dict(path=assets['location_map'], caption=f"{address}. Map: {place.get('map', {}).get('attribution_required', 'OneMap, Singapore Land Authority')}."))
    if not slots:
        return dict(status='gap', note='No saved image is held for this part.', slots=[])
    return dict(slots=slots)
