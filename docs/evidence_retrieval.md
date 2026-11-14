# Page evidence retrieval (B08)

B08 indexes held bytes and retrieves source context without model/search calls or network access. It does not draft, validate financial values, confirm evidence, close readiness gaps or change an ES. B09 owns extraction/spreading, B11/B12 claim validation/drafting, B14 the section source UI and S01 optional model usefulness scoring.

## Service and persistence

`EvidenceService(repository, storage_root)` uses the case's immutable team configuration. Callers own the transaction; serialize writers with SQLite `BEGIN IMMEDIATE`, as the API does. Indexing is explicit or lazy on a retrieval POST. Upload/folder/search services keep their existing behavior; first retrieval indexes their stored document versions.

`EvidenceIndex` is an additive, append-only table created by `create_database()`. It pins the normalizer version, source document version, evidence IDs, source locators and extraction gaps. Existing case/config/document pins remain unchanged. Evidence IDs deterministically hash case/document/content hash, normalizer version, original page and region. Identical bytes in another case have different IDs. Repeated indexing and process restarts reuse the same index, including failed-format gaps. A parser-version change creates a new index; old page and region references still resolve against their original index. Do not change normalization semantics without incrementing `VERSION`.

Every indexing attempt and source resolution verifies file location, regular-file status, byte limit and SHA-256 against configured content storage, including cached indexes. Unknown, cross-case and non-indexed evidence IDs are rejected. A later source revision never rewrites existing evidence. Current retrieval excludes superseded, pending/rejected and wrong-entity inputs; explicit historical citation resolution still returns the original text with `current: false` and the conflict status. It cannot substitute an old source into current retrieval.

## Location and table conventions

| Format | Citation page/region | Preserved context |
|---|---|---|
| PDF | Original one-based physical page; `whole` or a validated original-page bounding box | Complete page text from PyMuPDF plus original PDF navigation. PDF tables are not flattened into guessed financial rows. Curated multi-page source references include whole companion pages as review context. |
| DOCX | Normalized body-block ordinal; headers/footers have named package-part regions | A paragraph or an entire outer table, including nested tables, cell text, grid spans and vertical merges. These are normalized locations, not Word print pages. |
| XLSX | Normalized worksheet ordinal, sheet name and cell range | Whole worksheet, all rows, merged ranges and formula locations. Formula expressions remain source text; they are never executed or treated as recalculated values. |
| CSV | Normalized page 1, whole table | Original text and complete parsed rows, including quoted multiline cells. |
| TXT / EML | One-based form-feed-separated normalized pages | Complete text/plain content; email headers accompany the body. Attachments require separate upload and are a named gap. HTML-only email is a review gap. |

Printed PDF labels come only from stored, unambiguous page-reference mappings or embedded PDF labels. Unknown labels stay null. Physical page numbers never become invented printed labels. Region views do not infer separate left/right printed-page labels.

The region API takes `[x0, y0, x1, y1]` in unrotated original PyMuPDF page points (including rotated PDFs); locators carry the page rotation separately. B09 must retain this original-page mapping when producing split/cropped files. Regions retain a parent evidence ID and whole-page text, even when a crop cuts a table. Section retrieval ranks whole units, never region fragments. Blank/scanned pages, unreadable/encrypted sources, oversized whole units and unsupported formats produce named gaps; there is no OCR or silent truncation. Original bytes remain available for manual checking.

This is conservative source preservation, not automatic table-boundary recognition. Curated references preserve known facing/spanning tables (including ESR annual-report pages 72–73). For unannotated multi-page tables, review the original document; B08 does not infer table continuation. Companion pages are explicitly `review_context_only`, not independent support for the section. B09 must use validated operands before arithmetic.

Limits: 25 MiB source; existing 100 MiB/5,000-entry Office archive guard; 2,000 PDF pages/indexed units; 8 million extracted characters per document; 500,000 per whole unit; 200,000 worksheet/CSV cells; 1 million returned text characters including companion pages. A unit exceeding the response budget is withheld with a gap, not shortened.

## Selection and ranking

Retrieval uses only current documents whose normalized entity matches the case borrower and whose report period is known. It filters by the pinned section's applicable catalogue/suggestion input map. Public evidence cannot support private-only inputs; secondary catalogue mappings apply only to their explicit pages. External rating and partial public valuation/lease context retain their limits. Confirmation is displayed separately; retrieval does not establish readiness or replace required internal/full reports.

Optional `periods` matches **document reporting periods**, with `FY2025`, `2025` and `2025-12-31` equivalent, and quarterly periods mapped to quarter end. Omitting it permits the current report in each type/scope stream, with every result's period displayed. An annual report can contain observations on other dates: source-reference `as_of` dates are retained separately and never relabelled as the requested reporting period. `scope` is an exact stream filter, and `document_ids` narrows eligible current documents; neither bypasses case, period, version or section checks.

Explicit query keywords require at least one overlap. An empty query ranks using the configured section name/main inputs and permits input-type support without a keyword match. Score is ten per distinct matched token, plus two for full source coverage or one for partial coverage. Decimals remain intact; thousands separators normalize for matching. Ties use document ID, original page and region, so ordering is stable across restart. The score is inspectable and deterministic; it is neither semantic usefulness scoring nor proof that a claim is supported.

Returned content is untrusted source data. Strings resembling instructions, shell commands, URLs or markup are retained as quoted evidence only. The service has no execution, fetching or model capability. Downstream callers must keep source text out of instruction roles, escape it when rendering, and validate claims/citations/figures independently.

## HTTP contracts

All paths start `/cases/{case_id}`. No new authentication/role claim is made; existing prototype case scoping applies.

| Method/path | Input / result |
|---|---|
| `POST /documents/{document_id}/index` | Append/reuse index; returns evidence IDs, locators and named extraction gaps. Can inspect pending/history without making it eligible for retrieval. |
| `POST /sections/{section_id}/evidence` | JSON `{ "query": "aggregate leverage", "periods": ["FY2025"], "limit": 12 }`; optional `document_ids`, `scope`; limit 1–50. Returns whole evidence units, support mappings, scores, labels and gaps. |
| `GET /evidence/{evidence_id}` | Read-only exact source resolution, including locator, report/observation dates, document revision/hash, public URL/retrieval/cache/confirmation flags, synthetic label and content/preview links. |
| `POST /evidence/{evidence_id}/regions` | JSON `{ "bbox": [0, 0, 500, 600] }` against an indexed whole PDF page; idempotently persists an original-page region citation with parent context. |
| `GET /citations/{citation_id}` | Resolves an existing B01 claim/cell Citation to indexed document evidence. B24 owns CA-input citation behavior. |

HTTP 404 means unknown/cross-case/unindexed reference; 409 means source integrity failure; 422 means invalid filter/region; 503 means storage/persistence is not configured. Retrieval with no usable matches returns 200 with a named gap. Integrity failures during batch retrieval withhold the affected document and expose a gap; they never return cached evidence from changed bytes.

`content_url` reuses B07's hash-checked source download. PDF `preview_url` includes the original physical page fragment. The B07 dashboard is unchanged; B14 will consume these retrieval/source-resolution contracts. No frontend build/lint is needed for this backend-only block.

## Offline acceptance

`tests/test_retrieval.py` covers all 17 actual synthetic source files and six actual saved public PDFs, complete nested/merged tables, decimals, original/split-page mapping, printed/physical distinctions, partial public page mappings and labels, current-versus-historical resolution, entity/period/type/scope/case filtering, deterministic ranking, malicious source text, corruption/path guards, format/limit gaps, immutable indexes, parser-version/database upgrades, pinned alternate-team rules, HTTP contracts and concurrent/restarted indexing. All tests inherit socket/DNS blocking and mock mode from `tests/conftest.py`.
