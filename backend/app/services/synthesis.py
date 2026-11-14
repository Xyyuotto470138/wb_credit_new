"""B12 dependency snapshots; source-backed context, never a credit decision."""
from copy import deepcopy
from decimal import Decimal

from .. import schemas as s
from ..retrieval.service import identity

SECTIONS = {9, 11, 14}
VERSION = 'b12-synthesis-v1'


def dependencies(service, case, config, section_id, states):
    """Require ordered, current prerequisite drafts, allowing explicit partials.

    Readiness describes input completeness, not whether a draft actually exists.
    Pin both dimensions and carry unresolved draft gaps separately.
    """
    rule = next(r for r in config.dependencies.items if r.section_id == section_id)
    definitions = {d.id: d for d in config.template.sections}
    states = {st.section_id: st for st in states}
    snapshots, claims, sources, gaps, seen = {}, [], {}, [], {}
    for sid in rule.requires:
        definition, state = definitions[sid], states[sid]
        if rule.applicable_only and not state.applicable:
            snapshots[str(sid)] = dict(status='Not applicable', reason=state.na_reason)
            continue
        if rule.mandatory_only and not definition.mandatory_when.matches(case):
            continue
        if not state.current_draft_id or state.completeness == 'none':
            raise ValueError(f'Section {section_id} requires a usable current draft of section {sid}; draft prerequisites first.')
        draft = service.repo.get(s.DraftVersion, state.current_draft_id)
        if draft.case_id != case.id or draft.section_id != sid or draft.config_hash != case.config_hash:
            raise ValueError(f'Section {sid}: dependency draft ownership/configuration mismatch')
        if state.readiness == 'Stale' or draft.input_fingerprint != state.input_fingerprint:
            raise ValueError(f'Section {sid}: dependency is Stale or dependency version changed; explicit redraft/review required')
        if not draft.claim_spans or draft.claim_spans[0].get('kind') != 'draft_metadata':
            raise ValueError(f'Section {sid}: reviewed structured dependency content required')
        if draft.ca_edits and not meta_edits(draft):
            raise ValueError(f'Section {sid}: CA-edited dependency requires reviewed structured claims before synthesis')
        meta = draft.claim_spans[0]
        for ancestor, pin in meta.get('dependencies', {}).items():
            current = states[int(ancestor)]
            if pin.get('draft_id') and current.current_draft_id != pin['draft_id']:
                raise ValueError(f'Section {sid}: dependency version changed; explicit redraft/review required')
        snapshots[str(sid)] = dict(draft_id=draft.id, input_fingerprint=draft.input_fingerprint,
            completeness=state.completeness, readiness=state.readiness, gaps=draft.gaps,
            template_version_id=draft.template_version_id)
        gaps.extend(f'Section {sid}: {g}' for g in draft.gaps)
        if not draft.claim_spans[1:]:
            gaps.append(f'Section {sid}: no supported claims in prerequisite draft.')
        for original in draft.claim_spans[1:]:
            # Consume reviewed spans, not arbitrary surrounding prose or instructions.
            start, end = original.get('start'), original.get('end')
            if not isinstance(start, int) or not isinstance(end, int) or original['text'] not in draft.text[start:end]:
                raise ValueError(f'Section {sid}: dependency claim/text mismatch')
            refs = original.get('evidence_ids', [])
            resolved = [service.evidence.resolve(case.id, ref) for ref in refs]
            if any(not src['current'] for src in resolved):
                raise ValueError(f'Section {sid}: dependency source superseded; explicit redraft/review required')
            if not refs and original.get('kind') != 'case_input':
                gaps.append(f'Section {sid}: unsupported uncited claim withheld.')
                continue
            if original.get('kind') == 'case_input' and original.get('case_input') != dict(case_id=case.id, new_to_bank=True):
                raise ValueError(f'Section {sid}: unsupported case input')
            value_ids = set(original.get('computed_value_ids', []))
            if original.get('computed_value_id'):
                value_ids.add(original['computed_value_id'])
            for value_id in value_ids:
                value = service.repo.get(s.ComputedValue, value_id)
                operands = {r for group in value.operand_evidence_ids.values() for r in group}
                if value.case_id != case.id or not value.validated or value.value is None or value.gaps or not operands <= set(refs):
                    raise ValueError(f'Section {sid}: invalid dependency computed value')
                if original.get('computed_value_id') == value_id and original.get('value') != value.model_dump(mode='json'):
                    raise ValueError(f'Section {sid}: dependency computed value changed')
            signature = identity(original['text'], sorted(refs), sorted(value_ids))
            origin_ids = original.get('origin_claim_ids', [original['id']])
            if signature in seen:
                seen[signature]['origin_claim_ids'] = sorted(set(seen[signature]['origin_claim_ids']) | set(origin_ids))
                continue
            claim = deepcopy(original)
            claim.update(id='dependency-' + signature, dependency_section_id=sid, dependency_draft_id=draft.id,
                         dependency_claim_id=original['id'], origin_claim_ids=origin_ids)
            seen[signature] = claim
            # Retain facility field semantics when lifting a cell into narrative context.
            if claim['kind'] == 'facility':
                claim['text'] = f"{claim['facility']} / {claim['field']}: {claim['text']}"
                claim['kind'] = 'narrative'
            claims.append(claim)
            sources.update({src['evidence_id']: src for src in resolved})
    return snapshots, claims, sources, gaps


def reviewed_judgments(section_id, inherited, rules):
    """Reviewed offline risk wording requires every named supporting claim."""
    by_id = {key: c for c in inherited for key in c['origin_claim_ids']}
    result = []
    for rule in rules:
        if rule['section_id'] != section_id or not set(rule['requires']) <= set(by_id):
            continue
        supporting = [by_id[key] for key in rule['requires']]
        result.append(dict(id=rule['id'], kind='risk_mitigant', text=rule['text'],
            evidence_ids=sorted({ref for c in supporting for ref in c['evidence_ids']}),
            supporting_claim_ids=[c['id'] for c in supporting],
            dependency_draft_ids=sorted({c['dependency_draft_id'] for c in supporting})))
    return result


def repayment_findings(claims):
    """Deterministic interpretation of validated Python DSCR, with operand links."""
    findings = []
    for claim in claims:
        value = claim.get('value', {})
        if not value.get('metric', '').startswith('projection/') or not value['metric'].endswith('/dscr'):
            continue
        if Decimal(value['value']) >= 1:
            continue
        findings.append(dict(id='shortfall-' + value['id'], kind='computed_summary',
            evidence_ids=claim['evidence_ids'], computed_value_ids=[value['id']],
            text=f"Property cash available for debt service is below scheduled debt service in {value['period']} "
                 'under the supplied projection. Property-only repayment is insufficient in that year; '
                 'additional repayment funding requires evidence. This is a property scenario, not a consolidated group forecast.'))
    return findings


def meta_edits(draft):
    """Only version-service edits with per-claim CA provenance can be consumed."""
    return draft.claim_spans[0].get('edit_format') in {'b13-claim-edits-v1', 'b24-chat-v1'} and all(
        not c.get('ca_edit') or (c['ca_edit'].get('actor') and c['ca_edit'].get('recorded_at')
        and (c['ca_edit'].get('replacement') == c['text'] or
             c.get('facility') and c.get('field') and c['text'] ==
             f"{c['facility']} / {c['field']}: {c['ca_edit'].get('replacement')}")) for c in draft.claim_spans[1:])
