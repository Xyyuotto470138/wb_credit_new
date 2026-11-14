# WB Credit build plan

Planning baseline: 10 Nov 2026 evening; requirements: `WB_Credit_PROJECT.md` sections 2.3, 2.8–2.12, 5 and 11, tasks 0001–0003 and `AGENTS.md`.
Tasks 0001–0003 deliver bootstrap, the public pack and this revised plan. B01 is implemented by task 0004; B03 source fixtures are delivered by task 0005. Other application paths below remain planned.
Business requirements are fixed; design choices below remain proposed. No live calls are authorized.

## Phase 1 reconnaissance (read only)

Source root: `../financial-spreading-tool/`; inspected actual source plus `ARCHITECTURE.md` and `TECHNICAL_DOCUMENTATION.md`.
Backend: `backend/app/` has FastAPI routers, SQLAlchemy job models, services, extraction agent, adapters, templates and ratios; `backend/src/` holds older ingestion/extraction utilities.
Frontend: React 19/Vite JSX under `frontend/src/{pages,components,api}`; upload → metadata → tables → mapping → notes, with routing recovery, AG Grid and PDF viewer. No typecheck or test script in `frontend/package.json`.
Fast pipeline A produces metadata/key figures/ratios; pipeline B produces full tables. Mapping and notes enrichment follow analyst confirmation. Existing daemon-thread jobs are not durable.
Extraction: at most three iterations: full extraction plus missing-row check, targeted repairs of failed statements, deterministic fallback. Validator checks arithmetic, completeness and cross-statement links; skipped checks and keyword heuristics require manual review, not automatic acceptance.
Seven provider names share two adapters: anthropic, openai, together, groq, deepseek, qwen and ollama. Client loads environment and constructs a live adapter at import; no mock provider exists.
Tests: recursive inspection found no project tests or pytest configuration. A read-only pytest run against `backend/` collected zero tests (exit 5); this is not a passing test suite. No Phase 1 frontend build was run because it writes `dist/` there.
Read-only test command, run from WB Credit: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 LLM_PROVIDER=mock python3 -m pytest ../financial-spreading-tool/backend --rootdir=. --confcutdir=. --noconftest -p no:cacheprovider -q`.
This disables bytecode, plugins, conftest and cache writes; no application was imported. `LLM_PROVIDER=mock` alone would not make the existing adapter safe (it rejects that provider).
`config.py` creates upload/output directories on import; application startup initializes its database. Do not boot or run import-based application checks in the source tree.

| Module | Phase 1 path (relative to source root) | Decision | Why |
|---|---|---|---|
| API/database/job schema | `backend/app/{main,database,models,schemas,config}.py`, `routers/` | Adapt | Keep layering and session pattern; replace job-only schema, import writes and runtime paths with case/version ownership. |
| Provider interface | `backend/app/llm/client.py`, `llm/providers/{anthropic,openai_compat}.py` | Adapt | Preserve chat/raw contracts; lazy construction, injectable mock, explicit model setting and paid-call gate. |
| Extraction loop | `backend/app/extraction_agent/orchestrator.py`, `skills/`, `prompts/` | Adapt | Keep bounded correction and failed-statement targeting; route all calls through injected provider and retain page provenance. |
| Deterministic validation | `backend/app/extraction_agent/validator.py` | Adapt | Retain pure checks, add fixtures for REIT formats/tolerances and expose skipped checks; no inherited confidence guarantees. |
| PDF routing/text | `backend/app/services/{ai_routing,ai_extract,page_splitter}.py`, `extraction_agent/skills/claude_full_extract.py` | Adapt | Keep PyMuPDF quality handling and original PDF/printed-page mapping through splits. |
| Legacy extraction tools | `backend/src/extract/`, `src/run_ingest_extract.py` | Don't reuse wholesale | Camelot, Tabula/Java and other packages exceed the approved stack; use PyMuPDF/pdfplumber fallback only. |
| Dual pipelines | `backend/app/services/{extraction,pipeline_a_fast,pipeline_b_extraction}.py` | Adapt | Preview/full distinction useful; unify authoritative figures, persistence, cancellation and explicit failure states. |
| Spreading/mapping | `backend/app/services/{spreading_agent,mapping,notes_enrichment}.py`, `templates/{registry,bank,corporate,reit}.py` | Adapt | Retain mapping validations; move team selections/templates into YAML and preserve source operands. |
| Ratio engine/matcher | `backend/app/ratios/{engine,keyword_matcher}.py`, `ratios/definitions/*.json` | Adapt | Python calculations useful; normalize units/periods, add provenance and replace generic proxy definitions where required. |
| Bank NIM | `backend/app/ratios/nim_override.py` | Adapt, bank config only | Preserve published-PDF → public-search → labelled estimated proxy order; remove implicit live search. |
| Risk narrative/chat | `backend/app/ratios/risk_summary.py`, `routers/chat.py` | Don't reuse wholesale | Replace general risk assessment and web tools with section-scoped cited drafting and CA-owned conclusion. |
| Spreadsheet exports | `backend/app/routers/{tables,mapping}.py` | Adapt helpers only | Pandas/OpenPyXL formatting useful; Word ES export and evidence appendix are new. |
| Frontend components | `frontend/src/components/{FileUpload,PdfViewer,EditableTable,StatusBanner}.jsx`, `api/client.js` | Adapt | Reuse interaction patterns; build case dashboard/editor/workflow and updated contracts. |
| Old navigation/demo answers | `frontend/src/{App.jsx,pages/,data/bakedAnswers.js}` | Don't reuse wholesale | Spreading wizard and canned answers do not represent progressive ES workflow. |
| Existing databases/uploads/demo media | source runtime files and `FS/` | Don't reuse | Build a curated public/synthetic pack; no inherited client data or runtime state. |
| Tests | No project test files found | Don't reuse | Establish offline regression coverage before importing adapted behavior. |

Known DBS 2025 dual-page quirk: pdfplumber can drop financial numbers; prefer PyMuPDF and preserve original page plus left/right region if splitting. Regression fixture must expose dropped numbers and page mapping.
Known bank NIM method: search PDF first, then public web if authorized, then keep an explicitly labelled estimated proxy. The implementation scans relevant pages among the first 30 and uses model extraction; it is not a deterministic published-value guarantee. No NIM calculation in the REIT demo.
Copy only selected source into this repository in later tasks, recording source path and copy date; never import from or write into Phase 1.

## Architecture and configuration

FastAPI/Pydantic API → services → SQLAlchemy/SQLite. React 19/Vite frontend uses JavaScript and JSX only (no TypeScript), HTTP and polling, AG Grid for numeric review, react-pdf for evidence and react-dropzone for uploads.
Keep one local process and bounded jobs with persisted status; restart marks interrupted work retryable. No queue service, vector database, SSO or live internal integration.
Planned layout: `backend/app/{api,services,models,schemas,llm,retrieval,analytics,exports}`, `config/teams/fig/`, `frontend/src/`, `tests/fixtures/`, `demo/`, `scripts/`, `docs/`; runtime under ignored `runtime/`.
`config/teams/fig/{template,catalogue,rules,dependencies,analytics,prompts,workflow}.yaml` defines all 14 section names, modes, 22 catalogue types, mandatory/alternative groups, usual owners, allowed public substitutes, case applicability, dependency DAG, formula operands, prompts, workflow steps, roles and allowed outcomes. `template.yaml` stores versioned mapping rules, not a generated document layout.
Use validated declarative predicates/operators, not executable YAML or eval. Reject unknown section references, cycles and unsupported formula operators. Version/hash configuration with each case and draft.
Core reads team IDs without FIG-specific branching. CBK/CMB can be added by configuration alone within the shared rule/formula vocabulary; a test-only alternate team proves it. No CBK/CMB business content is invented.
Use only section 7 stack plus python-docx, pyyaml and one search client. Do not copy Phase 1 requirements wholesale. Pytest is explicitly required tooling; frontend checks are `npm run build` plus eslint, as decided in task 0003. Other unlisted dependencies still require a question.

## Data model and invariants

| Entity | Required fields/relationships |
|---|---|
| Case | ID, public borrower name/identifiers, team/config version, case/borrower/facility/security attributes, CA position, workflow state, active ES version, created/upload timestamps; explicit existing-client/new-to-bank distinction. |
| Document/version | Case, type, entity, period, immutable content hash/path, revision/supersedes ID, origin (upload/folder/public/generated), synthetic flag, original filename, URL/retrieved-at for public, confirmation and conflict status. |
| ExpectedDocument | Case/catalogue or suggestion ID, applicability/mandatory reason, alternative group, usual owner, affected sections, status, linked document versions, search attempt/outcome, generated offer, dismiss reason and confirmer. |
| Section | Case/config section ID, applicability and N/A reason, readiness, current draft version, confirmed version, dependency/input fingerprint, editor revision; status does not discard unresolved gaps. |
| DraftVersion / ESVersion | Immutable section content/claim spans, computed table references, input/config/prompt/model/template versions, author/time, parent and CA edits; ESVersion snapshots section version IDs at submission/export. |
| Citation / Evidence | Claim or table-cell reference, immutable document version, PDF page/printed page/region or normalized document page, excerpt, origin/synthetic flag; URL/date for public evidence; alternatively a CAInput version/message/actor/time for typed facts. Calculations link all operand citations. |
| WorkflowEvent | Case, action, actor/role, UTC time, from/to state, ES version, named returned sections, override reason, payload; append-only within prototype. |
| Comment | Case/section and draft/ES version, author/role/time, body, optional parent and resolution; core supports return comments, richer threads are Should. |
| TemplateVersion / TemplateChange | Immutable uploaded DOCX bytes/hash, team, display version, parent, parsed heading/table/fill-point map, parse gaps, status, active pointer; per-change before/after, formatting/prompt/code category, reason, admin confirmation actor/time and change-list export. B01 defines schema, B22 implements parsing/diff and B23 activation/UI. |
| ChatMessage / SectionProposal / CAInput | Case/section/base draft, actor/time, typed message, proposed cited text and computed-value references, model/fixture version, pending/accepted/rejected status; CAInput is a separately versioned source linked to its message. B01 defines schema; B24 implements behavior. |
| SubmissionCheck / ApproverQuestion | ES version, 14 confirmation or N/A reasons, mandatory-gap reasons, freshness results; question text, sections, answer, actors/times and resubmitted version. B01 defines storage; B16/B25 implement transitions/checks. |
| Spread / ComputedValue | Document/CAInput source versions, metric/formula version, operand values and citations, unit/currency/period/scope, value, validation/proxy/synthetic flags; computed in Python. |

Expected-document statuses exactly: Provided; Found publicly; Can generate; Missing; Suggested; Not applicable; Dismissed.
Readiness states exactly: Waiting for input; Can draft (partial); Can draft (full); Not applicable; Drafted; Stale; CA confirmed.
Keep underlying completeness separately from displayed drafting state. A Drafted section can still have gaps. A missing document never becomes a statement that it does not exist.
Public finds are usable in partial drafts with labels, but satisfy a mandatory input only after CA confirmation. Dismissal requires a reason and cannot silently waive a mandatory gap; submission override is separate.
Generated spreads satisfy their expected item only after generation/validation. An industry-code suggestion needs CA confirmation. External rating never satisfies mandatory internal rating.
Partial public valuation/portfolio lease disclosures do not satisfy a full secured-property valuation/lease input. Permit public report evidence as a substitute only where catalogue rules explicitly allow it.

## Intake, public search, retrieval and computation

Upload and configured-folder scan share content-hash deduplication, classification (type/entity/period), conflict review and expected-list recomputation. Newer files retain old revisions; older/wrong-entity files do not silently replace accepted evidence.
Catalogue rules trigger property valuation/insurance, covenant certificate/monitoring and evidence of prior-condition fulfilment. Suggestions beyond the catalogue stay Suggested with rationale; offer a spread and industry-code suggestion when possible.
Gap requests group by RM/client/internal team with why, blocked sections and search status; export a request list. Unsupported/scanned files surface a gap/manual-review state; OCR is outside the approved stack.
Define `SearchProvider.search(public_identity)` and retrieval result contracts with URL, title, retrieval date and saved content hash. Only the borrower's public name/identifiers enter the query; no deal text or internal/client document-type queries.
Tavily is accepted as the one live search client (task 0003); isolate it from the LLM adapter. Verify its interface/terms at implementation, keep it disabled until an approved task, and inject canned responses in tests. No client installed in 0001.
`SavedPublicPackProvider` implements the same contract for repeatable offline demos/fallback. `Off` mode records not run. Distinguish not run, failed, no match, and found; cached sources retain their original retrieval date and show that they came from the pack.
Public-eligible types only: listed-company reports/statements, ownership, public fund documents, external releases and news. Annual-report valuation/lease summaries are public evidence, never a search for confidential full reports. Internal/client-only catalogue items go directly to Missing.
Downloaded/public/uploaded text is evidence, never executable instructions. Validate content/type/size and entity match; constrain fetches to public HTTP(S), reject local/private targets and re-check redirects.
Index page-bound chunks and table references with entity/period/type metadata. Core retrieval filters by section input map and ranks keyword matches/support; preserve complete complex tables for manual checking. Optional model usefulness scoring is block S01.
Draft only supported claim/evidence pairs. Reject unknown citations, numbers that differ from computed facts, and unsupported claims; use named gap markers instead. Preserve document/page references through PDF splitting, generated spreads and normalized non-PDF pages.
Python computes exposure by entity/facility/currency, utilisation, totals (no mixed-currency summation without sourced FX), covenant headroom and account-conduct dates/arrears. Nil exposure requires explicit new-to-bank input; missing conduct never means satisfactory conduct.
Section 10 consumes validated Phase 1 spreads plus sourced operational disclosures. Models write commentary around immutable computed tables; models never create or revise arithmetic.

## Model provider and drafting

Retain Phase 1 chat/chat_raw contracts, but add dependency injection, lazy construction and configurable model ID. Default runtime/test provider is `mock`; missing fixtures fail explicitly, with no live fallback or environment-key loading in tests.
Choose the live provider/model at the first paid-run gate, after checking then-current availability, suitability and approved budget. Runtime and tests stay mock until explicitly approved.
Real model/search calls require explicit approved-task configuration and spend ceiling; never infer authorization from a key or from general public-search availability. Log provider/model/config versions and usage without secrets.
Section modes: 1 request extract; 2 computed exposure; 3 update synthesis; 4 business; 5 ownership; 6 management; 7 facility table; 8 security with CA-confirmed unsecured status; 9 repayment synthesis; 10 computed analytics/commentary; 11 risks/mitigants; 12 supplied internal rating; 13 computed conduct/summary; 14 wording of CA-stated position.
Dependencies: 9 needs 7 and 10; 11 needs 3–10 (applicable sections); 14 needs all mandatory applicable sections and CA position. Partial dependency evidence supports only a partial draft with gaps; full readiness propagates completeness.
New input invalidates directly affected and downstream sections. Preserve all CA edits and confirmation history, mark Stale, and offer explicit redraft into a new version; never overwrite edited text automatically.

## REIT analytics (section 10)

All thresholds below are the project section 3.1 planning baseline, not newly verified regulatory guidance. Store rule source/effective date and verify definitions against the supplied MAS reference before the analytics acceptance gate.
Phase 1 defines aggregate leverage as debt/assets, interest coverage as NPI/finance costs, and property yield as NPI/property value. These may be proxies; never relabel them as regulatory measures or valuation capitalisation rates.

| Measure | Planned evidence/calculation and validation |
|---|---|
| Aggregate leverage | Prefer sourced regulatory disclosure or compute with verified regulatory debt/assets scope; keep period/perpetual/JV treatment explicit. Show headroom `50.0% - leverage%` in percentage points; negative means breach of configured threshold. |
| Interest coverage | Use sourced regulatory ICR or validated definition with complete operands; a generic NPI/finance-cost proxy cannot drive regulatory headroom. Headroom `ICR - 1.5` times; flag `< 1.8` for the project-stated improvement-plan expectation. |
| Debt maturity profile | Bucket sourced maturity amounts/dates and sum in code; reconcile bucket totals to debt and expose unmatched totals, currencies and reporting date. |
| Fixed-rate debt share | Fixed/hedged debt divided by total debt with matched scope/date; distinguish hedging definition and prevent double counting. |
| Occupancy | Occupied area / lettable area where comparable; otherwise preserve sourced reported percentage and basis. No unweighted average of properties. |
| WALE | Weighted remaining lease years using stated rental-income or area weights; keep basis/as-of date. Prefer sourced figure if granular operands unavailable. |
| Net property income | Property income less property expenses with sign/unit checks; reconcile to reported NPI. |
| Distribution per unit | Sourced reported DPU, or distributions/eligible units on a stated basis; normalize cents vs currency units and period. |
| Portfolio valuation | Sum same-date comparable asset values with sourced FX if needed; retain ownership basis and distinguish portfolio from secured property. |
| Capitalisation rates | Extract disclosed valuation rates/ranges by property/date; an NPI/value yield is separately labelled as a proxy, never substituted. |

Unknown operands, incompatible definitions, zero denominators or mismatched periods yield N/A plus a gap, never zero or fabricated headroom. Use decimal arithmetic and round only display values; carry synthetic/proxy flags to every derived figure.
Do not present borrowing capacity from percentage-point headroom unless a separately reviewed scenario specifies how borrowing changes assets. Tests cover 50%, 1.5x and 1.8x boundaries, breaches and missing regulatory inputs.

## Section chat (B24, G2)

All 14 sections have typed chat. Each turn calls the injected model provider; offline tests use saved mock responses, never code edits or live calls. Include the section's evidence, current text, gaps and immutable computed values.
Persist a proposal against its base version with citations; accept creates a new draft and resets confirmation, reject keeps text unchanged. A concurrent edit or late evidence makes the proposal stale and requires regeneration/review, never a silent overwrite.
Typed facts become versioned CA input citations (actor, time, message and supplied fact), visibly distinguished from document/page evidence. Preserve ordinary document/page and public URL/date citations in revised text; do not invent source documents for CA assertions.
Chat cannot modify computed tables or smuggle changed numbers into narrative. A proposed numeric input requires explicit CA acceptance as a sourced input, validation and Python recomputation; persist operands/results and invalidate affected/downstream sections. Incomplete or invalid operands remain gaps.
Section 12 still uses supplied ratings only; section 14 only words the CA's stated position. Apply normal workflow locks and section permissions to chat acceptance and recompute inputs.

## Workflow, checks, outputs and measures

Team `workflow.yaml` defines roles, steps, transitions, return targets and outcome toggles. Default path: Draft → Submitted to Credit Head → Supported → With Credit Approver → Approved. Credit Head checks facility structure and recommendation and can support or return named sections with comments.
Role switcher exposes CA, Credit Head, Credit Approver and template admin. Backend validates actions; this is a process prototype, not real authentication. Template admin has no credit-decision privilege.
Approver outcomes: approve; approve with conditions (configurable, on by default, requires recorded conditions); raise question; decline (final); return to CA (named sections/comments). Persist Approved with conditions and Declined as distinct final outcomes; prevent further transitions or editing of their snapshots.
A question records text/sections and routes to CA; CA records an answer and resubmits to the approver directly. Proposed: only the answer is editable during the question cycle; substantive ES revisions use Return to CA and the normal Credit Head review path. Test the route, answer requirement and retained question history.
Lock section edits while with a reviewer; a recorded return unlocks working content. Every move records actor, role, time and ES version; retain Supported separately from handoff. Read views expose sources, questions/answers, conditions and version changes; richer threads/diffs remain S02/S03.
Before initial submission or resubmission, B25 checks all 14 sections: each must be CA confirmed against current content/inputs, or Not applicable with a nonblank reason. Show every outstanding section and disable Submit; API enforces the same rule. Stale sections need re-review and fresh confirmation.
Open mandatory document gaps require recorded reasons tied to each gap and the submitted snapshot; a dismissal is not an automatic override. Reviewers see these reasons and gaps. Missing confirmations or N/A reasons cannot be waived by a document-gap reason.
The future credit master panel lists limits, loans outstanding and other mapped figures it would compare, and states exactly: "Not connected: assumed consistent for this prototype". It never displays a passed check, verification badge or fabricated balances; it is not part of the pass count.
Approved and Approved with conditions snapshots and their template versions are immutable. Late evidence marks working content Stale; a new working version is explicit, with no automatic approval change. This is an accepted task-0003 decision, not an open proposal.
S06 optionally inserts credit admin support between Supported and With Credit Approver through configuration plus one screen for administrative checks and recorded system key-in status. It performs no actual integration; if not selected at the 20 Nov Should gate, document it on the roadmap.
B18 fills the pinned uploaded Word template, including draft exports by G2; B16/B19 add locked approved-snapshot export verification by G3. No generated replacement layout. Gap-request lists remain separately exportable by usual owner.
Core stores timestamps, versions, citations, gap confirmations and return events needed for project section 9 metrics; S04 calculates/displays first-upload→first-full-draft elapsed time, CA edit distance per section, return count/sections, sourced-claim share and public-gap closure share/CA confirmations.
Define full draft as all applicable mandatory sections having drafts with no unresolved mandatory gaps; record override submissions separately. Metric denominators exclude explicit gap markers, retain counts, and treat zero denominators as N/A. Manual-hours baseline stays blank unless supplied.
No AI approval wording; section 14 records the human position. Keep aspirational value claims labelled and do not extend Phase 1's demonstrated timing to the ES workflow.

## Uploaded template mapping and versioning

Read-only inspection of `templates/ES_Template_FIG_draft_v0.1.docx` on 10 Nov: SHA-256 `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`; 14 numbered Heading 1 paragraphs, 15 top-level tables (cover plus one wrapper per section), 28 nested tables. The mapping must recurse through wrapper cells; matching only top-level tables will fail.
B22 owns the shared parser/version registry, needed by B18 at G2; admin comparison and activation UI lands at G3. Preserve original bytes under runtime template storage, never write into owner-controlled `templates/`. Seed v0.1 as the initial active version and record hash/version on each ES snapshot/export. Later activation affects only explicitly selected new working versions, never historical ES exports.
Match headings by numeric section ID and configured normalized title; normalize whitespace/tab and decorative ⓘ only for lookup, preserving displayed text. Match tables within a section by ordered normalized header-cell text plus configured row labels for key/value tables. Ambiguous/missing anchors create named mapping gaps, never positional guesses.
Find italic [bracketed] placeholders across run boundaries, using effective style/direct formatting; many non-placeholder headers are also italic. Key repeated placeholders by section/table/cell/occurrence. FY[  ] tokens are period fills; DD/MM/YYYY and blank cells need explicit date/row-label mappings. Bracketed instructions are guidance, not source facts.
The following signatures are observed anchors (semicolon separates different tables; slash separates header cells). Implementation stores complete ordered headers in configuration, including columns abbreviated below; no hard-coded layout positions.

| Section / Heading 1 title | Table header or row-label anchors | Fill sources / repeat rule |
|---|---|---|
| Cover (before section 1) | Borrower(s) – CAS no.; Obligor Group; Country | Borrower/CAS/rating placeholders, group/country and explicit watchlist flags from sourced inputs; repeated borrower entries preserve cell structure. |
| 1 REQUEST / PURPOSE | Borrower/ Group / Current Classification / Date of classification (MMMYY) / Proposed classification; SM/DPD question | `[To provide details of the request]` from CAS/term sheet; classification/action-plan fields and CAS image are sourced or named gaps, never inferred from missing files. |
| 2 SUMMARY OF CURRENT CLIENT GROUP EXPOSURE | Borrower / Facility / Existing limit / Outstanding / Proposed limit / Change (+/-) / Expiry date / Secured / Unsecured | Python exposure rows replace borrower/facility placeholders; clone detail rows before Total obligor group; totals computed, nil requires explicit new-to-bank input. |
| 3 KEY UPDATES | Date / Development / Source / Credit impact / Comment; No. / Prior approval condition / credit comment / Status / Evidence / comment | Cited updates and prior-condition evidence; repeat development/condition rows; statuses never assumed met. |
| 4 BUSINESS BACKGROUND | Borrower (key/value); Property / Location / Sector / Valuation (S$m) / Valuation date / Occupancy (%) / WALE (years) | Industry and overview placeholders; repeat property rows before Total portfolio; N/A reason preserves section despite template's delete-if-inapplicable guidance. |
| 5 SHAREHOLDING STRUCTURE | Shareholder / unitholder / Holding (%) / Remarks; chart placeholder table | Repeat holder rows before Total; supplied chart or named gap, sponsor/change narrative with sources; fixed sample 100.0 must be validated, not assumed. |
| 6 KEY MANAGEMENT AND STAKEHOLDER | Name / Designation / Experience / years in role / Remarks; Stakeholder / Role / Relationship / comment | Repeat people/stakeholder rows and fill sourced change narrative; sample sponsor/manager/trustee labels do not establish facts. |
| 7 FACILITY STRUCTURE | Key terms / Facility 1 / Facility 2; rows Borrower through Other key terms and conditions | Explicit template instruction says add columns for additional facilities. Clone a facility column and corresponding grid/style cells, preserving key-term rows; overflow is a mapping/layout gap pending owner-reviewed format, never truncate facilities. |
| 8 SECURITY SUPPORT | Security / support / Description / Value (S$m) / Valuer and date / Basis / LTV (%) / Remarks; Insurer (key/value) | Repeat security rows; fill insurance row values; checkbox/unsecured basis needs CA confirmation; LTV is computed or a named missing-input gap. |
| 9 SOURCE OF REPAYMENT | Measure / FY[  ] / FY[  ] / Projected FY[  ] / Remarks; Year / % of gross rental income / % of net lettable area; Tenant / Trade sector / % of gross rental income / Lease expiry | Primary/secondary narrative placeholders; Python debt-service values with period mapping; repeat lease buckets and tenant rows beyond three seed tenants. |
| 10 FINANCIAL HIGHLIGHTS AND ANALYTICS | S$m / FY[  ] / FY[  ] / FY[  ] / [Interim] / Remarks; Measure / Limit / covenant / Actual / Headroom / Status; Scenario / Interest coverage (x) | Map named metric rows and period placeholders; repeat facility-covenant rows after fixed regulatory rows. Python computes sensitivity scenarios only with complete sourced assumptions; unknown DSCR/sensitivity/other template metrics stay named gaps. Fill commentary with citations. |
| 11 KEY CREDIT RISKS AND MITIGATES | No. / Key risk / Description / Mitigants | Repeat cited risk/mitigant rows; example risk labels are suggestions, not evidence. |
| 12 CREDIT RATING | Borrower / Current CRR/SL rating / Previous rating / Rating date / Change and reason; Agency / Rating / Outlook / Date | Repeat supplied internal rating and external agency rows separately; example agency names are not evidence that a rating exists. |
| 13 CONDUCT OF ACCOUNT | Facility / Limit / Peak utilisation / Average utilisation / Excesses (no. / max / days) / Past dues (no. / max DPD) / Remarks; Covenant / Requirement / Last tested / Actual / Compliant; adverse-findings question | Python facility/covenant rows grow as required; preserve dates and citations; absence of evidence cannot tick No adverse findings. |
| 14 RECOMMENDATION: CONCLUSION | No. / Condition / covenant / Timing; Role / Name / Decision / Date | Narrative/checkbox represents CA position only; repeat conditions; sign-off is populated from human workflow events, blank/pending in draft. Approver questions stay in workflow history because template has no question checkbox. |

Copy a styled seed row for each extra repeated record, retaining borders, widths, cell merges and paragraph/run properties; keep header/total rows separate and recalculate totals in Python. Zero/one/many rows, nested tables, merged cells and multi-page overflow need fixtures/render review. Never leave sample borrower/tenant data as apparent facts.
Fill a copy of the template in place; retain headings, order, section breaks, styles, headers/footers and table structure. Inline source markers, labels and named gaps use mapped text/remarks cells. Keep detailed source/gap manifests and status/template version in companion export metadata when no mapped location exists, rather than inventing an appendix or redesigning the ES.
A missing/ambiguous field yields a section/anchor-named gap in the preview and manifest, with an inline marker where a valid slot exists. Preserve every section; if a heading/section is absent from the template, flag the canonical missing section and block complete/final export rather than silently omit or synthesize a layout. Valid draft exports remain clearly identified as drafts in export metadata/UI and available mapped content.
Visual acceptance in B18 compares filled copy with the owner template using zero/one/many-row fixtures, long narrative and at least three facility columns. Validate structural preservation and content completeness; task 0003 inspected XML only and makes no rendered-layout claim. Use the documents skill render/verify process; raise any unlisted rendering dependency through the mailbox.

## Template admin (B22–B23, G3)

Admin upload creates an immutable candidate with parse report, before/after anchors and diff against the active version. Reject unreadable/unsupported files and report missing or duplicate sections; never replace active bytes on upload. Preserve all candidate and active versions.
Classify each change with its reason and affected section/anchor: formatting only when structure/mapping/instructions are unchanged (font, spacing, borders); prompt change for changed narrative guidance or drafting intent; code change for unsupported mapping/structure, new computed fields/formulas or ambiguous changes. Added/removed fields and headings cannot be silently classed as formatting only.
Use deterministic structural comparison with optional model explanation through the mock-first provider. A mixed candidate inherits the most restrictive unresolved change; uncertain classification requires review. The admin sees every change/reason and exports prompt/code items with before/after values and affected configuration/files for IT; no automatic prompt/code edits.
Only a fully mapped, formatting-only candidate can go live after explicit template-admin confirmation. Activation records actor/time, expected active version and candidate hash; reject concurrent stale diffs. Prompt/code candidates remain inactive pending a separately implemented/reviewed change list and revalidation; do not activate only part of a mixed file.
Test font-only changes, changed placeholder guidance, new formula/table/heading, duplicate anchors, mixed changes, unconfirmed activation, wrong role, old active-version race and historical export stability. The same parser and mappings serve export and admin, preventing divergent interpretations.

## Queueable blocks and gates

IDs below are plan IDs, not mailbox task IDs; orchestrator assigns tasks. Paths are relative to this repo, `app/` below means `backend/app/`.
Each block is about 0.5–1 focused builder day, including its tests. Shared paths are worked sequentially. A task may split a block when review requires it.
G1 = Fri 13 Nov intake/readiness; G2 = Fri 20 Nov sourced editable full draft, section chat and draft template export; G3 = Wed 25 Nov pre-submission checks, revised workflow, template admin and E2E and code freeze; G4 = Fri 27 Nov handover. Should work needs the 20 Nov go/no-go and must finish before freeze.

| ID / WS / effort / gate | Goal and primary files | done_when | Tests | depends_on |
|---|---|---|---|---|
| B00 / setup / 0.5 / G1 | Bootstrap; `.gitignore`, `BUILD_PLAN.md`, `BUILD_STATE.md` | Local repo on main, first commit includes mailbox/baseline and plans; no app code | Git/ignore/plan checks; document zero-test outcome | — |
| B01 / 1 / 1 / G1 | Schema, config and provider seam; `app/{models,schemas,llm,main}.py`, `config/teams/fig/`, `tests/conftest.py` | Persist case/version/entities; exact 14 sections and 22 types, workflow roles/outcomes, template/chat/check/question entities validate; mock boots without network/key | Schema relationships, cycle/invalid rule/outcome rejection, alternate-team config, blocked sockets | B00 |
| B02 / 2 / 0.5 / G1 | REIT shortlist/public pack (task 0002); `demo/reit_shortlist.md`, `demo/public_pack/<slug>/manifest.yaml` | Eligible listed REIT with external rating documented; saved public evidence has URL/date/pages/hash | Manifest completeness, entity/period checks, offline load | B00 |
| B03 / 2 / 1 / G1 | Synthetic three-tranche pack; `demo/synthetic/`, `tests/fixtures/` | All client/internal demo inputs and revised valuation exist with synthetic headers and consistent gold figures | Pack/schema/header and exposure/covenant reconciliation | B01, B02 |
| B04 / 3 / 0.5 / G1 | Upload/folder intake; `app/api/documents.py`, `app/services/intake.py` | Same files through either route create versioned evidence; duplicates/conflicts explained | Duplicate hash, wrong entity, old period, scan idempotence | B01 |
| B05 / 3 / 1 / G1 | Expected list/readiness; `app/services/{gaps,readiness}.py`, FIG rules | All seven document/readiness states and dependency effects match case rules; gaps grouped by owner | New/renewal, conditional/alternative inputs, dismissal, partial/full matrix | B01, B03, B04 |
| B06 / 3 / 0.5 / G1 | Search/generation offers; `app/services/search/`, `app/api/gaps.py` | Saved-pack/live/off contracts exist; partial/public confirmation and search-attempt outcomes visible | Query privacy allowlist, off/error/no-hit, external-vs-internal rating, partial valuation | B02, B05 |
| B07 / 6 / 0.5 / G1 | Intake dashboard; `frontend/src/{App,CaseDashboard,IntakePanel}.jsx`, `api/` | Three tranches visibly show provided/public/missing/draftable before drafting exists | API tranche assertions; frontend build + eslint; manual upload/scan review | B03, B06 |
| B08 / 4 / 0.5 / G2 | Page evidence retrieval; `app/retrieval/`, `app/services/normalize.py` | Section retrieval returns only case/entity/period-matched evidence with stable page/region citations | Citation resolver, split-page mapping, complex-table preservation, malicious evidence | B04, B06 |
| B09 / 5 / 1 / G2 | Adapt Phase 1 spreading; `app/extraction_agent/`, `app/services/spreading.py` | Mock extraction→validation→targeted fix/fallback→mapping persists cited figures and issues | Bounded three iterations, arithmetic failures, missing rows, DBS PyMuPDF regression | B01, B03, B08 |
| B10 / 5 / 0.5 / G2 | Computed tables and REIT set; `app/analytics/`, FIG analytics | Sections 2/10/13 match gold values; all ten REIT measures and additional mapped template metrics/sensitivity are computed from sourced operands or named gaps | Units/FX/scope, missing/zero denominators, MAS definition and boundary fixtures | B09 |
| B11 / 5 / 0.5 / G2 | First drafts 1–8,10,12,13; `app/services/drafting.py`, FIG prompts | Correct section modes, citations/public/synthetic labels, immutable computed tables and gaps | Unsupported claim/number rejection; supplied rating only; unsecured confirmation | B05, B08, B10 |
| B12 / 5 / 0.5 / G2 | Synthesis 9,11,14; `app/services/drafting.py`, FIG dependencies/prompts | Dependency ordering works; 14 cannot invent a CA position | Partial/full dependency chains; absent CA position, mandatory section gating | B11 |
| B13 / 5 / 0.5 / G2 | Versioning/Stale; `app/services/versions.py`, `app/api/sections.py` | Revised valuation marks 8 and downstream sections Stale without changing CA text; redraft creates version | Transitive invalidation, confirmation reset, revision conflict and preservation | B12 |
| B14 / 6 / 1 / G2 | Section editor/source panel; `frontend/src/{SectionEditor,SourcePanel}.jsx` | CA edits, redrafts/confirms with page citations and visible named gaps; typed refinement is B24 | API save/redraft/confirm; frontend build + eslint; manual source navigation | B07, B11, B13 |
| B15 / 6 / 0.5 / G2 | Full draft dashboard; `frontend/src/{CaseDashboard,VersionHistory}.jsx` | All 14 sections navigate; tranche progression, Stale choice, chat acceptance and draft template export demonstrated | Mock draft integration; frontend build + eslint; G2 walkthrough | B12, B14, B18, B24 |
| B16 / 7 / 0.5 / G3 | State machine/locks; `app/services/workflow.py`, `app/api/workflow.py` | Configured roles follow support/return and all five approver outcomes; question answers resubmit to approver, decline is final; versions locked and B25 gates enforced | Transition/outcome matrix, question loop, conditions toggle, finality, lock bypass, submission checks | B13, B15, B25 |
| B17 / 7 / 0.5 / G3 | Reviewer UI; `frontend/src/{ReviewPanel,RoleSwitcher}.jsx` | Credit Head returns 9; CA resubmits; Credit Head supports; approver outcomes/questions/conditions and template-admin role are visible | API role/return integration; frontend build + eslint; manual walkthrough | B16 |
| B18 / 8 / 1 / G2 | Template-filled Word/request exports; `app/exports/`, `app/api/exports.py` | Draft snapshot fills pinned template, all 14 sections retained; nested mappings/labels/gaps/version recorded; repeat rows/columns preserve format; no generated layout | Template hash/anchors, missing/ambiguous maps, zero/one/many repeats, DOCX citations and rendered comparison; historical stability at G3 | B10, B13, B14, B22 |
| B19 / 9 / 0.5 / G3 | Scripted demo/reset; `scripts/demo_mock.py`, `scripts/reset_demo.py`, `tests/test_demo.py` | Offline demo covers tranches, chat/recompute, checks, return/question/approval, late evidence, template diff/activation and pinned exports; reset repeatable | Full scenario twice with blocked network, deterministic gold assertions | B17, B18, B23, B24, B25 |
| B20 / 9 / 0.5 / G3 | Gate regression/fixes; `tests/`, affected app/frontend files | G1–G3 acceptance passes, no known core blocker, no running processes; freeze recorded | Entire mock pytest suite, frontend build + eslint, Word and UI review | B19 |
| B21 / 10 / 0.5 / G4 | Handover; `README.md`, `docs/{setup,configuration,demo,limits,handover}.md` | Clean setup/reset/demo documented; admin template swap and IT change-list process shown; owner/walkthrough outcome recorded | Fresh local setup smoke, links/commands, no secret/live-call defaults | B20 |
| B22 / 15 / 1 / G2 parser; G3 diff | Template registry/parser/diff; `app/services/templates.py`, `app/api/templates.py`, FIG `template.yaml`, `tests/test_templates.py` | G2 seeds versioned v0.1 with all nested mappings/gaps; G3 compares candidate to active, classifies every change with reason and exports prompt/code list | Actual template inventory; malformed/missing/duplicate anchors; formatting/prompt/code/mixed diffs; immutable bytes | B01 |
| B23 / 15 / 0.5 / G3 | Template admin; `frontend/src/TemplateAdmin.jsx`, `app/services/templates.py`, `tests/test_template_admin.py` | Admin uploads, sees diff/reasons, confirms formatting-only activation; other changes export for IT and stay inactive | Role, confirmation, mixed-change and concurrent-version checks; old export stable; frontend build + eslint; UI review | B17, B18, B22 |
| B24 / 16 / 1 / G2 | Typed section chat; `app/services/section_chat.py`, `app/api/chat.py`, `frontend/src/SectionChat.jsx`, `tests/test_section_chat.py` | All 14 sections propose cited revisions; CA accepts/rejects; CA facts cited as input; accepted numeric inputs recompute in Python | Mock turns, citation/number rejection, accept/reject/stale conflict, locks, immutable tables and validated recompute; frontend build + eslint | B10, B13, B14 |
| B25 / 17 / 0.5 / G3 | Pre-submission checks; `app/services/submission_checks.py`, `frontend/src/SubmissionChecks.jsx`, `tests/test_submission_checks.py` | All 14 confirmed or N/A with reason; gap-specific reasons visible; exact future-panel label and figures list; API/UI disable invalid submission | 14-section matrix, empty N/A/override reasons, stale confirmations, no master-system passed state; frontend build + eslint | B05, B13, B15 |
| B26 / 19 / 1 / G2 extension | Multi-model registry/picker/compare; `config/models.yaml`, `app/llm/`, `app/services/model_comparison.py`, `frontend/src/ModelControls.jsx` | Case default and redraft override persist concrete model provenance; two offline variants share prompt/evidence and Python numbers; no unauthorized live calls | Registry/route guards, default/override/history, preview isolation, citation/rejection/gap/latency/cost metrics, table equality; mock pytest, build/eslint | B13, B15 |
| S01 / 11 / 0.5 / G2 optional | Usefulness scoring; `app/retrieval/usefulness.py` | Section support scoring rejects irrelevant passages; intermediate decisions inspectable | Fixed relevant/irrelevant corpus with mock scorer | B08, B12 |
| S02 / 12 / 0.5 / G3 optional | Comment threads; `app/api/comments.py`, `frontend/src/Comments.jsx` | Version-bound threads/replies persist across return cycle | Thread permissions/version binding; frontend build + eslint | B17 |
| S03 / 12 / 0.5 / G3 optional | Visual diff; `frontend/src/VersionDiff.jsx` | Reviewer sees edits for selected draft versions including gaps/citations | Known before/after fixtures; frontend build + eslint | B15, B17 |
| S04 / 13 / 0.5 / G3 optional | Measures view/export; `app/services/metrics.py`, `frontend/src/Metrics.jsx` | Section 9 measures reproduce event/version fixture counts; blank baseline stays blank | Time/edit-distance/count/denominator checks; frontend build + eslint | B19 |
| S05 / 14 / 0.5 / G3 optional | UI polish; `frontend/src/styles/`, affected components | Keyboard, loading/empty/error states and source labels reviewed | Manual accessibility/layout review; frontend build + eslint | B17, B18, B23, B24, B25 |
| S06 / 18 / 0.5 / G3 optional | Credit admin support; FIG `workflow.yaml`, `frontend/src/CreditAdminSupport.jsx`, `tests/test_credit_admin_support.py` | Configuration plus one screen inserts support checks/key-in record between Credit Head and approver, or handover roadmap records deferral | Enabled/disabled route, role/lock checks, no integration claims; frontend build + eslint | B16, B17 |

Coverage: WS1 B01; WS2 B02–03; WS3 B04–06; WS4 B08; WS5 B09–13; WS6 B07/B14–15; WS7 B16–17; WS8 B18; WS9 B19–20; WS10 B21; WS11–14 S01–05; WS15 B22–23; WS16 B24; WS17 B25; WS18 S06. B00 is bootstrap overhead. IDs B00–B21 and S01–S05 are retained; dependency order is a DAG, not numeric order.
Core B01–B25: 16.5 builder days (previous 13 + 0.5 export + 1 template parser/diff + 0.5 admin + 1 chat + 0.5 checks). B00 adds 0.5; Should adds 3, including S06. Total including bootstrap: 17 core / 20 with all Should. Estimates remain planning effort, not observed execution time.
G1 is unchanged at 5 days plus bootstrap; G2 rises to 7.5 (B08–B15, B18, B24 and 0.5 of B22); G3 is 3.5 (B16–17, B19–20, B23, B25 and remaining 0.5 of B22); G4 is 0.5. Against four/five/three/two office days respectively, G1/G2/G3 need outside-office-hours work and prompt review. Completed B00/B02 account for 1 day of the estimate, leaving 16 core days of planned effort.
G2 parser milestone in B22 is needed before B18; B15 then integrates B18/B24. B25 follows B15 and precedes B16; admin B23 follows reviewer roles and parser/diff; B19 waits for all new core blocks. No G2 export dependency on G3 workflow remains.
G1 demo may use saved mock spread outputs; B09 must replace that seam with the adapted pipeline by G2. Each gate explicitly distinguishes mock evidence from an approved live run.
If late, drop Should work first; preserve Stale, gap list and named section returns. Orchestrator must escalate a missed core gate rather than quietly reduce a Business requirement.

## Test and delivery approach

Offline pytest is the default: injected mock model, saved public pack, synthetic fixtures and temporary SQLite/storage under this repo. Block outbound sockets in the test harness; no API keys, network, paid tests or dependencies fetched by tests.
Test pure arithmetic against hand-reviewed gold fixtures, readiness/state transitions as matrices, citations as immutable references, and APIs with mock providers. Never treat a confident model response as a passed arithmetic check.
Script B19: create renewal/upsize case → tranche 1 + saved public search → confirm appropriate public finds/industry code → generate spread → assert draftable 4/5/6/7/10 and partial 8/9 → tranche 2 → assert 1/2/3 and 8/9 complete, 11 opens → tranche 3 → 12/13 complete → CA position → 14.
Continue: CA edits 8 → chat proposes cited revision → reject/accept flows and numeric-input recompute → draft template export → all 14 confirmed or N/A with reasons → recorded mandatory-gap exceptions → full draft/submit → Credit Head returns 9 with comment → CA fixes/resubmits → Credit Head supports/handoff → approver question → CA answers/resubmits directly → approver approves → export approved snapshot → revised valuation is ingested, preserving the approved snapshot and marking working sections 8/9/11/14 Stale → explicit new working version/redraft. Do not silently reopen approval.
Also assert missing full-property reports remain gaps despite portfolio disclosures, internal rating cannot be filled by an external release, and no source states a missing document does not exist. Reset only demo-owned case IDs/files.
Separate cases exercise final Declined, Approved with conditions (on/off), return from approver, blocked incomplete submissions and the exact unconnected credit-master panel. Admin scenario uploads a formatting-only template, confirms activation, then demonstrates prompt/code change-list export without activation; re-export the prior approved ES with its original template. S06 is tested enabled/disabled only if selected.
For each frontend task run `npm run build` and eslint (`npm run lint` when configured). Use JavaScript/JSX only; no typecheck/TypeScript tooling requirement remains. Add no unlisted test/browser dependency without a mailbox decision.
For Word export, use the document skill's render/verify workflow in B18; any extra rendering dependency needs a dependency decision. Core API E2E is pytest/scripted; UI walkthrough supplements it without assuming an unapproved browser test package.
Every block records commands/results, unresolved limits, cost and commit in its mailbox reply and updates `BUILD_STATE.md`; red application tests mean blocked. Task 0001 creates no artificial app/tests merely to obtain a green test count.

## Assumptions, decisions and risks

- Proceed with project defaults: new/renewal only, Word, FIG only, input-only internal rating, CA-owned recommendation, all five configured approver outcomes. These do not block planning.
- Task 0002 recommends ESR-REIT (owner veto remains available) and delivers the downloaded public pack at `demo/public_pack/esr-reit/manifest.yaml`; comparison evidence is isolated under `demo/research/`. Task 0001 performed no retrieval. Live model/API behavior remains conditional on approved spend; public pack retrieval incurred US$0.
- Source code has no passing test baseline, import side effects and more dependencies than permitted. Budget B09 first for regression/adaptation; escalate if a parser dependency is essential.
- Regulatory definitions require evidence before implementation acceptance. Generic Phase 1 ratios, summary valuations and cap-rate proxies must not silently become regulatory/property-specific facts.
- Mandatory industry mapping and public confirmation are needed even though the demo tranches do not explicitly mention them; demo script includes CA confirmation of a generated suggestion.
- Accepted decisions: Tavily is the sole search client and remains off pending approval; mock is default; live model chosen at first paid-run gate; JavaScript/JSX with build + eslint; immutable approved snapshots and explicit stale working-version handling.
- Configuration-only team expansion assumes the common declarative vocabulary can represent the future templates. Unknown team analytics requiring new operators must be raised, not claimed supported.
- Single-machine SQLite and role switching demonstrate process, not production entitlements, durable distributed jobs or bank integration. Complex/scanned documents require manual review where extraction fails.
- Gate review turnaround, approved model/environment, Word rendering tooling and final handover owner are external dependencies. Bank deployment may require additional setup; no real-template fit or full-ES time-saving claim is proven here.
- The draft template includes more financial rows and checkboxes than the ten REIT measures. B10/B18 must either supply sourced, validated values or named gaps; sample labels/defaults cannot become factual findings. Exact live-bank template fit remains a bank-side handover check.

Requirement trace: 2.3/5 → B01 workflow config and B16–17 roles/outcomes; 2.8 → B25 checks; 2.9 → B22 parser/versioning and B18 template fill; 2.10 → B22 diff and B23 admin; 2.11 → B24 chat; 2.12 → S06 support/roadmap. Section 11 scope is reflected in these core/Should boundaries; voice, live credit-master integration, real entitlements and CBK/CMB content remain out.

## B26 Gate 2 extension (task 0021)

Requirement 2.13 adds registry-driven model routes, case/default and section choice,
and two-model comparison. B26 follows B15 without starting Gate 3. Estimate adds
one builder day to the prior baseline: 18 core including bootstrap / 21 with all
Should; G2 becomes 8.5 days. These remain estimates. Review hosted versus open-weight
Qwen variants separately; bank family availability does not establish an exact
endpoint or variant. Disabled direct/OpenRouter/local routes retain official links
or explicit TODOs. B26 acceptance is offline; live authorization and spend controls
require a later approved task. Existing G2/G3/G4 reviews stay with Sheryl.
