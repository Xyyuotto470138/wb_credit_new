"""Transactional public-evidence import and explicit CA confirmation."""
from ..locks import require_working
from hashlib import sha256
from pathlib import Path

import fitz

from ... import schemas as s
from ..gaps import GapService, current_documents, key
from ..intake import MAX_BYTES, normalize, period_key, safe_filename
from ..readiness import ReadinessService
from .contracts import PublicIdentity, SearchResult, entity_matches
from .providers import OffProvider


class PublicSearchService:
    def __init__(self, repository, storage_root, provider=None):
        self.repository = repository
        self.root = Path(storage_root).resolve()
        self.provider = provider if provider is not None else OffProvider()

    @staticmethod
    def eligible(snapshot, expected):
        if not snapshot.case.public_entity or not expected.applicable or expected.status == 'Dismissed':
            return False
        if expected.catalogue_id:
            item = next(i for i in snapshot.config.catalogue.items if i.id == expected.catalogue_id)
            return item.public_support != 'none'
        return any(i.id == expected.suggestion_id and i.public_search for i in snapshot.config.rules.suggestions)

    def search(self, case_id):
        require_working(self.repository, case_id)
        repo = self.repository
        snapshot = GapService(repo).refresh(case_id)
        targets = [e for e in snapshot.expected if self.eligible(snapshot, e)]
        if not targets:
            return self._response(case_id, SearchResult(outcome='not run', reason='No applicable public search targets.'), [])
        try:
            identity = PublicIdentity.from_case(snapshot.case)
            result = self.provider.search(identity)
        except Exception:
            # Never expose provider exceptions (may contain keys/query/headers).
            result = SearchResult(outcome='failed', reason='Public search failed; retry or use the saved pack.')
        imported = []
        if result.outcome == 'found':
            try:
                # Validate the complete batch before any new records are visible.
                selected = []
                for source in result.results:
                    primary = next((e for e in snapshot.expected if e.catalogue_id == source.catalogue_id
                                    and e.suggestion_id == source.suggestion_id), None)
                    # Saved packs may contain optional sources outside this pinned
                    # config or dismissed/non-applicable types. Do not undo that choice.
                    if primary and (not primary.applicable or primary.status == 'Dismissed'):
                        continue
                    if source.suggestion_id and (primary is None or not self.eligible(snapshot, primary)):
                        continue
                    selected.append(source)
                validated = [(source, self._validate(snapshot, source, identity)) for source in selected]
                with repo.session.begin_nested():
                    for source, page_count in validated:
                        imported.append(self._import(snapshot, source, page_count))
                if not imported:
                    result = SearchResult(outcome='no match', reason='No applicable public evidence accepted from this attempt.')
            except Exception:
                imported = []
                result = SearchResult(outcome='failed', reason='Public evidence failed validation; no sources from this attempt were imported.')
        sources_by_hash = {source.content_hash: source for source in result.results}
        refreshed = GapService(repo).refresh(case_id)
        by_key = {key(e): e for e in refreshed.expected}
        for target in targets:
            item = by_key[key(target)]
            linked = [d for d in imported if d.id in item.document_ids]
            outcome = result.outcome
            if outcome == 'found' and not linked:
                outcome = 'no match'
            attempt = dict(provider=self.provider.name, attempted_at=result.attempted_at.isoformat(),
                           outcome=outcome, reason=result.reason if outcome != 'no match' else 'No matching evidence for this public input in this attempt.',
                           document_ids=[d.id for d in linked],
                           sources=[dict(document_id=d.id, url=sources_by_hash[d.content_hash].url,
                                         retrieved_at=sources_by_hash[d.content_hash].retrieved_at.isoformat(),
                                         content_hash=d.content_hash, cached=sources_by_hash[d.content_hash].cached,
                                         held_origin=d.origin) for d in linked])
            repo.save(item.model_copy(update={'search_outcome': outcome, 'search_attempts': [*item.search_attempts, attempt]}))
        return self._response(case_id, result, imported)

    def _validate(self, snapshot, source, identity):
        if not entity_matches(identity, source.entity) or not period_key(source.period):
            raise ValueError('Public source entity/period mismatch')
        safe_filename(source.filename)
        if len(source.content) > MAX_BYTES or sha256(source.content).hexdigest() != source.content_hash:
            raise ValueError('Invalid source content')
        primary = next((e for e in snapshot.expected if e.catalogue_id == source.catalogue_id
                        and e.suggestion_id == source.suggestion_id), None)
        # Import public sources only where the pinned catalogue explicitly permits it.
        if primary is None or not self.eligible(snapshot, primary):
            raise ValueError('Public source mapping is not permitted')
        for mapping in source.catalogue_support:
            item = next((i for i in snapshot.config.catalogue.items if i.id == mapping.id), None)
            if item is None or item.public_support == 'none':
                raise ValueError('Private input cannot be mapped from public search')
        if source.media_type == 'application/pdf':
            if not source.content.startswith(b'%PDF-') or Path(source.filename).suffix.lower() != '.pdf':
                raise ValueError('Invalid PDF content')
            with fitz.open(stream=source.content, filetype='pdf') as pdf:
                if pdf.needs_pass or not len(pdf) or len(pdf) > 2000:
                    raise ValueError('Unreadable public PDF')
                page_count = len(pdf)
                text = '\n'.join(pdf[i].get_text()[:60000] for i in range(min(3, len(pdf))))
        else:
            if Path(source.filename).suffix.lower() != '.txt':
                raise ValueError('Invalid text content')
            text = source.content.decode('utf-8')
            if '\x00' in text:
                raise ValueError('Binary text content')
            page_count = 1
        if normalize(identity.name) not in normalize(text):
            raise ValueError('Borrower not identified in public source content')
        if 'SYNTHETIC DEMO DATA' in text.upper():
            raise ValueError('Synthetic file cannot be represented as public evidence')
        pages = [p for m in source.catalogue_support for p in m.pages]
        for ref in source.page_references:
            pages.extend(ref.get('pdf_pages', ref.get('normalized_pages', [])))
        if not pages or any(type(p) is not int or not 1 <= p <= page_count for p in pages):
            raise ValueError('Invalid public page references')
        return page_count

    def _import(self, snapshot, source, page_count):
        repo, case = self.repository, snapshot.case
        documents = repo.list_for_case(s.Document, case.id)
        duplicate = next((d for d in documents if d.content_hash == source.content_hash), None)
        if duplicate:
            self._verify_blob(duplicate)
            # Immutable classification, confirmation, rejection and origin survive.
            return duplicate
        stream = [d for d in documents if d.origin == 'public' and
                  (d.catalogue_id, d.suggestion_id, d.intake.get('scope')) ==
                  (source.catalogue_id, source.suggestion_id, source.scope)]
        current = current_documents(stream, case)
        previous = max(current, key=lambda d: (period_key(d.period), d.revision), default=None)
        conflict = previous is not None and period_key(source.period) <= period_key(previous.period)
        destination = self.root / source.content_hash[:2] / source.content_hash
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.parent.resolve().parent != self.root:
            raise ValueError('Invalid storage directory')
        try:
            with destination.open('xb') as output:
                output.write(source.content)
        except FileExistsError:
            if destination.is_symlink() or sha256(destination.read_bytes()).hexdigest() != source.content_hash:
                raise ValueError('Stored content failed integrity validation')
        return repo.save(s.Document(case_id=case.id, catalogue_id=source.catalogue_id,
            suggestion_id=source.suggestion_id, entity=source.entity, period=source.period,
            content_hash=source.content_hash, storage_path=str(destination),
            revision=max((d.revision for d in stream), default=0) + 1,
            supersedes_id=previous.id if previous and not conflict else None,
            origin='public', synthetic=False, original_filename=source.filename,
            url=source.url, retrieved_at=source.retrieved_at, conflict_status='pending' if conflict else 'none',
            intake=dict(provider=self.provider.name, cached=source.cached, source_id=source.source_id,
                        title=source.title, scope=source.scope, coverage=source.coverage,
                        catalogue_support=[m.model_dump() for m in source.catalogue_support],
                        page_references=source.page_references, page_count=page_count,
                        status='manual_review' if conflict else 'classified',
                        issues=['Older or changed same-period public evidence requires review.'] if conflict else [])))

    @staticmethod
    def _verify_blob(document):
        path = Path(document.storage_path)
        if (path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES
                or sha256(path.read_bytes()).hexdigest() != document.content_hash):
            raise ValueError('Stored content failed integrity validation')

    def confirm(self, case_id, document_id, *, actor, role='CA'):
        require_working(self.repository, case_id)
        if role != 'CA' or not actor.strip():
            raise ValueError('Public/industry evidence confirmation requires the CA and actor')
        repo = self.repository
        snapshot = GapService(repo).refresh(case_id)
        document = repo.get(s.Document, document_id)
        industry = any(i.id == document.catalogue_id and i.generation == 'industry code'
                       for i in snapshot.config.catalogue.items)
        if document.case_id != case_id:
            raise ValueError('Document belongs to another case')
        if document.origin != 'public' and not industry:
            raise ValueError('This route confirms only public evidence or industry code mappings')
        if document.id not in {d.id for d in current_documents(repo.list_for_case(s.Document, case_id), snapshot.case)}:
            raise ValueError('Resolve pending/rejected/superseded evidence before confirmation')
        self._verify_blob(document)
        if not document.confirmed_by:
            repo.save(document.model_copy(update={'confirmed_by': actor.strip(), 'confirmed_at': s.utcnow()}))
        return self._response(case_id)

    def _response(self, case_id, result=None, documents=()):
        gaps, sections = ReadinessService(self.repository).refresh(case_id)
        return dict(case_id=case_id, provider=self.provider.name,
                    search=result.model_dump(mode='json', exclude={'results'}) if result else None,
                    document_ids=[d.id for d in documents],
                    public_documents=[d.model_dump(mode='json') for d in self.repository.list_for_case(s.Document, case_id)
                                      if d.origin == 'public'],
                    expected_documents=[e.model_dump(mode='json') | dict(name=gaps.names[key(e)],
                        satisfied=GapService(self.repository).satisfied(gaps, e)) for e in gaps.expected],
                    sections=[v.model_dump(mode='json') for v in sections], gaps=gaps.groups,
                    generation_offers=generation_offers(gaps))


def generation_offers(snapshot):
    offers = []
    for expected in snapshot.expected:
        if not expected.generated_offer or not expected.applicable or expected.status == 'Dismissed':
            continue
        item = next(i for i in snapshot.config.catalogue.items if i.id == expected.catalogue_id)
        if snapshot.support[item.id].full:
            continue
        sources = {d.id: d for i in item.generation_inputs for d in snapshot.support[i].documents}
        offers.append(dict(expected_id=expected.id, catalogue_id=item.id, kind=item.generation,
                           description=expected.generated_offer, source_document_ids=sorted(sources),
                           source_confirmation_pending=any(d.origin == 'public' and not d.confirmed_by for d in sources.values()),
                           requires_validation=item.generation == 'spread', requires_ca_confirmation=True,
                           execution_available=False,
                           note='Offer only; no generated output or completed validation is implied.'))
    return offers
