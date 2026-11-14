"""Conservative, offline DOCX comparison. No template text is executed.

Compare expanded XML names, not ZIP timestamps, prefixes or serialization order.
Every changed package part is inspected; unrecognised changes require code review.
Locations use the shared parser's body-relative indices, never printed pages.
"""
from difflib import SequenceMatcher
from hashlib import sha256
from io import BytesIO
import json
import re
from zipfile import ZipFile

from .normalize import W, _xml
from .templates import paragraph_text

CLASSIFIER_VERSION = 'es-template-diff-v1'
# Italics, styles/inheritance, field instructions, grid spans and merge structure
# deliberately do not appear here: they can change the export mapping/meaning.
VISUAL = {W + name for name in (
    'rFonts', 'color', 'sz', 'szCs', 'b', 'bCs', 'u', 'strike', 'dstrike',
    'highlight', 'shd', 'spacing', 'ind', 'jc', 'keepNext', 'keepLines',
    'pageBreakBefore', 'widowControl', 'contextualSpacing',
    'pBdr', 'tblBorders', 'tcBorders', 'top', 'left', 'bottom', 'right',
    'insideH', 'insideV', 'start', 'end', 'between', 'bar', 'tblW', 'tcW',
    'tblCellMar', 'tcMar', 'tblInd', 'tblLayout', 'trHeight', 'cantSplit',
    'pgSz', 'pgMar', 'cols', 'col', 'docGrid', 'vAlign',
)}
PROPERTY_CONTAINERS = {W + name for name in ('rPr', 'pPr', 'tblPr', 'tcPr', 'trPr', 'sectPr')}
CALCULATION = re.compile(r'\b(?:calculat\w*|comput\w*|formula\w*|sum|ratio|headroom)\b|[=+*/<>\d]', re.I)


def _value(node):
    if node is None:
        return None
    return (node.tag, tuple(sorted(node.attrib.items())), node.text or '',
            tuple(_value(child) for child in node))


def _display(node):
    if node is None:
        return None
    return dict(tag=node.tag, attributes=dict(sorted(node.attrib.items())),
                text=node.text or '', children=[_display(child) for child in node])


def _visual(node):
    return node is None or (node.tag in VISUAL | PROPERTY_CONTAINERS
        and not (node.text or '').strip() and all(_visual(child) for child in node))


def _parts(content):
    with ZipFile(BytesIO(content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def compare_packages(before_bytes, after_bytes, before_map, after_map, team_id):
    """Return deterministic changes, preserving complete before/after values."""
    changes = []
    before_parts, after_parts = _parts(before_bytes), _parts(after_bytes)
    body_indices = {id(report): next(i for i, node in enumerate(_xml(parts['word/document.xml']))
                                    if node.tag == W+'body')
                    for report, parts in ((before_map, before_parts), (after_map, after_parts))}

    def context(report, part, path):
        if part != 'word/document.xml' or not path or path[0] != body_indices[id(report)]:
            return dict(section_id=None, anchor=part, locator=dict(part=part, path=path, basis='part-root'))
        # Shared parser paths start inside document/body.
        body_path = path[1:]
        headings = report['headings']
        previous = [h for h in headings if body_path and h['locator']['path'][0] <= body_path[0]]
        sid = max(previous, key=lambda h: h['locator']['path'][0])['section_id'] if previous else None
        tables = [t for t in report['tables'] if body_path[:len(t['locator']['path'])] == t['locator']['path']]
        table = max(tables, key=lambda t: len(t['locator']['path'])) if tables else None
        wrapper = table and table['id'] == report['bindings'].get(f"s{table['section_id']}.wrapper")
        return dict(section_id=table['section_id'] if table else sid,
                    anchor=(table.get('anchor', f"s{table['section_id']}.wrapper" if wrapper else table['id']) if table
                            else f's{sid}.heading' if previous and body_path[:1] == previous[-1]['locator']['path'] else part),
                    locator=dict(part=part, path=body_path, basis='document-body'))

    def narrative(report, path):
        # A prompt edit must be in an existing mapped wrapper narrative, not in
        # a computed/table cell or an arbitrary added paragraph.
        if not path or path[0] != body_indices[id(report)]:
            return False
        return any(f['kind'] == 'placeholder' and f['mapped']
            and f['locator']['path'] == path[1:]
            and f['table_id'] == report['bindings'].get(f"s{f['section_id']}.wrapper")
            for f in report['fill_points'])

    def emit(part, old, new, old_path, new_path, category, reason, before=None, after=None):
        old_context = context(before_map, part, old_path) if old is not None else None
        new_context = context(after_map, part, new_path) if new is not None else None
        selected = old_context or new_context
        files = [f'config/teams/{team_id}/template.yaml', 'backend/app/services/templates.py',
                 'backend/app/exports/mapping.py', 'tests/test_templates.py'] if category == 'code' else (
                [f'config/teams/{team_id}/prompts.yaml', f'config/teams/{team_id}/template.yaml',
                 'backend/app/services/drafting.py'] if category == 'prompt' else [])
        changes.append(dict(category=category, reason=reason, section_id=selected['section_id'],
            anchor=selected['anchor'], before_location=old_context, after_location=new_context,
            before=_display(old) if before is None else before,
            after=_display(new) if after is None else after, affected_files=files))

    def walk(part, old, new, old_path, new_path, prompt=False):
        if _value(old) == _value(new):
            return
        if _visual(old) and _visual(new):
            emit(part, old, new, old_path, new_path, 'formatting',
                 'Only allowlisted visual Word properties changed; mapping and text are checked separately.')
            return
        if old is None or new is None or old.tag != new.tag:
            emit(part, old, new, old_path, new_path, 'code',
                 'Content or structure was added, removed or replaced; mapping/export support requires IT review.')
            return
        if old.tag == W + 'p':
            prompt = (part == 'word/document.xml' and narrative(before_map, old_path)
                      and bool(re.fullmatch(r'\s*\[[^\[\]]+\]\s*', paragraph_text(new)))
                      and not CALCULATION.search(paragraph_text(new)))
        if old.attrib != new.attrib:
            emit(part, old, new, old_path, new_path, 'code',
                 'A non-visual XML attribute changed; its mapping or behavior is not safely inferred.',
                 before=dict(old.attrib), after=dict(new.attrib))
        if (old.text or '') != (new.text or ''):
            category = 'prompt' if prompt and old.tag == W + 't' else 'code'
            reason = ('Existing narrative guidance changed; review drafting instructions and its configured fill anchor.'
                      if category == 'prompt' else
                      'A heading, table label, field, sample value or unsupported instruction changed; review mapping and code.')
            emit(part, old, new, old_path, new_path, category, reason, before=old.text or '', after=new.text or '')
        old_children, new_children = list(old), list(new)
        matcher = SequenceMatcher(None, [_value(c) for c in old_children], [_value(c) for c in new_children], autojunk=False)
        for operation, i, j, k, l in matcher.get_opcodes():
            if operation == 'equal':
                continue
            # Match unchanged siblings first so section/table insertion does not
            # turn every subsequent XML locator into a spurious edit.
            for offset in range(max(j-i, l-k)):
                a, b = i + offset, k + offset
                walk(part, old_children[a] if a < j else None, new_children[b] if b < l else None,
                     old_path + [a], new_path + [b], prompt)

    for part in sorted(before_parts.keys() | after_parts.keys()):
        old, new = before_parts.get(part), after_parts.get(part)
        if old == new:
            continue
        supported = part in {'word/document.xml', 'word/styles.xml'} or (
            part.startswith(('word/header', 'word/footer')) and part.endswith('.xml'))
        if supported and old is not None and new is not None:
            walk(part, _xml(old), _xml(new), [], [])
        else:
            # Includes relationships, settings, media, fields in ancillary parts,
            # added/deleted parts and opaque content: never call these formatting.
            def descriptor(value):
                if value is None:
                    return None
                return dict(sha256=sha256(value).hexdigest(), bytes=len(value),
                            text=value.decode('utf-8', errors='replace') if part.endswith(('.xml', '.rels')) else None)
            changes.append(dict(category='code', section_id=None, anchor=part,
                before_location=dict(part=part), after_location=dict(part=part),
                before=descriptor(old), after=descriptor(new),
                reason='Package part changed outside supported visual properties; IT must review content, relationships or behavior.',
                affected_files=['backend/app/services/templates.py', 'backend/app/exports/word.py']))
    for index, change in enumerate(changes, 1):
        change['number'] = index
    return changes


def it_change_list(comparison):
    report = comparison.report
    lines = ['WB Credit template IT change list',
        f'Comparison: {comparison.id}', f'Created (UTC): {comparison.created_at.isoformat()}',
        f'Team: {comparison.team_id}',
        f'Baseline: {comparison.baseline_version_id} ({report["baseline"]["display_version"]}) / SHA-256 {report["baseline"]["content_hash"]}',
        f'Candidate: {comparison.template_version_id} ({report["candidate"]["display_version"]}) / SHA-256 {report["candidate"]["content_hash"]}',
        f'Classifier: {report["classifier_version"]}; parser: {report["parser_version"]}; mapping: {report["mapping_hash"]}',
        f'Overall classification: {report["category"]}; candidate remains inactive.',
        'This is a saved comparison; recompare against the active template before any future activation.',
        'Locations are XML paths in the named hash-pinned packages, not Word pages.',
        'Template wording is guidance, never credit evidence. No prompts or code have been changed.', '']
    items = [c for c in report['changes'] if c['category'] != 'formatting']
    if not items:
        lines.append('No prompt or code change items.')
    for change in items:
        lines.extend([f'{change["number"]}. {change["category"]} / section {change["section_id"]} / {change["anchor"]}',
            'Reason: ' + change['reason'],
            'Before location: ' + json.dumps(change['before_location'], ensure_ascii=False),
            'After location: ' + json.dumps(change['after_location'], ensure_ascii=False),
            'Before: ' + json.dumps(change['before'], ensure_ascii=False),
            'After: ' + json.dumps(change['after'], ensure_ascii=False),
            'Files to review: ' + ', '.join(change['affected_files']), ''])
    for side in ('baseline', 'candidate'):
        lines.append(f'{side.title()} mapping gaps:')
        lines.extend(report[side]['parse_gaps'] or ['None'])
    return '\n'.join(lines) + '\n'
