"""New information: when documents change after drafting, propose an update of each affected section.

A proposal is a full candidate version of the section, prepared against the current documents by the same engine
that drafts it (Python calculations, the model, the figure checks) and compared with the current version in Python.
Nothing reaches the section until the maker applies the proposal. Figure tables are taken together from the
candidate; each affected wording part is accepted or kept; wording that is not affected is kept as it is.
"""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
import json

from pydantic import Field

from .. import schemas as s
from ..llm.registry import load_registry
from ..services.drafting import DraftRequest
from ..services.gaps import current_documents
from ..services.locks import RevisionConflict
from ..services.readiness import content_hash
from ..services.versions import VersionRequest
from ..team_config import TeamConfig
from .drafting import MISSING_PREFIX, missing_fields, part_refs, render_text, used_refs, with_notes
from .spec import load_spec, section_parts

NOTE = ('A proposal is prepared by the system and the model against the current documents. Nothing changes in the section until you apply it. '
        'Figures are calculated or checked against their source by code. Wording is a suggestion for you to accept or keep.')
ACTIVE = ('waiting', 'ready', 'proposed')


class ApplyRequest(VersionRequest):
    keep: list[str] = Field(default_factory=list, max_length=60)  # wording parts to leave as they are


class DismissRequest(VersionRequest):
    pass


def part_kind(part):
    """figures: calculated by code, or copied from a source and checked. wording: written by the model. system: everything else."""
    if part.get('hidden') or part['fill'] not in ('python', 'extract', 'model'):
        return 'system'
    return 'figures' if part['fill'] == 'python' or (part['fill'] == 'extract' and part['type'] != 'narrative') else 'wording'


def part_view(part, body, claims):
    """What a reader sees of one part, for comparison."""
    body = body or {}
    if part['type'] == 'narrative':
        return dict(paragraphs=[c['text'] for c in claims if c.get('kind') not in ('ca_position', 'ca_input')], note=body.get('note', '') if body.get('status') else '')
    if part['type'] in ('table', 'keyvalue'):
        rows = body.get('rows', []) + ([body['total']] if body.get('total') else [])
        return dict(columns=body.get('columns') or [], rows=[[cell.get('text') or ('[gap]' if cell.get('status') == 'gap' else '') for cell in row] for row in rows],
                    note=body.get('note', '') if body.get('status') else '')
    if part['type'] == 'choice':
        return dict(answers=[[a['question'], a.get('selected') or '[gap]', a.get('note', '')] for a in body.get('answers', [])], note=body.get('note', '') if body.get('status') else '')
    return {}


def cell_changes(before, after):
    """Cell by cell differences between two versions of a table. Rows are matched on their first cell."""
    def keyed(body):
        out = {}
        for i, row in enumerate((body or {}).get('rows', []) + ([body['total']] if (body or {}).get('total') else [])):
            label = (row[0].get('text') if row else '') or f'Row {i + 1}'
            out[label if label not in out else f'{label} ({i + 1})'] = row
        return out
    text = lambda cell: cell.get('text') or ('[gap]' if cell.get('status') == 'gap' else '')
    old, new = keyed(before), keyed(after)
    columns = (after or {}).get('columns') or (before or {}).get('columns') or []
    out = []
    for label in dict.fromkeys([*old, *new]):
        b, a = old.get(label), new.get(label)
        if b is None or a is None:
            out.append(dict(row=label, column='', before='' if b is None else ' | '.join(text(c) for c in b[1:]), after='' if a is None else ' | '.join(text(c) for c in a[1:]),
                            change='row added' if b is None else 'row removed', lost=a is None))
            continue
        for i in range(max(len(a), len(b))):
            tb, ta = (text(b[i]) if i < len(b) else ''), (text(a[i]) if i < len(a) else '')
            if tb != ta:
                column = columns[i] if i < len(columns) else 'Value' if i == 1 else f'Column {i + 1}'
                out.append(dict(row=label, column=column, before=tb, after=ta, change='changed',
                                computed=i < len(a) and a[i].get('status') == 'computed',
                                lost=bool(tb) and tb != '[gap]' and ta in ('', '[gap]')))
    return out


def keep_unaffected_text(part, old_body, new_body, old_register, replaced):
    """In a table of figures copied from sources, the model also words the text cells (remarks, descriptions).
    Figure cells always come from the candidate. A text cell keeps its current wording unless that wording cites a
    replaced document, so a remark is not reworded just because the section was prepared again."""
    if part['fill'] != 'extract' or not old_body or not new_body or not new_body.get('rows') or old_body.get('columns') != new_body.get('columns'):
        return new_body
    label = lambda row: row[0].get('text') if row else None
    current = {}
    for row in old_body.get('rows', []):
        current.setdefault(label(row), row)
    on_replaced = lambda cell: any((old_register.get(ref) or {}).get('document_id') in replaced for ref in cell.get('cites', []))
    merged = deepcopy(new_body)
    for row in merged['rows']:
        before = current.get(label(row))
        if not before or len(before) != len(row):
            continue
        for i, cell in enumerate(row):
            was = before[i]
            is_figure = 'value' in cell or cell.get('status') == 'computed'
            if i and not is_figure and was.get('text') and was.get('status') != 'gap' and not on_replaced(was) and was.get('text') != cell.get('text'):
                row[i] = deepcopy(was)
    return merged


def documents_key(repo, case):
    """Which documents were current when a proposal was made. A proposal is void once this changes."""
    docs = current_documents(repo.list_for_case(s.Document, case.id), case)
    return sha256(json.dumps(sorted(d.id for d in docs)).encode()).hexdigest()


def replaced_documents(repo, case_id):
    return {d.supersedes_id for d in repo.list_for_case(s.Document, case_id) if d.supersedes_id and d.conflict_status in ('none', 'accepted')}


def upstream(config, spec, section_id, envelope):
    """Sections this one reads: recorded on its current version, declared in the specification, or required by the team rules."""
    rule = next((d for d in config.dependencies.items if d.section_id == section_id), None)
    declared = {n for part in section_parts(spec, section_id) for n in part.get('uses_sections', []) + part.get('reads_sections', [])}
    pinned = {int(n) for n in (envelope.get('freshness_dependencies') or {})}
    return (declared | pinned | set(rule.requires if rule else []) | set(rule.freshness_requires if rule else [])) - {section_id}


def overview(service, case_id):
    """New documents and the state of every affected section. Read only apart from the readiness refresh."""
    repo = service.repo
    case = repo.get(s.Case, case_id)
    spec = load_spec(case.team_id)
    config = TeamConfig.model_validate(case.config_snapshot)
    model = load_registry().get(case.default_model_id)
    base = dict(available=bool(spec), live=bool(spec) and model.route != 'mock' and model.runnable, note=NOTE, documents=[], sections=[])
    if not spec:
        return base
    states = service.sections(case_id)
    documents = {d.id: d for d in repo.list_for_case(s.Document, case_id)}
    replaced = replaced_documents(repo, case_id)
    names = {d.id: d.name for d in config.template.sections}
    types = {item.id: item.name for item in config.catalogue.items}
    drafts = {st.section_id: repo.get(s.DraftVersion, st.current_draft_id) for st in states if st.applicable and st.current_draft_id}
    key = documents_key(repo, case)
    proposals = sorted(repo.list_for_case(s.UpdateProposal, case_id), key=lambda p: (p.created_at, p.id))
    entries = {}
    for state in states:
        draft = drafts.get(state.section_id)
        envelope = draft.claim_spans[0] if draft and draft.claim_spans else {}
        if not draft or envelope.get('parts') is None:
            continue
        mine = [p for p in proposals if p.section_id == state.section_id]
        pending = next((p for p in reversed(mine) if p.status == 'pending' and p.base_draft_id == draft.id
                        and p.input_fingerprint == state.input_fingerprint and p.documents_key == key), None)
        applied = next((p for p in reversed(mine) if p.status == 'applied' and p.applied_draft_id == draft.id), None)
        cited = sorted(set(draft.document_ids) & replaced)
        reasons = (['Marked "Update required": an input or a section it reads has changed.'] if state.readiness == 'Stale' else []) + \
            ([f"Cites a replaced document: {', '.join(documents[d].original_filename for d in cited)}."] if cited else [])
        if not reasons and not applied:
            continue
        done = bool(applied) and state.readiness != 'Stale'
        # attention: updated, but the maker kept wording that cites a replaced document. It can be proposed again and does not hold other sections back.
        status = 'proposed' if pending else 'attention' if done and cited else 'updated' if done else 'ready'
        entries[state.section_id] = dict(
            section_id=state.section_id, name=names[state.section_id], readiness=state.readiness, reasons=reasons, status=status,
            reads=sorted(upstream(config, spec, state.section_id, envelope)),
            token=dict(expected_draft_id=state.current_draft_id, expected_revision=state.editor_revision, expected_input_fingerprint=state.input_fingerprint),
            proposal=pending.model_dump(mode='json', exclude={'candidate'}) if pending else None,
            applied=applied.model_dump(mode='json', exclude={'candidate'}) if applied else None,
            kept_on_replaced=[c['title'] for c in applied.changes if c['key'] in applied.decisions.get('keep', []) and c.get('cites_replaced')] if done and cited else [])
    for entry in entries.values():
        entry['waiting_on'] = [n for n in entry['reads'] if n in entries and entries[n]['status'] in ACTIVE] if entry['status'] in ACTIVE else []
        if entry['waiting_on'] and entry['status'] == 'ready':
            entry['status'] = 'waiting'
    in_use = lambda doc_id: sorted(n for n, draft in drafts.items() if doc_id in draft.document_ids)
    base['documents'] = [dict(id=d.id, filename=d.original_filename, type=types.get(d.catalogue_id, 'Other'), period=d.period, revision=d.revision,
                              received=d.created_at.isoformat(), synthetic=d.synthetic,
                              replaces=dict(id=d.supersedes_id, filename=documents[d.supersedes_id].original_filename, period=documents[d.supersedes_id].period,
                                            still_cited_in=in_use(d.supersedes_id)))
                         for d in sorted(documents.values(), key=lambda d: (d.created_at, d.id), reverse=True)
                         if d.supersedes_id and d.conflict_status in ('none', 'accepted')]
    base['sections'] = [entries[n] for n in sorted(entries)]
    base['open'] = sum(e['status'] != 'updated' for e in entries.values())
    return base


def compare(repo, case, spec, section_id, parent, candidate, states):
    """Part by part differences between the current version and the candidate, and which wording parts are affected."""
    old_env, old_claims = parent.claim_spans[0], parent.claim_spans[1:]
    new_env, new_claims = candidate['claim_spans'][0], candidate['claim_spans'][1:]
    documents = {d.id: d for d in repo.list_for_case(s.Document, case.id)}
    replaced = replaced_documents(repo, case.id)
    arrived = {d.id for d in documents.values() if d.created_at > parent.created_at}
    doc_of = lambda register, refs: {(register.get(ref) or {}).get('document_id') for ref in refs} - {None}
    # Other sections whose content has changed since this version was made.
    pins = old_env.get('freshness_dependencies') or {}
    moved = set()
    for state in states:
        if state.section_id == section_id or not state.current_draft_id:
            continue
        pin = pins.get(str(state.section_id))
        other = repo.get(s.DraftVersion, state.current_draft_id)
        if pin and 'content_hash' in pin:
            if pin.get('draft_id') != other.id and content_hash(other, pin.get('basis')) != pin['content_hash']:
                moved.add(state.section_id)
        elif other.created_at > parent.created_at:  # a version made before sections recorded what they read
            moved.add(state.section_id)
    parts = section_parts(spec, section_id)
    rows, kept = [], []
    figures_changed = False
    for part in parts:
        kind = part_kind(part)
        if kind != 'figures':
            continue
        cells = cell_changes(old_env['parts'].get(part['key']), new_env['parts'].get(part['key']))
        before, after = (part_view(part, env['parts'].get(part['key']), []) for env in (old_env, new_env))
        if cells or before != after:
            figures_changed = True
            rows.append(dict(key=part['key'], title=part.get('title') or part['key'], kind='figures', type=part['type'], locked=True,
                             origin='Calculated by code' if part['fill'] == 'python' else 'Copied from the source and checked by code',
                             reasons=[], cells=cells, before=before, after=after, lost=any(c.get('lost') for c in cells)))
    for part in parts:
        if part_kind(part) != 'wording':
            continue
        key = part['key']
        mine_old, mine_new = ([c for c in claims if c.get('part') == key] for claims in (old_claims, new_claims))
        before, after = part_view(part, old_env['parts'].get(key), mine_old), part_view(part, new_env['parts'].get(key), mine_new)
        if before == after:
            continue
        old_refs, new_refs = part_refs(old_env['parts'].get(key), mine_old), part_refs(new_env['parts'].get(key), mine_new)
        cites_replaced = bool(doc_of(old_env.get('source_register') or {}, old_refs) & replaced)
        reasons = (['Cites a replaced document.'] if cites_replaced else []) + \
            (['The proposal uses a document received after this version.'] if doc_of(new_env.get('source_register') or {}, new_refs) & arrived else [])
        reads = sorted((set(part.get('uses_sections', [])) | {n for c in mine_old + mine_new for n in c.get('section_refs', []) if isinstance(n, int)}) & moved)
        if reads:
            reasons.append('Draws on section' + ('s ' if len(reads) > 1 else ' ') + ', '.join(map(str, reads)) + ', which changed.')
        if figures_changed and any(c.get('computed_ref') for c in mine_old + mine_new):
            reasons.append('Refers to figures in this section that changed.')
        if not reasons:
            kept.append(key)  # not affected: the current wording stays, whatever the model wrote this time
            continue
        rows.append(dict(key=key, title=part.get('title') or key, kind='wording', type=part['type'], locked=False, reasons=reasons, cites_replaced=cites_replaced,
                         analyst_edit=any(c.get('ca_edit') for c in mine_old), before=before, after=after,
                         cells=cell_changes(old_env['parts'].get(key), new_env['parts'].get(key)) if part['type'] in ('table', 'keyvalue') else [],
                         lost=not (after.get('paragraphs') or after.get('rows') or after.get('answers'))))
    return rows, kept


def propose(service, case_id, section_id, request):
    """Prepare a candidate version of an affected section and save the comparison. The section itself is not changed."""
    state, parent = service.prepare(case_id, section_id, request)
    case = service.repo.get(s.Case, case_id)
    spec = load_spec(case.team_id)
    if not spec or not parent.claim_spans or parent.claim_spans[0].get('parts') is None:
        raise ValueError('Update proposals are available on sections drafted from the ES specification')
    entry = next((e for e in overview(service, case_id)['sections'] if e['section_id'] == section_id), None)
    if not entry or entry['status'] == 'updated':
        raise ValueError('This section is not affected by new information')
    if entry['waiting_on']:
        raise ValueError('Update section' + ('s ' if len(entry['waiting_on']) > 1 else ' ') + ', '.join(map(str, entry['waiting_on'])) + ' first: this section reads from it')
    confirmed_unsecured = not any('described as unsecured' in gap for gap in parent.gaps)
    candidate = service.drafting.generate(case_id, section_id, DraftRequest(
        actor=request.actor, template_version_id=parent.template_version_id, confirm_unsecured=confirmed_unsecured), parent_id=parent.id, preview=True)
    # Text cells of figure tables that are not affected keep their current wording (see keep_unaffected_text).
    replaced = replaced_documents(service.repo, case_id)
    held, register = candidate['claim_spans'][0]['parts'], parent.claim_spans[0].get('source_register') or {}
    for part in section_parts(spec, section_id):
        if part_kind(part) == 'figures' and part['key'] in held:
            held[part['key']] = keep_unaffected_text(part, parent.claim_spans[0]['parts'].get(part['key']), held[part['key']], register, replaced)
    states = service.sections(case_id)
    changes, kept = compare(service.repo, case, spec, section_id, parent, candidate, states)
    for earlier in service.repo.list_for_case(s.UpdateProposal, case_id):
        if earlier.section_id == section_id and earlier.status == 'pending':
            service.repo.save(earlier.model_copy(update=dict(status='superseded', resolved_by=request.actor, resolved_at=s.utcnow())))
    calls = candidate['claim_spans'][0].get('calls') or []
    cost = f"{sum(float(call.get('cost_usd') or 0) for call in calls):.4f}" if calls else None
    proposal = service.repo.save(s.UpdateProposal(
        case_id=case_id, section_id=section_id, base_draft_id=parent.id, input_fingerprint=state.input_fingerprint, documents_key=documents_key(service.repo, case),
        candidate=candidate, changes=changes, kept=kept, proposed_by=request.actor, cost_usd=cost))
    return proposal.model_dump(mode='json', exclude={'candidate'})


def current_proposal(service, case_id, proposal_id, request):
    proposal = service.repo.get(s.UpdateProposal, proposal_id)
    if proposal.case_id != case_id or proposal.status != 'pending':
        raise ValueError('Unknown or closed proposal')
    state, parent = service.prepare(case_id, proposal.section_id, request)
    case = service.repo.get(s.Case, case_id)
    if parent.id != proposal.base_draft_id or state.input_fingerprint != proposal.input_fingerprint or documents_key(service.repo, case) != proposal.documents_key:
        raise RevisionConflict('The section or its documents changed after this proposal was made; ask for a new proposal')
    return proposal, state, parent, case


def apply(service, case_id, proposal_id, request):
    """Save a new version of the section: figure tables from the candidate, accepted wording from the candidate, the rest as it was."""
    proposal, state, parent, case = current_proposal(service, case_id, proposal_id, request)
    section_id = proposal.section_id
    spec = load_spec(case.team_id)
    parts = section_parts(spec, section_id)
    choosable = {c['key'] for c in proposal.changes if c['kind'] == 'wording'}
    keep = set(request.keep)
    if not keep <= choosable:
        raise ValueError('Only proposed wording can be kept as it is; figure tables are updated together')
    from_current = keep | set(proposal.kept)
    old_env, old_claims = parent.claim_spans[0], parent.claim_spans[1:]
    new_env, new_claims = proposal.candidate['claim_spans'][0], proposal.candidate['claim_spans'][1:]
    content, claims = {}, []
    for part in parts:
        key = part['key']
        env, source = (old_env, old_claims) if key in from_current else (new_env, new_claims)
        if key in env['parts']:
            content[key] = deepcopy(env['parts'][key])
        for claim in source:
            if claim.get('part') == key and claim.get('kind') != 'ca_input':
                claims.append({k: v for k, v in deepcopy(claim).items() if k not in ('start', 'end')})
    # The analyst's position leads the recommendation, as in drafting.
    claims.sort(key=lambda claim: claim.get('kind') != 'ca_position')
    notes = [{k: v for k, v in deepcopy(claim).items() if k not in ('start', 'end')} for claim in old_claims if claim.get('kind') == 'ca_input']
    resolve = service.drafting.evidence.resolve
    register = {ref: resolve(case_id, ref) for ref in used_refs(content, claims + notes)}
    gaps = [g for g in proposal.candidate.get('gaps', []) if not g.startswith(MISSING_PREFIX)]
    gaps = list(dict.fromkeys(gaps + missing_fields(parts, content)))
    title = next(d.name for d in TeamConfig.model_validate(case.config_snapshot).template.sections if d.id == section_id)
    text = with_notes(render_text(section_id, title, parts, content, claims, gaps), notes, register)
    now = s.utcnow()
    envelope = deepcopy(new_env) | dict(
        parts=content, source_register=register, blocks=deepcopy(old_env.get('blocks') or []),
        ca_position=next((c.get('ca_position') for c in claims if c.get('kind') == 'ca_position'), None),
        update=dict(proposal_id=proposal.id, applied_by=request.actor, applied_at=now.isoformat(), kept=sorted(keep),
                    accepted=sorted(choosable - keep), figures=[c['key'] for c in proposal.changes if c['kind'] == 'figures']))
    candidate = proposal.candidate
    draft = service.repo.save(s.DraftVersion(
        case_id=case_id, section_id=section_id, parent_id=parent.id, text=text, claim_spans=[envelope] + claims + notes,
        document_ids=sorted({src['document_id'] for src in register.values() if src.get('document_id')}), config_hash=case.config_hash,
        prompt_version=candidate['prompt_version'], model_version=candidate['model_version'], template_version_id=candidate['template_version_id'],
        input_fingerprint=state.input_fingerprint, author=request.actor, gaps=gaps, ca_input_ids=list(parent.ca_input_ids),
        ca_edits=parent.ca_edits and bool(from_current)))
    for i, claim in enumerate(claims + notes):
        for ref in claim.get('evidence_ids', []):
            service.repo.save(s.Citation(case_id=case_id, evidence_id=ref, draft_id=draft.id, claim_or_cell=f'claim:{i}:{claim["id"]}'))
    service.repo.save(state.model_copy(update=dict(current_draft_id=draft.id, confirmed_draft_id=None, readiness='Drafted', editor_revision=state.editor_revision + 1)))
    service.repo.save(proposal.model_copy(update=dict(status='applied', decisions=dict(keep=sorted(keep), accepted=sorted(choosable - keep)),
                                                      resolved_by=request.actor, resolved_at=now, applied_draft_id=draft.id)))
    service.sections(case_id)
    return service.drafting.get(case_id, draft.id)


def dismiss(service, case_id, proposal_id, request):
    """Close a proposal without changing the section. The section stays marked until a proposal is applied."""
    proposal, *_ = current_proposal(service, case_id, proposal_id, request)
    service.repo.save(proposal.model_copy(update=dict(status='dismissed', resolved_by=request.actor, resolved_at=s.utcnow())))
    return overview(service, case_id)
