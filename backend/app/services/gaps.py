"""Deterministic expected inputs; public retrieval/generation belongs to B06/B09.

Callers own the transaction and serialize writes. Support mappings in immutable
Document.intake are a service-to-service contract, never upload metadata hints.
"""
from dataclasses import dataclass, field

from .locks import require_working
from .. import schemas as s
from ..team_config import TeamConfig
from .intake import normalize, period_key


@dataclass
class Support:
    documents: list[s.Document] = field(default_factory=list)
    usable: bool = False
    full: bool = False
    details: list[str] = field(default_factory=list)
    spread_ids: list[str] = field(default_factory=list)


@dataclass
class GapSnapshot:
    case: s.Case
    config: TeamConfig
    expected: list[s.ExpectedDocument]
    support: dict[int, Support]
    names: dict[str, str]
    groups: dict[str, list[dict]]


def key(item):
    return f'catalogue:{item.catalogue_id}' if item.catalogue_id is not None else f'suggestion:{item.suggestion_id}'


def current_documents(documents, case):
    eligible = [d for d in documents if d.conflict_status in {'none', 'accepted'}
                and normalize(d.entity) == normalize(case.borrower_name)]
    superseded = {d.supersedes_id for d in eligible}
    return sorted((d for d in eligible if d.id not in superseded), key=lambda d: d.id)


def coverage(document, item):
    """Only explicit, page-bound secondary mappings can reuse report evidence."""
    if document.catalogue_id == item.id:
        return document.intake.get('coverage', 'full')
    for mapping in document.intake.get('catalogue_support', []):
        if (mapping.get('id') == item.id and mapping.get('coverage') in {'full', 'partial'}
                and mapping.get('pages') and all(type(p) is int and p > 0 for p in mapping['pages'])):
            return mapping['coverage']
    return None


class GapService:
    def __init__(self, repository):
        self.repository = repository

    def refresh(self, case_id):
        repo = self.repository
        case = repo.get(s.Case, case_id)
        config = TeamConfig.model_validate(case.config_snapshot)
        documents = repo.list_for_case(s.Document, case_id)
        current = current_documents(documents, case)
        old = {key(e): e for e in repo.list_for_case(s.ExpectedDocument, case_id)}
        support = {}
        for item in config.catalogue.items:
            result = support[item.id] = Support()
            for doc in current:
                extent = coverage(doc, item)
                if not extent:
                    continue
                # Public evidence only supports catalogue-approved uses.
                if doc.origin == 'public' and item.public_support == 'none':
                    continue
                result.documents.append(doc)
                if item.generation == 'spread':
                    # A file labelled spread is not a validated computation.
                    result.details.append('Spread validation has not been established by this file alone.')
                    continue
                result.usable = True
                complete = extent == 'full'
                if doc.origin == 'public':
                    complete &= item.public_support == 'full after confirmation' and bool(doc.confirmed_by)
                    if not doc.confirmed_by:
                        result.details.append('Public evidence awaits CA confirmation.')
                    if item.public_support in {'partial only', 'external only'}:
                        result.details.append('Public context is partial and cannot replace the required full/internal report.')
                if item.generation == 'industry code' and not doc.confirmed_by:
                    complete = False
                    result.details.append('Industry code awaits CA confirmation.')
                if extent != 'full':
                    result.details.append('Only partial evidence is held; the full report remains a gap.')
                result.full |= complete
            # Pending records explain the gap without replacing usable evidence.
            for doc in documents:
                if doc.catalogue_id == item.id and doc.conflict_status == 'pending':
                    result.details.append(f'Manual review: {doc.original_filename} ({doc.id}).')
        current_by_id = {d.id: d for d in current}
        spreads = sorted(repo.list_for_case(s.Spread, case_id), key=lambda spread: spread.id)
        for item in config.catalogue.items:
            if item.generation != 'spread':
                continue
            for spread in spreads:
                if (spread.validation_status != 'valid' or not spread.document_ids
                        or not all(ref in current_by_id for ref in spread.document_ids)):
                    continue
                sources = [current_by_id[ref] for ref in spread.document_ids]
                if not all(any(coverage(doc, source_item) for source_item in config.catalogue.items
                               if source_item.id in item.generation_inputs) for doc in sources):
                    continue
                if spread.version == 'bounded-spread-v1':
                    request = spread.values.get('request', {})
                    profile = config.analytics.spreading.get(request.get('profile'))
                    years = {str(period_key(d.period).year) for d in sources if period_key(d.period)}
                    if (not profile or request.get('scope') != profile.readiness_scope
                            or not years <= set(request.get('periods', []))):
                        continue  # Comparative-only or other-scope output does not close the current spread gap.
                result = support[item.id]
                result.usable = True
                result.spread_ids.append(spread.id)
                # Generation cannot launder an unconfirmed public input.
                result.full |= all(d.origin != 'public' or d.confirmed_by for d in sources)
                if not result.full:
                    result.details.append('Spread source public evidence awaits CA confirmation.')
        expected, names = [], {}
        for item in config.catalogue.items:
            identity = f'catalogue:{item.id}'
            previous = old.get(identity)
            applicable = item.applicable_when.matches(case)
            result = support[item.id]
            offer = None
            if item.generated and item.generation and any(support[i].usable for i in item.generation_inputs):
                offer = f'Generate {item.name.lower()} from held evidence; validation/confirmation remains required.'
            if not applicable:
                status = 'Not applicable'
            elif previous and previous.status == 'Dismissed':
                status = 'Dismissed'
            elif result.spread_ids or any(d.origin != 'public' for d in result.documents):
                status = 'Provided'
            elif result.documents:
                status = 'Found publicly'
            else:
                status = 'Can generate' if offer else 'Missing'
            fields = dict(case_id=case_id, catalogue_id=item.id, applicable=applicable,
                          mandatory=applicable and item.mandatory_when.matches(case),
                          reason=(f'Applies: {item.applies_when}. Supports ES sections {", ".join(map(str, item.sections))}.'
                                  if applicable else f'Case does not meet rule: {item.applies_when}.'),
                          alternative_group=item.alternative_group, usual_owner=item.owner_group,
                          section_ids=item.sections, status=status,
                          document_ids=[d.id for d in result.documents], generated_offer=offer)
            record = self._save(previous, fields)
            expected.append(record)
            names[identity] = item.name
        for suggestion in config.rules.suggestions:
            identity = f'suggestion:{suggestion.id}'
            previous = old.get(identity)
            matches = ((suggestion.when is not None and suggestion.when.matches(case))
                       or any(support[i].usable for i in suggestion.trigger_catalogue_ids))
            found = [d for d in current if d.suggestion_id == suggestion.id]
            if not matches and not found and previous is None:
                continue
            fields = dict(case_id=case_id, suggestion_id=suggestion.id, applicable=bool(matches or found),
                          mandatory=False, reason=suggestion.reason, usual_owner=suggestion.owner_group,
                          section_ids=suggestion.sections,
                          status='Dismissed' if previous and previous.status == 'Dismissed' else
                                 'Suggested' if matches or found else 'Not applicable',
                          document_ids=[d.id for d in found])
            expected.append(self._save(previous, fields))
            names[identity] = suggestion.name
        snapshot = GapSnapshot(case, config, expected, support, names, {})
        snapshot.groups = self._groups(snapshot)
        return snapshot

    def _save(self, previous, fields):
        # Preserve search attempts and explicit dismissal across recalculation.
        record = s.ExpectedDocument.model_validate((previous.model_dump() if previous else {}) | fields)
        return self.repository.save(record)

    def satisfied(self, snapshot, item):
        if not item.applicable:
            return True
        if item.alternative_group:
            group = next(g for g in snapshot.config.rules.alternatives if g.id == item.alternative_group)
            return sum(snapshot.support[i].full for i in group.members
                       if next(e for e in snapshot.expected if e.catalogue_id == i).applicable) >= group.minimum
        return snapshot.support[item.catalogue_id].full if item.catalogue_id else bool(item.document_ids)

    def _groups(self, snapshot):
        groups = {owner: [] for owner in ('RM', 'client', 'internal team')}
        for item in snapshot.expected:
            if not item.applicable or self.satisfied(snapshot, item):
                continue
            details = snapshot.support[item.catalogue_id].details if item.catalogue_id else []
            # Dismissal suppresses optional requests, never mandatory gaps.
            if item.status == 'Dismissed' and not item.mandatory:
                continue
            groups[item.usual_owner].append(dict(
                id=item.id, name=snapshot.names[key(item)], catalogue_id=item.catalogue_id,
                suggestion_id=item.suggestion_id, status=item.status, mandatory=item.mandatory,
                alternative_group=item.alternative_group, reason=item.reason,
                section_ids=item.section_ids, search_outcome=item.search_outcome,
                search_attempts=item.search_attempts, details=list(dict.fromkeys(details)),
                generated_offer=item.generated_offer, dismiss_reason=item.dismiss_reason,
                note='Dismissed; mandatory gap remains open (no submission override).' if item.status == 'Dismissed'
                     else 'Required evidence not yet complete.' if item.mandatory else 'Optional supporting evidence requested.'))
        return groups

    def dismiss(self, case_id, expected_id, *, actor, reason):
        require_working(self.repository, case_id)
        if not actor.strip() or not reason.strip():
            raise ValueError('Dismissal requires an actor and a nonblank reason')
        record = self.repository.get(s.ExpectedDocument, expected_id)
        if record.case_id != case_id:
            raise ValueError('Expected document belongs to another case')
        self.repository.save(s.ExpectedDocument.model_validate(record.model_dump() | dict(
            status='Dismissed', dismiss_reason=reason.strip(), confirmed_by=actor.strip())))
        return self.refresh(case_id)

    def restore(self, case_id, expected_id):
        require_working(self.repository, case_id)
        record = self.repository.get(s.ExpectedDocument, expected_id)
        if record.case_id != case_id:
            raise ValueError('Expected document belongs to another case')
        self.repository.save(record.model_copy(update=dict(status='Missing', dismiss_reason=None, confirmed_by=None)))
        return self.refresh(case_id)


def request_list(snapshot):
    """Plain text export: no ES layout/template claim, no executable spreadsheet cells."""
    lines = [f'WB Credit document request list — {snapshot.case.borrower_name}',
             f'Generated: {s.utcnow().date().isoformat()} (UTC)',
             'Gaps describe evidence not yet complete; they do not assert that a document does not exist.',
             'Alternative-group items require the configured minimum, not every listed member.']
    for owner, items in snapshot.groups.items():
        lines.extend(['', owner])
        if not items:
            lines.append('No open requests.')
        for item in items:
            lines.extend([f'- {item["name"]} [{item["status"]}; {"mandatory" if item["mandatory"] else "optional"}]',
                          f'  Why: {item["reason"]}', f'  ES sections: {", ".join(map(str, item["section_ids"]))}',
                          f'  Public search: {item["search_outcome"]}.', f'  {item["note"]}'])
            if item['alternative_group']:
                lines.append(f'  Alternative group: {item["alternative_group"]}.')
            for detail in item['details']:
                lines.append(f'  {detail}')
            if item['generated_offer']:
                lines.append(f'  {item["generated_offer"]}')
            if item['dismiss_reason']:
                lines.append(f'  Dismissal reason: {item["dismiss_reason"]}')
    return '\n'.join(lines) + '\n'
