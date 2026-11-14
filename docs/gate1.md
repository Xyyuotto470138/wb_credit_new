# Gate 1 — intake and readiness walkthrough

This local prototype uses the supplied **SYNTHETIC DEMO DATA** and six saved public PDFs. Public search reads the saved pack only; no live model/search calls or keys are needed. The facility/internal records are fictional. Public reports retain their original dates and provenance.

## Start locally

From the WB Credit repository root, with the existing `.venv` set up as described in [setup.md](setup.md):

```sh
LLM_PROVIDER=mock PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m uvicorn backend.app.local:create_local_app --factory --host 127.0.0.1 --port 8000
```

This command uses the machine's existing Uvicorn (verified 0.44.0); task 0009 adds no Python server dependency. The factory creates `runtime/gate1/wb_credit.sqlite` and seeds one empty ESR-REIT renewal case. It does not reset an existing case. Document bytes stay in `runtime/gate1/blobs/`. Importing the module alone has no startup side effects.

In a second terminal, from the repository root:

```sh
cd frontend
npm ci --ignore-scripts --no-audit --no-fund
npm run dev
```

The install is needed only when `node_modules` is absent. This task populated it offline from a local copy of Phase 1's installed packages, then pruned to this frontend's lockfile; Phase 1 was read only. Ordinary `npm ci` requires registry access on a fresh machine. Node 22.13+ is suitable for this Vite version; verification used Node 25.8.0. No TypeScript is used.

Open **http://127.0.0.1:5173**. The frontend proxies `/api` to port 8000. Both servers bind only to loopback. Start at the empty case: all 14 sections are visible, zero stored documents and zero draftable sections. Enter the CA name at the top before confirming public evidence or dismissing a request. This is a prototype actor label, not authentication.

For a fresh walkthrough, stop both servers and **move** `runtime/gate1/` to an unused backup directory under `runtime/`, then restart. Keep the backup if it contains review work; no automatic reset or deletion is performed.

## Tranche 1 — initial request and saved public sources

1. In **Add documents**, browse/drop both files in `demo/synthetic/tranche_1/`, or select **Tranche 1 · synthetic demo files** and click **Scan folder**.
2. Keep **Use demo manifest hints for exact matching files** checked for uploads. Matching is by SHA-256, not filename; verified source files receive their manifest type, entity, effective date and synthetic label. For other uploads, open **Classification hints**; mixed batches normally use automatic type detection. Hints are not CA confirmation.
3. Review the intake results: two new versions, term sheet and RM support email. The register labels them synthetic. Scan the same folder again: both are duplicates, with unchanged version count.
4. Click **Check public sources**. Six saved PDFs appear. Expected inputs show **Found publicly**, retrieval date, cached-pack label, and pending confirmation. Click a source filename to open its PDF, use the page controls, and inspect its provenance. Non-PDF uploads offer download of the original.
5. In each of the six public source dialogs, select **Confirm public evidence reviewed** after review. The annual report supports several input categories; confirm its single document once. Confirmation refreshes readiness and remains recorded after restart.

After public confirmation, the overview reads **2 Provided / 6 Found publicly / 10 Missing / 8 draftable sections**. These are *input-category counts*, not file counts; the register has **8 documents**. Sections **5 and 6** can draft fully. Sections **1, 4, 7, 8, 9 and 10** can draft partially. Sections **2, 3, 11, 12, 13 and 14** wait for input.

Public portfolio valuations and leases remain partial: full secured-property reports are requested. The external agency release does not satisfy the internal rating. Under **Generation offers**, financial spreading and industry-code suggestion are offers only, explicitly unavailable for execution in B07. No spread, drafted text or invented CA position is inserted to make the dashboard appear complete.

## Tranche 2 — financial, security and renewal support

Upload the 12 files in `demo/synthetic/tranche_2/`, or select tranche 2 and scan. This includes the suggested limits/utilisation extract as well as CAS, prior ES, prior conditions, covenant monitoring, compliance, pricing, valuation, insurance, rent roll, property lease profile and projections.

The overview reads **13 Provided / 4 Found publicly / 1 Missing / 11 draftable sections**, with **20 stored documents**. Sections **1, 2, 3, 5, 6, 7 and 8** can draft fully. Sections **4, 9, 10 and 11** remain partial. Sections **12, 13 and 14** wait for input. Four mandatory requirements remain open: the spread, industry mapping, internal rating and account conduct.

The full valuation and secured-property lease files now satisfy their inputs. Public context remains available alongside them. Section 11 opens with named gaps from its dependencies. Pricing requests route to the internal team and projections to the RM, following the pinned catalogue's current owner defaults.

## Tranche 3 — conduct and internal rating

Upload both files in `demo/synthetic/tranche_3/`, or select tranche 3 and scan.

The overview reads **15 Provided / 3 Found publicly / 0 Missing / 13 draftable sections**, with **22 stored documents**. Sections **12 and 13** now can draft fully. Sections **4, 9, 10 and 11** remain partial; **14** still waits for the CA position and its other dependencies. **Two mandatory requirements remain open**, even though the Missing count is zero: spread and industry mapping are **Can generate**.

This is the actual B07 boundary. The scenario's eventual fully ready financial/synthesis sections require B09 spreading and confirmed industry mapping; section 14 requires a CA-stated position. Drafting and the CA workspace are later blocks. Readiness labels never mean that ES text already exists or credit has been approved.

## Other checks

- Filter expected inputs by each of the seven status labels. Expand **Why needed & actions** for the rule, owner, affected sections and alternative group. A dismissal requires a reason and CA name; dismissing a mandatory input leaves its gap open. Restore requires a reason too.
- Expand **Requests by owner**, then **Export request list**. The UTF-8 download lists RM/client/internal-team requests, why needed, affected sections and public-search results. It sends nothing to anyone.
- In **Document register**, inspect original bytes, revisions, synthetic/public labels, confirmation state, and pending-review reasons. Unreadable files, conflicts or wrong entities remain review items and do not silently become usable evidence. Resolution of intake conflicts is a later capability; no acceptance override is provided here.
- Reload or restart: all inputs, confirmations and dismissals persist. **Refresh status** retrieves current backend state. Error messages expose failed actions and retries; a failed refresh warns against relying on the displayed snapshot.
- Stop each terminal with **Ctrl+C** when finished. This task left no server/background process running.

## Verification and review boundary

Task 0009 verifies both raw upload and configured-folder routes through all three tranches, duplicate handling, public confirmation, persisted/restarted snapshots, dismissal/restore, request export, source bytes, cross-case isolation and corrupt/out-of-storage content rejection. Backend tests prohibit network/DNS. Frontend checks cover build, eslint, five API-client tests, and server-rendered HTML for all three real backend snapshots. The PDF worker is bundled locally; no CDN is required.

```sh
LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run lint
node frontend/scripts/check-dashboard.mjs runtime/pytest/test_dashboard_three_tranches_0/tranche-1.json runtime/pytest/test_dashboard_three_tranches_0/tranche-2.json runtime/pytest/test_dashboard_three_tranches_0/tranche-3.json
```

The final command uses snapshots emitted by the backend tests and writes review HTML beside them under ignored runtime storage. It checks rendered names, readiness labels, source filenames, synthetic labels, generation boundaries and all 14 sections. This does not simulate user clicks or establish visual fidelity.

The local servers and Vite proxy were HTTP-smoke-tested. **Interactive visual review remains for Sheryl:** the computer-use browser host was unavailable and native Chrome controls returned `cgWindowNotFound`. No screenshot, PDF-canvas interaction, drag/drop or responsive-layout signoff is claimed. Use the steps above to complete that review at Gate 1.

## Desktop screenshot review (task 0024)

The [screen pack](screens/README.md) adds a Playwright-driven, installed-Chrome
walkthrough at 1440 x 900 (scale 2), including real PDF canvases, folder intake,
source confirmation, grouped requests and downloads. See the pack for the visual
review findings and reproducible capture commands. This supersedes the earlier
browser-access limitation for desktop capture; Sheryl’s gate acceptance, mobile
layout and a comprehensive keyboard/accessibility review remain separate.
