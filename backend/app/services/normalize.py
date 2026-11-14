"""Offline source normalization. Text is untrusted data; tables stay indivisible.

Normalized DOCX pages are body blocks, XLSX pages are whole worksheets, CSV is
one whole table, and TXT/EML pages are form-feed separated. None claims Word or
Excel print pagination. PDF pages are always original one-based physical pages.
"""
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path
import csv
import json
import math
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import fitz
import openpyxl

from .intake import MAX_BYTES, archive_guard

VERSION = 'page-evidence-v1'
MAX_PAGES = 2000
MAX_CHARS = 8_000_000
MAX_UNIT_CHARS = 500_000
MAX_CELLS = 200_000
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


@dataclass
class Unit:
    page: int
    text: str
    kind: str
    region: str = 'whole'
    printed_page: str | None = None
    locator: dict = field(default_factory=dict)


@dataclass
class Normalized:
    units: list[Unit] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def add(self, unit):
        if len(self.units) >= MAX_PAGES or sum(len(u.text) for u in self.units) + len(unit.text) > MAX_CHARS:
            raise ValueError('Document exceeds normalization limits; manual review required.')
        if len(unit.text) > MAX_UNIT_CHARS:
            self.gaps.append(f'Page {unit.page}: complete source unit exceeds text limit; review original (not truncated).')
        elif not unit.text.strip():
            self.gaps.append(f'Page {unit.page}: no extractable text; review original or provide a readable copy.')
        else:
            self.units.append(unit)


def _xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unsupported XML declaration')
    return ET.fromstring(raw)


def _text(element):
    return ''.join(e.text or '' if e.tag == W + 't' else '\t' if e.tag == W + 'tab' else '\n'
                   for e in element.iter() if e.tag in {W + 't', W + 'tab', W + 'br', W + 'cr'})


def _table(element):
    # XML grid/cell merges and nested tables are retained for manual checking;
    # no model arithmetic or guessed flattened financial rows.
    return [[{'text': '\n'.join(_text(p) for p in cell.findall(W + 'p')),
              'grid_span': cell.find(W + 'tcPr/' + W + 'gridSpan').get(W + 'val')
                  if cell.find(W + 'tcPr/' + W + 'gridSpan') is not None else '1',
              'vertical_merge': cell.find(W + 'tcPr/' + W + 'vMerge').get(W + 'val', 'continue')
                  if cell.find(W + 'tcPr/' + W + 'vMerge') is not None else None,
              'tables': [_table(t) for t in cell.findall(W + 'tbl')]}
             for cell in row.findall(W + 'tc')] for row in element.findall(W + 'tr')]


def _printed_labels(references):
    labels = {}
    for ref in references:
        pages, printed = ref.get('pdf_pages', []), ref.get('printed_pages', [])
        if len(pages) == len(printed):
            for page, label in zip(pages, printed):
                labels.setdefault(page, set()).add(str(label))
    return {page: next(iter(values)) for page, values in labels.items() if len(values) == 1}


def normalize_document(content, filename, references=()):
    result = Normalized()
    suffix = Path(filename).suffix.lower()
    try:
        if not content or len(content) > MAX_BYTES:
            raise ValueError('Document exceeds byte limit or is empty')
        if suffix == '.pdf':
            if not content.startswith(b'%PDF-'):
                raise ValueError('Content is not PDF')
            with fitz.open(stream=content, filetype='pdf') as pdf:
                if pdf.needs_pass or not 0 < len(pdf) <= MAX_PAGES:
                    raise ValueError('Unreadable, encrypted or oversized PDF')
                labels = _printed_labels(references)
                has_labels = bool(pdf.get_page_labels())
                for page in pdf:
                    number = page.number + 1
                    result.add(Unit(number, page.get_text(sort=True), 'pdf_page',
                        printed_page=labels.get(number, page.get_label() if has_labels else None),
                        locator=dict(format='pdf', page_basis='physical',
                            bbox=list(page.rect * page.derotation_matrix), rotation=page.rotation,
                            coordinate_space='unrotated PyMuPDF page points',
                            table_policy='whole original page; table structure requires manual checking',
                            related_pages=sorted({p for ref in references if number in ref.get('pdf_pages', [])
                                                  for p in ref['pdf_pages'] if 1 <= p <= len(pdf)}))))
        elif suffix == '.docx':
            archive_guard(content, 'word/document.xml')
            with ZipFile(BytesIO(content)) as archive:
                root = _xml(archive.read('word/document.xml'))
                body = root.find(W + 'body')
                blocks = [b for b in body if b.tag in {W + 'p', W + 'tbl'}]
                for number, block in enumerate(blocks, 1):
                    is_table = block.tag == W + 'tbl'
                    text = '\n'.join(_text(p) for p in block.iter(W + 'p')) if is_table else _text(block)
                    if not text.strip():
                        continue
                    result.add(Unit(number, text, 'table' if is_table else 'paragraph', locator=dict(
                        format='docx', page_basis='normalized body block', body_block=number,
                        tables=[_table(block)] if is_table else [])))
                # Headers/footers are separate source units, never silently dropped.
                for name in sorted(n for n in archive.namelist() if n.startswith(('word/header', 'word/footer')) and n.endswith('.xml')):
                    text = '\n'.join(_text(p) for p in _xml(archive.read(name)).iter(W + 'p'))
                    if text.strip():
                        result.add(Unit(len(blocks) + 1, text, 'header_footer', region=name,
                            locator=dict(format='docx', page_basis='normalized package part', part=name)))
        elif suffix == '.xlsx':
            archive_guard(content, 'xl/workbook.xml')
            workbook = openpyxl.load_workbook(BytesIO(content), data_only=False, keep_links=False)
            try:
                total = sum(sheet.max_row * sheet.max_column for sheet in workbook.worksheets)
                if total > MAX_CELLS:
                    raise ValueError('Workbook exceeds cell limit; review whole original')
                for number, sheet in enumerate(workbook.worksheets, 1):
                    rows = [[str(cell.value) if cell.value is not None else '' for cell in row] for row in sheet]
                    formulas = [cell.coordinate for row in sheet for cell in row if cell.data_type == 'f']
                    if formulas:
                        result.gaps.append(f'Sheet {sheet.title}: formulas retained as source text, not recalculated or validated values.')
                    result.add(Unit(number, '\n'.join('\t'.join(row) for row in rows), 'table', locator=dict(
                        format='xlsx', page_basis='normalized worksheet', sheet=sheet.title,
                        cell_range=sheet.calculate_dimension(), rows=rows,
                        merged_ranges=[str(r) for r in sheet.merged_cells.ranges], formula_cells=formulas)))
            finally:
                workbook.close()
        elif suffix in {'.txt', '.csv', '.eml'}:
            if suffix == '.eml':
                message = BytesParser(policy=policy.default).parsebytes(content)
                body = message.get_body(preferencelist=('plain',))
                if body is None:
                    raise ValueError('No plain-text email body; review original')
                text = '\n'.join(f'{name}: {message.get(name, "")}' for name in ('Subject', 'From', 'To', 'Date')) + '\n\n' + body.get_content()
                if any(message.iter_attachments()):
                    result.gaps.append('Email attachments are not indexed; upload required evidence separately.')
            else:
                text = content.decode('utf-8-sig')
            if '\x00' in text:
                raise ValueError('Binary content in text source')
            if suffix == '.csv':
                rows = list(csv.reader(text.splitlines(keepends=True)))
                if sum(len(row) for row in rows) > MAX_CELLS:
                    raise ValueError('CSV exceeds cell limit')
                result.add(Unit(1, text, 'table', locator=dict(format='csv', page_basis='normalized whole table', rows=rows)))
            else:
                for number, part in enumerate(text.split('\f'), 1):
                    result.add(Unit(number, part, 'text', locator=dict(format=suffix[1:], page_basis='normalized form-feed page')))
        else:
            raise ValueError('Unsupported source format; manual review required')
    except Exception as error:
        # A failed parser must not leave apparently complete partial indexing.
        reason = str(error) if isinstance(error, ValueError) else 'Source could not be normalized; manual review required'
        return Normalized(gaps=[reason])
    if not result.units and not result.gaps:
        result.gaps.append('No extractable source text; manual review required.')
    return result


def pdf_region_unit(content, page_number, bbox):
    """Map a split/cropped view to original physical page coordinates.

    Caller must carry this mapping when B09 creates split files. A view never
    replaces its whole-page table context, and printed labels are not inferred.
    """
    if len(bbox) != 4 or any(not math.isfinite(v) for v in bbox):
        raise ValueError('Invalid PDF region')
    with fitz.open(stream=content, filetype='pdf') as pdf:
        if not 1 <= page_number <= len(pdf):
            raise ValueError('Invalid original PDF page')
        page = pdf[page_number - 1]
        rect = fitz.Rect(bbox)
        bounds = page.rect * page.derotation_matrix
        if rect.is_empty or rect.is_infinite or not bounds.contains(rect):
            raise ValueError('Region must be inside the original PDF page')
        coords = [float(v) for v in bbox]
        return Unit(page_number, page.get_text(clip=rect, sort=True), 'pdf_region',
                    region='bbox:' + json.dumps(coords, separators=(',', ':')),
                    locator=dict(format='pdf', page_basis='physical', bbox=coords,
                                 rotation=page.rotation, coordinate_space='unrotated PyMuPDF page points',
                                 table_policy='review whole parent page; region may cut a table'))
