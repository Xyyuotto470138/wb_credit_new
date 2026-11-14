# WB Credit build state

Updated: 11 Nov 2026. Tasks 0001–0003 delivered planning and a verified public demo pack. Task 0004 delivers B01 backend schema, FIG configuration and the offline provider seam; task 0005 delivers B03 synthetic source fixtures. Task 0006 delivers B04 shared upload/folder intake. Task 0007 delivers B05 expected inputs, grouped requests and section readiness. Task 0008 delivers B06 saved/off/disabled-live search contracts, public confirmation and generation offers. Task 0009 delivers B07 intake/readiness dashboard. Task 0010 delivers B08 offline page evidence indexing, section retrieval and stable source resolution; task 0011 delivers B22 G2 template registry/parser with v0.1 active. Task 0012 delivers B09 bounded mock spreading, cited core figures and the DBS regression. Task 0013 delivers B10 sourced computed tables and REIT analytics. Task 0013a aligns the synthetic property pack and dependent gold figures to the public annual report; task 0014 delivers B11 first drafts and a labelled preview. Task 0015 delivers B12 dependency-bound synthesis for sections 9, 11 and 14. Task 0016 delivers B13 section versions and Stale. Task 0017 delivers B14 section editing and source review; interactive visual acceptance remains pending, while later workflow behavior remains planned. Task 0018 delivers B18 draft template Word/request-list exports with rendered visual acceptance. Task 0019 delivers B24 typed section chat, CA-input provenance and accepted numeric recomputation; interactive UI review remains pending. Task 0020 integrates the B15 full draft dashboard, saved version history, local mock spreading and template export controls; Gate 2 review remains with Sheryl; task 0025 delivers the authorized B22 Gate 3 backend comparison work; task 0026 delivers B25 backend/API checks with the screen pending; task 0027 delivers B16 backend/API workflow and locks, with B17 screens held. Task 0020a enriches all fourteen offline mock drafts with template-part coverage, cited figures and credit wording.
Plan IDs below map to future mailbox tasks; an em dash means not delivered/assigned. Gates and acceptance criteria are in `BUILD_PLAN.md`.

| Block | Status | Gate | Delivering task |
|---|---|---|---|
| B00 Bootstrap and plan | done | 13 Nov | 0001 |
| B01 Schema/config/provider seam | done | 13 Nov | 0004 |
| B02 REIT shortlist/public pack | done | 13 Nov | 0002 |
| B03 Synthetic pack | done | 13 Nov | 0005 |
| B04 Upload/folder intake | done | 13 Nov | 0006 |
| B05 Expected list/readiness | done | 13 Nov | 0007 |
| B06 Search/generation offers | done | 13 Nov | 0008 |
| B07 Intake dashboard | done | 13 Nov | 0009; interactive visual review pending |
| B08 Evidence retrieval | done | 20 Nov | 0010 |
| B09 Phase 1 spreading adaptation | done | 20 Nov | 0012 |
| B10 Computed tables/REIT analytics | done | 20 Nov | 0013 |
| B11 First section drafts | done | 20 Nov | 0014; 0020a richer mocks |
| B12 Synthesis/dependencies | done | 20 Nov | 0015; 0020a richer mocks |
| B13 Versions/Stale | done | 20 Nov | 0016 |
| B14 Section editor/source panel | done | 20 Nov | 0017; interactive source-navigation review pending |
| B15 Full draft dashboard | done | 20 Nov | 0020; Sheryl Gate 2 review pending |
| B16 Workflow/locks | backend/API done | 25 Nov | 0027 |
| B17 Reviewer UI | todo | 25 Nov | — |
| B18 Template-filled Word/request exports | draft done; approved regression pending | 20 Nov draft; 25 Nov approved regression | 0018 |
| B19 Scripted demo/reset | todo | 25 Nov | — |
| B20 Gate regression/freeze | todo | 25 Nov | — |
| B21 Handover | todo | 27 Nov | — |
| B22 Template registry/parser/diff | G2 parser and G3 backend diff done | 20 Nov parser; 25 Nov diff | 0011 (G2); 0025 (G3 API) |
| B23 Template admin | todo | 25 Nov | — |
| B24 Typed section chat | done | 20 Nov | 0019 |
| B25 Pre-submission checks/future panel | backend/API done; screen pending | 25 Nov | 0026 (backend/API) |
| B26 Multi-model registry/picker/compare | done (offline) | Gate 2 extension | 0021; interactive visual review pending |
| S01 Usefulness scoring | todo | 20 Nov, optional | — |
| S02 Comment threads | todo | 25 Nov, optional | — |
| S03 Visual diff | todo | 25 Nov, optional | — |
| S04 Measures view/export | todo | 25 Nov, optional | — |
| S05 UI polish | todo | 25 Nov, optional | — |
| S06 Credit admin support | todo | 25 Nov, optional; otherwise roadmap | — |

## Historical verification baseline (task 0001)

Phase 1 inspected read only: no project test suite found; isolated pytest collected zero tests (exit 5), no application imports or network. Its frontend has build/lint scripts but no typecheck/test script.
At task 0001, WB Credit was a planning-only repo with no test suite or frontend. Zero collected tests are reported as unavailable coverage, not as passing application tests.
Task 0001 mock-mode pytest also collected zero tests (exit 5). Bootstrap checks passed: 27 matching plan/state blocks, ordered dependencies, plan below 400 lines, local main branch, 18 ignored-path cases and five trackable exceptions. Git whitespace check passed.
No live model/search calls, installed dependencies, servers or application code in task 0001. Cost US$0.

## Pending for Sheryl

- Confirm handover environment and owner. Choose the live model at the first paid-run gate; no model is recommended in advance. Runtime and tests default to mock; Tavily is accepted but off until an approved task.
- Sheryl confirmed ESR-REIT with 16 Tai Seng Street as the financing object. Tasks 0005/0013a supply the aligned fictional facility/internal pack; borrower-specific configuration is in `demo/synthetic/case.yaml`.
- Validate proposed mandatory flags, REIT analytics definitions, CA-led section 14, new/renewal scope; existing project defaults apply meanwhile. Approve, question, decline and return are confirmed; approve with conditions is configurable and on by default. Word must fill the uploaded template.
- Gate reviews 13/20/25 Nov; decide Should scope on 20 Nov and schedule synthetic FIG walkthrough and 27 Nov handover.

## Orchestrator follow-up

B02 is delivered by 0002. Queue 0004–0009 already assigns B01/B03–B07, with 0004 depending on this revision. B01 now includes workflow configuration, template versions/change records, chat/CA-input/proposals, submission checks and approver-question storage; behavior remains in the later blocks.
Frontend decision is settled: JavaScript/JSX, `npm run build` plus eslint. No TypeScript/typecheck approval is needed. Word render tooling outside the approved dependencies still requires a mailbox question before B18.
Accepted late-evidence behavior: approved snapshot immutable, working content Stale, explicit new working version. Verify MAS definitions in B10; Phase 1's NPI/finance-cost ratio must not silently become regulatory ICR.
Revised effort: 16.5 core builder days plus 0.5 bootstrap; 3 Should days (20 total including bootstrap if all selected). Completed B00/B02 account for 1 day, leaving 16 core days. G1 5 + bootstrap, G2 7.5, G3 3.5, G4 0.5; these are estimates, not timings inferred from planning tasks. Preserve core requirements and escalate slips; defer Should first.
G1 (13 Nov) unchanged. G2 (20 Nov) adds B24 chat and B18 template-filled draft, requiring B22's parser/version milestone first. G3 (25 Nov) adds B25 checks, B16/B17 revised workflow and B22/B23 template diff/admin. G4 handover stays 27 Nov. Choose S06 credit admin support on 20 Nov or put it on the roadmap.

## Task 0003 plan revision

`BUILD_PLAN.md` retains B00–B21 and S01–S05, adds B22–B25 and S06 with files, acceptance criteria, tests, dependencies and gates. Requirements 2.3, 2.8–2.12, 5 and 11 are covered by explicit plan sections and block tests.
Read-only template XML inspection found 14 numbered Heading 1 headings, 15 outer tables and 28 nested tables. The plan maps every section by heading/header/italic placeholder, handles row growth and section 7 facility-column growth, retains all sections and surfaces missing/ambiguous mappings as named gaps. Template SHA-256: `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.
Template versions pin each ES; only admin-confirmed formatting-only changes activate, while prompt/code changes export for IT. Typed chat proposes cited text for accept/reject and uses CA-input provenance; numeric inputs require validation and Python recomputation. All 14 sections must be confirmed or N/A with reason, mandatory gaps need recorded reasons, and the future credit-master panel is never a passed check.
Credit Head replaces the previous role label in active planning. All five approver outcomes and question/answer resubmission are planned; Declined is final. Template admin is a separate role; optional credit admin support is configuration plus one screen.
Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` — 12 passed, five existing PyMuPDF SWIG warnings; sockets/DNS blocked by tests. Plan checks passed: 32 matching IDs, acyclic dependencies, new-block fields, effort totals, 259 lines (under 450), 14 template headings/43 tables and unchanged template hash. Git whitespace check passed; frontend checks not applicable. No application/frontend code, dependency install, live API calls or servers. Template inspection is structural only; visual fidelity is an explicit B18 acceptance gate, not claimed here. Cost US$0.

## Task 0002 public pack

`demo/reit_shortlist.md` compares ESR-REIT, OUE REIT and FCT, with FY2025 ratios, report lengths and source pages. ESR-REIT is recommended for its complete accessible agency release and useful public update evidence.
`demo/public_pack/esr-reit/manifest.yaml` indexes six downloaded PDFs: FY2025 annual report (also ownership/sponsor source), latest listed 3Q2026 business update, Fitch release and three October 2026 exchange announcements. Hashes, physical/printed page references, dates and catalogue mappings are recorded. Four comparison PDFs and their manifest are separate under `demo/research/`.
This is public evidence, not synthetic data. CA confirmation is pending for all documents. Portfolio valuation/lease disclosures are partial; internal rating and property/client/internal inputs remain gaps. The public JPY facility announcement is not the synthetic demo deal. Tenant arrears are not borrower account conduct. Keep historical, latest actual and pro forma figures separate.
Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -p no:cacheprovider` — 12 passed, with five existing PyMuPDF SWIG deprecation warnings. Tests block socket connections/DNS and check saved-file hashes, page counts, entity/date/period provenance, cited text, required pack coverage and isolation. Five source pages were visually inspected, including the three ratio tables and ESR's facing-page property table. No frontend exists or was touched.
No dependencies installed, paid calls, synthetic files, servers or background processes. Cost US$0. Application integration remains unimplemented; passing pack tests are not application acceptance.

## Task 0004 B01 schema/config/provider seam

Delivered `backend/app/{database,models,schemas,repository,team_config,main}.py`, injected `llm/`, seven FIG YAML files, setup/configuration/reuse docs and offline tests. Twenty relational entities cover the original case/document/section/draft/evidence/computation records plus workflow/comments, template versions/change/activation records, chat/CA inputs/proposals, submission checks and approver questions added by task 0003. Scalar foreign keys, section uniqueness, provenance/cross-case checks, exact Decimal storage and UTC timestamps are enforced. Immutable version/document-content triggers preserve stored history; structured collection references use repository validation.

Configuration carries all 14 project section names/input maps/modes and 22 catalogue rows, executable case predicates, alternatives, dependencies, ten REIT measures, prompt safeguards and configured workflow roles/outcomes. Cases persist the full validated configuration snapshot plus hash/version; drafts/ES pin that hash and template version. Alternate-team loading, invalid rules/cycles/formulas/outcomes, role misuse and final-state transitions are tested. Threshold values are the project baseline, explicitly pending B10 verification; no analytics implementation or new regulatory claims.

`create_app()` boots mock and serves health without keys/network/database writes. Provider chat/raw contracts use exact-request fixtures; missing fixtures fail with no live fallback. Live adapters stay disabled until an approved paid-run task implements selection/spend controls. No frontend, intake/readiness engine, drafting, template parsing, activation behavior, workflow execution or submission-check behavior was added; those remain in their assigned blocks.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **53 passed**, five existing PyMuPDF SWIG warnings. Sockets/DNS blocked; temporary test files under ignored `runtime/pytest/`. Coverage includes all 20 entity round trips, exact catalogue/section comparison with the project file, conditional/alternative rules, immutable records, provenance, foreign keys, pinned configuration after YAML changes, ASGI health and provider fixtures. Git whitespace check passed. Build/eslint not applicable (no frontend).

The machine's global FastAPI 0.115.0 / Starlette 1.6.0 combination was incompatible. Created a local `.venv` with system-site packages and installed compatible Starlette 0.38.6 from an existing cached wheel using no-index/no-deps; global and Phase 1 environments untouched. Setup pins FastAPI 0.115.0 so clean dependency resolution selects compatible Starlette. Source adaptation paths/date are in `docs/phase1_reuse.md`. No network/paid calls, server or background process. Cost US$0.

## Task 0005 B03 synthetic pack

Delivered `demo/synthetic/` with 17 source files: two in tranche 1, twelve in tranche 2 (including the suggested limits extract), two in tranche 3 and the revised valuation separately. Formats are nine PDFs, six XLSX files, one template-filled DOCX and one `.eml`. Every source has the required synthetic header/first row; lender is the Bank and no real lending relationship is implied. `case.yaml` centralizes borrower identity, property/public evidence references and B01-compatible case attributes; `manifest.yaml` carries hashes, catalogue IDs, dates, ranges and revision links.

Gold fixtures independently reconcile existing limits 55m, outstanding 46m, proposed 75m, initial proposed LTV 50%, revised LTV 60% against a fictional 55% cap, group covenant headroom 0.9pp/0.6x, and conduct including a two-day 0.5m RCF excess and a three-day TL late payment. Average conduct uses 12 month-end observations, not daily averages. Property rent, lease buckets and projections reconcile; uncommitted refinancing is not assumed and maturity-year DSCR shortfalls remain visible. All arithmetic is Python/Decimal. Public group observations keep their original date, source and definition rather than becoming fictional portfolio totals.

The prior ES fills the owner template in place and preserves all 14 headings and 43 tables. Only text, the required synthetic header and field-refresh setting change; other package parts and original template bytes are unchanged. Public historical context cites saved FY2025 pages and the manifest's URL/retrieval register. Named historical gaps and fictional human signoffs remain explicit. Historical internal rating/conduct cannot substitute for current tranche-3 documents. Current CA position is null.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **80 passed**, five existing PyMuPDF SWIG warnings, sockets/DNS blocked. Includes file labels/hash/format coverage, B01 schema mapping, independent arithmetic, public provenance, template preservation and revision metadata. Updated the earlier public inventory test to scope public/research folders; synthetic inventory has its own assertion. No frontend changes; build/eslint inapplicable.

Visual QA inspected all eight template/final ES pages, eleven PDF report pages and all nine workbook sheets. Used the already bundled artifact tool/LibreOffice and approved project libraries; no project dependency changes or installations. Previews stay under ignored `runtime/b03/`. `scripts/` and the pack README document rebuilding. This is fixture verification, not implemented readiness/Stale or production export acceptance; those remain later blocks. No network/paid calls, server or background process. Cost US$0.

## Task 0006 B04 upload/folder intake

Delivered `backend/app/services/intake.py` and `backend/app/api/documents.py`, wired through explicit app-factory persistence/folder injection. Raw-byte uploads and configured-folder scans share classification, per-case SHA-256 deduplication, original-byte storage and document revision selection. Deterministic classification uses pinned catalogue names and bounded file previews, with supplied metadata recorded separately. PDF/DOCX/XLSX/EML/TXT/CSV are supported for preview; unreadable/scanned/unsupported files retain their bytes with named manual-review reasons. No model/search calls or new dependency outside the approved stack; PyMuPDF and OpenPyXL are now declared runtime dependencies, with no installation needed.

Newer usable inputs retain the old version and link their predecessor; wrong entities, older periods, changed same-period content and uncertain classification remain pending and never silently replace accepted evidence. Synthetic labels persist, CA confirmation is not inherited, and existing drafts/ES/workflow records are untouched. Distinct property/report streams use explicit `scope`. API writes serialize SQLite duplicate/version selection. Folder IDs are operator configured; scans reject symlinks/non-regular/oversize files and cannot overlap content storage. Scans are explicit and repeatable, without a watcher.

Added immutable `Document.intake` metadata with an additive B01 SQLite upgrade and unchanged case configuration pins. `docs/intake.md` specifies API contracts, limits, period/scope assumptions and service transaction ownership; `docs/setup.md` links the new intake setup. Classification is deliberately conservative and records manual-review gaps; automatic review resolution, B05 readiness, B08 page evidence retrieval and B13 Stale propagation are not implemented by this block. Original valuation uses its effective date, distinct from its issue date.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **98 passed**, five existing PyMuPDF SWIG warnings; sockets/DNS blocked. Added 18 intake tests covering both routes, all 17 actual synthetic sources/formats, dedup/restarts/cross-case isolation, progressive revisions, wrong/old/same-period conflicts, classification disagreements, external-rating scope, unreadable files, path/size/link boundaries, corrupt stored bytes, concurrent API duplicates and the B01 upgrade/immutability. No frontend changes; build/eslint inapplicable. No network/paid calls, dependency installation, server or background process. Cost US$0.

## Task 0007 B05 expected list and readiness

Delivered `backend/app/services/{gaps,readiness}.py`, `api/readiness.py`, app/intake integration, FIG generation/suggestion/draft-gate configuration, `tests/test_readiness.py` and `docs/readiness.md`. Persisted expected inputs cover all 22 catalogue rows with applicability/mandatory reasons, alternatives, evidence references, seven exact statuses, retained search outcomes, generation offers and reasoned dismissal. Requests group by RM/client/internal team and export as downloadable UTF-8 text. Dismissal never waives an unresolved mandatory input.

All 14 sections expose the seven exact readiness states, separate completeness and named gaps. Configured dependencies propagate partial/full input readiness; renewal updates need a prior-ES baseline, rating/conduct need their supplied current inputs, and section 14 needs a CA position. Public confirmation, full-property versus portfolio evidence, internal versus external rating, validated current-source spreads and confirmed industry codes are enforced. No live search/generation occurs. New/renewal and alternate-team rules are tested; optional new rule keys preserve old snapshot hashes rather than silently upgrading cases.

Upload, duplicate intake and folder scans refresh readiness in the caller's transaction. Existing draft fingerprints distinguish Drafted/CA confirmed/Stale while preserving all stored text, current/confirmed pointers, editor revision, ES snapshots and workflow state. B13 still owns explicit version/redraft and confirmation-reset behavior, approved working-version handling and further invalidation relationships. B06 owns search and evidence confirmation/generation actions; B09 owns the actual spread pipeline; B08 owns page-evidence validation. The request list is not the B18 ES Word export.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **117 passed**, five existing PyMuPDF SWIG warnings, sockets/DNS blocked. Nineteen B05 cases cover both intake routes using all three actual synthetic tranches plus saved public evidence/confirmed mapping and an explicitly labelled mock valid spread: 4/5/6/7/10 draftable and 8/9 partial at tranche 1; 1/2/3/8/9 full and 11 open at tranche 2; 12/13 full at tranche 3 and 14 only after CA position. Additional assertions cover dismissal, alternatives/conditions, conflicts, partial public evidence, validation and confirmation gates, persistence/idempotence, unchanged CA edits, old config pins, alternate configuration, API/export and invalid references. Git whitespace check passed. No frontend changes; build/eslint inapplicable.

Review configured draft gates and usual-owner defaults in `docs/readiness.md`: existing catalogue ownership routes pricing to internal teams and projections to the RM, rather than the illustrative scenario's request recipients. Free-text deal facts are not inferred; case attributes drive requirements and provided prior conditions trigger a Suggested fulfilment request. No dependencies, network/paid calls, servers or background processes. Cost US$0.


## Task 0008 B06 public search and generation offers

Delivered `backend/app/services/search/`, `api/gaps.py`, app wiring, an optional suggestion search flag in team/FIG configuration, `demo/public_pack/esr-reit/search-index.yaml`, `tests/test_search.py` and `docs/public_search.md` with setup/configuration links. Saved-pack, off and disabled Tavily providers share public-identity/result contracts. The six saved PDFs retain their original URL/retrieval date/hash, cache label, title and page references. The curated index maps audited financial statements, ownership and partial valuation/lease/external-rating evidence without changing the original manifest or source bytes.

Explicit search persists not run/failed/no match/found per eligible expected item; nonpublic cases and private-only inputs never call search. Only borrower public name and format-checked SGX/ISIN/LEI identifiers enter queries, never document/deal text. Suggestions require pinned `public_search: true`; older configuration hashes remain unchanged. CA confirmation requires current usable evidence and verified bytes, closes only eligible full public inputs, and is idempotent. Full secured-property reports and internal rating remain gaps despite confirmed partial public context. Spread and industry-code offers expose sources/confirmation requirements and do not imply generated or validated output; actual spreading remains B09.

Public import checks content/hash/size/format, entity, page bounds and permitted mappings. Duplicate hashes preserve existing metadata; attempt provenance retains rediscovered URLs even for prior local uploads. Cross-case records remain separate; newer same-scope evidence versions while older/changed same-period evidence stays pending. Failed batches roll back document rows. Confirmation/search refresh readiness and preserve CA-edited draft text/pointers, with Stale fingerprints where affected. No arbitrary URL fetcher exists; provenance URL validation does not claim DNS/redirect safety for a future downloader.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **155 passed**, five existing PyMuPDF warnings, sockets/DNS blocked. The 38 B06 cases cover actual tranche-one intake/public retrieval, all modes, public/private coverage, confirmation/offer guards, privacy, saved-pack integrity, malformed sources/URLs, inert evidence instructions, version conflicts, duplicate/cross-case behavior, old pins/dismissal, preserved CA edits, persistence/API/restarts and canned Tavily SDK calls. Git whitespace check passed. No frontend changes; build/eslint inapplicable.

Tavily SDK interface and terms were checked through free official documentation on 2026-11-10 (links in the search guide). The request/response/transport adapter is tested with canned clients, but its public search method always records not run. No SDK installation/import, credential read, live Tavily/model call or runtime unlock exists; an approved task must supply spend controls before enabling it. No new dependencies, servers or background processes. Cost US$0. Review the curated mappings, explicit search API and offer-only boundary before B07 UI integration; B08 still owns citation indexing and B13 explicit working-version behavior.


## Task 0009 B07 intake dashboard

Delivered React/Vite JavaScript/JSX frontend in `frontend/`, `backend/app/api/dashboard.py`, explicit `backend/app/local.py` startup, app wiring, `tests/test_dashboard.py`, and `docs/gate1.md` with setup/reuse links. The dashboard presents all seven input statuses, all 14 named sections, separate completeness and named gaps, owner-grouped/exportable requests, saved-public search/confirmation, offer-only generation, and the complete document/version register. Upload/drop and configured-folder scan share existing B04 services. Exact demo-file hashes select manifest hints; unknown files retain ordinary classification/manual-review behavior. Source review uses case-scoped hash-verified bytes, a local PDF worker, original downloads, URL/retrieval/cache labels and supplied page references. No financial computations or drafted prose were added.

The local factory seeds only the empty synthetic renewal case and resumes existing state without reset. Three actual tranches plus six saved public documents produce 8/20/22 stored files and 8/11/13 draftable sections. After public confirmation, tranche 1 has 2 Provided / 6 Found publicly / 10 Missing; tranche 2 has 13/4/1; tranche 3 has 15/3/0. Counts describe expected categories, not files. Spreading and industry mapping remain Can generate; sections 4/9/10/11 therefore remain partial, and section 14 waits for CA position/dependencies. No test-only spread or fabricated CA position enters the demo. B09 and later blocks own those capabilities.

Verification: full offline mock pytest **160 passed**, five existing PyMuPDF warnings. Five new dashboard API tests exercise both real three-tranche intake routes, duplicates, public confirmation, no-spread/no-draft boundaries, persistence/seed/restart, dismissal/restore, named review gaps, source download/preview bytes, cross-case/hash/storage boundaries and request export. Frontend build and eslint passed; five Node built-in API-client tests passed. Server-rendered HTML checked all three actual backend snapshots for all sections/statuses, source filenames, labels and offer boundaries. Local Uvicorn/Vite startup and proxy HTTP smoke passed. Temporary servers were stopped.

Interactive visual/keyboard/PDF/drag-drop review remains for Sheryl: computer-use browser host unavailable and native Chrome returned `cgWindowNotFound`; no screenshot or visual fidelity signoff is claimed. `docs/gate1.md` provides the review steps and actual expected states. Semantic render/API checks do not replace that review. Gate 1 human acceptance remains pending.

Phase 1 component patterns/installed packages were copied into this repo and adapted/pruned offline; no source-tree writes or imports. No new Python dependencies; existing Uvicorn supplies local serving. Frontend uses the approved React/Vite/dropzone/PDF stack and existing eslint/esbuild tooling. No model/search/network API calls or paid calls; the only HTTP check was loopback. Pre-existing replies 0001–0008 are excluded from this task commit. Orchestrator-owned new queue/log changes are committed unchanged separately. Cost US$0.


## Task 0010 B08 page evidence retrieval

Delivered `backend/app/retrieval/`, `services/normalize.py`, `api/evidence.py`, application wiring, additive immutable `EvidenceIndex` schema/repository support, `tests/test_retrieval.py` and `docs/evidence_retrieval.md` with setup link. Explicit/lazy indexing covers PDF/DOCX/XLSX/CSV/TXT/EML from shared stored document bytes. Stable citations pin document/content/normalizer/page/region; old versions still resolve after document and parser upgrades. Indexes, original documents, case configuration, drafts and workflow history are never overwritten by retrieval.

Section retrieval filters by current case/entity/report-period/type/scope and pinned applicable input maps; secondary public mappings apply only on their recorded pages. Ranking is deterministic keyword overlap plus configured input support, with decimal tokens preserved. Public URL/retrieval/cache/confirmation labels, synthetic flags, observation dates, partial coverage and external-rating limits remain explicit. Unknown/non-indexed/cross-case citations and corrupt/out-of-storage sources are rejected. Integrity failures withhold affected retrieval results with named gaps; source text never triggers calls or instructions.

Whole PDF pages, nested Word tables and complete worksheets/CSV tables are retained. Curated facing/spanning references include whole companion pages for review (ESR annual-report pages 72–73); unknown PDF table boundaries require original-document review, not guessed row extraction. PDF crops retain original physical-page coordinates, rotation and whole-page parent context. Printed labels are supplied/embedded only; non-PDF locations are explicitly normalized, not print pagination. Scanned/unreadable/oversized units, email attachments and unevaluated formulas produce named gaps. No OCR, model usefulness scoring, financial extraction/calculation, drafting or B14 UI is claimed.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **199 passed**, five existing PyMuPDF warnings; sockets/DNS blocked. The 39 new cases cover all 17 actual synthetic files and six actual saved public PDFs, nested/merged/whole tables, original/split/rotated page mapping, printed labels, partial public page restrictions, period/entity/scope/type/case filters, malicious evidence, source integrity, format/size gaps, immutable/history/version upgrades, alternate pinned configuration, API citation resolution, concurrent indexing and database restarts. Git whitespace check passed. No frontend changed; build/eslint inapplicable.

Review normalization conventions and conservative table boundary limitations in `docs/evidence_retrieval.md`. B09 must carry original-page mappings and validate operands; B11/B12 must validate supported claims, and B14 consumes the source API. The B07 dashboard is unchanged and its interactive Gate 1 acceptance remains pending. Pre-existing reply finalizations 0001–0009 are excluded from this task commit. No new dependencies, source-pack/template edits, network/paid calls, servers or background processes. Cost US$0.


## Task 0011 B22 G2 template registry/parser

Delivered `backend/app/services/templates.py`, `api/templates.py`, factory/local startup integration, validated FIG mapping configuration, `tests/test_templates.py` and `docs/templates.md` with setup link. The registry preserves exact DOCX bytes/hash, parent/version history, immutable parse reports and append-only activation history. Registered and activated the only owner file present, v0.1, in `runtime/gate1/`; SHA-256 remains `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`. No owner template was edited. Clean local startup seeds automatically; imports do not write. Fresh bootstrap orders newer owner versions numerically and activates the latest; restart preserves established active history and leaves subsequent candidates inactive.

The actual template resolves 14 canonical sections, 15 outer plus 28 nested tables, 29 configured content-table anchors plus 14 wrappers, 19 narrative anchors and 133 text fill points with no mapping gaps. Ordered headers, full seed row labels and cell spans identify targets; physical XML locations preserve merged/nested cell identity. Blanks, first-row key/value cells, dates, FY periods, checkboxes and sample defaults remain explicit source-required targets. Effective italic bracket placeholders span runs and paragraph/character/base-table style inheritance. Missing/duplicate/mismatched sections, tables, rows, cell structure and narratives yield named gaps; all canonical sections remain in the report.

Template text is guidance, not evidence. Repeat policies cover rows, facility columns and covenant rows but do not perform growth or calculations. Unsupported content controls, embedded content, tracked changes, conditional table-style italics and header/footer fills remain manual-mapping gaps. Malformed/encrypted/macro-bearing/duplicate-part/oversized packages and unsafe storage references are rejected. API exposes list, active, historical report, verified source bytes and candidate registration only. B18 owns template filling/rendering, ES pin selection and complete-export gating; G3 owns diff/classification/change lists and admin confirmation. No visual/export acceptance is claimed.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **226 passed**, five existing PyMuPDF warnings; sockets/DNS blocked. The 27 new cases cover actual inventory/locations, merged/nested targets, split-run/inherited italics, missing/duplicate/changed anchors and blank-cell geometry, malformed packages, named unsupported gaps, immutable registry/restarts/numeric seed ordering, candidate nonactivation, cross-team/storage/hash guards, concurrent API deduplication and unchanged old configuration snapshots. Local persistent seed/source verification and git whitespace check passed. No frontend changes; build/eslint inapplicable.

Review the B18 consumer contract and bootstrap-versus-admin boundary in `docs/templates.md`; zero mapping gaps does not mean evidence completeness or visual fidelity. Pre-existing reply changes 0001–0010 remain excluded. No new dependencies, network/paid calls, source-pack edits, servers or background processes. Cost US$0.

## Task 0012 B09 spreading adaptation

Delivered `backend/app/extraction_agent/`, `services/spreading.py`, `api/spreads.py`, app wiring, optional pinned FIG spreading profiles, readiness integration, `tests/test_spreading.py`, saved fixtures and `docs/spreading.md`. Adapted the selected Phase 1 extraction/validation/mapping/quality-gate portions with source paths/date in `docs/phase1_reuse.md`; copied the requested public DBS PDF unchanged into `tests/fixtures/spreading/`. Phase 1 and owner templates remain read only.

The injected mock pipeline performs full extraction plus missing-row review, targeted failed-statement repair, then a deterministic PyMuPDF-text fallback, bounded to three iterations/three provider calls. Exact complete-line source quotes, column/year/scope/unit/currency checks, configured aliases, Decimal equations and explicit skipped/failed issues replace confidence acceptance. Source documents, original pages/regions, URL/retrieval dates, synthetic labels, attempts, operands, figures and citations persist immutably. Missing fixtures and malformed responses persist invalid runs; live providers are rejected. The default mock remains empty until exact-request fixtures are injected.

The configured REIT core covers 17 rows and six equations in each requested annual period. The saved ESR fixture yields 34 cited FY2025/FY2024 values with 12 reconciliations; FY2025 Group assets SGD 5,864,836,000, NPI SGD 328,679,000 and closing cash equivalents SGD 45,928,000. This is a saved mock transcription with deterministic validation, not a live-model accuracy claim or complete statement transcription. B10 owns further operational/template operands and regulatory analytics. Unknown/wrapped/ambiguous rows and reported dashes remain gaps; no zero/proxy inference. Public confirmation, current source revisions, configured readiness scope and current report year still gate spread readiness. Existing configuration hashes and CA draft content remain preserved.

The DBS regression reproduces pdfplumber dropping `897,488` on physical page 59 (11 large-number tokens versus PyMuPDF's 128). Original-page/left-region citations retain the whole-page parent; a small B08 correction now also carries the supplied original printed spread label (114–115), with the earlier regression updated accordingly. No inferred half-page numbering is introduced.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **275 passed**, five existing PyMuPDF warnings. Forty-nine B09 cases plus the updated region-label regression cover extraction/repair/fallback, arithmetic/completeness, source boundaries, mapping/provenance, readiness, public confirmation, API/restarts, old configuration and both actual report fixtures. Git whitespace check passed. Frontend unchanged; build/eslint inapplicable. The approved-stack pdfplumber package is now declared in test requirements; already installed, no installation or new unapproved dependency. All tests block sockets/DNS; no network/paid calls, source-pack/template edits, servers or background processes. Cost US$0. Review the core-row scope, one-reported-unit tolerance, conservative fallback and new-case/old-pin boundary in `docs/spreading.md`; B07 UI integration and live-run acceptance remain later work. Pre-existing reply finalizations 0001–0011 are excluded from this task commit.


## Task 0013 B10 computed tables and REIT analytics

Delivered `backend/app/analytics/`, `api/analytics.py`, factory wiring, expanded pinned FIG analytics, `tests/test_analytics.py` and `docs/analytics.md` with setup link. Twenty-two metric slots cover the ten REIT measures, additional financial-template rows, separate ICR sensitivities and scoped LTV; unsupported inputs remain named gaps. Decimal calculations retain operands, formulas, source bindings, public URL/date/confirmation labels and synthetic/proxy flags. Immutable computation snapshots, numeric value IDs and operand citations use existing storage. Analytics reports cannot satisfy financial-spread readiness and are separated from B09's API. No draft, confirmation, ES or workflow pointer is mutated.

Strict whole-worksheet adapters compute exposure, contractual covenants, account conduct and property projections from actual B03 files. Independent gold values match: exposure 55/46/75/20 million, utilisation 83.636364%; contractual headrooms 0.9 pp/0.6x/20 pp; TL peak/mean 42 with three-day late payment; RCF peak 10.5, mean 4.583333, two excess days; projected DSCR 0.209651/1.575000/0.060577. Missing conduct is a gap, and nil existing exposure requires explicit new-to-bank case input. Complete events/date coverage, overlapping excess days, sample-average basis, source controls and incompatible extracts are tested.

MAS source references were checked through free official pages on 2026-11-10: thresholds effective 2024-11-28 remain 50%, 1.5x and improvement-plan expectation below 1.8x. Generic debt/assets or NPI/finance-cost proxies cannot drive headroom. Rate sensitivity uses full debt exposure including fixed/hedged debt, with complete reviewed annual regulatory operands, otherwise a gap. Headroom is pp/times, never inferred borrowing capacity. Actual saved ESR FY2025 page 59 yields 43.4%, 2.5x and headrooms 6.6 pp/1.0x, retaining unconfirmed-public provenance. The implementation is a pinned calculation baseline, not a live regulatory update service or legal/credit determination.

Verification: full offline mock pytest **330 passed**, then final conduct coverage/cure-date guards and regression additions verified with **57 B10 tests passed** (the final collection adds two cases); five existing PyMuPDF warnings. Commands: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` and the same with `tests/test_analytics.py`. Tests block sockets/DNS. Coverage includes MAS equality/breach/1.8 boundaries, adverse negative ICR and >100% leverage, exact units/precision, dates/scopes/currencies, proxy rejection, NPI reconciliation, maturity buckets, weight matching, sourced fallback, B09 references, APIs/rollback, source integrity/currentness, historical persistence and configuration pins. Git whitespace check passed; no frontend changes, so build/eslint inapplicable.

Review the explicit mapping boundary and consumer contract in `docs/analytics.md`: callers review semantic labels/column/definition/unit mappings; exact source matching and arithmetic validation do not independently prove semantic extraction. B10 has no automatic FX conversion, full statutory-ratio reconstruction or arbitrary-workbook adapter. Other currencies/layouts, unmapped cap-rate ranges and missing sensitivity assumptions are named gaps. Existing case configuration hashes remain unchanged. B11/B18 consume persisted value IDs; B13/B24 own invalidation and accepted typed-input recomputation; frontend integration remains later work.

No new dependencies, paid calls, Phase 1/template/source-pack edits, servers or background processes. Free official MAS source verification only; runtime and tests remain offline. Pre-existing reply finalizations 0001–0012 are excluded from the task commit. Concurrent orchestrator project/queue updates were committed unchanged separately as `87a0891`; no new queued task was started. Cost US$0.

## Task 0013a public-property alignment

Checked the saved FY2025 annual report physical pp72–73 (printed 70–71), row 5, including both rendered facing pages. `demo/synthetic/case.yaml` now separates public property facts from later fictional scenario inputs: NLA 19,187 sqm, GFA 22,798 sqm, multi-tenanted high-specifications industrial, 30+30-year tenure expiring 3 July 2067, 41.5 years remaining at 31 Dec 2025, acquisition 29 May 2012, purchase/development cost SGD 100.5m, occupancy 50.2%, valuation SGD 109.0m, and FY2025 rental income SGD 3.5m. Public URL/retrieval date are carried into the valuations and rent-roll source register; the original public PDFs/manifest and owner template remain unchanged.

Regenerated the dependent PDFs, four workbooks and prior ES using `scripts/`, then refreshed `demo/synthetic/manifest.yaml`. Initial/revised valuations are SGD 112m/104m, with a fictional 9 Nov non-renewal notice from Demo Tenant A (expiry 30 Apr 2027) explaining the revision. Proposed SGD 60m TL LTV is 53.571429%/57.692308%; revised headroom -2.692308 pp and proposed reduction to the 55% limit SGD 2.8m. Current drawn LTV is separately 37.5%/40.384615%. The prior ES uses the public historical SGD 109m valuation and 50.2% occupancy rather than a fabricated historical value.

Synthetic rent roll holds occupancy near the public baseline at 9,632/19,187 sqm (50.200657%, rounded to 50.2%) and annual rent SGD 3.48m. NPI/cash for service are SGD 1.68m/0.78m; projected DSCR is 0.043261/0.325000/0.012500 for 2027/2028/2029. Retained the resulting property cash-flow shortfall, unchanged facility amounts/cost/reserve assumptions, and explicit uncommitted renewals. The late report identifies the pre-notice rent/projection dates and calls for reassessment. No revised cash flow, actual tenant event or new public valuation is implied.

Updated independent gold controls and B10 occupancy/LTV assertions. Existing B10 table tests validate the new covenant/projection outputs; B09 public group spreads are unaffected and remain green. Actual valuation ingestion now exercises revision linking and preservation of CA-edited/confirmed drafts with Stale in sections 8/11/14. The existing manifest's intended downstream section-9 behavior remains for B13/B19; no workflow implementation changed.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **334 passed**, five existing PyMuPDF warnings, sockets/DNS blocked. Independent pack reconciliation: **28 passed**. Rendered and visually inspected all eight final prior-ES pages, seven changed PDF pages and affected worksheet views; no clipping. Preserved unchanged exposure/conduct workbook bytes after comparing cells/styles. Git whitespace check passed; frontend untouched, build/eslint inapplicable. No dependencies installed, paid/network calls or servers/background processes. Concurrent orchestrator edits committed unchanged as `499fffb`; pre-existing replies 0001–0013 excluded. Cost US$0.

Orchestrator review: the aligned rent exposes weak property-only debt service in every projected year. Keep that visible in the narrative and human decision; do not restore the former optimistic cash flow. Review the explicit public/historical versus synthetic/later boundary in `demo/synthetic/README.md`.

## Task 0014 B11 first drafts

Delivered `backend/app/services/drafting.py`, `api/drafts.py`, reviewed demo claim fixtures, factory wiring, FIG prompt v2, `frontend/src/DraftPreview.jsx`, dashboard integration, `tests/test_drafting.py` and `docs/drafting.md`. First drafts cover sections 1–8, 10, 12 and 13. Each persisted draft pins configuration/prompt/model/fixture/template versions, source documents/pages and claim citations. MOCK DRAFT, synthetic/public/proxy labels, public URLs/retrieval dates and named gaps survive both the UI preview and exact-text download. B18 remains responsible for the template-filled Word ES; no complete ES export or visual acceptance is claimed.

Offline prose is reviewed wording bound to borrower, source hash, reporting metadata, page and exact quote checks, then selected through the injected mock provider contract. Unknown/altered claims, numbers, IDs and response fields are rejected. Unknown/changed documents remain gaps; this is not a general semantic validator or live-model accuracy claim. Internal rating is supplied-only; external/historical grades cannot replace it. The RCF unsecured description requires explicit CA confirmation, retained with actor/source hash/draft timestamp. Legal perfection and industry mapping remain explicit review gaps.

Python B10 records supply exposure, conduct, covenants and financial disclosures, retaining immutable computed IDs and operand citations. Built-in exact-hash demo mappings make exposure/conduct and five FY2025 disclosed metrics available offline; other metrics stay gaps. Section 10 also consumes an existing validated B09 spread without changing its figures or running spreading automatically. Superseded or corrupt sources are not reused. The conduct summary preserves sample-average basis, excesses and late-payment exceptions. Nil exposure requires explicit new-to-bank case input. No existing draft, confirmation, ES or workflow pointer is overwritten; subsequent editing/redrafting remains B13/B14.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=runtime/pytest-b11-final` — **369 passed**, including 35 B11 tests, five existing PyMuPDF warnings. Sockets/DNS blocked. Frontend `npm run build`, `npm run lint` and all five `npm test` client tests passed. Git whitespace check passed. Tests cover all eleven sections against actual packs, public provenance, immutable computed/spread references, unsupported claims/numbers/IDs, malformed/missing fixtures, explicit unsecured confirmation, supplied-only rating, missing conduct, new-to-bank nil, hostile/changed evidence, currentness, cross-case boundaries, locks, API preview export and restart persistence. Corrected the old frontend term-sheet hash assertion to the current 0013a manifest hash. An overlapping pytest spot check collided with the repository's fixed scratch directory; the incomplete run was stopped and the final complete suite passed in the isolated directory. No failures waived. Interactive visual acceptance remains pending.

Orchestrator review: read the conservative fixture/consumer boundary in `docs/drafting.md`, review wording and field coverage in the preview, and preserve the mock label/gaps in B14/B18. First-draft creation does not implement later synthesis, CA editing/chat, Word layout or workflow gates. Existing case pins are unchanged. No new dependencies, paid/network calls, source-pack/template edits, servers or background processes. Pre-existing replies 0001–0013a are excluded. Cost US$0.


## Task 0015 B12 synthesis

Delivered B12 through `backend/app/services/{drafting,synthesis}.py`, `api/drafts.py`, `fixtures/synthesis.json`, FIG prompt v3, `tests/test_synthesis.py`, updated B11 gate tests and `docs/drafting.md`. The existing API supports all 14 first drafts. Prerequisite drafts must exist in configured order: 7/10 → 9; applicable 3–10 → 11; mandatory applicable 1–13 → 14. Partial source/draft gaps propagate; N/A reasons persist. Snapshots pin dependency versions, fingerprints, template/config/model/fixture versions and completeness. Missing, Stale, superseded/corrupt or mismatched dependencies are rejected; changed ancestor draft pointers require explicit review/redraft. Existing configuration pins and draft text remain unchanged.

Section 9 uses B10's Python projection adapter and preserves the aligned property-only DSCR shortfalls (0.043261x, 0.325x, 0.0125x). Section 11 distinguishes sourced risks and proposed review actions from achieved mitigants, retaining uncommitted renewals/refinancing and security-perfection evidence gaps. Document/page, public URL/date, synthetic/proxy labels and immutable computed IDs survive downstream synthesis and exact-text preview. Reviewed fixture claims are hash/page/quote bound; unsupported model wording/figures are rejected. Prerequisite facts and computed exceptions are carried outside model selection so omissions cannot erase them.

Section 14 requires a nonblank CA position supplied with the request or reaffirmed from the case, records it verbatim with actor/time/hash in the immutable draft, and preserves adverse findings/gaps independently of that position. RM support cannot substitute for the CA. API generation is transactional; no workflow/ES/confirmation is created or changed. The case-position snapshot is explicitly CA input, not independently verified, and does not fabricate a future B24 chat/CAInput record. Later case-position changes leave historical text intact and mark the conclusion Stale via existing readiness fingerprints.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=runtime/pytest-b12-final` — **400 passed**, including 31 B12 cases and the updated B11 gate checks; five existing PyMuPDF warnings. Sockets/DNS blocked. Full/partial actual-pack chains include a validated B09 spread, B10 projections, mandatory/N/A gates, absent/blank/hostile provider positions, source integrity/currentness, ancestor version changes, locks, API rollback and restart/exact-text preview. The full run exposed a provider-module reload exception-identity issue; drafting now resolves the missing-fixture exception from the module, matching B09. The affected ordered tests and final full rerun pass; no failures waived. Git whitespace check passed. Frontend unchanged; build/eslint inapplicable. No new dependencies, network/paid calls, source-pack/template edits, servers or background processes. Cost US$0.

Orchestrator review: the mock synthesis deliberately quotes the CA position exactly, with sourced supporting context; it is not a live-model quality claim. Full input readiness remains distinct from complete/confirmed draft coverage. B14/B15 own synthesis UI entry points; B13 owns redraft and CA-edit integration (unreviewed edited dependency text is rejected); B18 owns Word output. Preserve dependency/position snapshots, gaps and labels in those consumers. Pre-existing reply finalizations 0001–0014 remain excluded from this task commit.


## Task 0016 B13 section versions and Stale

Implemented `backend/app/services/versions.py`, `api/sections.py`, app wiring, append-only `SectionConfirmation` storage, readiness/drafting/synthesis integration, FIG freshness configuration, a revised-valuation mock claim, `tests/test_versions.py` and `docs/versions.md`. Save/redraft/confirm requests carry expected draft, editor revision and input fingerprint; serialized API transactions reject conflicts and roll back failures. Save appends structured CA wording edits with actor/time/original/replacement provenance, retains citations/labels/gaps and protects computed/supplied claims. Redraft appends a parent-linked version with the same template pin and resets confirmation. Confirmation records exact draft/input/actor/time history and rejects Stale/superseded/corrupt evidence. No ES/workflow pointer is changed.

Readiness now checks prerequisite draft IDs and propagates Stale transitively. Stale persists until explicit redraft, including when an input selection reverts. New FIG pins add the security → repayment freshness link, separate from section 9's 7/10 drafting prerequisites; old configuration snapshots/hashes remain unchanged. The actual revised valuation makes sections 8/9/11/14 Stale while section 7 stays confirmed, retaining CA-edited text, prior confirmations and an approved ES snapshot. An exact-hash/page/quote-bound mock claim supplies the revised SGD 104m valuation on explicit redraft; no computed cells or historical wording are rewritten.

Verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=runtime/pytest-b13-final` — **426 passed**, including 26 B13 cases; five existing PyMuPDF warnings. Sockets/DNS blocked. Coverage includes the actual late-valuation chain, approved/edited/confirmed history preservation, transitive version invalidation, parent/template pins, source labels, numeric/protected edit guards, stale tokens, concurrent API writes, SQL immutability, source integrity, restart/history, workflow locks, old configuration pins and sticky Stale after input reversion. Earlier targeted runs passed as well. Git whitespace check passed. Frontend untouched; build/eslint inapplicable. No failures waived.

Review the B14 consumer contract in `docs/versions.md`. A retained `confirmed_draft_id` on Stale content is historical only; consumers must require current `CA confirmed` readiness. Structured CA edits remain human assertions, with source links retained for review; the numeric-token guard is not semantic verification. New typed facts/numeric recomputation and chat remain B24. B16 owns named returns and explicit reopening/new working versions after approval; every non-Draft state stays locked here. B18 owns Word export. No new dependencies, network/paid calls, template/source-pack edits, servers or background processes. Pre-existing reply finalizations 0001–0015 are excluded. Cost US$0.

Concurrent orchestrator log/queue updates were committed unchanged separately as `45a6d5e`; no new queued task was started.


## Task 0017 B14 section editor and source panel

Implemented `frontend/src/{SectionEditor,SourcePanel}.jsx`, editor state helpers, dashboard/app integration and styles, replacing `DraftPreview.jsx`. All configured sections use the existing first-draft and B13 save/redraft/confirm APIs. Optimistic draft/revision/input tokens, current workflow/readiness, explicit CA position/unsecured inputs, unsaved navigation protection and conflict recovery preserve local wording and historical versions. Computed/supplied claims stay read-only; source/public/synthetic/proxy/mock labels and current/saved named gaps remain visible. Historical confirmation pointers never imply current confirmation on Stale content. No backend behavior/schema/configuration change.

Claim buttons resolve immutable evidence IDs through B08, open the original PDF at its cited physical page and retain separate printed/region labels, whole-page and related-page context. Non-PDF citations show normalized worksheet/block text and original download. Resolution failures display errors, and superseded sources retain historical labels. Existing document-register review remains available. The saved-text download contains persisted wording; Word export, new typed facts/chat, combined version-history dashboard and workflow transitions remain their later blocks.

Added `tests/test_section_editor.py`, frontend state/client tests, `frontend/scripts/check-section-editor.mjs`, `docs/section_editor.md` and related setup/drafting/version links. Focused API tests passed the save → confirm → late valuation/Stale → redraft → confirm chain, immutable prior text/confirmations, current/historical PDF references and normalized workbook/public provenance. Offline render checks passed for actual section 8/2/10/12 snapshots, including editable/read-only claims, locked selectable wording, escaping, exact saved text and source labels. Frontend build/eslint and all nine Node tests passed. Full mock pytest passed: **428 tests**, five existing PyMuPDF warnings, in 764.66 seconds; sockets/DNS blocked. Command: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=runtime/pytest-b14-final`. Final source-code build/eslint and git whitespace checks passed; no failures waived.

Interactive review remains pending: browser access host unavailable and native Chrome returned `cgWindowNotFound`. No PDF-canvas, focus or responsive-layout visual signoff is claimed; `docs/section_editor.md` supplies the manual source-navigation and conflict walkthrough. No new dependencies, paid/network calls, template/source-pack edits or servers. Pre-existing reply finalizations 0001–0016 are excluded from this task. Cost US$0.


## Task 0018 B18 template-filled draft exports

Implemented `backend/app/exports/`, `api/exports.py`, additive immutable `ExportArtifact` storage, app wiring, `tests/test_exports.py`, `scripts/export_demo.py` and `docs/exports.md`. Preview/token/create/download/history APIs produce a pinned Word copy, complete manifest and owner-grouped request list, individually or as a ZIP. All 14 sections, draft/Stale/N/A/source/synthetic/CA-edit labels, input/mapping gaps, template/configuration versions and exact saved wording remain reviewable. Supported tables use immutable Python computations; unstructured/unsupported fields stay gaps. Public URLs/dates and source-marker resolution are in the companion manifest. Draft-only export does not confirm, approve or move the active ES pointer. Missing/ambiguous template anchors block Word delivery with named preview gaps.

Validation: full mock suite **453 passed**, five existing SWIG warnings, 940.82 seconds (`--basetemp=runtime/pytest-b18-final`). After final exporter-only corrections to label preservation, extra computed narrative coverage, marker metadata and nested-table pagination, focused export suite **25 passed**, five existing warnings, 99.20 seconds (`--basetemp=runtime/pytest-b18-final-focused`). Both used `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`, with `tests/test_exports.py` for the focused run; sockets/DNS blocked. Coverage includes all-section actual saved packs, B09 scaling, immutable values/citations, malformed/cross-case inputs, token conflicts, API bundles, Stale/CA edits, template pins, historical bytes and zero/one/many repeats. Frontend untouched; build/eslint inapplicable. Git whitespace check passed.

Visual acceptance: bundled LibreOffice/documents renderer; every page inspected for owner template (8), final demo (18), zero (9), one long row/three facilities (9), and twelve rows/three facilities (10). No dropped sections, clipped content or broken tables in final exports. A pre-existing LibreOffice nested-table/page-boundary omission was reproduced in the owner template; exported copies add a one-point keep-with-next flow paragraph before five leading nested tables. Other differences: expanded pagination/rows, shared facility width, explicit gap/period/unit labels, and source text in existing slots. Original styles, section breaks, table borders, 43 table containers and all package parts outside document.xml are preserved; sparse pages and placeholder italics follow the template. See `docs/export_visual_review.md` and ignored `runtime/b18/verified/` for artifacts.

Orchestrator review: B15 owns dashboard integration; B16/B19 own approved snapshot/export acceptance. Review supported-field boundaries and companion-manifest requirement in `docs/exports.md`; 276 named field gaps remain in the demo rather than inferred facts. Supplied CA position is verbatim, sign-off/checkbox decisions pending. No new dependencies, network/paid calls, template/source-pack edits or servers/background processes. Pre-existing reply finalizations 0001–0017 excluded. Cost US$0.


## Task 0019 B24 typed section chat

Implemented `backend/app/services/section_chat.py`, `api/chat.py`, saved operation fixtures, additive proposal payload/immutability migration, app wiring, `frontend/src/SectionChat.jsx`, editor/source-view integration and `tests/test_section_chat.py`. All 14 applicable drafted sections support persisted cited proposals, explicit acceptance/rejection, history and optimistic base-version checks. Acceptance appends a draft, clears confirmation and invalidates downstream sections; rejection preserves text. Source/template integrity, case/section boundaries, CA role and Draft-only workflow locks apply. No ES/approval pointer is changed.

Typed facts have immutable CA-input/evidence records with actor/time/message/revision, separate from document/page evidence. Pending/rejected sources cannot feed analytics. Accepted inputs survive explicit redrafts and dependency synthesis; public URLs/dates, synthetic labels, named gaps and old tables remain. Source viewer, exact-text download and export source markers distinguish CA assertions without inventing a document page. Proposal content and resolved decisions are protected by repository checks and SQLite triggers; older schema-only proposals become stale.

The offline provider uses saved operations: emphasize an existing sourced claim, append a verbatim CA assertion, or preview numeric recomputation. Unknown model wording, numbers, citations, fields and operations are rejected; no live fallback. This is a constrained mock demonstration, not general free-form rewriting or semantic verification. Section 12's supplied rating and section 14's human position remain protected. The non-quantitative fact guard is token-based, not a guarantee that arbitrary human wording contains no numeric meaning.

Section 10 accepts explicit metric/period/scope/basis/units/currency/operand inputs. The shared B10 Decimal engine previews and reruns calculations on explicit numeric acceptance, persisting operands, value IDs, source references and gaps. Same-metric/period/scope inputs supersede prior CA inputs without rewriting historical computations. Missing/invalid operands stay cited gaps. The UI covers scalar configured formulas; API arrays support item/maturity mappings. Exposure, conduct and projection tables require revised source documents. Readiness fingerprints retain old configuration behavior for cases without accepted typed inputs.

Validation: full mock pytest **481 passed**, five existing PyMuPDF SWIG warnings, in 1293.74 seconds. Command: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -x -p no:cacheprovider --basetemp=runtime/pytest-b24-green`; sockets/DNS blocked. Includes all **28 B24 tests**: all-section actual packs, accept/reject, immutable sources/tables, numeric gaps and threshold results, supersession, downstream Stale/redraft/synthesis, concurrent API acceptance, cross-case/section/role guards, source integrity, rollback, restart and SQL immutability. Final frontend `npm run build`, `npm run lint` and all **12** Node tests passed, including escaped proposal rendering, explicit numeric acceptance, terminal/locked decisions and CA source labels. Git whitespace check passed.

The corrected numeric acceptance/supersession/redraft/synthesis chain also passed separately. Initial targeted failures were test assertion/setup issues (Decimal formatting, gap wording and an undrafted dependency). The first full run reached 281 passes before a test-only exception-identity mismatch after provider-module reload; the assertion now resolves the current exception class, and the complete rerun is green. No failures waived. Interactive browser layout/focus review remains pending; no visual signoff is claimed.

Orchestrator review: use `docs/section_chat.md` for API contracts, scope boundaries and the synthetic accept/reject/recompute/late-evidence walkthrough. B15 owns the combined dashboard/demo; B16 owns returns/reopening. No new dependencies, paid/network calls, template/source-pack changes or servers. Pre-existing reply finalizations 0001–0018 remain excluded. Cost US$0.


## Task 0020 B15 full draft dashboard (Gate 2)

Implemented `frontend/src/{CaseDashboard,SectionEditor,VersionHistory,DraftExport}.jsx`, dashboard state helpers and stage/progress styles. All 14 rows navigate to the editor, with previous/next controls and existing unsaved-input guards. Saved/confirmed/Stale/N/A counts remain separate from input readiness and mandatory gaps. Exact-source tranche counts distinguish historical originals from current replacements. Version selection shows immutable saved text, sources, template/model/parent IDs and current-versus-historical confirmations without changing the working draft. Existing B24 acceptance updates dashboard readiness through the shared refresh.

Draft export controls use the B18 preview token, show all section/current/saved/template-field gaps, then explicitly create an immutable Word/manifest/request bundle. Unsaved inputs, workflow locks, stale preview tokens and mapping blockers prevent inappropriate creation. History retains downloadable earlier snapshots. No exporter layout, arithmetic, approval pointer or owner template is changed.

The explicit local factory mounts `api/demo.py` only for the seeded demo case. Its CA/Draft-only action binds the reviewed B09 saved ESR transcription (copied into app fixtures) to the exact current, confirmed annual-report hash and indexed original pages; the existing Python pipeline validates FY2025/FY2024 Group core rows. No generic spreading/provider behavior, public confirmation or live fallback is changed. The industry-mapping offer remains an explicit unsupported action and mandatory gap.

`docs/gate2.md` gives startup, all three tranches, reject/accept chat, version review, template exports, the late valuation and explicit dependency redrafts, expected observations and shutdown. Updated setup/spreading links. API integration produces 7/11/14 saved sections across tranches and one remaining mandatory industry-mapping gap after tranche 3. Late evidence makes exactly 8/9/11/14 Stale; prior wording, confirmations and export contents survive.

Validation: final complete offline mock pytest **482 passed**, five existing PyMuPDF SWIG warnings, in 1464.83 seconds. Command: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -x -p no:cacheprovider --basetemp=runtime/pytest-b15-final` (log: `runtime/pytest-b15-final.log`); sockets/DNS blocked. Final frontend `npm run build`, `npm run lint` and all **16** Node tests passed, including delayed export-history response handling. Actual-snapshot HTML checks passed for six empty/tranche/Stale/redrafted snapshots, historical confirmation labels, exact saved text, export field gaps and escaping. Focused integration first uncovered two test-harness assumptions (late-update tranche selector and timestamped ZIP-container equality); corrected to the actual manifest selector and exact archived-content comparison. The full rerun passed with no failures waived. Git whitespace checks passed. Render command: `node frontend/scripts/check-full-dashboard.mjs runtime/pytest-b15-focused-green/test_gate2_three_tranches_chat0`.

Interactive review remains pending: browser host unavailable and native Chrome returned `cgWindowNotFound`. No PDF-canvas, click/focus or responsive visual signoff is claimed. Review the Gate 2 walkthrough and remaining industry-mapping/field gaps; Gate 3 waits for Sheryl. No new dependencies, paid/network calls, template/source-pack edits or servers. Pre-existing replies 0001–0019 excluded. Cost US$0.


## Task 0020a richer offline credit write-ups

Expanded `backend/app/fixtures/{first_drafts,synthesis}.json` and drafting presentation to cover the owner template's sub-parts with cited content or specific gaps. Requests now include both facility increases, maturities and rationale; other additions cover terms, insurance, public occupancy/WALE, management and trustee, dated external rating, tenant concentration, lease expiries, LTV and contractual headroom. Computed exposure/conduct labels and summaries use credit language. Removed process commentary from prose; retained mandatory mock/source/synthetic labels, adverse evidence and the verbatim CA position.

`services/draft_values.py` binds reviewed numeric tokens to exact current source hashes/pages/quotes, persists immutable values and operand citations, and uses Decimal for reported quantities, ratios, differences, LTV headroom and shares of summed components. No model arithmetic or live fallback. The initial/revised fully drawn LTVs are 53.57%/57.69%, with 1.43/-2.69 percentage points to the fictional ceiling. Tenant shares use complete saved component rows, not copied source percentages. Dates and identifiers remain cited metadata. Existing draft/version/export bytes are preserved; explicit dependency-order redraft is needed to update an existing demo.

Final validation: **484 passed**, five existing PyMuPDF SWIG warnings, 1384.03 seconds. Command: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -x -p no:cacheprovider --basetemp=runtime/pytest-0020a-green` (log `runtime/pytest-0020a-green.log`); sockets/DNS blocked. Includes all-section actual-pack coverage, exact quote/value/citation checks, provider rejection, late valuation, immutable history, Gate 2, chat, synthesis and exports. Focused richer-draft and export/internal-rating checks also passed. Initial checks exposed normalized PDF column-order mismatches and an export assertion expecting internal metric keys; corrected to supported quotes and readable labels, with no failures waived. Git whitespace check passed. Frontend untouched; build/eslint inapplicable.

Review `docs/drafting.md` and ignored `runtime/0020a/section-*.txt`. Unsupported classification decisions, stress assumptions, subsequent changes, agency coverage and sign-off stay named gaps. External Fitch context is dated and cannot replace the current internal rating. Content covers template sub-parts; existing export adapters still retain unmapped detail in narrative and named table-field gaps. No export-layout/visual acceptance claim, owner-template/source-pack changes, new dependencies, paid/network calls or running servers/background processes. Pre-existing replies 0001–0020 excluded. Cost US$0.


## Task 0021 B26 multi-model registry, picker and comparison

Implemented `config/models.yaml`, `backend/app/llm/{registry,adapters}.py`, model
profiles, `services/model_comparison.py`, model API routes, additive case-default
storage/migration, drafting/version integration, and `frontend/src/ModelControls.jsx`
with dashboard/editor integration. The registry contains 21 entries: two enabled
mock profiles and 19 disabled direct/OpenRouter/open-weight/local routes. Official
provider documentation supplies verified endpoints/IDs; unresolved details remain
null with explicit TODOs. Qwen family availability is user-supplied; exact bank
variants/access are not claimed. Hosted Plus/Max and open-weight entries are separate.

Case defaults and explicit first-draft/redraft overrides record concrete model and
registry-entry snapshots. Changing the default preserves existing confirmations and
readiness. Preview comparisons hold a serialized input snapshot, verify identical
prompt/evidence hashes and reuse/check exact Python tables and computed metrics.
They report actual citation coverage, per-row validator rejections, omissions,
malformed responses, gaps, local response/validation latency and zero mock cost.
No preview draft, CA position or confirmation is adopted. Evidence/computation
artifacts remain resolvable. Empty coverage is N/A; empty tables are labelled none.
Section 14 retains the exact human position and adverse inherited evidence.

Mock B reverses supported claim order and submits one deliberately unsupported
fixture row, which is rejected. This demonstrates the workflow, not hosted model
quality or unrestricted prose generation. Every live route remains blocked even
with keys/enabled flags; no environment/request budget bypass exists. Phase 1
transport contracts are adapted with injected fake clients; no SDK is installed or
live client constructed. A later approved task must implement server-side budget,
estimation/reservation/accounting and verified client construction before live use.

Validation: complete mock pytest **495 passed**, five existing PyMuPDF SWIG warnings,
in **989.05 seconds**; log `runtime/0021/full-tests.log`. Command:
`LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -x -p no:cacheprovider --basetemp=runtime/pytest-b26-full`.
The final focused B26 suite passed **13 tests** in **42.24 seconds**, including two
additional section-14/rejection-count cases and the final preview-only position-gap
correction, using `tests/test_model_registry.py` and
`--basetemp=runtime/pytest-b26-final-focused` with the same flags. Tests block sockets
and DNS. Frontend `npm run build`, `npm run lint`, and all **18 Node tests** passed.
Actual comparison HTML checks passed for sections 1/2/10/13 with exact text,
provenance, metrics, gaps and escaping. Git whitespace checks passed. An initial
focused assertion incorrectly assumed section 10 used a table container; its
computed metrics now have their own equality check. No failures waived.

Review `docs/{setup,model_comparison,phase1_reuse}.md` for API contracts, fixture
measurement limits, route TODOs and the demo walkthrough. Browser host unavailable
and native Chrome returned `cgWindowNotFound`; interactive visual/keyboard review
is pending, with no visual signoff claimed. No new dependencies, owner-template or
source-pack changes, live model calls, servers or background processes. Official
documentation research only; cost **US$0**. Pre-existing reply finalizations
0001–0020a are excluded. Gate 2 extension only; no next mailbox task started.

## Task 0022 — ES export presentation (11 November 2026)

Implementation, visual review and all 500 collected mock tests complete.
`backend/app/exports/{mapping,presentation,word,service}.py` now emits one document
status block, compact numbered citations and a complete Sources appendix. Bounded
saved-claim adapters fill supported business, portfolio, holder, management,
facility, security/insurance, repayment/lease/tenant, financial and rating tables.
Section 9 has three repayment sentences plus the debt-service tables; section 11
contains actual risks/mitigants, including saved LTV and leverage headroom.
Exact drafts, computations, evidence and detailed gaps remain pinned in metadata.

`scripts/export_demo.py --with-spread` reproduces the offline three-tranche case
with explicit saved-public-pack confirmation and validated B09 mock spread.
`docs/gate2_export_sample.pdf` is the final 16-page render. Every page and the
eight-page owner reference were visually inspected; the page ledger, artifact IDs
and hashes are in `docs/export_visual_review.md`. All 14 heading structures and
43 table containers remain; ZIP parts outside `word/document.xml` are byte-identical.
No clipping/overlap or lost tables observed. Sparse pages retain the owner's flow.

The original demo CAS leaves classification open, so it stays a gap. Only an
explicit CA assertion resolves Watchlist/SM tables to Not applicable. Financial
rows without validated matching values remain named gaps; similarly named Group
figures are not substituted. CA-edited wording keeps attribution and bypasses
format decoding. The initial-valuation PDF shows 53.57% LTV / 1.43 points headroom;
the late-valuation regression verifies 57.69% / −2.69 points after explicit redrafts.

Validation: **all 500 collected tests passed across two partitions**, with sockets
and DNS blocked. The full invocation passed 314 tests before finding one obsolete
section-chat assertion expecting CA provenance in the inline marker (554.72s;
`runtime/0022/complete-tests.log`). `tests/test_section_chat.py` now verifies the
actual exported DOCX marker and complete CA actor/message/time/revision/synthetic
provenance in Sources. That corrected test passed separately (6.21s), then all
186 tests from that node through the end passed (425.45s;
`runtime/0022/remaining-tests.log`). No application code changed between these
partitions. `runtime/0022/collected.txt` and `remaining-nodeids.txt` record exact
coverage. No failures waived; five existing PyMuPDF SWIG warnings per run.

Full invocation: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -x -p no:cacheprovider
--basetemp=runtime/pytest-0022-complete`. The remaining partition used the same
flags, `--basetemp=runtime/pytest-0022-remaining`, and the 186 recorded node IDs.
Final presentation regressions also passed **3 tests**, 25 deselected, in **37.45s**
(`runtime/0022/latest-focused.log`). Whitespace and final DOCX structural/source
checks passed. Frontend unchanged; npm build/eslint not applicable. No new
dependencies, owner-template edits, paid calls, live network, servers or background
processes remain. Cost **US$0**. Existing reply finalizations 0001–0021 remain
excluded; no next mailbox task started.

## Task 0023 — ES export polish (11 November 2026)

Implemented export-v3 display-only rounding, source-backed ESR Group / Singapore
headers, synthetic CAS Pass / no Watchlist-SM / current DPD 0 and matching hash
bindings. Added reviewed annual and quarterly financial cells with original-page,
exact-quote and numeric-token checks. Financial values reuse their persisted
snapshots on redraft/comparison; export validates those snapshots against storage.
Stored computations and existing export bytes retain their original precision.

Section 10 fills distribution, DPU, investment properties, gross debt, funds, NAV,
maturity and fixed-rate share, plus available interim figures. Four analytical
sentences replace the raw lists; Remarks carry compact markers. Section 9 uses
n.m. for cash bullet-maturity years with an explicit no-refinancing basis, retaining
the Python computation. Section 13 has three sentences retaining adverse conduct.
Section 14 preserves the standalone demo's exact conditional-support CA position,
with Credit Analyst / 10 Nov 2026 displayed and technical provenance in metadata.
Inserted text inherits the owner's body font explicitly. Public-news evidence now
supports partial section-10 context without satisfying mandatory financial inputs.

`docs/gate2_export_sample.pdf` is the verified 15-page render. Every page and the
one-page updated CAS were inspected; full financial-row checks supplement visual
QA. A reproduced LibreOffice page-boundary defect dropped the nested financial
continuation despite valid XML. An empty flow anchor before section 10 fixes it;
all 14 heading elements, 43 tables and ZIP parts outside `document.xml` remain.
The final DOCX/manifest live in `runtime/0023/verified/`; the page/hash ledger and
limitations are in `docs/export_visual_review.md`. Owner templates and public
source files were not changed. `docs/exports.md` and the synthetic README document
rounding, source definitions, remaining gaps, reproducibility and fictional dates.

Validation: 503 unique tests covered, with no unresolved failures. The initial
full mock pytest run completed with 500 passed / 3 failed (1651.55s). The failures
exposed the classification test setup and reused financial snapshot timestamps;
both were corrected. The final affected regression completed with 101 passed
(1179.11s), including all three failed cases, and covers exports, richer drafts,
full dashboard, model registry, section chat and version history. The earlier
focused export/richer-draft run passed 33 tests. Five existing PyMuPDF SWIG
warnings remain. Runs use `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`, with
separate basetemp paths. Logs and node-coverage proof: `runtime/0023/full-tests.log`,
`regression.log` and `test-coverage.txt`. Structural, source, font and PDF checks
also passed; `git diff --check` clean. Frontend unchanged, so npm build/eslint
not applicable. No new dependencies, live calls, servers or background processes
remain. Cost US$0. Pre-existing reply changes 0001–0022 remain outside this task.
Unchanged orchestrator log/task files were committed first as `cccbbbc`, per
AGENTS.md; no next mailbox task started.

## Task 0024 — Desktop screenshot pack (11 November 2026)

Added development-only Playwright and a repeatable real-UI walkthrough in
`scripts/screens/`. Installed Chrome captures an isolated mock case at 1440 × 900,
scale 2, on dedicated loopback ports; browser profiles, databases, downloads and
logs remain under ignored `runtime/0024/`. The capture closes its browser and
servers and rejects external browser requests. No live model/search calls.

`docs/screens/` contains 53 numbered PNGs, captions/index, capture metadata and a
local HTML gallery printed to `WB_Credit_screens.pdf` with Playwright `page.pdf`.
Coverage includes all fourteen section editors, three tranches, PDF/normalized/CA
sources, grouped requests, chat rejection/acceptance, immutable history, section
confirmation, export download, model routes/comparison, and the exact 8/9/11/14
Stale chain after the revised valuation. Explicit redrafts restore the chain.
`docs/gate1.md` and `docs/gate2.md` now link the pack; Sheryl's acceptance is still
pending. Fixed an expanded-intake checkbox displaced by `details input` width.
Remaining scrolling, normalized-workbook alignment, technical-label and desktop-
only limitations are listed in the screenshot index.

Validation: **503 passed**, five existing PyMuPDF SWIG deprecation warnings, in
**3405.56s**. Full offline command: `LLM_PROVIDER=mock
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m
pytest -q -p no:cacheprovider --basetemp=runtime/0024/pytest`. Tests block sockets
and DNS; log: `runtime/0024/pytest.log`. Frontend tests **18 passed**; production
build and ESLint passed. Script syntax and staged whitespace checks passed.

Final Chrome walkthrough: **53 screenshots**, zero browser errors or external
request attempts (`runtime/0024/capture-BTD4VA/`). Request download is nonempty;
downloaded ZIP integrity passed with DOCX, manifest and request-list members.
All screenshots and all 53 rendered PDF pages were visually reviewed. Automated
verification confirms matching captions, one contained screenshot per page,
2880 × 1800 PNG dimensions and 1080 × 720 point PDF pages. Render/check logs:
`runtime/0024/pdf-review/`, `pdf-review.log`, `gallery.log`; frontend logs also
remain under `runtime/0024/`.

An intermediate capture exposed an intermittent SQLite lock when chat-history
loading overlapped a section-11 redraft. Explicit history-ready waits allow the
final complete capture to pass; underlying concurrent backend handling is listed
for separate review in `docs/screens/README.md`, not claimed fixed. No backend or
owner-template behavior changed. All task browsers, servers and test processes
have exited; ports 15124/18024 are closed. Cost **US$0**. Unchanged orchestrator
log/queue files were committed first as `87d2e18`. Earlier reply finalizations
0001–0023 remain outside this task; no next mailbox task was started.


## Task 0025 — B22 template comparison and IT change list (backend)

Implemented immutable, version-pinned comparisons in
`backend/app/services/{templates,template_diff}.py`, `api/templates.py`, and the
additive `TemplateComparison` model/schema/repository protection. The API compares
hash-verified candidate/active packages under the same shared parser/config,
records each change's category, reason, before/after values, section/XML anchor
and files to review, and downloads prompt/code items as UTF-8 text. Retries
reuse the same snapshot; changed active versions produce new snapshots and
optional expected-active checks reject stale requests. Prior comparisons and
version bytes remain available. No activation endpoint or frontend was added.

Only allowlisted visual properties classify as formatting. Existing narrative
guidance edits classify as prompt; IT must also update the literal narrative
anchor. Renamed headers, new columns/sections, removed sections, formulas,
numeric instructions, unknown structure and ancillary parts require code review.
Mixed changes inherit the most restrictive category. Mapping gaps or changed
parser/config rules prevent a formatting-only result from being eligible for
future confirmation. All candidates remain inactive; B23 owns admin activation.
No model calls, template/config rewrites or arithmetic changes.

`tests/test_template_diff.py` generates labelled fixture copies of v0.1 under
isolated test directories. `tests/fixtures/template_variants/README.md` describes
them; `docs/templates.md` documents routes, conservative classification,
provenance, historical retrieval and the B23 boundary. Owner template SHA-256
remains `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.

Validation: full offline mock pytest **526 passed**, five existing PyMuPDF SWIG
warnings, **2169.36 seconds** (`runtime/0025/full-tests.log`). Command:
`LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m pytest -q -p no:cacheprovider
--basetemp=runtime/0025/pytest-full`. Sockets and DNS are blocked by test fixtures.
The final comparison suite passed **23 tests** in **78.93 seconds**, using the
same flags plus `tests/test_template_diff.py` and
`--basetemp=runtime/0025/pytest-comparison-final`
(`runtime/0025/comparison-final.log`). Final fixture review changed existing font,
colour and span properties instead of appending duplicates, and explicitly pinned
the candidate's parent in the active-baseline test. Application code did not change
between the full run and this final focused rerun. No failures waived.

Earlier parser/comparison validation passed 50 tests. Coverage includes required
font/colour/header/column/section variants, prompt/formula/mixed changes, duplicate
anchors, gaps, current-active versus parent selection, stale expected-active IDs,
concurrent retries, SQL immutability, restart, scoped retrieval, corrupt source
bytes and config revision review. Representative final JSON/text exports are in
ignored `runtime/0025/review/`; review `mixed-it.txt` and `docs/templates.md`.
Whitespace checks pass. Frontend untouched; build/eslint inapplicable. No new
dependencies, live calls, owner-template edits, servers or test processes remain.
Unchanged orchestrator log committed first as `df7fdcb`; earlier reply finalizations
0001–0024 remain outside this task. No next task started. Cost **US$0**.

## Task 0026 — B25 pre-submission checks (backend/API)

Implemented `backend/app/services/submission_checks.py`, its API/router wiring,
and an additive immutable `SubmissionCheck.report` snapshot. Preview recomputes
all 14 configured sections, current confirmation events/fingerprints/source
integrity and applicable mandatory document gaps. Record saves open or passed
results and gap-specific CA reasons; validate enforces the gate before creating
an ES snapshot with purpose `submission`. Neither route moves workflow state or
the active ES pointer. SQLite serialization and preview tokens reject changed
inputs/confirmations/gaps. B16 must rerun the gate inside its transition transaction.

Mandatory gaps reuse the existing alternative/public/generation/dismissal rules.
A dismissal does not supply a submission reason. Reasons are retained in both the
ES and check, with complete gap labels and reviewer context; they never waive
missing/stale confirmations or N/A reasons. Existing rule-derived N/A reasons
are supported; no discretionary N/A override endpoint was added. Historical
results remain immutable after late evidence and restart; legacy records migrate
with an empty report rather than invented historical details.

The future panel reads saved section-2 Python exposure cells and retains draft,
unit/currency/period, synthetic labels, computed-value IDs and document/page
operand sources. Missing/corrupt sources produce named gaps. It always states
"Not connected: assumed consistent for this prototype", has no passed field and
is excluded from pass counts. It performs no balance comparison or network call.

The actual three-tranche demo plus confirmed saved-public evidence and mock spread
leaves catalogue 19 (industry mapping) open. Fourteen drafted sections produce
15 open checks; all confirmed yields 14 passed/1 open; a recorded industry-mapping
reason yields 15 passed/0 open. The revised valuation reopens 8/9/11/14 and preserves
the earlier snapshot. The panel carries TL-01 existing/outstanding/proposed limits
of SGD 45m/42m/60m and RCF-01 10m/4m/15m, all synthetic. Samples are saved under
ignored `runtime/0026/review/{b25-passed,b25-stale}.json`.

Validation: complete offline mock pytest **549 passed**, five existing PyMuPDF
SWIG warnings, **1498.10 seconds** (`runtime/0026/full-tests.log`, basetemp
`runtime/0026/pytest-full`). Includes all 23 B25 tests. Earlier focused B25 suite
**21 passed** (60.03s, `focused2.log`), then N/A/nil and legacy migration checks
**2 passed** (4.28s, `migration.log`). All runs use `LLM_PROVIDER=mock
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m
pytest -q -p no:cacheprovider`, with isolated basetemp paths below `runtime/0026/`.
Tests block sockets and DNS. The first focused run exposed an obsolete per-facility
expected value in the new test; corrected against the actual saved synthetic
workbook, with no application arithmetic change or waived failure.

Review `docs/submission_checks.md` and the setup link for contracts and the B16
integration boundary. SubmissionChecks UI remains pending Sheryl's review.
Frontend, owner templates and source packs are unchanged; the owner template hash
remains `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.
Whitespace checks pass. Frontend build/eslint are inapplicable. No new
dependencies, paid/live calls, servers or test processes remain. Cost **US$0**.
Earlier reply finalizations 0001–0025 remain excluded; orchestrator-owned paths
had no pending changes to commit separately. No next mailbox task started.

## Task 0027 — B16 workflow state machine and locks (backend/API)

Implemented configured human transitions in `services/workflow.py`, `api/workflow.py`
and app wiring. Submit and answer/resubmit rerun B25 in the same serialized SQLite
transaction that records the ES, check, event and active pointer. State/event/ES
and preview tokens reject stale actions and duplicate submissions. Credit Head
support and handoff remain separate events. Named-section returns, all five
approver outcomes, repeatable answer-only question cycles, recorded conditions,
immutable final snapshots, scoped retrieval and restart are covered at API level.

Shared `services/locks.py` guards existing section/chat/model/evidence/intake/gap/
spread/computation mutation paths, with repository checks for content and pointers.
A return clears confirmations for named sections and configured dependants. New
inputs can also unlock affected Stale sections for explicit repair; their revised
versions remain confirmable throughout that return cycle. Reviewer/question custody
blocks intake and content edits. Late final-state uploads may mark working content
Stale but never reopen or change the active final ES. Existing immutable triggers
protect ES/draft/event/check records; additive triggers and repository checks retain
question text and permit only one complete answer/resubmission update.

`docs/workflow.md` documents contracts, error codes, question/return policy, history
and the prototype role boundary. B17 screens remain pending. FIG S06 remains off;
the reserved configuration seam can assign the Supported-state handoff to the admin
role, without implementing admin checks, key-in or a screen. Existing Word creation
remains a labelled draft export, including returned cases; approved Word rendering
and a new working-cycle/reopen flow remain later Gate 3 integration, with no final
outcome silently reopened. No frontend or arithmetic changes.

Validation: **569 unique tests covered, no unresolved failures**. Full offline
mock pytest completed with **566 passed / 3 failed** in **2435.90 seconds**. All
three failures were obsolete synthesis assertions expecting “Draft state” instead
of the shared “locked” message. Updated that single assertion and reran the entire
synthesis file: **31 passed** in **767.50 seconds**, including all three failures.
No application code changed between those runs. Final standalone workflow suite:
**20 passed** in **79.87 seconds**; initial workflow/B25/schema/config suite:
**79 passed** in **117.73 seconds**. Five existing PyMuPDF SWIG warnings remain.
No failures waived. An early full invocation was stopped after 97 passes to finish
the new-input return repair regression; it is not counted as final coverage.

All runs used `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`,
with separate `--basetemp` directories below `runtime/0027/`. Sockets and DNS are
blocked. Logs: `full-final.log`, `synthesis-final.log`, `workflow-final.log` and
`focused.log`; exact collection/coverage: `collected.txt`, `test-coverage.txt`.
The workflow matrix includes 394 disallowed state/role/action combinations and
all successful routes, concurrent duplicate submits, direct lock bypasses,
immutable SQL history, conditions toggles and restart. The actual demo follows
submit → return → redraft/reconfirm → submit → support → handoff → question →
answer/resubmit → conditional approval. All 14 source registers, the one recorded
industry-mapping reason and the exact unconnected-master label remain pinned.
Late valuation leaves the final ES unchanged and marks working 8/9/11/14 Stale.
Review JSON samples: `runtime/0027/review/workflow-{final,snapshot}.json`.

Whitespace checks pass. Frontend unchanged; npm build/eslint inapplicable. No new
dependencies, paid/live calls, servers or test processes remain. Owner template
SHA-256 remains `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.
The orchestrator's unchanged log was committed first as `c3e91cf`; prior reply
finalizations 0001–0026 remain excluded. No next mailbox task started. Cost US$0.

## Claude build session, 11 Nov 2026: handover steps 1 and 2

Claude took over as builder under `CLAUDE.md` and `collab/HANDOVER_BUILD.md`. The front end is being rebuilt to project file section 2.14; the back end, tests and export stay.

**Step 1, test speed: done.** Cause: most tests rebuild the whole demo case (23 documents) and run in one process. Fix: `scripts/run_tests.sh` runs the suite in parallel with pytest-xdist (added to `requirements-test.txt`, installed in `.venv`), and 13 end-to-end demo tests are marked `slow` in `pytest.ini`. Measured on this machine: normal run 556 passed in 3 min 11 s; full parallel run 569 passed in 7 min 6 s (5 min 51 s on a second run); per-file baseline all 25 files passed. The one-process full run (`--gate`) was not re-timed today; the last recorded time is about 40 minutes. No test logic or application code changed. Commands are in `docs/setup.md`.

Not done: application hot spots were left alone. Profiling shows `Repository.save` and repeated document indexing dominate; that is a possible later speed-up, not needed for the target.

**Step 2, design mock-ups: shown to Sheryl, waiting for her go.** Static pictures only, in `docs/mockups/` (`inputs.png`, `workbench.png`, built from the HTML beside them with `node docs/mockups/capture.mjs`). Figures are illustrative synthetic demo data. No screen code is written until she agrees.

**Next:** steps 3 to 9 in the handover order. Step 10 (first live run) follows the "Live models" section of the handover: routing rules, registry changes and cost tracking come before the first live call.

## Claude build session, 12 Nov 2026: template v0.3 and handover steps 3 to 5 (first pass)

Sheryl approved the mock-ups and asked for the build in mock mode, plus a demo video and phone access.

**Template v0.3: done.** Built from Sheryl's v0.2 (`scripts/build_template_v0_3.py`), mapped (`scripts/map_template_v0_3.py`), export adjusted. Details in `docs/templates.md`. A mock ES exports on it; the changed pages were rendered and inspected. Interpretations to confirm with Sheryl: "analytics" was read as an Analytics heading with an analysis prompt above the existing headroom and sensitivity tables; "compare past years" as a separate Major changes table; the last column heading of her section 3 matrix was kept word for word.

**Step 3, Inputs screen: built.** Upload or scan a folder, intake summary, borrower flag, three-column checklist, start drafting. `frontend/src/workbench/InputsScreen.jsx`.

**Step 4, ES workbench: built.** Top bar with logo, ES status and Inputs button; left rail with status icons and Full ES; section view in the template's heading and box layout; Confirm; Edit text; Update section; version history; Full ES with Word export; right panel with Credit Assistant and Sources; phone layout. `frontend/src/workbench/`.

**Step 5, Credit Assistant and tracked changes: first pass.** A typed note becomes a suggested change shown with additions highlighted and deletions struck through, with Accept and Reject. On Full ES the user picks the section. It reuses the section chat and versions APIs unchanged.

Not built, or limited:
- Roll back to an earlier version (versions are listed and readable; no rollback API yet).
- The assistant answering questions, rewording, or working out the section on Full ES by itself. The mock provider only adds a typed note as CA input, and refuses notes with figures or dates. These need the live model (step 10).
- Remove or keep actions on a borrower-mismatch flag (the flag and View file exist; a flagged file is not used).
- Section view is heading, sub-headings, paragraphs and tables in template order, not a cell-for-cell copy of every template table. The Word export is the exact template.
- New v0.3 tables have no drafting support yet and show as gaps.
- Reviewer mode, checks panel, template admin, settings page (steps 6 to 8). Model picker, compare and the full file register are still reachable in the first dashboard at `#/classic`.

**Verification.** `scripts/run_tests.sh --all`: 569 passed (4 min 42 s). Front end: `npm test` 18 passed, eslint clean, `npm run build` clean. Three test files were updated for v0.3 (`test_templates.py`, `test_exports.py`, `test_template_diff.py`): expected values recomputed from the real v0.3 file and export, no assertions removed. Screens `docs/screens/wb_01` to `wb_13` captured and looked at; the capture also exercises edit, sources, reject and confirm. No live or paid calls. Servers stopped.

**Demo.** `docs/demo/WB_Credit_demo.mp4` (70 s, recorded by `scripts/demo/record_demo.mjs` on a fresh mock case), the exported ES as PDF and Word beside it, and `docs/demo/phone.md` for Tailscale access (`scripts/demo/serve.sh --phone --prepared`). Phone access was checked from the laptop only.

**Next:** Sheryl's review of the screens and v0.3; then rollback, reviewer mode (step 6), checks panel and template admin (step 7), settings page (step 8).

## Claude build session, 12 Nov 2026 (later): template v1.0, new-to-bank case, first live run

Sheryl's direction: v0.3 was not good enough. Treat her v0.2 edits as instructions, rebuild the template professionally, make the FIG demo a commercial building with real photographs and a map, generate a full input set for a new-to-bank client, and make the next end-to-end run live. Her choices: Keppel REIT with Ocean Financial Centre; external rating only for section 12; build straight through.

**Design (details in `docs/es_spec.md`).** One specification, `config/teams/fig_re/es_spec.yaml`, drives the Word template, what the model is asked for, what Python computes, the export fill and the screen layout. New code is in `backend/app/es2/`. The first-generation path (team `fig`, template v0.3, mock wording) is unchanged and stays the offline regression case.

**Done.**
- Template `templates/ES_Template_FIG_v1.0.docx`, built by `scripts/build_template_fig_v1.py`: 14 sections, 64 visible parts, cover grid, navy table headers, logo, photograph and map slots, section 10 rebuilt to Sheryl's notes (SGD'000, year-on-year change, segmental and geographic tables, analytics, base case, stress cases, assumptions and basis, inter-company debts, FX checklist). Parses with no mapping gaps.
- Public pack `demo/public_pack/keppel-reit/` (research by a background agent, 145 fact quotes machine-checked against page text) and synthetic deal papers `demo/synthetic_keppel/` (10 files, all labelled).
- Live drafting: Claude Fable 5.2 direct, gated by `WB_CREDIT_LIVE=1`, every call in the cost ledger. Python checks every citation and copied figure against the cited page, converts units, and computes changes, shares, totals, LTV, headroom, coverage ratios and the lease and tenant tables.
- Export fills template v1.0, including two photographs (Wikimedia Commons, credited), the OneMap location map and an ownership chart drawn from the checked unitholders table. Sources and open items are appendices.
- Workbench shows the structured sections in template order; `scripts/demo/serve.sh --keppel` opens the saved live case with no model calls.

**Live run result.** `docs/demo/Keppel_REIT_ES_live.pdf` (37 pages) and `.docx`. 13 applicable sections drafted (section 13 is not applicable to a new client). About 630 figures and fields passed the source checks, about 115 are computed by Python, 19 cells are unfilled and each is listed as an open item, and 1 model figure was rejected by the checks in the final run. No guidance text remains and no wording implies approval.

**Cost.** USD 54.35 in total for 58 calls on 12 Nov (`docs/cost_log.md`): the first full run, three partial reruns and two further full runs while the template, prompt and checks were refined. One full run is about USD 10 to 16 and 12 to 25 minutes. One call hit the output limit and was wasted (USD 1.77) before large sections were split into two requests.

**Verification.** `scripts/run_tests.sh --all`: 577 passed (569 earlier tests plus 8 new offline tests in `tests/test_es2.py`: figure checks, the live gate, cost ledger, workbook calculations, export with images). One existing test was extended to list the Keppel pack's manifest. Front end: 18 tests, eslint and build clean. Screens `docs/screens/live_01` to `live_09` captured from the saved live case and looked at. Servers stopped.

**Open with Sheryl.**
- Keppel REIT has no current public rating (S&P BBB and Moody's Baa3 were withdrawn in 2015 and 2016). I had told her it was rated BBB by S&P, from a stale broker note; that was wrong. With her "external rating only" choice, section 12 shows the withdrawn ratings as history and the internal rating as open. Alternative: add a synthetic internal rating worksheet (one-section redraft, under USD 1).
- The last column of her section 3 matrix was read as "No updates to report" (Yes for an existing borrower with no update in all five areas, and for a new borrower).
- The synthetic deal mortgages the whole building, although Keppel REIT holds about 79.9% through a property holding entity with other partners. The papers make partner consent a condition precedent.

**Not built or limited.**
- Credit Assistant on the live case still uses the mock chat operations (adds a typed note); live rewording and question answering are not built.
- A template rebuild means redrafting, because drafts pin the template version. Applying a formatting-only template change to saved drafts belongs to the template admin step.
- The demo video and `docs/demo/WB_Credit_ES_export.*` are from the earlier mock case, not this live case.
- Reviewer mode, checks panel, template admin, settings page (handover steps 6 to 8) are not started. Cost totals are at `GET /costs` and in `docs/cost_log.md`, not yet on a settings page.
- GPT and OpenRouter routes stay disabled; only the Fable 5.2 direct route is enabled.

## Claude build session, 12 Nov 2026 (evening): internal rating worksheet, product video, two fixes

Sheryl's direction: add the synthetic internal rating worksheet, then make a product demo video of the live case in a product launch style: no narration captions, large call-outs, divider screens for Documents Input, ES Drafting Pilot, Credit Chat Assistant and so on.

**Done.**
- `demo/synthetic_keppel/deal_folder/internal_rating_worksheet.xlsx` (catalogue type 10, labelled synthetic, fictional scale). Section 12's internal rating line is now read from it by Python (`compute.internal_rating`) with its source cited. The cover shows the rating. The pack has 11 files.
- `docs/demo/WB_Credit_product_video.mp4`, 2 min 52 s, 1920 x 1080, no sound. Built by `scripts/demo/record_product_video.mjs` from the real screens: intro card, five divider screens (Documents Input, ES Drafting Pilot, Credit Chat Assistant, Analyst Review, Word Export), large call-outs with a spotlight on the element, zooms, a page montage of the exported ES and a closing card. The Documents Input scene uses a fresh case. Section 12 is drafted on screen with the live model, with the wait shown at 8x and labelled. Everything else is the saved live case.
- Fix: amounts under an "SGD m" heading are now converted by Python (`amount_m`). The loan to value row in section 8 had shown 700,000,000 under "SGD m", giving a nonsense LTV and an "Outside limit" line in the section 10 headroom table. Now 24.3% against the 45% covenant, 20.7 points of headroom. This error was in the ES sent earlier today.
- Fix: the Credit Assistant on specification-driven sections. The suggested change had shown the whole section struck out with record ids, and the accepted note was not visible. It now appends the note under its own heading; see `docs/es_spec.md`.

**Live calls.** Sections 12 and 14 (rating), 8, 14, then 10, 11 and 14 again (LTV fix), and two section 12 drafts for the video. Total to date USD 63.43 over 68 calls (`docs/cost_log.md`); this session added USD 9.08.

**Verification.** `scripts/run_tests.sh --all`: 577 passed. `tests/test_es2.py` now also covers the rating worksheet line, the millions conversion and the assistant note on a specification-driven section, including its export. Front end: 18 tests, eslint and build clean. `docs/screens/live_01` to `live_09` refreshed and looked at. Every scene of the video was reviewed frame by frame. Servers stopped.

**Final ES.** `docs/demo/Keppel_REIT_ES_live.pdf`, 36 pages. 16 cells still read "Not provided", each listed as an open item. No current external rating exists, which is correct for this borrower.

**Known limits.**
- The Credit Assistant is still the mock operation (adds the typed note); the panel says so on screen and in the video. Live rewording and question answering are not built.
- A redraft of a section drops an accepted assistant note on specification-driven sections.
- Section 10 was not marked for update when section 8 changed, although its headroom table reads section 8. The dependency list needs that link. Found during this session; not fixed yet.
- The Inputs screen still shows the first demo's checkbox about the RCF being unsecured, which is wrong for this case (both facilities are secured). Not shown in the video; not fixed yet.
- `scripts/build_keppel_pack.py` rewrites workbooks with new file hashes on each run although the content is the same. Rebuild only when the content changes, then rerun intake.
- The video has no music or voice.

## Claude build session, 12 Nov 2026 (night): product video restyled

Sheryl's direction after seeing the first cut: flow is good; background and text boxes not modern enough; use the light look of the reference launch video; show the product as GWB; slightly faster; the Word export part may go.

- `docs/demo/WB_Credit_product_video.mp4` re-recorded: 2 min 2 s (was 2 min 52 s). Light background with a soft blue fade, dark type with one blue accent, frosted white call-outs, blue spotlight ring. Intro is an icon tile, "Introducing GWB Credit", then three short lines.
- The product is shown as "GWB Credit" on the cards, and the top bar label is restyled for the recording only. The app, the ES and the file names still say WB Credit; renaming the product itself is Sheryl's call.
- The Word Export divider, the export click and the page montage are removed. Four dividers remain: Documents Input, ES Drafting Pilot, Credit Chat Assistant, Analyst Review.
- Pace: holds, zooms, typing and dividers shortened (factor `K` in `scripts/demo/record_product_video.mjs`).
- One more live draft of section 12 for the recording. Total to date USD 63.90 over 69 calls.
- All scenes reviewed from frame sheets. No code outside the recorder changed, so the test results from the evening session stand. Servers stopped; the saved live case was restored.

## Enhancement plan agreed, 13 Nov 2026

Sheryl's feedback after the product video: offline editing with upload back, comments between roles, a checker view, updates from new information, switching between papers, and an ES flexible enough for pasted tables and screenshots and for template changes without code. She also asked for a model sense check on tables that code does not check, shown as a suggestion for a human check.

The ranked plan is in `docs/enhancement_plan.md`. Overnight build proposed: fixes, free blocks, sense check, papers list, maker and checker. Not started until Sheryl confirms.

## Claude build session, 13 Nov 2026 (overnight): enhancement ranks 1 to 5

Sheryl's direction: build ranks 1 to 5 of `docs/enhancement_plan.md` overnight without review. All five are built. Rules and limits for each are in `docs/es_spec.md`.

**Rank 1, fixes.**
- A draft now pins what it read from other sections. Section 10 is marked "Update required" when the loan to value line of section 8 changes, and sections 11 and 14 when the wording they read changes. A new version with the same content (an added note) does not mark it. Drafts saved before this change gain pins at their next redraft, so the saved live case's current drafts are not yet pinned.
- A redraft keeps accepted assistant notes and analyst added content.
- The "RCF as unsecured" checkbox is gone for this case. On specification-driven cases the question is asked only when the case has no security or a draft describes a facility as unsecured.
- A model reply in the wrong shape for a fixed-row table is treated as nothing supplied instead of failing the section (found while writing the test).
- The first mock demo's video and ES moved to `docs/demo/earlier_mock_case/` with a note.

**Rank 2, analyst added content.** Text, a table pasted from Excel or Word, or a screenshot can be added after any part of a section, moved, edited and removed. Each change is a new version. Blocks are labelled as analyst added and not checked, kept on redraft, and placed in the Word ES where they sit on screen. Rendered and checked in LibreOffice.

**Rank 3, model sense check.** The model reads the tables that code does not check and suggests what to recheck. Python keeps only suggestions that point at a real table and row and drops wording that reads as an assurance. Suggestions can be marked as looked at; open ones are listed in the Word ES open items. Run live on the whole saved Keppel ES: 13 sections, USD 1.63, one suggestion (section 4: the 34.2% lease expiry share in the concentration table against 29.9% in the lease expiry profile). A deliberate typing slip in a pasted table (an average of 48.8 instead of 38.8) was found in the screenshot run.

**Rank 4, papers list.** One store can hold several papers. `scripts/demo/serve.sh --keppel` now opens the live Keppel REIT paper with the ESR-REIT renewal (mock drafts) as a second paper. Papers screen with stage, who it is waiting for, progress and attention items; paper switcher in the top bar. The second paper was added to the saved live store; a copy from before is at `runtime/demo_live/case_single_paper`.

**Rank 5, maker and checker.** Role switch (credit analyst, Credit Head). Maker: pre-submission list and submit. Checker: mark each section reviewed or raise a query, return queried sections with a comment, support. Maker: sees the query on each returned section, changes only what was returned, replies and resubmits. Review trail. Run end to end in the browser on a throwaway copy of the live paper.

**Live calls.** Sense checks only: USD 1.99 over 14 calls. Total to date USD 65.88 over 83 calls (`docs/cost_log.md`). No drafting calls. The ES files in `docs/demo/` are unchanged.

**Verification.** `scripts/run_tests.sh --all`: 582 passed (577 before, plus 5: pins and kept notes, analyst blocks with export, sense check, two papers in one store, checker marks and resubmission). Front end: 21 tests (3 new for the paste reader), eslint and build clean. Screens `docs/screens/live_01` to `live_09` refreshed and `enh_01` to `enh_18` added, all looked at. Servers stopped. The saved live case was restored after every screenshot run (`scripts/screens/enhancements.sh` backs it up and puts it back).

**Known limits.**
- The role switch is a demo control, not a login or permission system. Role checks on moves are in the workflow API; the page itself trusts the switch.
- "Support only after every section is reviewed" is a screen rule, not an API rule.
- Analyst added tables are plain grids. Merged cells, cell formatting and formulas from Excel are not kept. Images are stored at up to 8 MB and exported as JPEG.
- The sense check reads one section's tables against the computed tables. It does not open source documents, and results vary between runs (two runs on section 4 gave two different valid suggestions).
- The second paper is on the first-generation path (mock wording, no analyst added content, no sense check).
- The submit check still lists "Financial spread" as a required input not complete for the Keppel case, although its figures come from the financial statements. The maker records a reason. The requirement should be switched off for specification-driven cases; not done.
- The Credit Assistant is still the mock operation.
- The product video predates these screens (new top bar, Review page). It still plays, but the recorder has not been rerun against the new layout.
- Phone layout: the top bar now takes four rows on a phone.

**Not started.** Ranks 6 to 10 of the enhancement plan (new information update, review threads with the live assistant, offline round trip, calculated tables in configuration, template upload), and the handover items: rollback, checks panel, settings page, scripted demo and reset, handover pack.

## Claude build session, 13 Nov 2026 (afternoon): enhancement rank 6, new information update

Sheryl chose the scenario: an updated CAS and a revised valuation on the Keppel REIT case. Specification with actual versus assumed state: `docs/new_information_spec.md`. This is a first working version.

**Built.**
- Four fictional revised papers in `demo/synthetic_keppel/late_update/` (CAS and term sheet with TL-01 raised from SGD 600m to SGD 650m, projections on the higher loan, valuation of SGD 2,750.0m against SGD 2,880.0m). The term sheet and projections were added so the papers agree with each other. No published figure of the real trust is changed. `scripts/build_keppel_pack.py --late` rebuilds only these; a full rebuild changes workbook bytes.
- `backend/app/es2/updates.py`: overview of new documents and affected sections, ordering, proposal (candidate version compared in Python), apply and dismiss. New record `UpdateProposal`. Endpoints under `/cases/{id}/sections/`.
- What changed page (`frontend/src/workbench/Updates.jsx`), a rail link with the count, and a link from a section marked "Update required".
- `reads_sections` in the ES specification (section 10's headroom table reads section 8).

**Found on the first live run and fixed.** In tables of figures copied from sources, the model also rewords the text cells. Those rewordings were shown and applied although nothing they rested on had changed (63 cells in section 10). Now a text cell keeps its current wording unless it cites a replaced document; figure cells always come from the new version. On the saved candidates this cut the cells shown from 100 to 57. A heavily rewritten paragraph is now shown as two whole blocks, not word marks.

**Live calls.** USD 18.78 over 20 drafting calls: USD 13.77 for the full run (12 sections), USD 5.01 to rerun sections 8, 1 and 10 after the fix. Before the run I had told Sheryl USD 5 to 10; the term sheet and CAS are cited in almost every section, so nearly the whole ES is affected. Total to date USD 84.66 over 103 calls (`docs/cost_log.md`).

**Result.** All 12 affected sections updated. The ES after the update (`docs/demo/Keppel_REIT_ES_after_update.docx`, 39 pages) cites no replaced document. Loan to value moves from 24.3% to 27.3%, headroom from 20.7 to 17.7 points. Remaining mentions of the first amount and value are "from, to" statements or open points (the pricing report and support email still state SGD 600m). `docs/demo/Keppel_REIT_ES_live.*` are unchanged.

**Verification.** `scripts/run_tests.sh --all`: 585 passed. Front end: 22 tests, eslint and build clean. New tests: `tests/test_updates.py` (3), `frontend/tests/diff.test.mjs` (1). Screens `enh_19` to `enh_29` captured with no page errors and looked at.

**Known limits.**
- Screens 23, 24 and 26 to 29 and the after-update ES come from the first full run, before the text cell fix. They show the flow correctly; some remark cells in that ES were reworded. Screens 21, 22 and 25 are from after the fix. The whole-block view of rewritten wording was checked against a saved proposal, not captured in the pack.
- Cost: an update of this size costs about as much as redrafting the ES. A section that only cites a replaced document for a minor point still needs a full proposal.
- Accept or keep is per part, not per sentence. A model written table is one part.
- A row the model does not return again is shown as "no longer sourced" and is dropped with the figures. The maker can propose again or dismiss, but cannot keep that one row.
- Tracked changes are on screen only. The Word ES holds the applied result.
- The saved live case is unchanged (no late papers). The updated state is kept at `runtime/demo_live/case_after_update`; it only runs when moved to `runtime/demo_live/case`. A scripted switch between the two is part of the scripted demo item.
- The Files screen still shows "Drafted" in its section list for a section marked "Update required".
- The second paper (first generation path) has no proposals. A proposal needs live model calls; with them off the page says so.

**Not started.** Ranks 7 to 10 and the handover items (rollback, checks panel, settings page, scripted demo and reset due 25 Nov, handover pack 27 Nov).
