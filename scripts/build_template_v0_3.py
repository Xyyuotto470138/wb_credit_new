"""Build templates/ES_Template_FIG_draft_v0.3.docx from Sheryl's v0.2.

v0.2 is read only. Her section 1 to 4 edits are kept as she made them. Her
"Sheryl Update points" notes in section 10 are replaced by the tables they ask
for. Every other package part is copied byte for byte.

Run: .venv/bin/python scripts/build_template_v0_3.py
"""
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'templates/ES_Template_FIG_draft_v0.2.docx'
TARGET = ROOT / 'templates/ES_Template_FIG_draft_v0.3.docx'
WIDTH = 9360

BORDERS = '<w:tcBorders>' + ''.join(
    f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>' for side in ('top', 'left', 'bottom', 'right')
) + '</w:tcBorders>'
MARGINS = ('<w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
           '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>')
TABLE_PR = ('<w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblBorders>' + ''.join(
    f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')
) + '</w:tblBorders><w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
    '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>')
ROW_PR = '<w:tblPrEx><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPrEx>'
SIZE = '<w:sz w:val="18"/><w:szCs w:val="18"/>'
SYMBOL = '<w:rFonts w:ascii="Segoe UI Symbol" w:eastAsia="Segoe UI Symbol" w:hAnsi="Segoe UI Symbol" w:cs="Segoe UI Symbol"/>'
YES_NO = object()


def text_run(text, props=''):
    return f'<w:r><w:rPr>{props}{SIZE}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def cell_runs(value, bold=False):
    """Plain text, an italic [placeholder], or the template's Yes/No checkbox pair."""
    if value is YES_NO:
        box = f'<w:r><w:rPr>{SYMBOL}{SIZE}</w:rPr><w:t xml:space="preserve">☐ </w:t></w:r>'
        return box + text_run('Yes     ') + box + text_run('No')
    if not value:
        return ''
    if bold:
        return text_run(value, '<w:b/><w:bCs/>')
    return text_run(value, '<w:i/><w:iCs/>' if value.startswith('[') else '')


def cell(value, width, header=False, span=1, fill=None):
    shade = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill or "F2F2F2"}"/>' if header or fill else ''
    grid = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ''
    return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{grid}{BORDERS}{shade}{MARGINS}</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:after="40"/></w:pPr>{cell_runs(value, header or bool(fill))}</w:p></w:tc>')


def table(widths, headers, rows):
    assert sum(widths) == WIDTH and len(headers) == len(widths), headers
    grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>'
    out = [f'<w:tr>{ROW_PR}<w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>'
           + ''.join(cell(h, w, header=True) for h, w in zip(headers, widths)) + '</w:tr>']
    for row in rows:
        if isinstance(row, str):  # band row across the table, as in the financial highlights table
            cells = cell(row, WIDTH, span=len(widths), fill='E7EBF2')
        else:
            assert len(row) == len(widths), row
            cells = ''.join(cell(v, w) for v, w in zip(row, widths))
        out.append(f'<w:tr>{ROW_PR}<w:trPr><w:cantSplit/></w:trPr>{cells}</w:tr>')
    return f'<w:tbl>{TABLE_PR}{grid}{"".join(out)}</w:tbl>'


def heading(text):
    return ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/><w:u w:val="single"/></w:rPr><w:t>{escape(text)}</w:t></w:r></w:p>')


def guidance(text):
    return ('<w:p><w:pPr><w:spacing w:after="80"/><w:rPr><w:i/><w:iCs/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:i/><w:iCs/></w:rPr><w:t>{escape(text)}</w:t></w:r></w:p>')


GAP = '<w:p><w:pPr><w:spacing w:after="60"/></w:pPr></w:p>'
blank = lambda n: [''] * n

PERFORMANCE_WIDTHS = [2340, 1404, 1404, 1124, 1216, 1872]


def performance(first, examples):
    headers = [first, 'FY[  ]', 'FY[  ]', 'Change (%)', '% of total', 'Remarks']
    return table(PERFORMANCE_WIDTHS, headers, [[e] + blank(5) for e in examples] + [['Total'] + blank(5)])


AFTER_FINANCIALS = ''.join([
    heading('Major changes in profit and loss and balance sheet'),
    guidance('[Highlight the major profit and loss and balance sheet items and compare them with prior years. '
             'Explain each significant movement.]'),
    table([2340, 1310, 1310, 1124, 3276], ['Line item', 'FY[  ]', 'FY[  ]', 'Change (%)', 'Reason for change'],
          ['Profit and loss', ['[Line item]'] + blank(4), ['[Line item]'] + blank(4),
           'Balance sheet', ['[Line item]'] + blank(4), ['[Line item]'] + blank(4)]),
    heading('Segmental performance'),
    guidance('[If applicable. Revenue or net property income by business segment or asset class. '
             'State "Not applicable" with the reason if the borrower has a single segment.]'),
    performance('Segment', ['[Segment 1]', '[Segment 2]']),
    heading('Geographic performance'),
    guidance('[If applicable. Revenue or net property income by country or region. '
             'State "Not applicable" with the reason if operations are in one country.]'),
    performance('Country / region', ['[Country 1]', '[Country 2]']),
    heading('Analytics'),
    guidance('[Analysis of profitability, balance sheet strength, leverage, liquidity and debt maturity, '
             'with the reasons for the main movements over the periods shown.]'),
])

FX_CHECKS = [
    'No or insignificant FX risk: revenue, costs and borrowings are in the same currency',
    'Mismatch between revenue currency and cost currency',
    'Mismatch between revenue currency and borrowing currency',
    'Mismatch between asset currency and liability currency (balance sheet translation)',
    'Facility currency differs from the currency of the repayment source',
    'Natural hedge in place (matching currency income, assets or borrowings)',
    'Financial hedges in place (forwards, cross currency swaps), in line with a stated hedging policy',
    'Unhedged exposure is material to debt service or financial covenants',
]

BEFORE_COMMENTARY = ''.join([
    heading('Cash flow projection and analysis'),
    guidance('[Detailed projection over the facility tenor. Base case assumes stable cash flow. '
             'State every assumption and the basis for it.]'),
    heading('Base case'),
    table([2808, 1310, 1310, 1310, 2622],
          ["SGD'000", 'Projected FY[  ]', 'Projected FY[  ]', 'Projected FY[  ]', 'Remarks'],
          [[label] + blank(4) for label in (
              'Gross revenue', 'Net property income / EBITDA', 'Operating cash flow', 'Capital expenditure',
              'Interest expense', 'Scheduled debt repayment', 'Cash available for debt service',
              'Debt service coverage (x)', 'Closing cash balance')]),
    heading('Stress cases'),
    table([1872, 2434, 1124, 1124, 2806],
          ['Scenario', 'Stress applied', 'Minimum DSCR (x)', 'Minimum interest coverage (x)', 'Outcome / comment'],
          [['Base case'] + blank(4), ['[Stress case 1]'] + blank(4), ['[Stress case 2]'] + blank(4)]),
    heading('Assumptions and basis'),
    table([2340, 1872, 1872, 3276], ['Assumption', 'Base case', 'Stress case', 'Basis for assumption'],
          [[label] + blank(3) for label in (
              'Revenue / rental growth', 'Occupancy', 'Operating costs', 'Interest rate',
              'Capital expenditure', 'Refinancing')]),
    heading('Inter-company debts'),
    table([2808, 1686, 4866], ['Any inter-company debts?', 'Yes / No', 'Comments'],
          [['[Borrower A]', YES_NO, '[Amount, counterparty, terms and subordination, if any]']]),
    heading('FX risk checklist'),
    table([5242, 1686, 2432], ['FX risk check', 'Yes / No', 'Comments'],
          [[f'{n}. {check}', YES_NO, ''] for n, check in enumerate(FX_CHECKS, 1)]),
])


def once(text, old, new):
    assert text.count(old) == 1, (text.count(old), old)
    return text.replace(old, new)


def paragraph_start(text, index):
    return max(text.rfind('<w:p ', 0, index), text.rfind('<w:p>', 0, index))


def fill_empty_box(text, label, placeholder):
    """Put an italic prompt into the empty row under a one-column box heading."""
    row = text.index('<w:tr', text.index(label))
    end = text.index('</w:p>', row)
    assert '<w:r>' not in text[row:end] and '<w:r ' not in text[row:end], label
    run = f'<w:r><w:rPr><w:i/><w:iCs/></w:rPr><w:t>{escape(placeholder)}</w:t></w:r>'
    return text[:end] + run + text[end:]


def update_document(text):
    # Section 3: Sheryl's Y/N matrix. Make the [Y/N] prompts italic, the template's convention for fill points.
    text, count = re.subn(r'<w:r(?: [^>]*)?><w:t>\[Y/N\]</w:t></w:r>',
                          '<w:r><w:rPr><w:i/><w:iCs/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>[Y/N]</w:t></w:r>', text)
    assert count == 12, count

    # Section 4: Sheryl's new boxes. Fix one typo and add prompts to the two empty narrative boxes.
    text = once(text, 'updaes', 'updates')
    text = fill_empty_box(text, 'Industry/peer comparison',
                          '[Compare the borrower with its industry and peers on scale, leverage and performance.]')
    text = fill_empty_box(text, 'recent developments</w:t>',
                          '[Business updates and recent developments since the last review.]')

    # Section 10: units, then replace Sheryl's notes with the tables they ask for.
    text = once(text, '<w:t>S$m</w:t></w:r><w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:i/><w:iCs/></w:rPr>'
                      '<w:t xml:space="preserve"> unless stated. Rows follow',
                "<w:t>SGD'000</w:t></w:r><w:proofErr w:type=\"spellEnd\"/><w:r><w:rPr><w:i/><w:iCs/></w:rPr>"
                '<w:t xml:space="preserve"> unless stated. Rows follow')
    start = text.index('</w:p>', text.index('set in the system configuration.]')) + len('</w:p>')
    end = text.index('<w:tbl>', start)
    notes = text[start:end]
    assert 'Sheryl Update points' in notes and 'checklist' in notes and '<w:tc>' not in notes
    text = text[:start] + text[end:]
    head = text.index('S$m', start)
    assert head - start < 6000
    text = text[:head] + "SGD'000" + text[head + 3:]
    assert 'Sheryl Update points' not in text

    marker = text.index('Headroom to regulatory limits and financial covenants')
    at = paragraph_start(text, marker)
    text = text[:at] + AFTER_FINANCIALS + text[at:]
    marker = text.index('<w:t>Commentary</w:t>')
    at = paragraph_start(text, marker)
    return text[:at] + BEFORE_COMMENTARY + text[at:]


def build():
    with ZipFile(SOURCE) as source, ZipFile(TARGET, 'w', ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == 'word/document.xml':
                data = update_document(data.decode('utf-8')).encode('utf-8')
            elif info.filename == 'word/header1.xml':
                data = once(data.decode('utf-8'), 'template  v0.1', 'template  v0.3').encode('utf-8')
            target.writestr(info, data)
    print(f'wrote {TARGET.relative_to(ROOT)}')


if __name__ == '__main__':
    build()
