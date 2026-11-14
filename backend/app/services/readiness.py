"""Input completeness and draft display state, independent of generated prose."""
from hashlib import sha256
import json

from .. import schemas as s
from .gaps import GapService, key


def content_hash(draft, basis='text'):
    """What another section read from this draft: its computed parts only, or its wording with analyst added content."""
    envelope = draft.claim_spans[0] if draft.claim_spans else {}
    held = dict(parts=envelope.get('parts', {})) if basis == 'parts' else dict(text=draft.text, blocks=envelope.get('blocks', []))
    return sha256(json.dumps(held, sort_keys=True, default=str).encode()).hexdigest()


class ReadinessService:
    def __init__(self, repository):
        self.repository = repository

    def refresh(self, case_id, *, accepted_ca_inputs=None):
        gap_service = GapService(self.repository)
        snapshot = gap_service.refresh(case_id)
        case, config = snapshot.case, snapshot.config
        from .section_chat import accepted_inputs
        typed = accepted_inputs(self.repository, case_id) if accepted_ca_inputs is None else accepted_ca_inputs
        message_sections = {m.id: m.section_id for m in self.repository.list_for_case(s.ChatMessage, case_id)}
        previous = {v.section_id: v for v in self.repository.list_for_case(s.Section, case_id)}
        definitions = {d.id: d for d in config.template.sections}
        dependencies = {d.section_id: d for d in config.dependencies.items}
        computed = {}

        def visit(section_id):
            if section_id in computed:
                return computed[section_id]
            definition = definitions[section_id]
            rule = dependencies[section_id]
            applicable = definition.applicable_when.matches(case)
            deps = [visit(i) for i in rule.requires
                    if (not rule.applicable_only or definitions[i].applicable_when.matches(case))
                    and (not rule.mandatory_only or definitions[i].mandatory_when.matches(case))]
            freshness = [visit(i) for i in rule.freshness_requires if definitions[i].applicable_when.matches(case)]
            items = [e for e in snapshot.expected if e.applicable and section_id in e.section_ids]
            inputs = [snapshot.support[e.catalogue_id] for e in items if e.catalogue_id]
            gaps, mandatory_gaps = [], []
            for item in items:
                if gap_service.satisfied(snapshot, item):
                    continue
                if item.status == 'Dismissed' and not item.mandatory:
                    continue
                label = f'{snapshot.names[key(item)]}: {item.status}; evidence not yet complete.'
                gaps.append(label)
                if item.mandatory:
                    mandatory_gaps.append(label)
            for dep in deps:
                if dep.applicable and dep.completeness != 'full':
                    label = f'Section {dep.section_id} ({definitions[dep.section_id].name}): {dep.completeness}; ' + '; '.join(dep.gaps)
                    gaps.append(label)
                    mandatory_gaps.append(label)
            gates = [g for g in config.rules.draft_gates if g.section_id == section_id and g.when.matches(case)]
            blocked = False
            for gate in gates:
                if not any(snapshot.support[i].full for i in gate.any_inputs):
                    gaps.append(gate.reason)
                    mandatory_gaps.append(gate.reason)
                    blocked = True
            if definition.requires_supplied_internal_rating and not any(
                    snapshot.support[e.catalogue_id].full for e in items if e.catalogue_id and e.mandatory):
                blocked = True
                if not gates:
                    gaps.append('Supplied internal rating not yet complete; never infer it from external context.')
                    mandatory_gaps.append(gaps[-1])
            position_needed = definition.requires_ca_position or rule.ca_position
            if position_needed and not (case.ca_position and case.ca_position.strip()):
                gaps.append('CA position not yet stated; recommendation wording must follow the CA position.')
                mandatory_gaps.append(gaps[-1])
                blocked = True
            # Every dependency needs usable input before a synthesis can open.
            usable = any(v.usable for v in inputs) or any(e.document_ids for e in items if e.suggestion_id) or bool(deps)
            blocked |= any(dep.applicable and dep.completeness == 'none' for dep in deps)
            completeness = 'none' if blocked or not usable else 'partial' if mandatory_gaps else 'full'
            fingerprint = sha256(json.dumps(dict(
                applicable=applicable, inputs=[dict(id=e.catalogue_id,
                    documents=[(d.id, d.confirmed_by, d.conflict_status) for d in snapshot.support[e.catalogue_id].documents],
                    spreads=snapshot.support[e.catalogue_id].spread_ids,
                    full=snapshot.support[e.catalogue_id].full) for e in items if e.catalogue_id],
                suggestions=[(e.suggestion_id, e.document_ids) for e in items if e.suggestion_id],
                gaps=gaps, dependencies=[d.input_fingerprint for d in deps + freshness],
                position=case.ca_position if position_needed else None,
                **({'ca_inputs': sorted(v.id for v in typed if message_sections[v.message_id] == section_id)}
                   if any(message_sections[v.message_id] == section_id for v in typed) else {}),
                config_hash=case.config_hash), sort_keys=True).encode()).hexdigest()
            old = previous.get(section_id)
            readiness = {'none': 'Waiting for input', 'partial': 'Can draft (partial)', 'full': 'Can draft (full)'}[completeness]
            if old and old.current_draft_id:
                draft = self.repository.get(s.DraftVersion, old.current_draft_id)
                pins = draft.claim_spans[0].get('dependencies', {}) if draft.claim_spans else {}
                freshness_pins = draft.claim_spans[0].get('freshness_dependencies', {}) if draft.claim_spans else {}
                def moved(sid, pin):
                    other = previous.get(int(sid))
                    if not other:
                        return False
                    if 'content_hash' not in pin:
                        return other.current_draft_id != pin.get('draft_id')
                    # Pinned on what was read: a new version of the other section with the same content does not count.
                    return other.current_draft_id != pin.get('draft_id') and (not other.current_draft_id or content_hash(
                        self.repository.get(s.DraftVersion, other.current_draft_id), pin.get('basis')) != pin['content_hash'])
                changed_freshness = any(moved(sid, pin) for sid, pin in freshness_pins.items())
                changed_version = any(pin.get('draft_id') and previous.get(int(sid)) and
                    previous[int(sid)].current_draft_id != pin['draft_id'] for sid, pin in pins.items())
                if old.readiness == 'Stale' or draft.input_fingerprint != fingerprint or changed_version or changed_freshness or any(d.readiness == 'Stale' for d in deps + freshness):
                    readiness = 'Stale'
                elif old.confirmed_draft_id == old.current_draft_id:
                    readiness = 'CA confirmed'
                else:
                    readiness = 'Drafted'
            fields = dict(case_id=case_id, section_id=section_id, applicable=applicable,
                          na_reason=None if applicable else f'Case does not meet section rule: {definition.case_rule}.',
                          readiness=readiness if applicable else 'Not applicable',
                          completeness=completeness if applicable else 'none', gaps=gaps if applicable else [],
                          input_fingerprint=fingerprint)
            if old and old.current_draft_id and (old.input_fingerprint != fingerprint or
                    (readiness == 'Stale' and old.readiness != 'Stale')):
                fields['editor_revision'] = old.editor_revision + 1
            value = s.Section.model_validate((old.model_dump() if old else {}) | fields)
            computed[section_id] = self.repository.save(value)
            return computed[section_id]

        for section in config.template.sections:
            visit(section.id)
        return snapshot, [computed[d.id] for d in config.template.sections]
