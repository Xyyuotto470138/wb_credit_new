# Gate 2 — sourced draft review

For Sheryl: this walkthrough demonstrates all 14 saved sections, progressive evidence, section chat, retained versions, Stale review and a draft Word bundle. Use only the supplied public pack and **SYNTHETIC DEMO DATA**. Saved mock responses make no live model/search calls and cost US$0. This is a reviewable draft with visible gaps; credit decisions remain with human reviewers. Gate 3 workflow and submission checks wait for your review.

## Start and resume

From the repository root, using the existing environment ([setup](setup.md)):

```sh
LLM_PROVIDER=mock PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m uvicorn backend.app.local:create_local_app --factory --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**. Dependencies are already present on this build machine. For a fresh machine, follow setup; `npm ci --ignore-scripts --no-audit --no-fund` is needed if `node_modules` is absent and requires registry access. No API keys are needed.

The app resumes `runtime/gate1/`, including drafts and exports. Startup never resets review work or changes existing case configuration pins. For a fresh, current-configuration walkthrough, stop both servers and move `runtime/gate1/` to an unused backup directory under `runtime/`, then restart. Retain the backup. Old cases may lack the latest spreading/freshness configuration; a named configuration error requires a fresh case, not an implicit migration.

Enter your CA name in the header. It labels prototype actions; it is not authentication. At the empty case, expect 14 visible sections, zero saved sections and zero documents. Use the jump links to reach **Draft progress**, **Section editor**, **Draft template export**, or intake. Each row in **ES section readiness** opens that section. The editor selector and Previous/Next buttons also cover all 14 sections. Unsaved wording or typed chat input disables section/case navigation and export preparation until saved or discarded.

## Tranche 1 — request and saved public evidence

1. In **Add documents**, select **Tranche 1 · synthetic demo files**, then **Scan folder**. Alternatively upload both files in `demo/synthetic/tranche_1/`, leaving **Use demo manifest hints for exact matching files** checked.
2. Click **Check public sources** in Expected inputs. The local saved pack adds six public PDFs. Open each source, review it, then click **Confirm public evidence reviewed**. Sources retain their URL, original retrieval date and cached-pack label. Confirming the annual report once covers its eligible input categories.
3. Under **Generation offers**, click **Generate saved mock spread** once. This local-demo action requires the reviewed, exact saved FY2025 report and runs the existing B09 validator on the saved transcription. Expect a validated core Group spread for FY2025/FY2024. It is not a complete statement transcription or proof of live-model quality. Unsupported analytics remain gaps. The industry-code offer remains unavailable and the mandatory industry-mapping gap stays open.
4. Open and create first drafts in order **4, 5, 6, 7, 10, 8, 9**. Use **Create mock first draft**. For sections 7 and 8, review the term sheet and tick the supplied unsecured-description confirmation for its RCF; this does not describe the secured term loan as unsecured. Section 9 needs saved drafts of 7 and 10.
5. Review a source link in a claim. PDFs open at the original physical page; printed page/region labels remain distinct. Workbook sources show normalized text and original download. Section 10's values are read-only Python output; FY2025 public Group NPI includes SGD 328,679,000 from the core spread.

Expect **8 stored documents**, tranche coverage **2/2, 0/12, 0/2**, and **7/14 saved sections** after these actions. Public portfolio valuation/leases do not satisfy full property reports. Internal rating and account conduct still wait for tranche 3. Saved partial drafts retain named gaps; the input-readiness count is separate from saved draft coverage.

## Tranche 2 — financial, security and renewal support

1. Scan **Tranche 2 · synthetic demo files**, or upload all 12 files in `demo/synthetic/tranche_2/` (including the limits extract).
2. Expect **20 stored documents** and tranche coverage **2/2, 12/12, 0/2**. Previously saved affected sections may become **Stale**. Their text stays intact until you explicitly redraft.
3. Work in order **1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11**. Create missing drafts; use **Redraft as new version** on existing ones for this walkthrough. If the editor warns that inputs changed, click **Reload section** first. Save/copy local wording before discarding it. Reaffirm the supplied unsecured RCF description for 7/8 when redrafting.
4. Review section 2's computed exposure and section 9's property cash-flow shortfalls. The synthetic maturity-year refinancing is uncommitted; weak repayment evidence remains visible. The full property valuation and lease inputs are now held, but legal perfection, industry mapping and unsupported content remain named gaps.

Expect **11/14 saved sections**: sections 12, 13 and 14 remain undrafted. All input files being held does not mean every claim or template field is complete. No dashboard count represents approval or submission readiness.

## A section chat edit

1. Open section 8. Under **Typed section chat**, choose **Add CA fact or review note**, keep the synthetic label checked, and type `Legal review remains pending.` Click **Propose revision**.
2. Read the complete proposed text and sources. The saved draft is unchanged. Click **Reject revision**; the proposal remains in chat history and the saved version stays unchanged.
3. Propose the same note again, then click **Accept revision**. Expect a new saved version, the exact note labelled as CA input with actor/time/message provenance, and cleared current confirmation. Sections 9 and 11 become Stale when they depend on the changed section 8.
4. Expand **Saved version history**. Select the earlier draft and inspect/download its exact text. Selection is read-only and does not restore it. Open a saved source reference to inspect evidence. Accepted/rejected proposals remain in chat history.

The mock uses saved operations, including verbatim CA assertions, rather than general free-form rewriting. For the separately supported section-10 numeric flow see [section chat](section_chat.md); supplied operands require explicit acceptance and Python recomputation. Exposure/conduct/projection cells cannot be edited through chat.

## Tranche 3 — rating, conduct and human position

1. Scan tranche 3, or upload both files in `demo/synthetic/tranche_3/`. Expect **22 stored documents** and tranche coverage **2/2, 12/12, 2/2**. The supplied current internal rating and conduct inputs become usable; an external rating never replaces the internal rating.
2. Refresh affected prerequisites in order **1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 13**. Create missing drafts; redraft only Stale drafts. Reload an open editor when it reports changed inputs. Accepted chat notes survive explicit redraft with CA-input provenance.
3. Open section 14. Enter your stated position. For a reproducible synthetic review use `Defer pending evidence and legal review.` Click **Create mock first draft**. The model words the human position; it does not form a recommendation. No first conclusion is created without a CA position.
4. Expect **14/14 saved sections**, no Stale sections once dependencies are refreshed, and one open mandatory requirement (industry mapping) still visible. Review section 8 and click **Confirm section reviewed**. The current confirmation count increases; gaps remain. Saved sections and CA-confirmed sections have separate counts.

## Export the template-filled draft

1. Save/discard any local edits or typed chat input. Go to **Draft template export** and click **Preview draft export**.
2. Review the **DRAFT — CA REVIEW REQUIRED** label, pinned template version, all 14 saved draft IDs/readiness states, current and saved gaps, template field gaps and pinned request list. Many template fields remain gaps because they have no supported structured source. This is expected; they must not become invented facts.
3. Click **Create draft bundle**, then **Download draft bundle** under Saved export history. The ZIP contains `draft.docx`, `manifest.json` and `request-list.txt`. Individual Word/manifest/request downloads are also available. Keep the manifest with the Word file: it carries exact saved text, detailed sources, public URLs/retrieval dates and field gaps.
4. Open Word and check all 14 numbered sections, the single draft/mock/synthetic status block, numbered source markers, Sources appendix and gaps. It fills a copy of the pinned owner template; the owner file is unchanged. Rows/pages may expand. The task 0022 sample below has been checked page by page; review each new export's pagination as part of acceptance.
5. The case remains **Draft**, and the export does not count as submission, confirmation or approval. Each saved export is a fixed snapshot. If inputs/sections change between preview and creation, the API rejects the old token; refresh the preview and review again. Refresh before creating another bundle. Older downloads retain their original content after later changes.

Partial and Stale drafts may be exported with their labels and gaps. Missing/ambiguous template anchors block Word creation with named errors. Do not interpret a successful draft download as a clean or final ES.

## Late valuation and the Stale choice

1. After saving/confirming section 8 and exporting the first bundle, upload `demo/synthetic/late_update/valuation_v2.pdf` with demo manifest hints enabled. Use upload; the three folder choices deliberately exclude the late file.
2. Expect **23 stored document versions** and **Stale in 8, 9, 11 and 14**. Section 7 remains current. Tranche 2's exact-original-file coverage becomes **11/12**, because its original valuation is now historical; the revised valuation satisfies the current valuation input. The document register shows the revision link.
3. Open section 8. Keeping it for review requires no action and leaves it Stale. The earlier saved note/text and confirmation are retained in history. Confirmation is disabled while Stale; a historical confirmation does not count as current.
4. To use the new source, reload the section, review the revised valuation, then choose **Redraft as new version**. Review the synthetic SGD 104m value and the cited changed circumstances. Reaffirm the unsecured RCF description as applicable. The accepted chat note remains; earlier manual wording edits remain in history and are not automatically carried into redrafts.
5. Redraft **9 → 11 → 14** in order, supplying/reaffirming your section-14 position. Explicitly confirm reviewed sections again if appropriate. Expect Stale counts to clear only as the affected chain is redrafted. Earlier versions, confirmations and the first exported Word/manifest remain unchanged.
6. Preview and create a second bundle if desired. Its export history entry is distinct; the first still downloads its original snapshot.

## Finish and review boundary

Stop both terminals with **Ctrl+C**. Work resumes from the same database next time. No automatic reset or background worker is required.

Offline acceptance covers the real three tranches, validated mock spread, all 14 drafts, reject/accept chat, history, late valuation, dependency redrafts, export-token conflict, pinned bundle contents, restart and workflow locks. Frontend build/eslint, state tests and actual-snapshot HTML rendering supplement those API checks. Interactive visual acceptance remains pending: browser host unavailable and native Chrome returned `cgWindowNotFound` during task 0020. Please review keyboard navigation, PDF opening, chat controls, export downloads, and narrow-screen layout using these steps. API/static-render checks do not substitute for that review.

Gate 3 remains paused pending your review: no submit/support/return/question/approval controls or template-admin activation are added in B15. The industry-mapping generation/confirmation gap also remains for orchestrator follow-up. No live calls, new dependencies or real internal records are used.

## ES presentation sample (task 0022)

Open [gate2_export_sample.pdf](gate2_export_sample.pdf) for the reviewed offline export after all three tranches and the saved B09 spread. New Word exports use compact numbered citations, a Sources appendix, populated supported tables and actual credit-risk rows. Create a new export to see these changes; historical downloads keep their original bytes. The CAS leaves Watchlist/SM classification open and unsupported financial fields remain gaps. No change to the existing tranche/chat/export UI steps is required. Reproduction command and mapping boundaries are in [exports.md](exports.md#task-0022-presentation-contract).

## Desktop screenshot review (task 0024)

The [screen pack](screens/README.md) covers all fourteen section editors, citation
dialogs, rejected/accepted chat, immutable history, model comparison, draft export
and the revised-valuation Stale/redraft chain in installed Chrome. It includes a
numbered PNG index and one-screen-per-page PDF for Sheryl’s review. The captured
CA actions are synthetic fixture actions; they do not constitute gate acceptance.
Reproduction and the remaining desktop/coverage limitations are recorded there.
