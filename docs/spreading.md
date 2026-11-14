# Financial spreading (B09)

B09 provides a synchronous, offline extraction → validation → repair/fallback → mapping service. It persists immutable `Spread`, `ComputedValue` and `Citation` records and refreshes readiness. It uses the injected B01 mock provider and B08 source resolver. Live providers are rejected before any call, regardless of credentials. No servers, background threads or source-tree imports are started by this module.

The FIG `analytics.yaml` now includes the versioned `reit_core` spreading profile. It covers 17 core statement rows, two annual periods in the saved ESR fixture, six accounting/cross-statement equations, exact account aliases, units, currencies and scopes. This is a core financial spread, **not a complete line-by-line transcription**, a regulatory ratio set or a credit recommendation. B10 owns further sourced operands, ratios and template-specific analytics. In particular, property expenses are signed as reported; NPI is revenue plus signed expenses. Cash change excludes FX, which is separately reconciled in the opening-to-closing cash bridge. Cash-flow starting profit is compared with the same before-tax income-statement concept. No bank NIM or regulatory proxy is introduced.

Old case configuration snapshots retain their hash and do not silently acquire the profile. An old case without it receives a named configuration error. Create a new case with the current configuration for B09 verification; migration/reset remains an explicit later operation. Profiles use the same declarative vocabulary for other teams; missing borrower-specific profiles remain gaps.

## Source and API contract

Use existing B08 indexing and evidence endpoints to select original financial-statement pages and the currency declaration page. Whole tables retain every period/scope column. For side-by-side PDF statements, create an explicit B08 region citation, retaining its physical page and whole-page parent. B08 uses PyMuPDF, avoiding the known DBS pdfplumber number loss. `pdf_quality.py` retains the Phase 1 numeric-quality comparison as a separately tested legacy-text diagnostic; it is not a second runtime parser or a confidence guarantee.

`POST /cases/{case_id}/spreads` accepts:

```json
{
  "profile": "reit_core",
  "evidence_ids": ["indexed-page-id", "currency-declaration-page-id"],
  "periods": ["2025", "2024"],
  "scope": "Group"
}
```

Maximum selection is 40 evidence units / 250,000 source characters and five unique annual years. Sources must resolve through the case's immutable B08 indexes, match the current borrower/document version, and support a pinned spread-generation input on the selected page. A source report cannot supply a requested future year. File hashes, ownership, storage containment and original region mappings are checked before provider use. All selected source documents are conservatively pinned, even if some selected pages do not ultimately supply figures.

`GET /cases/{case_id}/spreads` lists history; `GET /cases/{case_id}/spreads/{spread_id}` returns a spread and its computed figures. Each POST is an explicit new immutable run, including failures. There is no automatic retry or overwrite. API writers serialize the short mock operation with `BEGIN IMMEDIATE`; direct service callers own serialization, commit and rollback. Historical GET returns the stored snapshot; resolving its citations performs current byte-integrity verification. Failure of a mock fixture returns a persisted **invalid** run, not successful extraction. Invalid requests and source integrity failures use 422/404/409 responses. Persistence not configured is 503.

The application factory's injected provider can be populated with B01 exact-request fixtures. `orchestrator.messages()` defines the versioned request contents. Tests bind the saved public response to actual indexed evidence IDs and register exact request hashes, rather than weakening the mock's matching contract. The default empty mock fails explicitly. No production route silently imports a canned response or test data; B07's offer-only UI remains unchanged.

## Validation and bounded correction

1. Iteration 1 requests full extraction and a missing-row review through `chat_raw`. The second response only adds rows. Duplicate/ambiguous mappings fail validation; additions cannot overwrite an earlier row.
2. Iteration 2 sends issues only for failed or incomplete statements. Cross-statement issues target both affected statements. Repairs cannot alter passing statements. Revalidate the complete retained extraction.
3. Iteration 3 runs a deterministic fallback on affected statements only. It reuses **validated source headers**, scans exact configured aliases and complete numeric tails on source text lines, and revalidates. It cannot invent missing headers or reconstruct ambiguous/wrapped tables.

At most three iterations and three provider calls (full, missing rows, targeted fix). Missing fixtures stop immediately and persist a named failure. Malformed/truncated/oversized responses remain explicit failures even if a subsequent fallback recovers numeric rows. No model confidence score bypasses validation.

Source validation checks original evidence IDs, complete source-line quotes, labels, optional note columns, every value column, year order, scope order, unit and a same-document currency declaration. Full-line matching prevents accepting a prefix of a Group/Trust row as a different scope or truncating a number. Unsupported formatting, multi-line rows, unknown aliases, reported dashes and ambiguous/missing values are named issues. Dashes are never zero. Source text cannot invoke tools or change this procedure. These deterministic transcription and accounting checks do not prove every semantic interpretation of a complex annual report; analyst source review remains necessary.

Python Decimal normalizes units and evaluates equations for **every requested year**, with 64-digit local precision and bounded numeric tokens. The profile tolerance is one reported unit, scaled to currency units (SGD 1,000 in the saved report); residuals, tolerances, operands and evidence IDs are persisted. Missing required operands are skipped checks and force manual review, not a pass. Arithmetic failures, duplicate mappings and unsupported source transcriptions produce invalid status. Retained figures from an unresolved run have `validated=false` and a gap; B10 must only consume validated figures from valid/current spreads with matching period, scope and currency.

Only a valid spread for the profile's readiness scope (`Group`) covering the source reports' current year satisfies the generated-spread input. Comparative-only or other-scope output cannot close that gap. Public evidence must still be CA confirmed for full readiness; a generated spread cannot launder unconfirmed sources. Synthetic labels propagate from source operands. Superseding a source removes its old spread from readiness while preserving all historical values/citations and CA-edited drafts.

## Verification and limits

`tests/test_spreading.py` covers saved ESR extraction, independent synthetic arithmetic, missing rows, targeted repairs, fallback, three-stage bounds, numeric/sign/unit/period/scope checks, mixed/unknown evidence, immutable persistence, API restart/isolation, public confirmation, old-source invalidation, old pins, alternate configuration and mock/live guards. The public ESR fixture uses physical pages 127, 128, 155, 156 and 162 (financial statements and currency declaration). Expected values include FY2025 Group assets SGD 5,864,836,000, NPI SGD 328,679,000 and closing cash equivalents SGD 45,928,000. This is a saved mock transcription with deterministic validation, not evidence of live-model accuracy.

The copied DBS PDF regression reproduces pdfplumber dropping `897,488` from physical page 59. PyMuPDF retains it; a left-region citation maps to that same physical page with printed spread label 114–115. See the fixture README and adaptation record for byte provenance. No retrieval date or new download is invented for this supplied copy.

All verification is offline; pdfplumber is an approved-stack **test** requirement already present on the supplied machine. No new library was installed. B09 does not implement OCR, automatic whole-report routing, complete financial statement mapping, a durable live job runner, bank NIM/search, ES drafting or frontend source review. B08 preserves unsupported/complex source tables for manual review, and B10/B14 own the next consumers.

## Local Gate 2 demonstration

The explicit local factory now mounts `POST /cases/{case_id}/demo/spread` for its seeded demo case only. This CA/Draft-only action requires the exact current, confirmed saved ESR FY2025 report hash. It binds the reviewed B09 transcription (copied to `backend/app/fixtures/esr-core-response.json`) to indexed pages 127/128/155/156/162, registers exact mock request fixtures and invokes the existing service/validator. No live fallback or source confirmation is introduced. Generic `create_app` does not mount this route. See [Gate 2](gate2.md) for the UI. Industry mapping remains a named gap.
