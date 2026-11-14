# Phase 1 adaptation record

Source root, read only: `../financial-spreading-tool/`.
Copy/adaptation date: **2026-11-10** (task 0004).

| Source path | Destination | Adapted portion |
|---|---|---|
| `backend/app/database.py` | `backend/app/database.py` | SQLAlchemy engine/session pattern; replaced global import-time engine with explicit initialization, foreign-key enforcement and immutable-version triggers. |
| `backend/app/llm/client.py` | `backend/app/llm/client.py` | `chat` / `chat_raw` call signatures, response contract and fence-cleaning helper; replaced global live provider and environment reads with injection and exact-request mock fixtures. |

The domain schema, repository, FIG configuration, validators, app factory and tests are new WB Credit code. No Phase 1 live adapters, provider/model defaults, dependencies file, runtime data or extraction pipeline were copied. There are no runtime imports from the source tree. Phase 1 was not edited or booted. B09 owns later extraction/spreading adaptation.

## B07 frontend adaptation (2026-11-10, task 0009)

| Phase 1 source path | WB Credit destination | Adapted portion |
|---|---|---|
| `frontend/src/components/FileUpload.jsx` | `frontend/src/components/FileUpload.jsx`, `IntakePanel.jsx` | Dropzone/browse, drag state and busy pattern; multiple input formats/files, explicit hints, content-verified demo metadata, per-file errors and duplicate reporting. |
| `frontend/src/components/PdfViewer.jsx` | `frontend/src/components/PdfViewer.jsx`, `SourcePanel.jsx` | Page navigation, resize-to-fit, wide-page horizontal scroll, loading/error feedback; local bundled worker replaces CDN and case-scoped verified content replaces job PDF URL. |
| `frontend/src/components/StatusBanner.jsx` | `frontend/src/components/StatusBanner.jsx` | Current-stage strip; intake is current, future preparation/review steps stay labelled, ES workflow state displayed separately. |
| `frontend/eslint.config.js`, package versions/lock | `frontend/eslint.config.js`, `package*.json` | JSX/Vite checks and approved React/dropzone/PDF dependencies only. New UI, CSS and API contracts replace the spreading wizard. |

No source-tree symlink or runtime import is used. Installed packages were copied into this repo's ignored `frontend/node_modules` and pruned offline; no Phase 1 application/runtime data was copied and no Phase 1 files were written. The initial offline npm resolution found no registry metadata cache; reuse of the existing lock/package copy resolved installation without network. Node's built-in test runner and Vite's existing esbuild dependency provide frontend checks; no new browser/test dependency was added.

## B09 spreading adaptation (2026-11-10, task 0012)

| Phase 1 source path | WB Credit destination | Adapted portion |
|---|---|---|
| `backend/app/extraction_agent/orchestrator.py` | `backend/app/extraction_agent/orchestrator.py` | Three-iteration full/missing-row → failed-statement repair → deterministic fallback algorithm; injected mock calls, no confidence bypass, explicit cross-statement targets, immutable trace. |
| `backend/app/extraction_agent/validator.py` | `backend/app/extraction_agent/validator.py` | Completeness, balance-sheet equation, income flow, cash bridge and cross-profit validation; rebuilt around exact configured aliases, all-period Decimal arithmetic, source quotes and named skipped checks. |
| `backend/app/extraction_agent/skills/{claude_full_extract,pdfplumber_fallback}.py` | `backend/app/extraction_agent/{pdf_quality,orchestrator}.py` | Numeric-quality comparison and targeted-only fallback; B08 PyMuPDF supplies runtime text, conservative complete-line fallback replaces the legacy pipeline/dependencies. |
| `backend/app/services/mapping.py`, `backend/app/templates/reit.py` | `backend/app/extraction_agent/{contracts,validator}.py`, `config/teams/fig/analytics.yaml` | Allowed-code/alias mapping pattern and selected REIT labels; exact aliases and schema validation replace unconstrained model mapping and hardcoded template imports. |
| `FS/dbs-annual-report-2025.pdf` | `tests/fixtures/spreading/dbs-annual-report-2025.pdf` | Exact public-PDF bytes for the physical-page-59 number-loss and region-mapping regression; source hash/provenance in fixture README. |

Only the adapted portions above and the requested public PDF were copied/reworked. The service/API/persistence glue and source contract are WB Credit code. Phase 1 was never imported, booted or written. No legacy provider, Camelot/Tabula, runtime data, NIM search or proxy calculation was copied. See [spreading.md](spreading.md) for the configured-core-row scope and conservative parser limits.


B26 (task 0021, 2026-11-11) additionally adapts
`../financial-spreading-tool/backend/app/llm/providers/openai_compat.py` into
`backend/app/llm/adapters.py`: injected transport, explicit model and timeout,
optional JSON mode, and normalized chat/raw output. A native Anthropic transport
contract uses the same result envelope. No SDK import, environment/key read,
live client construction or automatic fallback is copied. `llm/registry.py`
selects offline fixtures; all non-mock entries remain blocked. Fake-transport
contract checks do not establish live endpoint compatibility.
