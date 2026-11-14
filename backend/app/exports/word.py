"""Patch hash-pinned OOXML targets only. No replacement document/layout builder."""
from copy import deepcopy
from io import BytesIO
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from ..services.templates import W, paragraph_text


def locate(body, locator):
    element = body
    for index in locator['path']:
        element = element[index]
    return element


def set_paragraph(paragraph, text):
    """Retain paragraph and seed run properties; use real Word line breaks."""
    seed = next(paragraph.iter(W + 'r'), None)
    properties = deepcopy(seed.find(W + 'rPr')) if seed is not None and seed.find(W + 'rPr') is not None else None
    for child in list(paragraph):
        if child.tag != W + 'pPr':
            paragraph.remove(child)
    run = ET.SubElement(paragraph, W + 'r')
    run.set('inserted', 'true')  # Removed before serialization; normalize only new text.
    if properties is not None:
        run.append(properties)
    for i, line in enumerate(str(text).split('\n')):
        if i:
            ET.SubElement(run, W + 'br')
        node = ET.SubElement(run, W + 't', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'})
        node.text = line


def set_cell(cell, text):
    paragraphs = cell.findall(W + 'p')
    if not paragraphs:
        paragraphs = [ET.SubElement(cell, W + 'p')]
    set_paragraph(paragraphs[0], text)
    for paragraph in paragraphs[1:]:
        set_paragraph(paragraph, '')


def rows(table):
    return table.findall(W + 'tr')


def cells(row):
    return row.findall(W + 'tc')


def fill_row(row, values):
    targets = cells(row)
    if len(targets) != len(values):
        raise ValueError('Repeat row shape differs from mapped template seed')
    for cell, value in zip(targets, values):
        set_cell(cell, value)


def repeat_rows(table, records, *, start=1, total=False):
    """Zero retains a named-gap seed; one/many clone only the mapped detail row."""
    original = rows(table)
    end = len(original) - int(total)
    seed = deepcopy(original[start])
    if not records:
        raise ValueError('Zero records require an explicit gap or N/A row')
    position = list(table).index(original[start])
    for row in original[start:end]:
        table.remove(row)
    for offset, values in enumerate(records):
        row = deepcopy(seed)
        fill_row(row, values)
        table.insert(position + offset, row)


def facility_columns(table, columns):
    """Share the existing facility-width budget; preserve key column and styling."""
    if not columns:
        raise ValueError('Zero facilities require an explicit named-gap column')
    grid = table.find(W + 'tblGrid')
    widths = [int(c.get(W + 'w')) for c in grid]
    if len(widths) < 2 or any(len(cells(row)) != len(widths) for row in rows(table)):
        raise ValueError('Facility column grid does not match its mapped cells')
    count = len(columns)
    available = sum(widths[1:])
    # Narrow columns are withheld, never silently truncated or shrunk to unreadability.
    if available // count < 1700:
        raise ValueError('Facility columns exceed template width; owner-reviewed format required')
    new_widths = [available // count + (i < available % count) for i in range(count)]
    seed_grid = deepcopy(grid[1])
    for child in list(grid)[1:]:
        grid.remove(child)
    for width in new_widths:
        node = deepcopy(seed_grid); node.set(W + 'w', str(width)); grid.append(node)
    for ri, row in enumerate(rows(table)):
        seed = deepcopy(cells(row)[1])
        for cell in cells(row)[1:]:
            row.remove(cell)
        for width, column in zip(new_widths, columns):
            cell = deepcopy(seed)
            tcw = cell.find(W + 'tcPr/' + W + 'tcW')
            if tcw is not None:
                tcw.set(W + 'w', str(width))
            set_cell(cell, column[ri]); row.append(cell)


def serialize(root, original):
    namespaces = dict(pair for _, pair in ET.iterparse(BytesIO(original), events=['start-ns']))
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    rendered = ET.tostring(root, encoding='unicode')
    for prefix, uri in namespaces.items():
        declaration = 'xmlns:' + prefix if prefix else 'xmlns'
        if declaration + '=' not in rendered:
            root.set(declaration, uri)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


class TemplateCopy:
    def __init__(self, content, report):
        self.content, self.report = content, report
        with ZipFile(BytesIO(content)) as archive:
            self.original = archive.read('word/document.xml')
            styles = ET.fromstring(archive.read('word/styles.xml'))
        normal = next((s for s in styles if s.get(W+'styleId') == 'Normal'), None)
        default_fonts = styles.find(W+'docDefaults/'+W+'rPrDefault/'+W+'rPr/'+W+'rFonts')
        normal_fonts = normal.find(W+'rPr/'+W+'rFonts') if normal is not None else None
        self.body_fonts = deepcopy(normal_fonts if normal_fonts is not None else default_fonts)
        self.root = ET.fromstring(self.original)
        self.body = self.root.find(W + 'body')
        # Resolve every locator before any mutation changes child indices.
        self.tables = {t['id']: locate(self.body, t['locator']) for t in report['tables']}
        self.paragraphs = {f['id']: locate(self.body, f['locator']) for f in report['fill_points']}
        self.bound = {name: self.tables[ref] for name, ref in report['bindings'].items()}
        self.cell_targets = {c['key']: locate(self.body, c['locator']) for t in report['tables']
                             for row in t['rows'] for c in row if 'key' in c}

    def sanitize(self, gap):
        """Clear mapped values, including sample/default labels, before filling."""
        for table in self.report['tables']:
            for row in table['rows']:
                for cell in row:
                    if cell.get('role') == 'value':
                        set_cell(self.cell_targets[cell['key']], gap(table, cell))
        for fill in self.report['fill_points']:
            if fill['mapped'] and fill['table_id'] in self.report['bindings'].values():
                paragraph = self.paragraphs[fill['id']]
                table = next(t for t in self.report['tables'] if t['id'] == fill['table_id'])
                cell = fill.get('cell')
                role = table['rows'][cell['row']][cell['cell']].get('role') if cell else None
                if role in {'header', 'label'} and fill['kind'] == 'date':
                    continue  # MMMYY inside a column label is a format cue, not a dated fact.
                # Header period tokens and wrapper checkboxes are not factual defaults.
                text = paragraph_text(paragraph)
                if fill['text'] in text:
                    set_paragraph(paragraph, text.replace(fill['text'], '[GAP: period]' if fill['kind']=='period'
                                  else 'Pending CA selection' if fill['kind']=='checkbox' else '[GAP: input not mapped]', 1))

    def narrative(self, fill_id, paragraphs):
        target = self.paragraphs[fill_id]
        parent = next(p for p in self.root.iter() if target in list(p))
        seed = deepcopy(target)
        set_paragraph(target, paragraphs[0] if paragraphs else '')
        index = list(parent).index(target)
        for offset, text in enumerate(paragraphs[1:], 1):
            paragraph = deepcopy(seed)
            set_paragraph(paragraph, text)
            parent.insert(index + offset, paragraph)

    def status(self, text):
        paragraph = ET.Element(W + 'p')
        properties = ET.SubElement(paragraph, W + 'pPr')
        ET.SubElement(properties, W + 'pStyle', {W + 'val': 'Normal'})
        set_paragraph(paragraph, text)
        # The cover is already bound before mutation; insert under the title.
        cover = self.bound['s0.cover']
        self.body.insert(list(self.body).index(cover), paragraph)

    def appendix(self, title, entries):
        # Explicitly requested appendix; reuse the owner's existing styles and
        # page geometry, with no new tables/package parts/section definitions.
        for i, text in enumerate([title, *entries]):
            paragraph = ET.Element(W + 'p')
            properties = ET.SubElement(paragraph, W + 'pPr')
            ET.SubElement(properties, W + 'pStyle', {W + 'val': 'Heading2' if i == 0 else 'Normal'})
            if i == 0:
                ET.SubElement(properties, W + 'pageBreakBefore')
                ET.SubElement(properties, W + 'keepNext')
            set_paragraph(paragraph, text)
            self.body.insert(list(self.body).index(self.body.find(W + 'sectPr')), paragraph)

    def bytes(self):
        # LO can drop this dense nested grid if its header lands at a page foot.
        # Start the financial section on a fresh page without rewriting the
        # owner's heading, tables or section geometry. Empty flow anchor only.
        wrapper = self.bound.get('s10.wrapper')
        if wrapper is not None and not getattr(self, '_financial_break_added', False):
            children = list(self.body)
            if wrapper in children:
                index = children.index(wrapper)
                heading = children[index-1] if index else None
                style = heading.find(W+'pPr/'+W+'pStyle') if heading is not None else None
                if style is not None and style.get(W+'val') == 'Heading1':
                    paragraph = ET.Element(W+'p')
                    properties = ET.SubElement(paragraph, W+'pPr')
                    ET.SubElement(properties, W+'pageBreakBefore')
                    ET.SubElement(properties, W+'keepNext')
                    ET.SubElement(properties, W+'spacing', {W+'before':'0', W+'after':'0', W+'line':'20', W+'lineRule':'exact'})
                    self.body.insert(index-1, paragraph)
                    self._financial_break_added = True
        for run in self.root.iter(W+'r'):
            if run.attrib.pop('inserted', None) and self.body_fonts is not None:
                properties = run.find(W+'rPr')
                if properties is None:
                    properties = ET.Element(W+'rPr'); run.insert(0, properties)
                for font in properties.findall(W+'rFonts'):
                    properties.remove(font)
                properties.insert(0, deepcopy(self.body_fonts))
        # LibreOffice can omit a leading nested table when its wrapper starts at
        # a page boundary (also reproducible in the unfilled owner template).
        # A one-point, keep-with-next paragraph gives it an explicit flow anchor.
        # Apply after filling so frozen B22 locators remain valid; idempotent.
        for cell in self.root.iter(W + 'tc'):
            content = [c for c in cell if c.tag != W + 'tcPr']
            if content and content[0].tag == W + 'tbl':
                paragraph = ET.Element(W + 'p')
                properties = ET.SubElement(paragraph, W + 'pPr')
                ET.SubElement(properties, W + 'keepNext')
                ET.SubElement(properties, W + 'spacing', {
                    W + 'before': '0', W + 'after': '0',
                    W + 'line': '20', W + 'lineRule': 'exact'})
                cell.insert(list(cell).index(content[0]), paragraph)
        result = BytesIO()
        with ZipFile(BytesIO(self.content)) as source, ZipFile(result, 'w') as destination:
            for info in source.infolist():
                destination.writestr(info, serialize(self.root, self.original) if info.filename=='word/document.xml' else source.read(info.filename))
        return result.getvalue()
