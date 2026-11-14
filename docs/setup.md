# Local setup and verification

Run from the repository root. For the combined draft workspace, start with the [Gate 2 walkthrough](gate2.md): three tranches, explicit mock spreading, all-section drafts, chat, Stale review and pinned Word bundles. B01 delivers backend storage, configuration and the provider seam; B04 adds upload/folder intake (see `intake.md`). B05/B06 add readiness and saved public search; B07 adds the intake dashboard. Follow [Gate 1 walkthrough](gate1.md) for local backend/frontend startup and all three tranches. B09/B10 backend spreading and computations are available through APIs; B11/B12 section drafting is available through the draft API; B16 adds the [backend workflow API and locks](workflow.md); reviewer screens remain B17.

Use Python 3.12 and a project-local environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt -r requirements-test.txt
scripts/run_tests.sh
```

Test runs (all offline, mock provider):

| Command | What runs | Time on a 14-core laptop, 11 Nov 2026 |
|---|---|---|
| `scripts/run_tests.sh` | Normal run: parallel, without the 13 end-to-end tests marked `slow` (556 tests) | about 3 minutes |
| `scripts/run_tests.sh --all` | Every test, parallel (569 tests). Run before a block counts as done. | about 7 minutes |
| `scripts/run_tests.sh --gate` | Every test in one process, slowest listed. Run at gates and the freeze. | about 40 minutes |

Extra arguments pass through to pytest. Parallel runs use pytest-xdist, one worker per core (`TEST_WORKERS` overrides). The `slow` marker is declared in `pytest.ini`.

Tests block outbound connections and DNS. They read the saved public pack and use synthetic in-memory records; temporary files live under ignored `runtime/pytest*/`. B07 frontend checks are `npm --prefix frontend run build`, `npm --prefix frontend run lint` and `npm --prefix frontend test`; see the Gate 1 walkthrough for setup. The test requirements use only the approved stack, pytest and pytest-xdist.

The supplied machine had FastAPI 0.115.0 with incompatible Starlette 1.6.0. Task 0004 created `.venv` with system-site packages and installed **Starlette 0.38.6 from an existing local pip wheel cache**, using `--no-index --no-deps`. This is a transitive FastAPI dependency, not a new application dependency. Nothing was installed into the global or Phase 1 environment. A clean install of the pinned FastAPI requirements resolves its compatible Starlette dependency. The cached wheel is local ignored runtime material; ordinary setup does not depend on that machine-specific cache.

Importing `backend.app.main` does not create a database, load keys or instantiate a provider. `create_app()` validates FIG configuration and constructs an offline mock; `/health` reports team/config/provider versions. No server package is added by B01. Tests exercise the ASGI app directly without an HTTP client or server.

For explicit persistence initialization:

```python
from pathlib import Path
from backend.app.database import create_database
from backend.app.repository import Repository

Path('runtime').mkdir(exist_ok=True)
engine, sessions = create_database(Path('runtime/wb_credit.sqlite'))
with sessions.begin() as session:
    repository = Repository(session)
    # Construct schemas.Case / schemas.Document / other records and save here.
engine.dispose()
```

`create_database` creates schema only when explicitly called. The caller owns transactions and engine disposal. `Repository.save` flushes without committing; exceptions require rollback. Public services should use this seam, not direct ORM writes. SQLite foreign keys, enum checks and immutable-version triggers provide additional protection. Structured list/map references are checked in the repository; they are not SQL foreign keys. There are no database migrations yet because this is the first application schema.

Pydantic schemas reject unknown fields and validate UTC times, source provenance and references. A coupled update (for example confirmation actor and time) should create a copy with both fields and pass it through `save`, which revalidates it. Changing a version means creating a new ID with its parent/supersedes reference. Case configuration is stored as a validated snapshot with its hash/version, so subsequent YAML changes cannot reinterpret existing cases. Decimal values are stored as exact strings, never binary SQLite floats.

Template storage holds immutable paths/hashes and parsed-map slots; B22 will copy/parse the owner template into runtime storage. `TemplateActivation` records the active-version pointer as an append-only sequence (latest confirmed activation for a team); activation authorization/concurrency checks arrive in B23. Draft/ES versions pin a template ID. B01 does not parse or edit any DOCX.

B25 now implements [pre-submission checks and immutable gap reasons](submission_checks.md). B16 implements [workflow transitions, question answers and locks](workflow.md). B24 now implements [typed section proposals and acceptance](section_chat.md). The same distinction applies to readiness fields and expected-document state in B05.

Expected inputs/readiness and request-list routes are documented in [readiness.md](readiness.md). They share the injected SQLite sessions and require no additional dependencies.

B06 public search defaults to off. Inject `SavedPublicPackProvider` for the offline demo; see [public search setup and API](public_search.md). Tavily remains disabled regardless of keys/environment. Generation endpoints offer work; they do not run the B09 spread pipeline.

B08's offline page indexing, section retrieval and stable source-resolution API are documented in [evidence_retrieval.md](evidence_retrieval.md). Existing databases gain the append-only evidence index on explicit `create_database()` startup; no source files or case configuration pins are rewritten.

Template registry/parser setup and the read/register API are documented in [templates.md](templates.md). Explicit local startup seeds the owner template into immutable runtime storage; generic app imports do not write files. Candidate registration does not activate a template.

B09's explicit mock spread generation, source selection, pinned configuration and API contracts are documented in [spreading.md](spreading.md). Existing case pins are preserved; new profiles require a newly configured case. The default empty mock records a failed run until exact-request fixtures are injected. B07 generation offers remain UI-only; B09 can be exercised through its service/API and offline tests.

B10 reviewed source mappings, Decimal calculations, computed tables and the immutable analytics API are documented in [analytics.md](analytics.md). Old case configuration pins remain unchanged; B10 does not automatically update dashboard drafts or readiness.

B11/B12 offline first drafts, dependency-bound synthesis and preview API: see [drafting.md](drafting.md). The local app's template bootstrap supplies the required active template. Load the demo inputs/public pack before creating first drafts; the new preview panel preserves mock labels in its text download.

Section version history and the B14 save/redraft/confirm integration contract are documented in [versions.md](versions.md). Database initialization adds immutable confirmation history without rewriting existing case pins or drafts.

B14 now supplies the [section editor and source-review walkthrough](section_editor.md), including immutable save/redraft/confirm, conflict recovery, cited PDF/normalized pages and the pending manual UI acceptance checks.

## Draft Word exports

See [exports.md](exports.md) for B18 preview/snapshot/download APIs, offline demo reproduction and the companion source/gap manifest. B15 provides dashboard preview, creation and download controls; B16 provides immutable final JSON snapshots; approved Word export integration remains B19.

## B26 model registry and offline comparison

`config/models.yaml` drives the model list. Existing databases receive an additive
`case.default_model_id` column (`mock-v1`); existing immutable drafts retain their
original model metadata. The dashboard lets the CA save a case default, and the
section editor offers an explicit first-draft/redraft override. A preference change
does not redraft, clear a confirmation or change readiness.

Two enabled models are offline fixtures: Mock A uses the reviewed claim order;
Mock B reverses that order and submits an intentionally unsupported fixture row
which the existing validator rejects. Neither simulates a named provider's quality.
The comparison panel shows citation coverage, rejected/omitted claims, malformed
responses, named gaps, measured local latency and US$0 estimated cost. The server
checks matching prompt/evidence hashes and exact Python table and metric equality.
A comparison is an ephemeral preview, not an adopted draft or a credit decision.
Choose a model and explicitly redraft to save a new immutable version. New accepted
chat inputs and any late evidence follow the existing freshness rules.

To prepare a provider route for a later approved run:

1. Choose its separate `direct`, `openrouter` or optional `ollama` registry entry.
   Verify the current official source links in that entry. Fill all `TODO: confirm`
   values, including JSON mode/context limits, current pricing, exact model ID and
   account availability. Do not substitute a family name for a model ID. Qwen
   hosted Plus/Max and open-weight variants are separate entries. `bank_available`
   records the supplied family-level fact, not a verified bank deployment/size.
2. Put the key in the repo-root `.env` using the entry's `api_key_env` name:
   `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
   `DASHSCOPE_API_KEY`, `MOONSHOT_API_KEY` or `ZAI_API_KEY`. Set values locally;
   never paste keys into YAML, the browser, mailbox replies or logs. `.env` is
   gitignored. Do not commit it. Mock mode never reads these keys.
3. For Qwen direct, use the Singapore Model Studio endpoint specified by the
   account; replace `{WorkspaceId}` with the confirmed workspace ID. The provider
   docs currently show this workspace-specific endpoint. Qwen 3.6 Plus was found
   in coding/token-plan examples; its pay-as-you-go Singapore availability still
   needs confirmation. An OpenRouter route uses the one `OPENROUTER_API_KEY` and
   its own verified route ID. Some requested route IDs remain null/TODO.
4. Set `enabled: true` only after configuration review. This makes a complete
   route configured, **not runnable in this offline release**: both API and UI
   keep every non-mock route blocked even with keys and an enabled flag. The
   application has no client-supplied `approved_usd` or environment bypass.
   A later mailbox task must carry the explicit approved budget and supply reviewed
   server-side authorization, pre-run estimate/reservation, spend accounting and
   SDK/client construction before any live call. Changing configuration alone
   cannot authorize spend. No live route has been connectivity-tested here.
5. Ollama is optional and also blocked by that gate. The documented local endpoint
   is `http://localhost:11434/v1/`; verify the installed Qwen tag, size, license and
   configured context. Do not claim that a hosted Max variant has open weights.
   This task neither installs a model nor starts an Ollama server.

`backend/app/llm/adapters.py` copies the Phase 1 injected OpenAI-compatible
chat/raw transport pattern and adds the native Anthropic result normalization.
Tests use fake transports. No new SDK dependency or network client is installed,
constructed or invoked by the application. Provider-specific options must be
validated in the later approved integration; these are transport contracts, not
live acceptance.

See [B26 model comparison](model_comparison.md) for API contracts, measurement
boundaries and the review walkthrough. Official documentation was read on
11 Nov 2026 without calling model endpoints; sources sit next to every registry
entry. Unverified identifiers are null with explicit TODOs, never guessed.
