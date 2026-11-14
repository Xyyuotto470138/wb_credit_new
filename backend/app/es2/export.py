"""Fill the team's Word template from specification-driven drafts.

Each part of the specification is found in the template by its mapped anchor (tables) or its guidance
placeholder (narrative) and filled from the saved draft. Nothing is computed or reworded here.
"""
from datetime import date
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from PIL import Image

from ..exports.word import cells, rows, fill_row, repeat_rows, facility_columns, set_cell, set_paragraph
from ..services.templates import W
from .blocks import LABEL as BLOCK_LABEL, image_path, ordered
from .compute import asset_path
from .spec import applies, column_names

ROOT = Path(__file__).resolve().parents[3]
BOX, TICK = '☐', '☒'
EMU_PER_INCH = 914400
IMAGE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'
NOT_PROVIDED = 'Not provided'
NUMERIC = __import__('re').compile(r'^\(?-?[\d,]+(\.\d+)?\)?\s?(%|x|pp)?$')


def placeholder(part):
    text = part.get('guidance') or (part.get('title') if part['type'] == 'narrative' else None)
    return f'[{text}]' if text else None


def drawing(rel_id, number, width_inches, ratio):
    cx, cy = int(width_inches * EMU_PER_INCH), int(width_inches * ratio * EMU_PER_INCH)
    xml = (f'<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           f'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
           f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{1000 + number}" name="Picture {number}"/>'
           '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
           f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{1000 + number}" name="picture{number}"/><pic:cNvPicPr/></pic:nvPicPr>'
           f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
           f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
           '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
    return ET.fromstring(xml)


class Filler:
    def __init__(self, copy, manifest, case, spec, storage_root=None):
        self.copy, self.manifest, self.case, self.spec, self.storage_root = copy, manifest, case, spec, storage_root
        self.numbers = {ref: i for i, ref in enumerate(manifest['sources'], 1)}
        self.media, self.open_items, self.ca_notes = [], [], []
        self.tails = {}  # the source line under a table, so added content is placed below it
        manifest['source_markers'] = {str(i): ref for ref, i in self.numbers.items()}
        manifest['filled_targets'] = {}

    # ---- small helpers
    def marks(self, refs, sections=()):
        out = [f'[{self.numbers[ref]}]' for ref in dict.fromkeys(refs) if ref in self.numbers]
        out += [f'(see section {n})' for n in sections]
        return ' '.join(out)

    def cell_text(self, cell, with_marks=False):
        if not cell:
            return NOT_PROVIDED
        text = cell.get('text') or (NOT_PROVIDED if cell.get('status') == 'gap' else '')
        return (text + ' ' + self.marks(cell.get('cites', []), cell.get('sections', []))).strip() if with_marks else text

    def row_texts(self, row):
        return [self.cell_text(cell) for cell in row]

    def source_line(self, table, rows_of_cells, answers=()):
        """One small line under a table naming its sources, so cells stay clean."""
        cells_flat = [cell for row in rows_of_cells for cell in row if cell]
        refs = [ref for cell in cells_flat for ref in cell.get('cites', [])] + [ref for a in answers for ref in a.get('cites', [])]
        sections = sorted({n for cell in cells_flat for n in cell.get('sections', [])})
        computed = any(cell.get('status') == 'computed' for cell in cells_flat)
        pieces = []
        if refs:
            pieces.append('Sources: ' + self.marks(refs))
        if sections:
            pieces.append('See section' + ('s ' if len(sections) > 1 else ' ') + ', '.join(str(n) for n in sections))
        if computed:
            pieces.append('Ratios, changes, shares and totals are computed by the system')
        if not pieces:
            return
        paragraph = ET.Element(W + 'p')
        properties = ET.SubElement(paragraph, W + 'pPr')
        ET.SubElement(properties, W + 'spacing', {W + 'before': '40', W + 'after': '100'})
        run = ET.SubElement(paragraph, W + 'r')
        run.set('inserted', 'true')
        style = ET.SubElement(run, W + 'rPr')
        ET.SubElement(style, W + 'color', {W + 'val': '7F7F7F'})
        ET.SubElement(style, W + 'sz', {W + 'val': '15'}); ET.SubElement(style, W + 'szCs', {W + 'val': '15'})
        node = ET.SubElement(run, W + 't', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'})
        node.text = '. '.join(pieces) + '.'
        parent = next(p for p in self.copy.root.iter() if table in list(p))
        parent.insert(list(parent).index(table) + 1, paragraph)
        self.tails[id(table)] = paragraph

    def remove_placeholder(self, fill):
        paragraph = self.copy.paragraphs[fill['id']]
        for parent in self.copy.root.iter():
            if paragraph in list(parent):
                parent.remove(paragraph)
                return

    def fills(self, section_id):
        wrapper = self.copy.report['bindings'].get(f's{section_id}.wrapper')
        return {f['text']: f for f in self.copy.report['fill_points'] if f['section_id'] == section_id and f['kind'] == 'placeholder' and f['table_id'] == wrapper}

    # ---- part fillers
    def narrative(self, fill, part, body, claims, fallback):
        paragraphs = [(c['text'] + ' ' + self.marks(c.get('evidence_ids', []), c.get('section_refs', []))).strip() for c in claims if c.get('part') == part['key']]
        if not paragraphs:
            paragraphs = [body.get('note') if body.get('status') == 'na' else fallback]
        self.copy.narrative(fill['id'], paragraphs)
        target = self.copy.paragraphs[fill['id']]
        parent = next(p for p in self.copy.root.iter() if target in list(p))
        index = list(parent).index(target)
        self.last_span = dict(start=target, end=list(parent)[index + len(paragraphs) - 1])
        for paragraph in list(parent)[index:index + len(paragraphs)]:  # filled wording is upright black, not guidance grey italics
            for run in paragraph.iter(W + 'r'):
                properties = run.find(W + 'rPr')
                if properties is not None:
                    for tag in ('i', 'iCs', 'color'):
                        for node in properties.findall(W + tag):
                            properties.remove(node)
            mark = paragraph.find(W + 'pPr/' + W + 'rPr')
            if mark is not None:
                paragraph.find(W + 'pPr').remove(mark)

    def note_row(self, table, note, total=False):
        """Replace the detail rows with one row that carries a note across the full table width."""
        width = len(cells(rows(table)[1]))
        repeat_rows(table, [[note] + [''] * (width - 1)], start=1, total=total)
        row = rows(table)[1]
        first, rest = cells(row)[0], cells(row)[1:]
        total_width = sum(int(c.find(W + 'tcPr/' + W + 'tcW').get(W + 'w')) for c in cells(row))
        properties = first.find(W + 'tcPr')
        properties.find(W + 'tcW').set(W + 'w', str(total_width))
        span = ET.Element(W + 'gridSpan', {W + 'val': str(width)})
        properties.insert(list(properties).index(properties.find(W + 'tcW')) + 1, span)
        for cell in rest:
            row.remove(cell)

    def table(self, key, part, body):
        table = self.copy.bound.get(key)
        if table is None:
            return
        if body.get('status') in ('na', 'gap', 'workflow') and not body.get('rows'):
            if part.get('rows') and not part.get('facility_columns') and body.get('status') != 'na':
                return  # fixed-label tables keep their labels; the open item is listed in the appendix
            note = body.get('note') or NOT_PROVIDED
            if part.get('rows'):
                first = rows(table)[1]
                set_cell(cells(first)[-1] if len(cells(first)) > 1 else cells(first)[0], note)
            else:
                self.note_row(table, note, total=bool(part.get('total')))
                if part.get('total'):
                    table.remove(rows(table)[-1])
            return
        if body.get('facility_columns'):
            names = body['columns'][1:]
            if not names:
                self.note_row(table, NOT_PROVIDED)
                return
            columns = [[name] + [self.cell_text(row[i + 1]) for row in body['rows']] for i, name in enumerate(names)]
            facility_columns(table, columns)
            self.source_line(table, body['rows'])
            return
        header = cells(rows(table)[0])
        for i, name in enumerate(body.get('columns', [])[:len(header)]):
            if name != column_names(part)[i]:
                set_cell(header[i], name)
        self.source_line(table, (body.get('rows') or []) + ([body['total']] if body.get('total') else []))
        if part.get('rows'):
            for ri, row in enumerate(body.get('rows') or []):
                texts = self.row_texts(row)
                for ci, target in enumerate(cells(rows(table)[ri + 1])):
                    if ci:
                        set_cell(target, texts[ci])
        elif body.get('rows'):
            repeat_rows(table, [self.row_texts(row) for row in body['rows']], start=1, total=bool(part.get('total')))
            if part.get('total'):
                if body.get('total'):
                    fill_row(rows(table)[-1], [self.cell_text(cell) for cell in body['total']])
                else:
                    table.remove(rows(table)[-1])
        else:
            self.note_row(table, NOT_PROVIDED, total=bool(part.get('total')))

    def keyvalue(self, key, body):
        table = self.copy.bound.get(key)
        if table is None:
            return
        for ri, row in enumerate(body.get('rows') or []):
            set_cell(cells(rows(table)[ri])[1], self.cell_text(row[1]))
        self.source_line(table, body.get('rows') or [])
        if not body.get('rows'):
            set_cell(cells(rows(table)[0])[1], body.get('note') or NOT_PROVIDED)

    def choice(self, key, part, body):
        table = self.copy.bound.get(key)
        if table is None:
            return
        answers = body.get('answers') or []
        for ri, row in enumerate(rows(table)):
            answer = answers[ri] if ri < len(answers) else {}
            boxes = ('\n' if len(part['options']) > 2 else '     ').join(f"{TICK if option == answer.get('selected') else BOX} {option}" for option in part['options'])
            if body.get('status') == 'na':
                boxes = body['note']
            elif answer.get('note'):
                boxes += '\n' + (answer['note'] + ' ' + self.marks(answer.get('cites', []))).strip()
            set_cell(cells(row)[1], boxes)

    def image(self, key, part, body):
        table = self.copy.bound.get(key)
        if table is None:
            return
        picture, caption = rows(table)[0], rows(table)[1]
        slots = body.get('slots') or []
        width = 6.1 if part['slots'] == 1 else 2.95
        for i, target in enumerate(cells(picture)):
            if i >= len(slots):
                set_cell(target, 'No image held' if not slots else '')
                set_cell(cells(caption)[i], body.get('note', '') if not slots and i == 0 else '')
                continue
            path = asset_path(slots[i]['path'], self.storage_root)
            with Image.open(path) as image:
                image = image.convert('RGB')
                image.thumbnail((1500, 1500))
                ratio = image.height / image.width
                if part['slots'] > 1:  # paired photographs are centre-cropped to the same square frame
                    side = min(image.width, image.height)
                    left, top = (image.width - side) // 2, (image.height - side) // 2
                    image = image.crop((left, top, left + side, top + side))
                    ratio = 1
                data = BytesIO()
                image.save(data, 'JPEG', quality=85)
            number = len(self.media) + 1
            rel_id, name = f'rIdEs{number}', f'media/es_image{number}.jpg'
            self.media.append((rel_id, name, data.getvalue()))
            paragraph = target.find(W + 'p')
            set_paragraph(paragraph, '')
            for run in list(paragraph.findall(W + 'r')):
                paragraph.remove(run)
            paragraph.append(drawing(rel_id, number, width, ratio))
            set_cell(cells(caption)[i], slots[i].get('caption', ''))
            for run in cells(caption)[i].iter(W + 'r'):
                properties = run.find(W + 'rPr')
                if properties is not None:
                    for node in properties.findall(W + 'i') + properties.findall(W + 'iCs'):
                        properties.remove(node)

    # ---- analyst added content
    def styled(self, text, *, bold=False, grey=False, size=None, before=60, after=60, right=False, keep=False):
        paragraph = ET.Element(W + 'p')
        properties = ET.SubElement(paragraph, W + 'pPr')
        if keep:
            ET.SubElement(properties, W + 'keepNext')
        ET.SubElement(properties, W + 'spacing', {W + 'before': str(before), W + 'after': str(after)})
        if right:
            ET.SubElement(properties, W + 'jc', {W + 'val': 'right'})
        set_paragraph(paragraph, text)
        for run in paragraph.findall(W + 'r'):
            style = ET.Element(W + 'rPr')
            if bold:
                ET.SubElement(style, W + 'b')
            if grey:
                ET.SubElement(style, W + 'color', {W + 'val': '7F7F7F'})
            if size:
                ET.SubElement(style, W + 'sz', {W + 'val': str(size)}); ET.SubElement(style, W + 'szCs', {W + 'val': str(size)})
            run.insert(0, style)
        return paragraph

    def block_table(self, block):
        table = ET.Element(W + 'tbl')
        properties = ET.SubElement(table, W + 'tblPr')
        ET.SubElement(properties, W + 'tblW', {W + 'w': '5000', W + 'type': 'pct'})
        borders = ET.SubElement(properties, W + 'tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            ET.SubElement(borders, W + side, {W + 'val': 'single', W + 'sz': '4', W + 'space': '0', W + 'color': 'A6A6A6'})
        width = len(block['rows'][0])
        grid = ET.SubElement(table, W + 'tblGrid')
        for _ in range(width):
            ET.SubElement(grid, W + 'gridCol', {W + 'w': str(9000 // width)})
        for ri, values in enumerate(block['rows']):
            row = ET.SubElement(table, W + 'tr')
            head = ri == 0 and block.get('header', True)
            row_properties = ET.SubElement(row, W + 'trPr')
            ET.SubElement(row_properties, W + 'cantSplit')
            if head:
                ET.SubElement(row_properties, W + 'tblHeader')
            for value in values:
                cell = ET.SubElement(row, W + 'tc')
                cell_properties = ET.SubElement(cell, W + 'tcPr')
                ET.SubElement(cell_properties, W + 'tcW', {W + 'w': str(5000 // width), W + 'type': 'pct'})
                if head:
                    ET.SubElement(cell_properties, W + 'shd', {W + 'val': 'clear', W + 'color': 'auto', W + 'fill': 'EDEDED'})
                cell.append(self.styled(value, bold=head, size=17, before=20, after=20, right=not head and bool(NUMERIC.match(value))))
        return table

    def block_image(self, block):
        path = image_path(self.storage_root, self.case.id, block['image'])
        with Image.open(path) as image:
            image = image.convert('RGB')
            image.thumbnail((2000, 2000))
            ratio, natural = image.height / image.width, image.width / 150
            data = BytesIO()
            image.save(data, 'JPEG', quality=90)
        number = len(self.media) + 1
        rel_id, name = f'rIdEs{number}', f'media/es_image{number}.jpg'
        self.media.append((rel_id, name, data.getvalue()))
        paragraph = ET.Element(W + 'p')
        width = min(6.0, max(1.5, natural))
        paragraph.append(drawing(rel_id, number, min(width, 7.5 / ratio), ratio))  # also kept within one page height
        return paragraph

    def block_elements(self, block):
        out = []
        if block.get('title'):
            out.append(self.styled(block['title'], bold=True, before=120, after=40, keep=True))
        if block['kind'] == 'text':
            out += [self.styled(line) for line in block.get('text', '').split('\n') if line.strip()]
        elif block['kind'] == 'table':
            out.append(self.block_table(block))
        else:
            try:
                out.append(self.block_image(block))
            except (OSError, ValueError):
                out.append(self.styled('[Image not available]', grey=True))
        out.append(self.styled(BLOCK_LABEL, grey=True, size=15, before=40, after=120))
        return out

    def place_blocks(self, sid, blocks, ends, keys, titles):
        """Insert the analyst's blocks after the part each one follows. `ends` maps a part key to its last element."""
        if not blocks or not ends:
            return
        parents = {child: parent for parent in self.copy.root.iter() for child in parent}
        first = next(iter(ends.values()))
        placed = {}  # elements already inserted after an anchor, so later groups follow them
        for key in [''] + keys + [None]:
            group = [b for b in blocks if (b['after'] == key if key is not None else b['after'] not in [''] + keys)]
            if not group:
                continue
            if key == '':
                anchor, offset = first['start'], 0
                # Above the first part means above its heading too, when the template gives it one.
                siblings = list(parents[anchor]) if anchor in parents else []
                before_it = siblings[siblings.index(anchor) - 1] if anchor in siblings and siblings.index(anchor) > 0 else None
                if before_it is not None and before_it.tag == W + 'p' and titles.get(keys[0]) and ''.join(n.text or '' for n in before_it.iter(W + 't')).strip() == titles[keys[0]]:
                    anchor = before_it
            else:
                known = [k for k in keys[:keys.index(key) + 1] if k in ends] if key is not None else list(ends)
                anchor, offset = (ends[known[-1]]['end'], 1) if known else (first['start'], 0)
            parent = parents.get(anchor)
            if parent is None:
                continue
            index = list(parent).index(anchor) + offset + (placed.get(id(anchor), 0) if offset else 0)
            before = index
            for block in group:
                for element in self.block_elements(block):
                    parent.insert(index, element)
                    index += 1
            if offset:
                placed[id(anchor)] = placed.get(id(anchor), 0) + index - before
            self.manifest['filled_targets'][f's{sid}.analyst_added.{key if key is not None else "end"}'] = len(group)

    # ---- cover
    def cover(self, drafts):
        table = self.copy.bound.get('s0.cover')
        if table is None:
            return
        parts = lambda n: ((drafts.get(n) or {}).get('claim_spans') or [{}])[0].get('parts', {})
        facts = {row[0]['text']: row[1] for row in parts(1).get('cover_facts', {}).get('rows', [])}
        fact = lambda label: self.cell_text(facts.get(label)) if facts.get(label, {}).get('status') == 'ok' else NOT_PROVIDED
        exposure = parts(2).get('exposure', {})
        total = exposure.get('total') or []
        names = exposure.get('columns', [])
        proposed = total[names.index('Proposed')]['text'] if total and 'Proposed' in names else ''
        ratings = parts(12).get('external_ratings', {}).get('rows', [])
        internal = parts(12).get('internal_rating', {}).get('rows', [])
        review = {'new': 'New', 'renewal': 'Renewal'}.get(self.case.case_type)
        paper = fact('Paper type')
        tick = lambda options, chosen: '     '.join(f"{TICK if chosen and option.lower().startswith(chosen.lower()) else BOX} {option}" for option in options)
        options = self.spec['cover']['options']
        values = {
            'Borrower(s) and CAS no.': f"{self.case.borrower_name}\nCAS no. {fact('CAS number')}",
            'Paper type': tick(options['Paper type'], paper if paper != NOT_PROVIDED else None),
            'Obligor group': fact('Obligor group'), 'Review type': tick(options['Review type'], review),
            'Country of risk': fact('Country of risk'), 'Industry': fact('Industry'),
            'Internal rating (CRR)': internal[0][1]['text'] if internal else NOT_PROVIDED,
            'External rating': ('None current; see section 12' if not ratings or all('withdrawn' in row[1].get('text', '').lower() for row in ratings)
                                else '; '.join(' '.join(c['text'] for c in row[:3] if c.get('text')) for row in ratings[:2])),
            'Total proposed limits': f"SGD'000 {proposed}" if proposed else NOT_PROVIDED,
            'Relationship manager': fact('Relationship manager'),
            'Credit analyst': (drafts.get(1) or {}).get('author') or NOT_PROVIDED,
            'Date of paper': date.today().strftime('%d %B %Y').lstrip('0'),
        }
        for ri, pair in enumerate(self.spec['cover']['pairs']):
            row = cells(rows(table)[ri])
            set_cell(row[1], values[pair[0]]); set_cell(row[3], values[pair[1]])

    # ---- run
    def run(self):
        drafts = {int(n): sec.get('draft') for n, sec in self.manifest['sections'].items()}
        synthetic = any(src.get('synthetic') for src in self.manifest['sources'].values())
        self.copy.status('DRAFT FOR CREDIT ANALYST REVIEW. Wording drafted with AI assistance and checked against the cited sources; figures in computed tables '
                         'are calculated by the system.' + (' Includes SYNTHETIC DEMO DATA.' if synthetic else '')
                         + f" Template {self.manifest['template']['display_version']}.")
        self.cover(drafts)
        for section in self.spec['sections']:
            sid = section['id']
            state = self.manifest['sections'][str(sid)]
            draft = drafts.get(sid)
            envelope = (draft['claim_spans'][0] if draft else {})
            content, claims = envelope.get('parts', {}), (draft['claim_spans'][1:] if draft else [])
            fills = self.fills(sid)
            fallback = 'Not provided: no supported wording is available from the evidence held.' if draft else 'Not drafted.'
            ends = {}  # where each part starts and ends in the document, for placing analyst added content
            for part in section['parts']:
                if part.get('hidden'):
                    continue
                key = f"s{sid}.{part['key']}"
                body = content.get(part['key']) or {}
                if not state['applicable']:
                    body = dict(status='na', note='Not applicable: new to bank. There is no prior relationship or account history with the Bank.'
                                if self.case.new_to_bank else 'Not applicable. ' + (state.get('na_reason') or ''))
                elif not draft and not applies(part, self.case):
                    body = dict(status='na', note='Not applicable: new to bank.')
                fill = fills.get(placeholder(part))
                if part['type'] == 'narrative':
                    if fill:
                        self.narrative(fill, part, body, claims, fallback)
                        ends[part['key']] = self.last_span
                    continue
                bound = self.copy.bound.get(key)
                if fill:
                    self.remove_placeholder(fill)
                if part['type'] == 'table':
                    self.table(key, part, body)
                elif part['type'] == 'keyvalue':
                    self.keyvalue(key, body)
                elif part['type'] == 'choice':
                    self.choice(key, part, body)
                elif part['type'] == 'image':
                    self.image(key, part, body)
                if bound is not None:
                    ends[part['key']] = dict(start=bound, end=self.tails.get(id(bound), bound))
            keys = [part['key'] for part in section['parts'] if not part.get('hidden')]
            self.place_blocks(sid, ordered(envelope.get('blocks') or [], [''] + keys), ends, keys, {part['key']: part.get('title') for part in section['parts']})
            for claim in claims:
                if claim.get('kind') == 'ca_input':
                    self.ca_notes.append(f"Section {sid}: {claim['text'].split(chr(10), 1)[-1].strip()} (CA input, not independently verified.)")
            for gap in (draft or {}).get('gaps', []) if state['applicable'] else []:
                self.open_items.append(f'Section {sid}: {gap}')
            if state['applicable'] and not draft:
                self.open_items.append(f'Section {sid}: not drafted.')
        entries = []
        for ref, number in self.numbers.items():
            source = self.manifest['sources'][ref]
            detail = f"{source['filename']}, page {source['page']}"
            if source.get('synthetic'):
                detail += '. SYNTHETIC DEMO DATA'
            elif source.get('origin') == 'public':
                detail += f". Public source: {source.get('url')}, retrieved {str(source.get('retrieved_at'))[:10]}"
            entries.append(f'[{number}] {detail}.')
        self.copy.appendix('Sources', entries or ['No sources cited.'])
        if self.ca_notes:
            self.copy.appendix("Credit analyst's notes", self.ca_notes)
        self.open_items += self.manifest.get('suggested_checks', [])
        self.copy.appendix('Open items for the credit analyst', list(dict.fromkeys(self.open_items)) or ['None recorded.'])
        self.manifest['mapping_gaps'] += [dict(anchor='open item', reason=item) for item in dict.fromkeys(self.open_items)]
        return self.package(self.copy.bytes())

    def package(self, content):
        """Add the pictures to the Word package: media parts, relationships and the JPEG content type."""
        if not self.media:
            return content
        result = BytesIO()
        with ZipFile(BytesIO(content)) as source, ZipFile(result, 'w') as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == 'word/_rels/document.xml.rels':
                    extra = ''.join(f'<Relationship Id="{rel_id}" Type="{IMAGE_REL}" Target="{name}"/>' for rel_id, name, _ in self.media)
                    data = data.decode('utf-8').replace('</Relationships>', extra + '</Relationships>').encode('utf-8')
                elif info.filename == '[Content_Types].xml' and b'Extension="jpg"' not in data:
                    data = data.decode('utf-8').replace('<Default Extension="rels"', '<Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="rels"').encode('utf-8')
                target.writestr(info, data)
            for _, name, data in self.media:
                target.writestr('word/' + name, data)
        return result.getvalue()


def fill(copy, manifest, case, spec, storage_root=None):
    return Filler(copy, manifest, case, spec, storage_root).run()
