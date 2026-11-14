"""Build the FIG ES template v1.0 and its mapping from config/teams/fig_re/es_spec.yaml.

Output: templates/ES_Template_FIG_v1.0.docx and config/teams/fig_re/template.yaml.
The package shell (styles, numbering, header, footer, page set-up) comes from the owner's
v0.2 file, which is only read. The body is laid out from the specification.

Run: .venv/bin/python scripts/build_template_fig_v1.py
"""
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SHELL = ROOT / 'templates/ES_Template_FIG_draft_v0.2.docx'
LOGO = ROOT / 'templates/UOB_logo.png'
TEAM = ROOT / 'config/teams/fig_re'
SPEC = yaml.safe_load((TEAM / 'es_spec.yaml').read_text())
TARGET = ROOT / SPEC['template']
WIDTH = 9360
NAVY, LABEL, BAND, RULE, GREY = '002060', 'EEF1F6', 'DCE3EE', 'B4BDCB', '7F7F7F'
BOX = '☐'

BORDERS = '<w:tcBorders>' + ''.join(
    f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="{RULE}"/>' for side in ('top', 'left', 'bottom', 'right')) + '</w:tcBorders>'
MARGINS = ('<w:tcMar><w:top w:w="70" w:type="dxa"/><w:left w:w="70" w:type="dxa"/>'
           '<w:bottom w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tcMar>')
TABLE_PR = ('<w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblBorders>' + ''.join(
    f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="{RULE}"/>'
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')) +
    '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
    '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>')
SIZE = '<w:sz w:val="18"/><w:szCs w:val="18"/>'
SYMBOL = '<w:rFonts w:ascii="Segoe UI Symbol" w:eastAsia="Segoe UI Symbol" w:hAnsi="Segoe UI Symbol" w:cs="Segoe UI Symbol"/>'
NARROW = ('kind', 'amount', 'number')
WIDE = re.compile(r'remark|comment|description|mitigant|basis|purpose|update|condition|outcome|stress applied|risk check|root cause|strategy|source|relationship', re.I)


def run(text, props=''):
    return f'<w:r><w:rPr>{props}{SIZE}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def options_runs(options):
    """Unticked boxes followed by their labels, as in the bank's form."""
    out = ''
    for i, option in enumerate(options):
        out += f'<w:r><w:rPr>{SYMBOL}{SIZE}</w:rPr><w:t xml:space="preserve">{BOX} </w:t></w:r>' + run(option + ('     ' if i < len(options) - 1 else ''))
    return out


def cell(content, width, *, fill=None, bold=False, colour=None, span=1, align=None, italic=False, raw=False):
    shade = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ''
    grid = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ''
    props = ('<w:b/><w:bCs/>' if bold else '') + ('<w:i/><w:iCs/>' if italic else '') + (f'<w:color w:val="{colour}"/>' if colour else '')
    body = content if raw else run(content, props)  # blank cells keep an empty run, so filled text takes the cell's font size
    jc = f'<w:jc w:val="{align}"/>' if align else ''
    return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{grid}{BORDERS}{shade}{MARGINS}</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:after="40"/>{jc}</w:pPr>{body}</w:p></w:tc>')


def row(cells, header=False):
    props = '<w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if header else '') + '</w:trPr>'
    return f'<w:tr>{props}{"".join(cells)}</w:tr>'


def table(widths, rows):
    assert sum(widths) == WIDTH, widths
    grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>'
    return f'<w:tbl>{TABLE_PR}{grid}{"".join(rows)}</w:tbl>'


def column_widths(columns, first_wide=True):
    """Each column gets room for its longest header word (and for figures or dates), then spare width goes to wording columns."""
    names = [c['name'] if isinstance(c, dict) else c for c in columns]
    minimums, weights = [], []
    for i, column in enumerate(columns):
        name = names[i]
        figure = (isinstance(column, dict) and column.get('kind') in NARROW) or bool(re.search(r'FY\[|Interim|%|\(x\)|\(pp\)|SGD m', name))
        minimum = max(max(len(word) for word in name.split()) * 112 + 150, 640)  # bold 9 pt header word plus cell margins
        if figure:
            minimum = max(minimum, 1000)
        if re.search(r'date|expiry|maturity', name, re.I):
            minimum = max(minimum, 1280)
        weight = 3.2 if WIDE.search(name) else 0.5 if figure else 1.5
        if i == 0 and first_wide:
            weight = max(weight, 2.2)
        if name == 'No.':
            minimum, weight = 520, 0
        minimums.append(minimum); weights.append(weight)
    spare = WIDTH - sum(minimums)
    if spare < 0:
        widths = [int(m * WIDTH / sum(minimums)) for m in minimums]
    else:
        widths = [m + int(spare * w / sum(weights)) for m, w in zip(minimums, weights)]
    widths[-1] += WIDTH - sum(widths)
    return names, widths


def heading(text, keep=True):
    # LibreOffice chains keep-with-next from the section heading into the wrapper, pushing every
    # section to a new page, so the first sub-heading of a section does not carry it.
    return (f'<w:p><w:pPr>{"<w:keepNext/>" if keep else ""}<w:spacing w:before="{220 if keep else 60}" w:after="80"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/><w:color w:val="{NAVY}"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t>{escape(text)}</w:t></w:r></w:p>')


def placeholder_text(part):
    return '[' + (part.get('guidance') or part['title']) + ']'


def guidance(text):
    props = f'<w:i/><w:iCs/><w:color w:val="{GREY}"/>'
    return (f'<w:p><w:pPr><w:spacing w:after="80"/><w:rPr>{props}</w:rPr></w:pPr>'
            f'<w:r><w:rPr>{props}</w:rPr><w:t>{escape(text)}</w:t></w:r></w:p>')


GAP = '<w:p><w:pPr><w:spacing w:after="0" w:line="120" w:lineRule="exact"/></w:pPr></w:p>'


def header_row(names, widths):
    return row([cell(n, w, fill=NAVY, bold=True, colour='FFFFFF') for n, w in zip(names, widths)], header=True)


def label_cell(text, width, span=1):
    if text.startswith('# '):
        return cell(text[2:], WIDTH, fill=BAND, bold=True, span=span)
    return cell(text, width, fill=LABEL, bold=True, italic=False)


def part_table(part):
    """A part's table: header, then fixed label rows or blank seed rows, then an optional total row."""
    if part['type'] == 'keyvalue':
        widths = [2808, 6552]
        rows = [row([cell(label, widths[0], fill=LABEL, bold=True), cell('', widths[1])]) for label in part['rows']]
        return table(widths, rows)
    if part['type'] == 'choice':
        questions = part.get('questions') or [part.get('title') or 'Select one']
        widths = [5200, 4160] if part.get('questions') else [2808, 6552]
        return table(widths, [row([cell(q, widths[0], fill=LABEL, bold=True), cell(options_runs(part['options']), widths[1], raw=True)]) for q in questions])
    if part['type'] == 'image':
        slots = part['slots']
        widths = [WIDTH // slots] * slots
        widths[-1] += WIDTH - sum(widths)
        label = '[Photograph]' if slots > 1 else f"[{part['title']}]"
        picture = [cell(label, w, italic=True, colour=GREY, align='center') for w in widths]
        caption = [cell('[Caption and source]', w, italic=True, colour=GREY, align='center') for w in widths]
        return table(widths, [row(picture), row(caption)])
    if part.get('facility_columns'):
        widths = [2808, 3276, 3276]
        rows = [header_row(['Key terms', 'Facility 1', 'Facility 2'], widths)]
        rows += [row([cell(label, widths[0], fill=LABEL, bold=True), cell('', widths[1]), cell('', widths[2])]) for label in part['rows']]
        return table(widths, rows)
    names, widths = column_widths(part['columns'])
    numeric = [isinstance(c, dict) and c.get('kind') in NARROW for c in part['columns']]
    rows = [header_row(names, widths)]
    blank = lambda start=0: [cell('', w, align='right' if numeric[i] else None) for i, w in enumerate(widths)][start:]
    if part.get('rows'):
        for label in part['rows']:
            rows.append(row([label_cell(label, WIDTH, len(widths))] if label.startswith('# ') else [label_cell(label, widths[0])] + blank(1)))
    else:
        rows += [row(blank()) for _ in range(part.get('seed_rows', 2))]
    if part.get('total'):
        rows.append(row([cell(part['total'], widths[0], fill=LABEL, bold=True)] + [cell('', w, fill=LABEL, align='right' if numeric[i + 1] else None) for i, w in enumerate(widths[1:])]))
    return table(widths, rows)


def cover_table():
    cover = SPEC['cover']
    widths = [2200, 2480, 2200, 2480]
    rows = []
    for left, right in cover['pairs']:
        cells = []
        for label, width in ((left, widths[1]), (right, widths[3])):
            options = cover.get('options', {}).get(label)
            cells += [cell(label, widths[0], fill=LABEL, bold=True),
                      cell(options_runs(options), width, raw=True) if options else cell('', width)]
        rows.append(row(cells))
    return table(widths, rows)


def section_body(section):
    """Wrapper cell content and the wrapper-level placeholders (the narrative fill points)."""
    out, placeholders = [], []
    for part in section['parts']:
        if part.get('hidden'):
            continue  # extracted for cover fields and calculations; not laid out in the template
        if part.get('title'):
            out.append(heading(part['title'], keep=bool(out)))
        if part['type'] == 'narrative':
            placeholders.append(placeholder_text(part))
            out.append(guidance(placeholder_text(part)))
            continue
        if part.get('guidance'):
            placeholders.append(placeholder_text(part))
            out.append(guidance(placeholder_text(part)))
        out.append(part_table(part))
        out.append(GAP)
    return ''.join(out), placeholders


def wrapper(content):
    borders = '<w:tcBorders>' + ''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>' for s in ('top', 'left', 'bottom', 'right')) + '</w:tcBorders>'
    margins = '<w:tcMar><w:top w:w="120" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
    return (f'<w:tbl><w:tblPr><w:tblW w:w="9638" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid><w:gridCol w:w="9638"/></w:tblGrid>'
            f'<w:tr><w:tc><w:tcPr><w:tcW w:w="9638" w:type="dxa"/>{borders}{margins}</w:tcPr>{content}</w:tc></w:tr></w:tbl>')


def section_heading(number, name):
    return ('<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:pBdr><w:bottom w:val="single" w:sz="8" w:space="4" w:color="002060"/></w:pBdr>'
            f'<w:tabs><w:tab w:val="left" w:pos="720"/></w:tabs></w:pPr><w:r><w:t>{number}.</w:t></w:r><w:r><w:tab/><w:t>{escape(name.upper())}</w:t></w:r></w:p>')


def logo(rel_id):
    cx, cy = 1188720, 338043  # 1.3 inch wide, the file's own proportions
    return ('<w:p><w:pPr><w:spacing w:after="120"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="900" name="Bank logo"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="900" name="logo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


def section_names():
    base = yaml.safe_load((ROOT / 'config/teams/fig/template.yaml').read_text())
    return base, {s['id']: s['name'] for s in base['sections']}


def document(shell_xml):
    base, names = section_names()
    head = shell_xml[:shell_xml.index('<w:body>') + len('<w:body>')]
    tail = shell_xml[shell_xml.rindex('<w:sectPr'):]
    body = [logo('rIdLogo'), '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>EXECUTIVE SUMMARY (ES)</w:t></w:r></w:p>',
            '<w:p><w:pPr><w:spacing w:after="160"/></w:pPr><w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
            '<w:t>Financial Institutions Group · Credit application</w:t></w:r></w:p>', cover_table()]
    placeholders = {}
    for section in SPEC['sections']:
        content, placeholders[section['id']] = section_body(section)
        body += [section_heading(section['id'], names[section['id']]), wrapper(content)]
    return head + ''.join(body) + tail, placeholders


def mapping(placeholders):
    """Table and narrative anchors for the registry parser, derived from the specification."""
    base, _ = section_names()

    def anchor(key, section_id, headers, labels, spans, repeat='none'):
        return dict(id=key, section_id=section_id, headers=headers, row_labels=labels, repeat=repeat,
                    source_policy='Filled from the ES specification; guidance and sample labels are not facts.',
                    cell_spans=spans, kind='records')

    cover = SPEC['cover']
    anchors = [anchor('cover', 0, [cover['pairs'][0][0], '', cover['pairs'][0][1], f"{BOX} " + f"     {BOX} ".join(cover['options'][cover['pairs'][0][1]])],
                      [pair[0] for pair in cover['pairs'][1:]], [[1, 1, 1, 1]] * len(cover['pairs']))]
    for section in SPEC['sections']:
        for part in section['parts']:
            kind = part['type']
            if kind == 'narrative' or part.get('hidden'):
                continue
            options = f"{BOX} " + f"     {BOX} ".join(part['options']) if kind == 'choice' else None
            if kind == 'keyvalue':
                headers, labels, spans = [part['rows'][0], ''], part['rows'][1:], [[1, 1]] * len(part['rows'])
            elif kind == 'choice':
                questions = part.get('questions') or [part.get('title') or 'Select one']
                headers, labels, spans = [questions[0], options], questions[1:], [[1, 1]] * len(questions)
            elif kind == 'image':
                first = '[Photograph]' if part['slots'] > 1 else f"[{part['title']}]"
                headers, labels, spans = [first] * part['slots'], ['[Caption and source]'], [[1] * part['slots']] * 2
            elif part.get('facility_columns'):
                headers, labels, spans = ['Key terms', 'Facility 1', 'Facility 2'], part['rows'], [[1, 1, 1]] * (len(part['rows']) + 1)
            else:
                headers = [c['name'] if isinstance(c, dict) else c for c in part['columns']]
                n = len(headers)
                if part.get('rows'):
                    labels = [label[2:] if label.startswith('# ') else label for label in part['rows']]
                    spans = [[1] * n] + [[n] if label.startswith('# ') else [1] * n for label in part['rows']]
                else:
                    labels, spans = [''] * part.get('seed_rows', 2), [[1] * n] * (part.get('seed_rows', 2) + 1)
                if part.get('total'):
                    labels, spans = labels + [part['total']], spans + [[1] * n]
            repeat = 'facility_columns' if part.get('facility_columns') else 'rows' if part.get('repeat') else 'none'
            anchors.append(anchor(part['key'], section['id'], headers, labels, spans, repeat))
    return dict(team_id='fig_re', version=SPEC['version'], default_template=SPEC['template'], mapping=base['mapping'],
                sections=base['sections'], table_anchors=anchors,
                narrative_anchors=[dict(section_id=sid, text=text) for sid, texts in placeholders.items() for text in texts])


def build():
    with ZipFile(SHELL) as shell:
        xml, placeholders = document(shell.read('word/document.xml').decode('utf-8'))
        with ZipFile(TARGET, 'w', ZIP_DEFLATED) as target:
            for info in shell.infolist():
                data = shell.read(info.filename)
                if info.filename == 'word/document.xml':
                    data = xml.encode('utf-8')
                elif info.filename == 'word/header1.xml':
                    texts = iter(['FIG Executive Summary template ', 'v1.0', ' · November 2026 · Confidential'])
                    data = re.sub(r'(<w:t[^>]*>)[^<]*(</w:t>)', lambda m: m.group(1).replace('<w:t>', '<w:t xml:space="preserve">') + next(texts) + m.group(2), data.decode('utf-8')).encode('utf-8')
                elif info.filename == 'word/_rels/document.xml.rels':
                    data = data.decode('utf-8').replace('</Relationships>',
                        '<Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.png"/></Relationships>').encode('utf-8')
                elif info.filename == '[Content_Types].xml' and b'Extension="png"' not in data:
                    data = data.decode('utf-8').replace('<Default Extension="rels"', '<Default Extension="png" ContentType="image/png"/><Default Extension="rels"').encode('utf-8')
                target.writestr(info, data)
            target.writestr('word/media/logo.png', LOGO.read_bytes())
    (TEAM / 'template.yaml').write_text(yaml.safe_dump(mapping(placeholders), sort_keys=False, width=100, allow_unicode=True))
    print(f'wrote {TARGET.relative_to(ROOT)} and {(TEAM / "template.yaml").relative_to(ROOT)}')


if __name__ == '__main__':
    build()
