"""Model sense check of the tables that code does not check.

Python computes and checks many tables. The rest are drafted by the model from cited sources (each figure is
matched to its source line, but the table as a whole is not reasoned about) or added by the analyst (not checked
at all). This asks a model to read those tables and say what does not look reasonable. Each finding is a
suggestion for a human check. It never changes a value, never blocks anything, and a table without a finding
is not thereby verified.
"""
from hashlib import sha256
import json
import re

from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from ..llm import live
from ..llm.client import clean_json_response
from ..llm.registry import load_registry
from ..team_config import TeamConfig
from .numbers import squash
from .spec import load_spec, section_parts

CONCERNS = ('total', 'unit', 'sign', 'date', 'inconsistent', 'implausible', 'incomplete', 'other')
MAX_FINDINGS = 8
NOTE = 'Suggested by the model for a human check. It is not a verification, and a table without a suggestion is not verified by this.'
# A suggestion must not read as a decision or an assurance.
UNSAFE = re.compile(r'\b(approv\w*|verified|guarantee\w*|is correct|are correct|safe to)\b', re.I)

SYSTEM = f"""You read tables in a draft bank credit paper (an Executive Summary) for a credit analyst. You change nothing. Your only task is to point out values that do not look reasonable, so that a person rechecks them.

Look for: totals or shares that do not add up; a wrong unit or scale (thousands against millions, percent against times); a wrong sign; dates that are out of order or implausible; a figure that disagrees with the reference tables or with another row; a value that is implausible for the kind of item; a row that is clearly incomplete.

Rules
1. Only report what a careful analyst would want to recheck. No finding is better than a weak one. At most {MAX_FINDINGS} findings.
2. Do not report missing citations, wording style, or cells marked [gap]: those are handled elsewhere.
3. In a reason, name a table by its title and a row by its label, never by its id. Each reason is one plain sentence that says what looks wrong and what to compare it with. Do not say anything is verified, approved or correct. Do not give a credit view.
4. Reply with JSON only: {{"findings": [{{"table": "<table id, for example T2>", "row": "<row id, for example r3, or total>", "column": "<column name, or empty>", "concern": "<one of: {', '.join(CONCERNS)}>", "reason": "<one sentence>"}}]}}
5. If nothing needs a recheck, reply {{"findings": []}}."""


class SenseRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')


class ResolveRequest(SenseRequest):
    finding_id: str = Field(min_length=1, max_length=40)
    note: str = Field(default='', max_length=500)


def row_text(row):
    return ' | '.join(cell.get('text') or ('[gap]' if cell.get('status') == 'gap' else '') for cell in row)


def unchecked_tables(spec, section_id, envelope):
    """Tables of this draft that code does not check: [{id, key, title, origin, columns, rows, total}]."""
    tables = []
    content = envelope.get('parts') or {}
    for part in section_parts(spec, section_id):
        body = content.get(part['key']) or {}
        if part.get('hidden') or part['fill'] not in ('model', 'extract') or part['type'] not in ('table', 'keyvalue') or not body.get('rows'):
            continue
        tables.append(dict(key=part['key'], title=part.get('title') or part['key'], origin='drafted by the model from cited sources',
                           columns=body.get('columns') or [], rows=[row_text(row) for row in body['rows']], labels=[row[0].get('text', '') for row in body['rows']],
                           total=row_text(body['total']) if body.get('total') else None))
    for block in envelope.get('blocks') or []:
        if block['kind'] == 'table':
            head = block.get('header', True)
            tables.append(dict(key='block:' + block['id'], title=block.get('title') or 'Table added by the analyst', origin='added by the analyst, not checked',
                               columns=block['rows'][0] if head else [], rows=[' | '.join(row) for row in block['rows'][1 if head else 0:]],
                               labels=[row[0] for row in block['rows'][1 if head else 0:]], total=None))
    for i, table in enumerate(tables, 1):
        table['id'] = f'T{i}'
    return tables


def reference_tables(service, case, spec, states):
    """Tables computed by Python across the ES, as the reference the model compares against."""
    out = []
    for state in states:
        if not state.current_draft_id:
            continue
        draft = service.repo.get(s.DraftVersion, state.current_draft_id)
        content = (draft.claim_spans[0] if draft.claim_spans else {}).get('parts') or {}
        for part in section_parts(spec, state.section_id):
            body = content.get(part['key']) or {}
            if part['fill'] == 'python' and body.get('rows'):
                out.append(f"Section {state.section_id}, {part.get('title') or part['key']}\n" + ' | '.join(body.get('columns') or []) + '\n'
                           + '\n'.join(row_text(row) for row in body['rows'][:40]))
    return '\n\n'.join(out)[:40000]


def keep(raw, tables):
    """Keep only findings that point at a table and row that were sent; reword nothing."""
    by_id = {table['id']: table for table in tables}
    findings, seen = [], set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        table = by_id.get(str(item.get('table', '')).strip())
        reason = squash(str(item.get('reason') or ''))[:400]
        row = str(item.get('row', '')).strip().lower()
        if not table or not reason or UNSAFE.search(reason):
            continue
        # The ids are for the reply only. Where one slips into the wording, show the table's title and the row's label instead.
        def named(match):
            other = by_id.get(match.group(1))
            if not other:
                return match.group(0)
            number = int(match.group(2)) - 1 if match.group(2) else None
            label = other['labels'][number] if number is not None and 0 <= number < len(other['labels']) else None
            return f"the table \"{other['title']}\"" + (f" (row \"{label[:60]}\")" if label else '')
        reason = re.sub(r'\b(T\d+)(?:,? (?:row )?r(\d+))?\b', named, reason)
        index = int(row[1:]) - 1 if re.fullmatch(r'r\d+', row) else None
        if row == 'total' and not table['total']:
            row = ''
        if index is not None and not 0 <= index < len(table['rows']):
            continue
        if index is None and row not in ('total', ''):
            continue
        column = squash(str(item.get('column') or ''))
        column = column if column in table['columns'] else ''
        concern = item.get('concern') if item.get('concern') in CONCERNS else 'other'
        finding = dict(table=table['key'], table_title=table['title'], origin=table['origin'], row=index, row_label='Total' if row == 'total' else table['labels'][index] if index is not None else '',
                       column=column, concern=concern, reason=reason)
        finding['id'] = sha256(json.dumps(finding, sort_keys=True).encode()).hexdigest()[:12]
        if finding['id'] not in seen:
            seen.add(finding['id'])
            findings.append(finding)
    return findings[:MAX_FINDINGS]


def run(service, case_id, section_id, request, client=None):
    """Read the current draft's unchecked tables with the case's model and save the suggestions."""
    case = service.repo.get(s.Case, case_id)
    spec = load_spec(case.team_id)
    if not spec:
        raise ValueError('The sense check is available on sections drafted from the ES specification')
    states = [st for st in service.repo.list_for_case(s.Section, case_id)]
    state = next((st for st in states if st.section_id == section_id), None)
    if not state or not state.current_draft_id:
        raise ValueError('Draft the section first')
    draft = service.repo.get(s.DraftVersion, state.current_draft_id)
    envelope = draft.claim_spans[0] if draft.claim_spans else {}
    tables = unchecked_tables(spec, section_id, envelope)
    model = load_registry().get(case.default_model_id)
    if not tables:
        return service.repo.save(s.SenseCheck(case_id=case_id, section_id=section_id, draft_id=draft.id, model='none', checked_by=request.actor))
    model.require_runnable()
    if model.route == 'mock':
        raise ValueError('The sense check needs a live model; this case uses the mock provider')
    title = next(d.name for d in TeamConfig.model_validate(case.config_snapshot).template.sections if d.id == section_id)
    user = (f'Section {section_id}. {title}\nBorrower: {case.borrower_name}\n\nTables to read\n\n'
            + '\n\n'.join(f"{t['id']} \"{t['title']}\" [{t['origin']}]\n" + (' | '.join(t['columns']) + '\n' if t['columns'] else '')
                          + '\n'.join(f'r{i}: {row}' for i, row in enumerate(t['rows'], 1)) + (f"\ntotal: {t['total']}" if t['total'] else '') for t in tables)
            + '\n\nReference tables computed by the system (take these as given)\n\n' + (reference_tables(service, case, spec, states) or 'None.'))
    try:
        text, call = live.AnthropicLive(model, client=client).complete(SYSTEM, user, case_id=case_id, section_id=section_id, purpose='sense_check', max_tokens=16000)
    except live.LiveCallError as error:
        raise ValueError(f'The sense check did not run: {error}.') from error
    try:
        raw = json.loads(clean_json_response(text)).get('findings')
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('The model reply could not be read; nothing was recorded. Run the sense check again.') from error
    return service.repo.save(s.SenseCheck(case_id=case_id, section_id=section_id, draft_id=draft.id, findings=keep(raw, tables), tables_checked=len(tables),
                                          model=call['model'], cost_usd=call['cost_usd'], checked_by=request.actor))


def listing(repo, case_id):
    """The latest sense check of each section, saying whether it still matches the section's current version."""
    current = {st.section_id: st.current_draft_id for st in repo.list_for_case(s.Section, case_id)}
    latest = {}
    for check in sorted(repo.list_for_case(s.SenseCheck, case_id), key=lambda c: (c.created_at, c.id)):
        latest[check.section_id] = check
    return [check.model_dump(mode='json') | dict(current=check.draft_id == current.get(check.section_id), note=NOTE,
                                                 open=sum(f['id'] not in check.resolutions for f in check.findings)) for check in latest.values()]


def resolve(repo, case_id, check_id, request):
    """Record that a person looked at a suggestion. The table is not changed."""
    check = repo.get(s.SenseCheck, check_id)
    if check.case_id != case_id or not any(f['id'] == request.finding_id for f in check.findings):
        raise ValueError('Unknown suggestion')
    resolutions = dict(check.resolutions)
    resolutions[request.finding_id] = dict(actor=request.actor, at=s.utcnow().isoformat(), note=squash(request.note))
    return repo.save(check.model_copy(update=dict(resolutions=resolutions)))
