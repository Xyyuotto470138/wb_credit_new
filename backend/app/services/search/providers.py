"""Saved-pack/off providers and a deliberately disabled Tavily adapter."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import yaml

from ...schemas import utcnow
from ..intake import MAX_BYTES, normalize, safe_filename
from .contracts import PublicResult, SearchResult, entity_matches

DEFAULT_PACK = Path(__file__).resolve().parents[4] / 'demo/public_pack/esr-reit'


class OffProvider:
    name = 'off'

    def search(self, public_identity):
        return SearchResult(outcome='not run', reason='Public search is switched off.')


class SavedPublicPackProvider:
    name = 'saved-pack'

    def __init__(self, pack_root=DEFAULT_PACK):
        self.root = Path(pack_root).resolve()

    def search(self, public_identity):
        try:
            manifest = yaml.safe_load((self.root / 'manifest.yaml').read_text())
            if not entity_matches(public_identity, manifest['borrower']['name']):
                return SearchResult(outcome='no match', reason='No matching borrower in the saved public pack.')
            for field in ('sgx_code', 'isin', 'lei'):
                supplied = getattr(public_identity, field)
                if supplied and supplied != manifest['borrower'].get(field):
                    return SearchResult(outcome='no match', reason='Public identifiers do not match the saved pack.')
            index = yaml.safe_load((self.root / 'search-index.yaml').read_text())
            results = []
            for source in manifest['documents']:
                mapping = index['documents'].get(source['id'])
                if not mapping:
                    continue
                filename = safe_filename(source['file'])
                path = self.root / filename
                if path.is_symlink() or path.resolve().parent != self.root or path.stat().st_size > MAX_BYTES:
                    raise ValueError('Invalid saved source')
                content = path.read_bytes()
                if len(content) != source['bytes'] or source['media_type'] != 'application/pdf':
                    raise ValueError('Invalid saved source')
                results.append(PublicResult(
                    title=source['title'], url=source['url'],
                    retrieved_at=datetime.fromisoformat(source['retrieved_at']).replace(tzinfo=timezone.utc),
                    entity=source['entity'], period=source.get('period_end', source['date']),
                    filename=filename, content=content, content_hash=source['sha256'],
                    media_type=source['media_type'], cached=True, source_id=source['id'],
                    page_references=source['evidence'], **mapping))
            return SearchResult(outcome='found' if results else 'no match', results=results,
                                reason='Saved public pack; original retrieval dates retained.')
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
            return SearchResult(outcome='failed', reason='Saved public pack failed integrity or metadata checks; review the pack.')


class TavilyProvider:
    """Production search remains locked in B06, independent of keys/environment.

    The SDK request/response adapter is implemented for offline contract tests.
    A later approved task must add task-bound spend reservation before enabling
    this route. This release neither imports nor constructs a Tavily client.
    """
    name = 'tavily'

    def search(self, public_identity):
        return SearchResult(outcome='not run', reason='Live Tavily is disabled pending an approved paid-run task and spend controls.')

    def _search_with_client(self, public_identity, client):
        """SDK transport seam for canned-client tests; disabled search never calls it."""
        try:
            response = client.search(**self.request_parameters(public_identity))
            return self.decode_response(public_identity, response)
        except Exception:
            return SearchResult(outcome='failed', reason='Public search failed; retry or use the saved pack.')

    @staticmethod
    def request_parameters(public_identity):
        return dict(query=public_identity.query, search_depth='basic', topic='general',
                    auto_parameters=False, max_results=5, include_answer=False,
                    include_raw_content='text', include_images=False, timeout=20)

    @staticmethod
    def decode_response(public_identity, response, *, retrieved_at=None):
        """Adapt supplied SDK data only. Never fetch/execute URLs or content.

        Search snippets/raw text are partial public context, not verified complete
        annual reports/statements or ratings. B08/later review can classify them.
        """
        retrieved_at = retrieved_at or utcnow()
        try:
            rows = response['results']
            if not isinstance(rows, list) or len(rows) > 5:
                raise ValueError('Invalid search response')
            results = []
            for row in rows:
                text = row.get('raw_content') or row.get('content') or ''
                if not isinstance(text, str) or not isinstance(row.get('title'), str):
                    raise ValueError('Invalid content')
                if not text.strip() or normalize(public_identity.name) not in normalize(row['title'] + ' ' + text):
                    continue
                content = text.encode('utf-8')
                digest = sha256(content).hexdigest()
                results.append(PublicResult(title=row['title'], url=row['url'], retrieved_at=retrieved_at,
                    entity=public_identity.name, period=retrieved_at.date().isoformat(),
                    filename=f'public-context-{digest[:12]}.txt', content=content, content_hash=digest,
                    media_type='text/plain', suggestion_id='public_news', coverage='partial',
                    scope=f'public-context:{digest}', source_id=digest,
                    page_references=[{'topic': 'provider_text', 'normalized_pages': [1]}]))
            return SearchResult(outcome='found' if results else 'no match', results=results,
                                reason='Public search context; source classification and completeness require review.')
        except (ValueError, KeyError, TypeError, AttributeError):
            return SearchResult(outcome='failed', reason='Public search response failed validation.')
