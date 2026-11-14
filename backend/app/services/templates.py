"""Shared template parser, immutable registry and comparison. No model calls.

Locations are XML child-index paths in a hash-pinned package, not Word pages.
Template text and sample values are instructions only, never credit evidence.
"""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import re
from zipfile import ZipFile, BadZipFile

from sqlalchemy import select

from .. import models, schemas as s
from .intake import MAX_BYTES, archive_guard, safe_filename
from .normalize import W, _xml, _text

PARSER_VERSION = 'es-template-v1'
BRACKET = re.compile(r'\[[^\[\]]*\]')
PERIOD = re.compile(r'(?:Projected\s+)?FY\[\s*\]')
DATE = re.compile(r'DD/MM/YYYY|MMMYY')


class TemplateNotFound(ValueError):
    pass


class TemplateIntegrityError(ValueError):
    pass


def normalized(text):
    return ' '.join(text.replace('ⓘ', '').split()).casefold()


def paragraph_text(paragraph):
    # w:tab inside pPr/tabs is a tab-stop definition, not visible text.
    return ''.join(_text(run) for run in paragraph.iter(W + 'r'))


def _value(element, name):
    node = element.find(name)
    return node.get(W + 'val') if node is not None else None


def _on(element):
    return element is not None and element.get(W + 'val', '1').lower() not in {'0', 'false', 'off'}


class Styles:
    def __init__(self, root):
        self.styles = {x.get(W + 'styleId'): x for x in root.findall(W + 'style')}
        self.default_italic = _on(root.find(W + 'docDefaults/' + W + 'rPrDefault/' + W + 'rPr/' + W + 'i'))
        self.default_paragraph = next((key for key, x in self.styles.items()
            if x.get(W + 'type') == 'paragraph' and x.get(W + 'default') == '1'), None)

    def chain(self, key):
        seen = set()
        chain = []
        while key in self.styles:
            if key in seen:
                raise ValueError('Cyclic Word style inheritance')
            seen.add(key)
            style = self.styles[key]
            chain.append(style)
            key = _value(style, W + 'basedOn')
        return list(reversed(chain))

    def heading(self, paragraph, expected):
        key = _value(paragraph, W + 'pPr/' + W + 'pStyle') or self.default_paragraph
        return any(normalized(_value(style, W + 'name') or '') == normalized(expected) for style in self.chain(key))

    def italic(self, paragraph, run, table_style=None):
        value = self.default_italic
        keys = [table_style, _value(paragraph, W + 'pPr/' + W + 'pStyle') or self.default_paragraph,
                _value(run, W + 'rPr/' + W + 'rStyle')]
        for key in keys:
            # Italic is a toggle in a style hierarchy; false leaves it unchanged.
            for style in self.chain(key):
                if _on(style.find(W + 'rPr/' + W + 'i')):
                    value = not value
        direct = run.find(W + 'rPr/' + W + 'i')
        return _on(direct) if direct is not None else value


def _package(content):
    if not content or len(content) > MAX_BYTES:
        raise ValueError('Template is empty or exceeds byte limit')
    try:
        archive_guard(content, 'word/document.xml')
        with ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicate package parts are unsupported')
            for info in archive.infolist():
                if info.flag_bits & 1:
                    raise ValueError('Encrypted templates are unsupported')
            root = _xml(archive.read('word/document.xml'))
            styles = Styles(_xml(archive.read('word/styles.xml')))
            content_types = archive.read('[Content_Types].xml')
            if b'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml' not in content_types:
                raise ValueError('Expected an ordinary Word DOCX template')
            extras = {name: _xml(archive.read(name)) for name in names
                      if name.startswith(('word/header', 'word/footer')) and name.endswith('.xml')}
            return root, styles, extras
    except (BadZipFile, KeyError, OSError) as error:
        raise ValueError('Unreadable Word DOCX template') from error


def parse_template(content, config):
    """Return complete physical inventory plus unambiguous configured bindings/gaps."""
    try:
        root, styles, extras = _package(content)
    except Exception as error:
        # XML parse failures are invalid input, not a partly successful mapping.
        if isinstance(error, ValueError):
            raise
        raise ValueError('Malformed Word template XML') from error
    body = root.find(W + 'body')
    if body is None:
        raise ValueError('Word template has no body')
    if sum(1 for _ in root.iter()) > 200_000:
        raise ValueError('Template XML exceeds element limit')
    result = dict(parser_version=PARSER_VERSION, content_hash=sha256(content).hexdigest(),
                  mapping_hash=sha256(json.dumps(config.model_dump(mode='json', exclude_unset=True),
                      sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                  location_basis='XML child indices in original hash-pinned package; not print pages',
                  sections=[], tables=[], fill_points=[], bindings={}, gaps=[],
                  template_text_policy='guidance and sample labels only; not evidence')
    gaps = result['gaps']
    expected = {x.id: x for x in config.sections}
    section = 0
    headings = []
    wrappers = {}

    def gap(section_id, anchor, reason):
        gaps.append(f'Section {section_id} / {anchor}: {reason}')

    def visit(element, path, sid, table=None, cell=None):
        if len(path) > 80:
            raise ValueError('Template nesting exceeds supported limit')
        locator = dict(part='word/document.xml', path=path)
        if element.tag == W + 'tc' and table is not None:
            table['rows'][cell['row']][cell['cell']]['locator'] = locator
        if element.tag == W + 'tbl':
            rows = []
            for ri, row in enumerate(element.findall(W + 'tr')):
                cells = []
                column = int(_value(row, W + 'trPr/' + W + 'gridBefore') or 0)
                for ci, tc in enumerate(row.findall(W + 'tc')):
                    span = int(_value(tc, W + 'tcPr/' + W + 'gridSpan') or 1)
                    cells.append(dict(row=ri, cell=ci, grid_column=column, grid_span=span,
                        vertical_merge=_value(tc, W + 'tcPr/' + W + 'vMerge') or
                            ('continue' if tc.find(W + 'tcPr/' + W + 'vMerge') is not None else None),
                        text='\n'.join(paragraph_text(p) for p in tc.findall(W + 'p'))))
                    column += span
                rows.append(cells)
            table = dict(id='table:' + '.'.join(map(str, path)), section_id=sid,
                         locator=locator, parent_table=table['id'] if table else None, rows=rows,
                         headers=[c['text'] for c in rows[0]] if rows else [])
            table['style_id'] = _value(element, W + 'tblPr/' + W + 'tblStyle')
            for style in styles.chain(table['style_id']):
                if any(condition.find(W + 'rPr/' + W + 'i') is not None for condition in style.findall(W + 'tblStylePr')):
                    gap(sid, table['id'], 'conditional table-style italic formatting needs manual mapping')
            result['tables'].append(table)
            if table['parent_table'] is None and sid:
                wrappers.setdefault(sid, []).append(table)
        if element.tag == W + 'p':
            text = paragraph_text(element)
            runs = list(element.iter(W + 'r'))
            run_text = ''.join(_text(run) for run in runs)
            italics = [styles.italic(element, run, table.get('style_id') if table else None) for run in runs for _ in _text(run)]
            if text != run_text:
                gap(sid, str(path), 'unsupported paragraph text container')
            matches = [(m, 'period') for m in PERIOD.finditer(text)]
            period_ranges = [(m.start(), m.end()) for m, _ in matches]
            for match in BRACKET.finditer(text):
                if any(a <= match.start() < b for a, b in period_ranges):
                    continue
                kind = 'placeholder' if all(italics[match.start():match.end()]) and len(italics) >= match.end() else 'unmapped_bracket'
                matches.append((match, kind))
                if kind == 'unmapped_bracket':
                    gap(sid, match.group(), 'bracketed text is not effectively italic; manual mapping required')
            matches += [(m, 'date') for m in DATE.finditer(text)
                        if not any(a.start() <= m.start() < a.end() for a, _ in matches)]
            matches += [(m, 'checkbox') for m in re.finditer('[☐☑☒]', text)]
            for occurrence, (match, kind) in enumerate(sorted(matches, key=lambda item: item[0].start()), 1):
                offsets, start = [], 0
                for index, run in enumerate(runs):
                    end = start + len(_text(run))
                    if start < match.end() and end > match.start():
                        offsets.append(dict(run=index, start=max(0, match.start()-start), end=min(end-start, match.end()-start)))
                    start = end
                result['fill_points'].append(dict(id=f's{sid}:' + '.'.join(map(str, path)) + f':{occurrence}',
                    section_id=sid, table_id=table['id'] if table else None, cell=cell,
                    kind=kind, text=match.group(), locator=locator, start=match.start(), end=match.end(), runs=offsets))
        if element.tag in {W+'sdt', W+'altChunk', W+'txbxContent', W+'ins', W+'del'}:
            gap(sid, str(path), 'unsupported content control, embedded content or tracked change; manual mapping required')
        # Walk physical XML cells once: merged grid aliases never duplicate targets.
        ri = ci = 0
        for index, child in enumerate(element):
            next_cell = cell
            if child.tag == W + 'tr':
                next_cell = dict(row=ri, cell=None)
                ri += 1
            elif child.tag == W + 'tc':
                next_cell = dict(row=cell['row'], cell=ci)
                ci += 1
            visit(child, path + [index], sid, table, next_cell)

    for index, block in enumerate(body):
        if block.tag == W + 'p' and styles.heading(block, config.mapping.heading_style):
            text = paragraph_text(block)
            match = re.fullmatch(r'\s*(\d+)\s*[.)]\s*(.*?)\s*', text)
            section = int(match[1]) if match else -1
            headings.append(dict(section_id=section, text=text, title=match[2] if match else text,
                                 locator=dict(part='word/document.xml', path=[index])))
        visit(block, [index], section)
    for sid, definition in expected.items():
        found = [h for h in headings if h['section_id'] == sid]
        valid = len(found) == 1 and normalized(found[0]['title']) == normalized(definition.name)
        if not valid:
            gap(sid, 'heading', 'missing, duplicate or mismatched numbered Heading 1: ' + definition.name)
        result['sections'].append(dict(section_id=sid, name=definition.name, headings=found, mapped=valid))
        outer = wrappers.get(sid, [])
        if len(outer) != 1:
            gap(sid, 'wrapper', 'expected one section wrapper table; found ' + str(len(outer)))
        elif valid:
            result['bindings'][f's{sid}.wrapper'] = outer[0]['id']
    for heading in headings:
        if heading['section_id'] not in expected:
            gap(heading['section_id'], 'heading', 'unknown or malformed numbered Heading 1')
    result['headings'] = headings  # includes unknown IDs for exact diff attribution
    if [h['section_id'] for h in headings] != list(expected):
        gap(0, 'section order', 'headings do not match configured section order')

    mapped_tables = set(result['bindings'].values())
    for anchor in config.table_anchors:
        candidates = [t for t in result['tables'] if t['section_id'] == anchor.section_id
                      and [normalized(h) for h in t['headers']] == [normalized(h) for h in anchor.headers]]
        name = f's{anchor.section_id}.{anchor.id}'
        if len(candidates) != 1:
            gap(anchor.section_id, anchor.id, f'expected unique ordered table headers; found {len(candidates)}')
            continue
        table = candidates[0]
        labels = [normalized(row[0]['text']) if row else '' for row in table['rows'][1:]]
        if labels != [normalized(label) for label in anchor.row_labels]:
            gap(anchor.section_id, anchor.id, 'missing, duplicate or changed row labels; row mapping withheld')
            continue
        if anchor.cell_spans and [[c['grid_span'] for c in row] for row in table['rows']] != anchor.cell_spans:
            gap(anchor.section_id, anchor.id, 'changed cell count or merged-cell structure; cell mapping withheld')
            continue
        if anchor.section_id and not next(x['mapped'] for x in result['sections'] if x['section_id'] == anchor.section_id):
            gap(anchor.section_id, anchor.id, 'section heading unresolved; table mapping withheld')
            continue
        result['bindings'][name] = table['id']
        mapped_tables.add(table['id'])
        table.update(anchor=name, repeat=anchor.repeat, kind=anchor.kind, source_policy=anchor.source_policy)
        # All cells are explicit targets in the configured table, including dates,
        # blanks, totals and sample defaults. Roles do not authorize using samples.
        for row in table['rows']:
            for cell in row:
                cell['key'] = f"{name}.r{cell['row']}.c{cell['cell']}"
                cell['row_label'] = row[0]['text'] if row else ''
                cell['column_header'] = table['headers'][cell['grid_column']] if cell['grid_column'] < len(table['headers']) else None
                if anchor.kind == 'chart':
                    cell['role'] = 'value'
                elif anchor.kind in {'key_value', 'checkboxes'}:
                    cell['role'] = 'label' if cell['cell'] == 0 else 'value'
                else:
                    cell['role'] = 'header' if cell['row'] == 0 else 'label' if anchor.kind == 'matrix' and cell['cell'] == 0 else 'value'
                cell['requires_sourced_value'] = cell['role'] == 'value'
    for table in result['tables']:
        if table['id'] not in mapped_tables:
            gap(table['section_id'], table['id'], 'table has no unambiguous configured mapping')
    for anchor in config.narrative_anchors:
        matches = [f for f in result['fill_points'] if f['section_id'] == anchor.section_id
                   and normalized(f['text']) == normalized(anchor.text)
                   and f['kind'] == 'placeholder' and f['table_id'] == result['bindings'].get(f's{anchor.section_id}.wrapper')]
        if len(matches) != 1:
            gap(anchor.section_id, anchor.text, 'missing or duplicate narrative placeholder')
    for fill in result['fill_points']:
        fill['mapped'] = fill['table_id'] in mapped_tables and fill['kind'] != 'unmapped_bracket'
        if (fill['kind'] == 'placeholder'
                and fill['table_id'] == result['bindings'].get(f"s{fill['section_id']}.wrapper")
                and not any(a.section_id == fill['section_id'] and normalized(a.text) == normalized(fill['text'])
                            for a in config.narrative_anchors)):
            fill['mapped'] = False
        if not fill['mapped']:
            gap(fill['section_id'], fill['id'], 'fill point has no unambiguous mapped table')
    # Header/footer text is retained verbatim. Dynamic fill here needs a future
    # explicit mapping; fields such as PAGE are preserved rather than filled.
    result['header_footer_text'] = {name: _text(root) for name, root in extras.items()}
    for name, extra in extras.items():
        if BRACKET.search(_text(extra)) or DATE.search(_text(extra)) or '☐' in _text(extra):
            gap(0, name, 'header/footer fill point needs explicit mapping')
    result['gaps'] = list(dict.fromkeys(gaps))
    result['complete'] = not result['gaps']
    return result


class TemplateRegistry:
    """Caller owns the transaction; serialize writes with BEGIN IMMEDIATE."""
    def __init__(self, repository, storage_root):
        self.repo = repository
        self.root = Path(storage_root).resolve()

    def versions(self, team_id):
        self.repo.config_loader(team_id)
        rows = self.repo.session.scalars(select(models.TemplateVersion).where(
            models.TemplateVersion.team_id == team_id).order_by(models.TemplateVersion.created_at, models.TemplateVersion.id))
        return [self.repo.get(s.TemplateVersion, row.id) for row in rows]

    def get(self, team_id, version_id):
        try:
            version = self.repo.get(s.TemplateVersion, version_id)
        except ValueError as error:
            raise TemplateNotFound('Template version not found') from error
        if version.team_id != team_id:
            raise TemplateNotFound('Template version not found for team')
        return version

    def content(self, team_id, version_id):
        version = self.get(team_id, version_id)
        path = Path(version.storage_path)
        expected = self.root / f'{version.content_hash}.docx'
        if path != expected or path.is_symlink() or path.resolve() != expected:
            raise TemplateIntegrityError('Template storage boundary mismatch')
        try:
            if path.stat().st_size > MAX_BYTES:
                raise TemplateIntegrityError('Stored template exceeds byte limit')
            content = path.read_bytes()
        except OSError as error:
            raise TemplateIntegrityError('Stored template bytes unavailable') from error
        if sha256(content).hexdigest() != version.content_hash:
            raise TemplateIntegrityError('Stored template hash mismatch')
        return content

    def active(self, team_id):
        rows = list(self.repo.session.scalars(select(models.TemplateActivation).where(
            models.TemplateActivation.team_id == team_id)))
        if not rows:
            return None
        # Follow the append-only pointer chain, avoiding equal-timestamp ordering.
        current = None
        seen = set()
        for _ in range(len(rows)):
            links = [r for r in rows if r.expected_previous_id == current and r.id not in seen]
            if len(links) != 1:
                raise TemplateIntegrityError('Ambiguous template activation history')
            seen.add(links[0].id)
            current = links[0].template_version_id
        return self.get(team_id, current)

    def compare(self, team_id, version_id, expected_active_id=None):
        from .template_diff import CLASSIFIER_VERSION, compare_packages

        candidate = self.get(team_id, version_id)
        baseline = self.active(team_id)
        if baseline is None:
            raise TemplateIntegrityError('No active template to compare against')
        if expected_active_id is not None and baseline.id != expected_active_id:
            raise TemplateIntegrityError('Active template changed; compare against the current active version')
        if candidate.id == baseline.id:
            raise ValueError('Comparison requires an inactive candidate')
        # Reparse both hash-verified packages with exactly the same configuration.
        # Stored historical maps are never overwritten by a newer parser/config.
        config = self.repo.config_loader(team_id).template
        before_bytes = self.content(team_id, baseline.id)
        after_bytes = self.content(team_id, candidate.id)
        before_map = parse_template(before_bytes, config)
        after_map = parse_template(after_bytes, config)
        changes = compare_packages(before_bytes, after_bytes, before_map, after_map, team_id)
        for version, parsed in ((baseline, before_map), (candidate, after_map)):
            if (version.parsed_map.get('mapping_hash'), version.parsed_map.get('parser_version')) != (
                    parsed['mapping_hash'], parsed['parser_version']):
                changes.append(dict(number=len(changes)+1, category='code', section_id=None,
                    anchor='comparison configuration', before_location=None, after_location=None,
                    before={key: version.parsed_map.get(key) for key in ('mapping_hash', 'parser_version')},
                    after={key: parsed[key] for key in ('mapping_hash', 'parser_version')},
                    reason=f'{version.display_version} was registered under different parser/mapping rules; IT revalidation required.',
                    affected_files=[f'config/teams/{team_id}/template.yaml', 'backend/app/services/templates.py']))
        category = next((c for c in ('code', 'prompt', 'formatting') if any(x['category'] == c for x in changes)), 'unchanged')
        def descriptor(version, parsed):
            return dict(id=version.id, display_version=version.display_version,
                        content_hash=version.content_hash, parse_gaps=parsed['gaps'], complete=parsed['complete'])
        report = dict(classifier_version=CLASSIFIER_VERSION, parser_version=PARSER_VERSION,
            mapping_hash=before_map['mapping_hash'], baseline=descriptor(baseline, before_map),
            candidate=descriptor(candidate, after_map), changes=changes, category=category,
            counts={c: sum(x['category'] == c for x in changes) for c in ('formatting', 'prompt', 'code')},
            formatting_only=category == 'formatting' and before_map['complete'] and after_map['complete'],
            requires_it=category in {'code', 'prompt'} or not before_map['complete'] or not after_map['complete'],
            activation_available=False,
            activation_note='All candidates remain inactive. Admin confirmation/activation is B23; prompt/code changes require IT review.')
        # Stable identity deduplicates retries and binds every change to both
        # immutable versions and the comparison rules; no mutable active pointer.
        comparison_id = sha256(json.dumps(report, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        existing = self.repo.session.get(models.TemplateComparison, comparison_id)
        if existing:
            return self.repo.get(s.TemplateComparison, comparison_id)
        return self.repo.save(s.TemplateComparison(id=comparison_id, team_id=team_id,
            template_version_id=candidate.id, baseline_version_id=baseline.id, report=report))

    def comparison(self, team_id, version_id, comparison_id):
        self.get(team_id, version_id)
        try:
            comparison = self.repo.get(s.TemplateComparison, comparison_id)
        except ValueError as error:
            raise TemplateNotFound('Template comparison not found') from error
        if comparison.team_id != team_id or comparison.template_version_id != version_id:
            raise TemplateNotFound('Template comparison not found for candidate/team')
        return comparison

    def register(self, team_id, display_version, filename, content, parent_id=None):
        safe_filename(filename)
        if Path(filename).suffix.lower() != '.docx':
            raise ValueError('Template must be a DOCX file')
        if not re.fullmatch(r'v\d+(?:\.\d+){1,3}', display_version):
            raise ValueError('Template display version must be v followed by numeric components')
        config = self.repo.config_loader(team_id).template
        if parent_id:
            self.get(team_id, parent_id)
        digest = sha256(content).hexdigest()
        for old in self.versions(team_id):
            if old.display_version == display_version:
                if old.content_hash != digest:
                    raise ValueError('Display version already registered with different bytes')
                self.content(team_id, old.id)
                return old
        parsed = parse_template(content, config)
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f'{digest}.docx'
        if path.is_symlink() or path.resolve().parent != self.root or self.root.is_symlink():
            raise TemplateIntegrityError('Template storage symlink rejected')
        if path.exists():
            if path.read_bytes() != content:
                raise TemplateIntegrityError('Stored template hash collision or corruption')
        else:
            with path.open('xb') as stream:
                stream.write(content)
        return self.repo.save(s.TemplateVersion(team_id=team_id, display_version=display_version,
            content_hash=digest, storage_path=str(path), parent_id=parent_id,
            parsed_map=parsed, parse_gaps=parsed['gaps'], status='mapped' if parsed['complete'] else 'review required'))

    def seed_owner_templates(self, team_id, project_root):
        """Operator-only bootstrap authorized by task 0011; no public activation API.

        Existing activation history is never changed on restart. Later owner
        files become candidates; G3 owns confirmation/diff for later activation.
        """
        config = self.repo.config_loader(team_id).template
        project_root = Path(project_root).resolve()
        default = project_root / config.default_template
        match = re.fullmatch(r'(.*)_v(\d+(?:\.\d+){1,3})\.docx', default.name)
        if not match or default.is_symlink() or not default.resolve().is_relative_to(project_root / 'templates'):
            raise ValueError('Default template must be an owner templates/ versioned DOCX')
        candidates = []
        for path in default.parent.glob(match[1] + '_v*.docx'):
            found = re.fullmatch(re.escape(match[1]) + r'_(v\d+(?:\.\d+){1,3})\.docx', path.name)
            if found:
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
                    raise ValueError('Owner template must be a bounded regular file')
                candidates.append((tuple(map(int, found[1][1:].split('.'))), found[1], path))
        if not default.is_file():
            raise ValueError('Default owner template unavailable')
        had_active = self.active(team_id)
        versions = []
        parent = None
        for _, display, path in sorted(candidates):
            version = self.register(team_id, display, path.name, path.read_bytes(), parent)
            versions.append(version)
            parent = version.id
        if not had_active:
            for version in versions:
                # Initial seeding is explicitly authorized; mapping gaps remain
                # visible and block complete export even on an active seed.
                previous = self.active(team_id)
                self.repo.save(s.TemplateActivation(team_id=team_id, template_version_id=version.id,
                    expected_previous_id=previous.id if previous else None,
                    actor='task-0011 owner-template bootstrap', role='template admin'))
        return versions
