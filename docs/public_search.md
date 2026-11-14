# Public search and generation offers (B06)

B06 uses the pinned case catalogue and public identity to retrieve supporting evidence. Search is an explicit action; uploading/scanning still refreshes readiness without network calls. Production defaults to **off**. The saved-pack provider supplies repeatable offline evidence. Tavily is implemented as a disabled adapter; no SDK import, client construction, installation or paid call occurs in this release.

## Setup and API

Inject the provider at app construction, alongside the existing session factory and content storage:

```python
from backend.app.main import create_app
from backend.app.services.search import SavedPublicPackProvider

app = create_app(sessions=sessions, storage_root=storage_root,
                 search_provider=SavedPublicPackProvider())
```

Omit `search_provider` for off mode. The application never reads `TAVILY_API_KEY` or `SEARCH_PROVIDER`; an environment variable or API request cannot enable live calls. Pack roots and providers are operator configuration, never client-supplied paths/names. No search fallback happens silently.

| Route | Input | Result |
|---|---|---|
| `POST /cases/{case_id}/public-search` | `{"actor":"demo-ca","role":"CA"}` | Overall attempt, imported/deduplicated IDs, public documents, expected list, sections, requests and generation offers |
| `POST /cases/{case_id}/documents/{document_id}/confirm` | Same CA/actor body | Confirms current usable public evidence or an existing industry-code mapping and refreshes readiness |
| `GET /cases/{case_id}/generation-offers` | None | Available spread/industry offers and their source IDs/confirmation requirements |
| `GET /cases/{case_id}/readiness` | Existing B05 route | Persisted per-item search outcomes/attempts, statuses and completeness |
| `GET /cases/{case_id}/documents` | Existing B04 route | Stored document provenance including public URL/date and intake page metadata |

Bodies reject extra fields, including queries, deal text, provider names and approval flags. Only the CA role may search/confirm; roles remain a prototype switch, not authentication. Unknown cases return 404, invalid requests/references 422, non-CA actions 403, unconfigured persistence/storage 503. Provider/content failures are recorded as `failed` with safe messages (HTTP 200), not raw exception text.

Callers of `PublicSearchService` own the transaction. Routes serialize SQLite writes with `BEGIN IMMEDIATE`; all documents in a search attempt are imported in one savepoint. Failed batches retain an attempt but no new document rows; unreferenced hash blobs may remain after rollback. They are reusable on retry. No servers, watchers or background jobs are required.

## Identity and outcomes

`SearchProvider.search(PublicIdentity)` accepts only the public name plus `sgx_code`, `isin` and `lei`. Unknown identifier keys are discarded, known identifiers have format validation, and private/nonpublic cases do not call a provider. The query is precisely these identity values: no requested document type, deal terms, CA position, file text or internal fields.

Catalogue `public_support` determines permitted public evidence uses. Public suggestions require `public_search: true` in the pinned rules. Added this optional key for FIG bank disclosures, external releases and public news; old snapshots retain their hash and default to no suggestion search. A case-specific or dismissed type is not reactivated by retrieval. Confidential full reports are never query targets: valuation/lease input support is limited to public summaries returned by the identity search.

| Outcome | Meaning |
|---|---|
| `not run` | Off/disabled provider or no applicable public targets |
| `failed` | Provider, saved-pack integrity or evidence validation failed |
| `no match` | Attempt returned no matching usable evidence for this item |
| `found` | Matching accepted evidence is held and linked to the item |

Each eligible item's attempt includes provider, timestamp, outcome and matched document IDs/URL/original retrieval date/hash/cache label. A batch can find news while recording no match for a financial report. Internal/client-only items retain `not run` with no attempt. Suggested rows stay Suggested; their outcome and document links expose the find.

The latest attempt outcome is separate from document status: switching off, failing or finding no match never removes existing public evidence. An unresolved item remains a gap, never a statement that a document does not exist. The request list retains the B05 grouping and these search outcomes.

## Saved evidence, confirmation and versions

`demo/public_pack/esr-reit/manifest.yaml` retains its B02 source records. The new adjacent `search-index.yaml` adds explicit document-to-catalogue mappings; original source bytes and manifest are unchanged. Six sources are imported under content hashes with `origin=public`, `synthetic=false`, title, URL, original retrieval date, provider, cache label, period, scope and page references. The saved pack does not establish fresh internet coverage on a later replay.

The annual report maps to annual reports, audited statements (physical pages 127–225), ownership (10, 229–231), partial valuation (50, 72–73, 210–211) and partial lease profile (53). The agency release maps to the external-release suggestion plus partial catalogue rating evidence; it cannot fill the internal rating. Each news item has its own source scope so unrelated announcements do not supersede one another. This curated mapping is separate from B08's page retrieval/citation index.

The importer verifies hash/size, supported PDF/plain-text format, readability, page bounds, borrower content match and configured public mappings. Saved source files reject traversal/symlinks; wrong borrower/identifier packs return no match. Synthetic-labelled content cannot be imported as public evidence. External content is retained as data and never executed, sent as search instructions or interpreted as permission to access other files.

Confirmation needs a nonblank CA actor and current usable evidence with an intact content blob. Pending, rejected, superseded and cross-case records cannot be confirmed here. Confirmation is idempotent and retains the first actor/time. Public annual/financial/ownership inputs can meet mandatory requirements only after confirmation. Confirming a public valuation summary, portfolio lease disclosure or external rating never changes its limited coverage.

Same-case duplicate hashes retain the existing record's origin, mappings, conflicts and confirmation; search-attempt provenance records the rediscovered public URL/date. An earlier local upload is not silently relabelled public. Cross-case records remain separate. Newer same-scope public sources create revisions; older or changed same-period sources stay pending for manual review. Draft text, confirmed/current pointers and historical ES records are unchanged; B05 fingerprints expose Stale when relevant evidence changes. B13 still owns explicit working-version/redraft/reset behavior.

## Generation offers

Held usable annual/financial evidence offers a spread; configured business evidence offers an industry-code suggestion. Responses list source document IDs and pending source confirmations. Offers are not completed output: `execution_available=false`. B09 owns the actual validated spreading pipeline; this task does not invent spread values or an industry code. A separately supplied industry-code mapping can be CA-confirmed using the document confirmation route. Spreads require validation/current sources and industry codes require confirmation under the existing B05 rules.

## Disabled live adapter and interface verification

`TavilyProvider.search()` always records not run. Its SDK transport seam, request builder and response decoder are exercised only with canned clients. A later task carrying `approved_usd` must implement task-bound spend reservation/limits before wiring a real client. There is no runtime unlock in this release. No client dependency was installed or added to required offline dependencies.

Verified against the [official Python SDK reference](https://docs.tavily.com/sdk/python/reference) on 2026-11-10: `client.search` receives the identity query, basic/general search, disabled automatic parameters/answers/images, five results, raw text and a 20-second timeout. The adapter stores returned text with a hash and UTC retrieval date. Unclassified SDK text is partial public-news context, never automatically a complete report or internal rating. Errors are sanitized and missing borrower content is ignored.

The [Tavily terms](https://www.tavily.com/terms) govern access and usage limits. Its [retention guidance](https://help.tavily.com/articles/1612400809-storing-caching-retaining-output) permits cached output while requiring respect for publisher rights. This is an interface/terms review for the prototype, not authorization for a live call or redistribution of source content.

No result URL is fetched by this implementation: the saved provider reads bounded local pack files and the SDK decoder consumes supplied response text. Provenance URLs require HTTP(S) and reject literal private/local addresses, credentials and unusual ports. **This syntactic validator is not a network allowlist.** Any future direct downloader must resolve/check every target IP, pin connections against rebinding, enforce content/type/byte limits and revalidate every redirect before it can be enabled; B06 provides no arbitrary fetch path.

## Verification

`tests/test_search.py` exercises the actual tranche-one sources and six-file public pack, all modes, privacy allowlist, public/private coverage, confirmation, generation offers, retries/restarts, corrupt content, page/entity/type checks, malicious evidence text, old pins/dismissal, duplicates/cross-case isolation, Stale text preservation, API access and canned Tavily responses. All tests block sockets and DNS. No frontend exists or changes in B06.
