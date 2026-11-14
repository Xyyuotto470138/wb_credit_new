"""Live drafting for teams with an ES specification.

The model writes wording and copies figures, each tied to a source page. Python then checks every
citation and every figure against the cited page, converts units, computes derived columns and
totals, and fills the parts that come from structured workbooks. Anything that fails a check is
withheld and recorded as a gap; it is never repaired by guessing.
"""
from decimal import Decimal
import hashlib
import json
import re

from .. import schemas as s
from ..llm import live
from ..llm.client import clean_json_response
from ..services.gaps import current_documents
from ..services.readiness import content_hash
from . import compute
from .numbers import SCALES, canon, evaluate, figure_in, fmt, parse_printed, squash, unsupported_figures
from .spec import applies, column_names, column_spec, section_parts

LABEL = 'AI DRAFT. Live model output checked against cited sources. For credit analyst review.'
VERSION = 'es2-drafting-v1'
SMALL_DOCUMENT_PAGES = 12
LARGE_PAGE_LIMIT = 40
PAGE_CHARS = 7000
PARTS_PER_REQUEST = 6

SYSTEM = """You draft one section of a bank Executive Summary (a wholesale credit paper) for a credit analyst, who reviews and confirms it. Credit decisions are made by the bank's approving officers, never by you.

Rules
1. Use only the evidence pages supplied. Each paragraph, table row, field and answer must cite the evidence ids it rests on, for example ["E4"]. If a prior section is supplied you may also cite it as "S7". If tables computed by the system are supplied, you may use their figures exactly as shown and cite them as "C".
2. Never calculate, round, convert, annualise or infer a figure. Copy figures exactly as printed. In wording, use only figures that appear on the pages you cite, written the same way.
3. For a cell that asks for a figure, give "raw" (the figure exactly as printed, for example "5,864,836" or "(117,305)"), "scale" (unit, thousand, million or billion: the unit the source states for that figure), "q" (the exact source line that contains the figure, copied character for character) and "c" (citations). Totals, changes, percentages of total, headroom and ratios marked as computed are calculated by the system: leave them out.
4. If the evidence does not support a field, leave it out and add one line to "gaps" naming what is missing. A missing document is a gap, never a fact. Do not fill a field with a guess or with general knowledge.
5. Documents marked SYNTHETIC DEMO DATA are the deal papers for this demonstration case. Use them as the deal's inputs.
6. Decision-safe wording: do not state or imply that the facility is approved or will be approved, and do not form a recommendation of your own. Where a section asks for a recommendation, word the credit analyst's stated position.
7. Style: concise professional credit-paper English, British spelling, plain sentences, no marketing language, no bullet symbols, no dashes used as punctuation. One to three short paragraphs per narrative part unless the guidance needs more.
8. Table cells are short: a name, a date, a rating, or a phrase of a few words. Put explanation in a Remarks, Comments or Description column if the table has one, otherwise in a narrative part. Use the borrower's plain name in a Borrower column.
9. "gaps" is only for information this section needs and the evidence does not hold: at most five lines, one sentence each. Do not use it for commentary, caveats or notes about your own formatting.
10. For a borrower that is new to the bank, existing limits and drawn amounts are entered by the system as nil: leave those cells out. Follow a column's hint where one is given.
11. If a figure cell does not apply to a row (for example a value for an assignment of rental proceeds), give {"v": "n.a."} for it.

Output: one JSON object and nothing else, in this shape:
{"parts": {"<part key>": <content>}, "gaps": ["..."]}
Content by part type:
- narrative: {"paragraphs": [{"text": "...", "cites": ["E1"]}]}
- keyvalue: {"rows": {"<row label>": {"v": "...", "c": ["E1"]}}}
- choice: {"answers": [{"selected": "<one of the options>", "note": "<short reason>", "c": ["E1"]}]} with one answer per question, in order
- table with fixed rows: {"rows": {"<row label>": {"<column>": <cell>}}}
- table with repeating rows: {"rows": [{"<column>": <cell>}]}
- facility table: {"facilities": ["<facility name>"], "rows": {"<row label>": [<cell for each facility, in order>]}}
- table with periods: add "periods": ["FY2024", "FY2025"] (older first, as labelled in the source) and, if the part asks for an interim column and one is published, "interim": "<label, for example 9M 2026>". Use those labels and "interim" as the column keys.
A text cell is {"v": "...", "c": ["E1"]}. A figure cell is {"raw": "...", "scale": "...", "q": "...", "c": ["E1"]}."""


def identity(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


class Sources:
    """Every indexed page of the case's current documents, with short labels for the prompt."""

    def __init__(self, service, case):
        self.service, self.case = service, case
        self.pages, self.gaps = [], []
        for doc in current_documents(service.repo.list_for_case(s.Document, case.id), case):
            try:
                index = service.evidence.index_document(case.id, doc.id)
            except Exception as error:  # integrity or format failure: the document is withheld, with a named gap
                self.gaps.append(f'{doc.original_filename}: could not be read ({error}); withheld.')
                continue
            refs = [service.repo.get(s.Evidence, ref) for ref in index.evidence_ids]
            whole = [e for e in refs if (e.region or 'whole') == 'whole' or not e.region]
            for evidence in sorted(whole or refs, key=lambda e: e.page):
                self.pages.append(dict(ref=evidence.id, document_id=doc.id, filename=doc.original_filename, page=evidence.page,
                                       text=evidence.excerpt, large=len(whole or refs) > SMALL_DOCUMENT_PAGES,
                                       synthetic=doc.synthetic, origin=doc.origin))
        self.by_ref = {p['ref']: p for p in self.pages}

    def select(self, keyword_sets, quotas=None):
        """All pages of short documents, and for long ones the best-matching pages for each part in turn,
        so one part's common words cannot crowd out the pages another part needs."""
        chosen = {p['ref']: p for p in self.pages if not p['large']}
        large = [(p, p['text'].lower()) for p in self.pages if p['large']]
        share = max(6, LARGE_PAGE_LIMIT // max(len(keyword_sets), 1))
        for index, keywords in enumerate(keyword_sets):
            words = [k.lower() for k in keywords]
            limit = (quotas or {}).get(index) or share
            scored = []
            for page, text in large:
                hits = [(min(text.count(word), 3), word) for word in words if word in text]
                if hits:
                    # Phrases count for more than single words, and pages matching several different terms rank higher.
                    scored.append((sum(count * (3 if ' ' in word else 1) for count, word in hits) + 2 * len(hits), page))
            scored.sort(key=lambda item: (-item[0], item[1]['filename'], item[1]['page']))
            for _, page in scored[:limit]:
                chosen[page['ref']] = page
        return sorted(chosen.values(), key=lambda p: (p['filename'], p['page']))


def part_brief(part, case):
    """What the model is told about one part."""
    brief = dict(key=part['key'], type=part['type'], title=part.get('title'), guidance=part.get('guidance'))
    if part['type'] == 'table':
        if part.get('facility_columns'):
            brief.update(shape='facility table', rows=part['rows'])
        else:
            columns = []
            for name in column_names(part):
                spec = column_spec(part, name)
                if spec.get('compute') or name in ('Change (%)', '% of total'):
                    continue  # computed by the system
                columns.append(dict(name=name, figure=spec.get('kind') in ('amount', 'amount_m', 'number', 'percent'), **({'hint': spec['hint']} if spec.get('hint') else {})))
            brief.update(columns=columns, shape='fixed rows' if part.get('rows') else 'repeating rows')
            if part.get('rows'):
                brief['rows'] = part['rows']
            if part.get('periods'):
                brief.update(shape=brief['shape'] + ' with periods', periods=part['periods'], interim=bool(part.get('interim')),
                             note='Every period cell is a figure cell. The first column and Remarks are text cells.')
            if part.get('total'):
                brief['note'] = (brief.get('note', '') + ' Do not supply the total row.').strip()
    elif part['type'] == 'keyvalue':
        brief['rows'] = part['rows']
    elif part['type'] == 'choice':
        brief.update(questions=part.get('questions') or [part.get('title') or 'Select one'], options=part['options'])
    return {k: v for k, v in brief.items() if v is not None}


class Checker:
    """Validates one model response against the evidence it cites."""

    def __init__(self, labels, sources, prior, case=None, computed=''):
        self.labels, self.sources, self.prior, self.case = labels, sources, prior, case  # prior: {section id: text}
        self.computed = computed  # text of the tables Python computed for this section; cited as "C"
        self.rejected = []

    def refs(self, cites):
        out = []
        for cite in cites or []:
            if cite in self.labels:
                out.append(self.labels[cite])
        return list(dict.fromkeys(out))

    def section_refs(self, cites):
        return sorted({int(c[1:]) for c in cites or [] if re.fullmatch(r'S\d+', str(c)) and int(c[1:]) in self.prior})

    def cited_text(self, cites):
        text = ' '.join(self.sources.by_ref[ref]['text'] for ref in self.refs(cites))
        return text + ' ' + ' '.join(self.prior[n] for n in self.section_refs(cites))

    def text_cell(self, raw, where, known=''):
        """A wording cell or paragraph: needs a citation, and its figures must be on the cited pages."""
        if isinstance(raw, str):
            raw = dict(v=raw, c=[])
        value = squash((raw or {}).get('v') or (raw or {}).get('text') or '')
        if not value:
            return None
        cites = (raw or {}).get('c') or (raw or {}).get('cites') or []
        refs, sections = self.refs(cites), self.section_refs(cites)
        computed = 'C' in cites and bool(self.computed)
        if not refs and not sections and not computed:
            self.rejected.append(f'{where}: no valid citation; withheld.')
            return None
        missing = unsupported_figures(value, self.cited_text(cites) + ' ' + known + (' ' + self.computed if computed else ''))
        if missing:
            self.rejected.append(f'{where}: figure {", ".join(missing[:3])} is not on the cited page; withheld.')
            return None
        return dict(text=value, cites=refs, sections=sections, status='ok', **({'computed_ref': True} if computed else {}))

    def figure_cell(self, raw, where, kind):
        """A copied figure: the quoted line must be on a cited page and contain the figure. Returns the cell or None."""
        if not isinstance(raw, dict) or raw.get('raw') in (None, ''):
            return None
        refs = self.refs(raw.get('c'))
        quote = squash(raw.get('q') or '')
        value = parse_printed(raw['raw'])
        scale = SCALES.get(str(raw.get('scale', 'unit')).lower())
        if not refs or value is None or scale is None or not quote:
            self.rejected.append(f'{where}: figure without a usable citation, quote or unit; withheld.')
            return None
        if not any(canon(quote) in canon(self.sources.by_ref[ref]['text']) for ref in refs):
            self.rejected.append(f'{where}: quoted line not found on the cited page; withheld.')
            return None
        if not figure_in(raw['raw'], quote):
            self.rejected.append(f'{where}: figure is not in the quoted line; withheld.')
            return None
        actual = value * scale
        # Amounts are presented in thousands, or in millions where the column says so; other figures as printed.
        shown = actual / 1000 if kind == 'amount' else actual / 1_000_000 if kind == 'amount_m' else value
        text = fmt(shown, 'amount') if kind == 'amount' else fmt(shown, 'number', 1) if kind == 'amount_m' else str(raw['raw']).strip()
        return dict(text=text, value=str(shown), cites=refs, sections=[], status='ok', quote=quote)


def computed_cell(value, kind='percent'):
    return dict(text=fmt(value, kind), value=str(value), cites=[], sections=[], status='computed')


def gap_cell(reason='Not provided'):
    return dict(text='', cites=[], sections=[], status='gap', note=reason)


def note_cell(text, status='na'):
    return dict(text=text, cites=[], sections=[], status=status)


def cell_cites(cells):
    return list(dict.fromkeys(ref for cell in cells for ref in (cell or {}).get('cites', [])))


def build_table(part, raw, check):
    """Model or extract table -> {columns, rows, total, period labels}. Missing cells become gap cells."""
    names = column_names(part)
    where = part.get('title') or part['key']
    raw = raw or {}
    if part.get('facility_columns'):
        facilities = [squash(f) for f in raw.get('facilities') or []][:4]
        rows = []
        for label in part['rows']:
            given = (raw.get('rows') or {}).get(label) or []
            cells = [check.text_cell(given[i] if i < len(given) else None, f'{where} / {label}') or gap_cell() for i in range(len(facilities))]
            rows.append([note_cell(label, 'label')] + cells)
        return dict(columns=['Key terms'] + facilities, rows=rows, facility_columns=True)

    periods = [squash(p) for p in raw.get('periods') or []][:part.get('periods', 0)] if part.get('periods') else []
    interim = squash(raw.get('interim') or '') if part.get('interim') else ''
    default_kind = part.get('value_kind', 'number')

    def period_columns(index):
        """Map a template period column to the model's key for it."""
        slots = [n for n in names if n.startswith('FY[')]
        return periods[index] if index < len(periods) else None, slots

    def build_row(label, given, fixed):
        kind_for_row = (part.get('row_kinds') or {}).get(label, default_kind)
        cells, values, period_index = [], {}, 0
        for position, name in enumerate(names):
            spec = column_spec(part, name)
            place = f'{where} / {label or "row"} / {name}'
            if position == 0 and fixed:
                cells.append(note_cell(label, 'label'))
            elif name.startswith('FY['):
                key, _ = period_columns(period_index)
                period_index += 1
                cell = check.figure_cell(given.get(key), place, kind_for_row) if key else None
                cells.append(cell or gap_cell())
                if cell:
                    values[f'P{period_index}'] = Decimal(cell['value'])
            elif name == 'Interim':
                cell = check.figure_cell(given.get('interim') or given.get(interim), place, kind_for_row) if interim else None
                cells.append(cell or (gap_cell() if interim else note_cell('n.a.')))
            elif spec.get('compute') or name in ('Change (%)', '% of total'):
                cells.append(None)  # filled below
            elif spec.get('nil_when_new') and check.case is not None and check.case.new_to_bank:
                # Case input, not a model figure: a new-to-bank borrower has no existing limits or outstanding amounts.
                cells.append(dict(text='Nil', value='0', cites=[], sections=[], status='case'))
                values[name] = Decimal(0)
            elif spec.get('kind') in ('amount', 'amount_m', 'number', 'percent'):
                if isinstance(given.get(name), dict) and squash(given[name].get('v') or '').lower() in ('n.a.', 'na', 'not applicable'):
                    cells.append(note_cell('n.a.'))
                    continue
                cell = check.figure_cell(given.get(name), place, spec['kind'])
                cells.append(cell or gap_cell())
                if cell:
                    values[name] = Decimal(cell['value'])
            else:
                key = name if name in given else ('name' if position == 0 and 'name' in given else name)
                cells.append(check.text_cell(given.get(key), place) or (note_cell('') if name == 'Remarks' else gap_cell()))
        for position, name in enumerate(names):
            if cells[position] is not None:
                continue
            spec = column_spec(part, name)
            if name == 'Change (%)':
                # Change in size, so a cost printed as a negative figure shows a fall as a fall. Not meaningful across a sign change.
                first, second = values.get('P1'), values.get('P2')
                same_sign = first is not None and second is not None and first != 0 and (first > 0) == (second > 0)
                if first is not None and second is not None and not same_sign:
                    cells[position] = note_cell('n.m.')
                    continue
                result = (abs(second) - abs(first)) / abs(first) * 100 if same_sign else None
            elif name == '% of total':
                result = None  # needs the column total; filled after all rows are built
                cells[position] = dict(pending='share')
                continue
            else:
                result = evaluate(spec['compute'], values, names)
                if result is not None:
                    values[name] = result
            cells[position] = computed_cell(result, spec.get('kind', 'percent')) if result is not None else gap_cell('Not computed: an input is missing')
        return cells, values

    rows, row_values = [], []
    if part.get('rows'):
        for label in part['rows']:
            # A reply in the wrong shape for this table is treated as nothing supplied: gaps, never a failure.
            supplied = raw.get('rows') if isinstance(raw.get('rows'), dict) else {}
            cells, values = build_row(label, supplied.get(label) if isinstance(supplied.get(label), dict) else {}, True)
            rows.append(cells); row_values.append(values)
    else:
        for given in (raw.get('rows') or [])[:60]:
            if isinstance(given, dict):
                cells, values = build_row('', given, False)
                if any(c.get('status') == 'ok' for c in cells):
                    rows.append(cells); row_values.append(values)
    total = None
    latest = f'P{len(periods)}' if periods else None
    if part.get('total') and rows:
        total = [note_cell(part['total'], 'label')]
        for position, name in enumerate(names[1:], 1):
            spec = column_spec(part, name)
            key = f'P{sum(1 for n in names[:position + 1] if n.startswith("FY["))}' if name.startswith('FY[') else name
            summable = name.startswith('FY[') or spec.get('total') == 'sum'
            if summable and all(key in values for values in row_values):
                total.append(computed_cell(sum(values[key] for values in row_values), 'amount' if spec.get('kind', default_kind) == 'amount' else 'number'))
            elif name == 'Change (%)' and all('P1' in v and 'P2' in v for v in row_values):
                first, second = sum(v['P1'] for v in row_values), sum(v['P2'] for v in row_values)
                total.append(computed_cell((second - first) / abs(first) * 100) if first else gap_cell())
            elif name == '% of total':
                total.append(computed_cell(Decimal(100)))
            else:
                total.append(note_cell(''))
    for cells, values in zip(rows, row_values):
        for position, cell in enumerate(cells):
            if cell.get('pending') == 'share':
                whole = sum(v[latest] for v in row_values) if latest and all(latest in v for v in row_values) else None
                cells[position] = computed_cell(values[latest] / whole * 100) if whole and latest in values else gap_cell('Not computed: an input is missing')
    columns = list(names)
    slot = 0
    for position, name in enumerate(columns):
        if name.startswith('FY['):
            columns[position] = periods[slot] if slot < len(periods) else 'Period not stated'
            slot += 1
        elif name == 'Interim' and interim:
            columns[position] = interim
    return dict(columns=columns, rows=rows, total=total)


def render_text(section_id, title, parts_order, content, claims, gaps):
    """Plain text of the draft. Narrative claims get exact spans so the versions service can edit them."""
    text = f'{LABEL}\n{section_id}. {title}\n'
    by_part = {}
    for claim in claims:
        by_part.setdefault(claim['part'], []).append(claim)
    for part in parts_order:
        if part.get('hidden'):
            continue
        body = content.get(part['key']) or {}
        if part.get('title'):
            text += f"\n{part['title']}\n"
        for claim in by_part.get(part['key'], []):
            claim['start'] = len(text)
            text += claim['text']
            claim['end'] = len(text)
            text += '\n'
        if body.get('status') in ('na', 'gap') and body.get('note'):
            text += body['note'] + '\n'
        if body.get('rows') and part['type'] in ('table', 'keyvalue'):
            if body.get('columns'):
                text += ' | '.join(body['columns']) + '\n'
            for row in body['rows'] + ([body['total']] if body.get('total') else []):
                text += ' | '.join(cell.get('text') or ('[gap]' if cell.get('status') == 'gap' else '') for cell in row) + '\n'
        for answer in body.get('answers', []):
            text += f"{answer['question']}: {answer.get('selected') or '[gap]'}" + (f" ({answer['note']})" if answer.get('note') else '') + '\n'
    if gaps:
        text += '\n' + '\n'.join('[GAP] ' + gap for gap in gaps) + '\n'
    return text


MISSING_PREFIX = 'Fields without a sourced value: '


def missing_fields(parts, content):
    """The gap line naming the visible parts that still lack a sourced value."""
    missing = [f"{part.get('title') or part['key']}" for part in parts if not part.get('hidden') and (
        content.get(part['key'], {}).get('status') == 'gap'
        or (part['type'] == 'table' and not content.get(part['key'], {}).get('rows') and content.get(part['key'], {}).get('status') not in ('na', 'workflow'))
        or any(cell.get('status') == 'gap' for row in content.get(part['key'], {}).get('rows', []) for cell in row)
        or any(not a.get('selected') for a in content.get(part['key'], {}).get('answers', [])))]
    return [MISSING_PREFIX + '; '.join(dict.fromkeys(missing)) + '.'] if missing else []


def part_refs(body, claims=()):
    """Every source a part cites: its wording, its cells and its answers."""
    return list(dict.fromkeys([ref for claim in claims for ref in claim.get('evidence_ids', [])]
        + [ref for row in (body or {}).get('rows', []) + ([body['total']] if (body or {}).get('total') else []) for ref in cell_cites(row)]
        + [ref for answer in (body or {}).get('answers', []) for ref in answer.get('cites', [])]))


def used_refs(content, claims):
    return list(dict.fromkeys(part_refs(None, claims) + [ref for body in content.values() for ref in part_refs(body)]))


def with_notes(text, kept, register):
    """Append the analyst's accepted notes to a rendered section, giving each its exact span."""
    if not kept:
        return text
    from ..services.drafting import source_label
    text = text.rstrip('\n') + "\n\nCredit analyst's notes\n"
    for i, claim in enumerate(kept, 1):
        claim['start'] = len(text)
        text += claim['text'] + '\n' + '\n'.join(f'[CA{i}] {source_label(register[ref])}' for ref in claim.get('evidence_ids', [])) + '\n'
        claim['end'] = len(text)
    return text


def prior_sections(service, case, states, numbers):
    """Current draft text of other sections, for sections that draw on them."""
    out = {}
    for state in states:
        if state.section_id in numbers and state.current_draft_id:
            draft = service.repo.get(s.DraftVersion, state.current_draft_id)
            added = (draft.claim_spans[0].get('blocks') or []) if draft.claim_spans else []
            if added:  # what the analyst added to that section is read with it
                from .blocks import blocks_text
            out[state.section_id] = draft.text + ('\n\n' + blocks_text(added) if added else '')
    return out


def draft_parts(service, case, section_id):
    """The structured parts of a section's current draft, or {} when it has none."""
    state = next((st for st in service.repo.list_for_case(s.Section, case.id) if st.section_id == section_id), None)
    if not state or not state.current_draft_id:
        return {}
    draft = service.repo.get(s.DraftVersion, state.current_draft_id)
    return (draft.claim_spans[0] if draft.claim_spans else {}).get('parts', {})


def generate(service, case, config, spec, states, state, section_id, request, model, template, parent_id=None, preview=False, client=None):
    """Draft one section with the live model and return the saved draft (same record as the first-generation path)."""
    parts = [p for p in section_parts(spec, section_id)]
    title = next(d.name for d in config.template.sections if d.id == section_id)
    sources = Sources(service, case)
    content, claims, gaps = {}, [], list(sources.gaps)
    asked = [p for p in parts if p['fill'] in ('model', 'extract') and applies(p, case)]
    uses = sorted({n for p in asked for n in p.get('uses_sections', [])})
    prior = prior_sections(service, case, states, uses)
    position = None
    if section_id == 14:
        position = request.ca_position if request.ca_position is not None else case.ca_position
    info, prompt_hash, labels = dict(provider='none'), identity(SYSTEM, VERSION), {}
    # Tables Python computes from workbooks are prepared first, so the wording can refer to them.
    read = set()  # other sections whose computed parts this section's tables read

    def other_section(n):
        read.add(n)
        return draft_parts(service, case, n)
    context = lambda held: compute.Context(service, case, sources, held, other_section)
    early = {p['key']: compute.run(p, context({})) for p in parts if p['fill'] == 'python' and applies(p, case)}
    computed_text = '\n\n'.join(f"{p['title']}\n" + ' | '.join(early[p['key']].get('columns', [])) + '\n'
                                + '\n'.join(' | '.join(c.get('text', '') for c in row) for row in early[p['key']]['rows'])
                                for p in parts if early.get(p['key'], {}).get('rows'))
    response = {}
    calls = []
    # Large sections are drafted in more than one request, so no response runs into the output limit.
    for start in range(0, len(asked), PARTS_PER_REQUEST):
        chunk = asked[start:start + PARTS_PER_REQUEST]
        finding = [p for p in chunk if p.get('find')]
        pages = sources.select([p['find'] for p in finding], {i: p['pages'] for i, p in enumerate(finding) if p.get('pages')})
        offset = len(labels)
        chunk_labels = {f'E{offset + i}': page['ref'] for i, page in enumerate(pages, 1)}
        labels.update(chunk_labels)
        evidence = '\n\n'.join(f"[E{offset + i}] {page['filename']}, page {page['page']}" + (' (SYNTHETIC DEMO DATA)' if page['synthetic'] else '')
                               + f"\n{page['text'][:PAGE_CHARS]}" for i, page in enumerate(pages, 1))
        facts = dict(borrower=case.borrower_name, case_type=case.case_type, new_to_bank=bool(case.new_to_bank),
                     existing_client=bool(case.existing_client), section=f'{section_id}. {title}')
        user = ('Case\n' + json.dumps(facts) + '\n\nParts to draft\n' + json.dumps([part_brief(p, case) for p in chunk], ensure_ascii=False)
                + (f'\n\nCredit analyst\'s stated position (word this; do not change its substance)\n{position}' if position else '')
                + ''.join(f'\n\nPrior section S{n} (current draft)\n{text[:30000]}' for n, text in prior.items())
                + (f'\n\nTables computed by the system for this section (cite as "C")\n{computed_text}' if computed_text else '')
                + '\n\nEvidence pages\n' + evidence)
        provider = live.AnthropicLive(model, client=client)
        info = provider.get_provider_info()
        prompt_hash = identity(prompt_hash, user)
        try:
            text, call = provider.complete(SYSTEM, user, case_id=case.id, section_id=section_id, purpose='draft')
        except live.LiveCallError as error:  # recorded in the cost ledger; nothing is saved for this section
            raise ValueError(f'Section {section_id} was not drafted: {error}.') from error
        calls.append(call)
        try:
            reply = json.loads(clean_json_response(text))
            response.setdefault('parts', {}).update(reply.get('parts') or {})
            response.setdefault('gaps', []).extend(reply.get('gaps') or [])
        except (ValueError, TypeError):
            gaps.append('A model response could not be read; nothing from it was used. Redraft the section.')
    check = Checker(labels, sources, prior, case, computed_text)
    given = response.get('parts') or {}
    known = ''
    for part in parts:
        key = part['key']
        raw = given.get(key) or {}
        if not applies(part, case):
            content[key] = dict(status='na', note='Not applicable: new to bank. There is no prior relationship or account history with the Bank.')
        elif part['fill'] in ('model', 'extract') and part['type'] == 'narrative':
            kept = []
            for i, paragraph in enumerate(raw.get('paragraphs') or []):
                cell = check.text_cell(paragraph, f"{part['title']} paragraph {i + 1}", known)
                if cell:
                    kept.append(cell)
                    claims.append(dict(id=f'{key}.{len(kept)}', kind='narrative', part=key, subpart=part['title'], text=cell['text'],
                                       evidence_ids=cell['cites'], section_refs=cell['sections'], computed_ref=bool(cell.get('computed_ref'))))
            content[key] = dict(paragraphs=len(kept)) if kept else dict(status='gap', note='No supported wording available from the evidence held.')
        elif part['fill'] in ('model', 'extract') and part['type'] == 'table':
            content[key] = build_table(part, raw, check)
            known += ' ' + ' '.join(cell.get('text', '') for row in content[key]['rows'] for cell in row)
        elif part['fill'] == 'model' and part['type'] == 'keyvalue':
            content[key] = dict(rows=[[note_cell(label, 'label'), check.text_cell((raw.get('rows') or {}).get(label), f"{part.get('title', key)} / {label}") or gap_cell()]
                                      for label in part['rows']])
        elif part['fill'] == 'model' and part['type'] == 'choice':
            questions = part.get('questions') or [part.get('title') or 'Select one']
            answers = []
            for i, question in enumerate(questions):
                answer = (raw.get('answers') or [])[i] if i < len(raw.get('answers') or []) else {}
                selected = answer.get('selected') if answer.get('selected') in part['options'] else None
                refs = check.refs(answer.get('c'))
                if selected and not refs:
                    check.rejected.append(f'{question}: answer without a citation; withheld.')
                    selected = None
                answers.append(dict(question=question, options=part['options'], selected=selected, note=squash(answer.get('note') or '') if selected else '', cites=refs if selected else []))
            content[key] = dict(answers=answers)
        elif part['fill'] == 'python':
            content[key] = compute.run(part, context(content))
        elif part['fill'] == 'case':
            content[key] = compute.case_part(part, case)
        elif part['fill'] == 'ca':
            chosen = next((o for o in part['options'] if position and position.strip().lower().startswith(o.lower())), None)
            content[key] = dict(answers=[dict(question=part.get('title') or 'Recommendation', options=part['options'], selected=chosen,
                                              note='' if chosen else 'For the credit analyst to select.', cites=[])])
        elif part['fill'] == 'workflow':
            content[key] = dict(status='workflow', note='Completed by the approval workflow: names, decisions and dates are recorded when each officer acts.')
        elif part['fill'] == 'asset':
            content[key] = compute.asset_part(part, case, content, service.storage_root)
    if section_id == 14 and position:
        snapshot = dict(case_id=case.id, text=position, actor=request.actor, role='CA', recorded_at=s.utcnow().isoformat(),
                        content_hash=identity(position), origin='CA input', basis='Position stated by the credit analyst; not independently verified')
        claims.insert(0, dict(id='ca-position', kind='ca_position', part='recommendation', subpart='Credit analyst\'s position',
                              evidence_ids=[], section_refs=[], text='Credit analyst\'s stated position: ' + position, ca_position=snapshot))
        if not preview and case.ca_position != position:
            case.ca_position = position
            service.repo.save(case)
    gaps += [squash(g) for g in response.get('gaps') or [] if squash(g)][:12] + check.rejected
    gaps += missing_fields(parts, content)
    unsecured = any(a.get('selected') in ('Unsecured', 'Partially secured') for a in content.get('security_type', {}).get('answers', [])) or any(
        'unsecured' in cell.get('text', '').lower() for row in content.get('facilities', {}).get('rows', []) for cell in row[1:])
    if unsecured and not request.confirm_unsecured:
        gaps.append('A facility is described as unsecured: the credit analyst is to confirm that description.')
    # Input gaps from the readiness check are kept, except "can generate" items: for this team the figures a generated
    # spread would hold are copied from the financial statements and checked in section 10.
    gaps = list(dict.fromkeys([g for g in state.gaps if 'Can generate' not in g and not (position and g.startswith('CA position not yet stated'))] + gaps))
    register = {ref: service.evidence.resolve(case.id, ref) for ref in used_refs(content, claims)}
    # A redraft keeps what the analyst added to the version it replaces: accepted notes and added content.
    parent = service.repo.get(s.DraftVersion, parent_id) if parent_id else None
    kept = [dict(claim) for claim in parent.claim_spans[1:] if claim.get('kind') == 'ca_input'] if parent and parent.claim_spans else []
    blocks = (parent.claim_spans[0].get('blocks') or []) if parent and parent.claim_spans else []
    register.update({ref: service.evidence.resolve(case.id, ref) for claim in kept for ref in claim.get('evidence_ids', [])})
    text = with_notes(render_text(section_id, title, parts, content, claims, gaps), kept, register)
    claims = claims + kept
    envelope = dict(kind='draft_metadata', mock=False, label=LABEL, provider=info, prompt_hash=prompt_hash, spec_version=spec['version'],
                    engine=VERSION, mode='live', source_register=register, computed_tables=[], parts=content, blocks=blocks,
                    calls=[{k: call[k] for k in ('model', 'input_tokens', 'output_tokens', 'cost_usd', 'seconds')} for call in calls],
                    rejected=len(check.rejected), ca_position=claims[0].get('ca_position') if section_id == 14 and position else None)
    # Pin what was read from other sections, so this section is marked for update when that content changes.
    pins = {}
    for n in sorted(set(uses) | read):
        other = next((st for st in states if st.section_id == n and st.applicable), None)
        if other:  # a section not yet drafted is pinned as empty, so its first draft marks this one for update
            basis = 'text' if n in uses else 'parts'
            pins[str(n)] = dict(draft_id=other.current_draft_id, basis=basis, content_hash=content_hash(
                service.repo.get(s.DraftVersion, other.current_draft_id), basis) if other.current_draft_id else '')
    envelope['freshness_dependencies'] = pins
    draft = s.DraftVersion(case_id=case.id, section_id=section_id, parent_id=parent_id, text=text, claim_spans=[envelope] + claims,
                           document_ids=sorted({src['document_id'] for src in register.values() if src.get('document_id')}),
                           config_hash=case.config_hash, prompt_version=f"{spec['version']}:{prompt_hash[:16]}",
                           model_version=f"live:{info.get('model', 'none')}:{VERSION}", template_version_id=template.id,
                           input_fingerprint=state.input_fingerprint, author=request.actor, gaps=gaps,
                           ca_input_ids=list(parent.ca_input_ids) if parent else [])
    if preview:
        return draft.model_dump(mode='json')
    draft = service.repo.save(draft)
    for i, claim in enumerate(claims):
        for ref in claim['evidence_ids']:
            service.repo.save(s.Citation(case_id=case.id, evidence_id=ref, draft_id=draft.id, claim_or_cell=f'claim:{i}:{claim["id"]}'))
    service.repo.save(state.model_copy(update=dict(current_draft_id=draft.id, confirmed_draft_id=None, readiness='Drafted',
                                                   editor_revision=state.editor_revision + 1)))
    return draft
