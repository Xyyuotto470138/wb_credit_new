# Section editor and source review (B14)

Start the offline local app using [gate1.md](gate1.md), load the synthetic tranches and saved public pack, then open **Section editor**. B14 replaces the first-draft preview with the existing B11/B12/B13 API operations. It adds no provider, arithmetic, database migration or dependency. The CA name is a local prototype identity label, not authentication.

Select a section. Its current input completeness, named input/draft gaps and readiness remain visible. Create a mock first draft if none exists; synthesis still requires the configured prerequisite drafts. For section 14, enter the CA's position explicitly for each creation/redraft; the generated wording records that position. Sections 7/8 offer explicit confirmation of the supplied unsecured description. Neither action establishes legal perfection or approves credit.

Review individual claims and their source links. Existing narrative/facility wording can be edited; computed claims, conduct summaries, supplied internal ratings, case inputs, unsecured confirmations and the CA position are read-only. Save appends a new version using the exact loaded draft, editor revision and input fingerprint. Numeric edits are rejected by B13. The CA is responsible for the meaning of edited prose; source links are retained as review context, not independent verification. Use [typed section chat](section_chat.md) for CA facts and reviewed proposals; section 10 accepts explicit operands for Python recomputation.

Unsaved wording or new-draft options prevent changing sections/cases and trigger the browser's page-leaving prompt. **Save wording as new version** saves only the changed claims. **Discard local changes and reload** explicitly discards local wording/options after a successful reload. Refreshing the dashboard never overwrites local wording. A changed revision/input or 409 blocks actions and retains selectable, read-only local wording for copying before reload; the UI never retries a conflicting write automatically. If a write succeeds but loading its new history fails, reload before doing anything else.

**Redraft as new version** explicitly generates fresh wording from current evidence. It preserves the prior version, including its edits, and clears current confirmation; earlier edits are not automatically carried into the generated wording. Saving on Stale content leaves it Stale. Confirmation is disabled on Stale, conflicting, unsaved or already-confirmed content. **Confirm section reviewed** records CA acceptance of the saved version and inputs; named gaps remain open. Historical confirmation records are labelled separately. All editing actions are disabled outside Draft or on N/A sections; the API independently enforces those locks. B16 owns later reopening/returns and B25 owns submission checks and gap exceptions.

Source buttons resolve the immutable evidence ID afresh. The panel displays the exact original PDF page (with separate printed-page and region labels), revision, current/historical status, synthetic/public provenance, retrieval date, cache and confirmation labels. A region opens the whole original PDF page; its excerpt and whole-page parent are available without inventing half-page numbering. Related facing/spanning pages are explicitly review context. Non-PDF citations show the normalized worksheet/block text plus the original download, not fictional print pagination. Corrupt/missing/cross-case source responses show an error rather than reusing the saved source snapshot. Public links are provenance; the app does not fetch them automatically.

**Download saved section text** exports the persisted exact text with mock labels and sources. It excludes unsaved wording and is not the template-filled Word ES (B18). B15's combined draft dashboard and version-history view remain separate work.

## Manual walkthrough pending

1. Load all three tranches and the saved public pack. Create section 8. Open `valuation_v1.pdf` from a claim; verify PDF page 1, revision 1 and SYNTHETIC DEMO DATA. Use next/previous page, close with Escape, and confirm focus returns to the claim link.
2. Edit a narrative without changing numbers. Verify the unsaved indicator, blocked section/case switching, enabled Save and disabled Confirm/Redraft. Save, reload and confirm the exact wording and CA edit attribution persist. Confirm section review; gaps remain visible.
3. Create section 2 and open its exposure worksheet citation; verify normalized page/sheet and read-only computed figures. In section 10, open the public annual report citation at its specified PDF page; verify printed-page, public URL/date and confirmation labels. Inspect a narrow window and a wide PDF page.
4. Open the case in two browser tabs. Save in one, then try to save/confirm from the other. Verify the conflict message, retained local wording and explicit discard/reload recovery.
5. Upload `demo/synthetic/late_update/valuation_v2.pdf` with its manifest classification. Refresh status: section 8 becomes Stale while text/earlier confirmation remain. Its old source link resolves revision 1 as historical. Redraft explicitly, inspect the new SGD 104m source, then confirm. Upstream synthesis may need redrafting first where its prerequisites are Stale.
6. Review section 12's supplied rating and section 14's CA position as read-only claims. For section 14 create prerequisite drafts first, then enter a position. Check read-only behavior on a reviewer/final-state case; no workflow transition is implemented here.

The task's browser host was unavailable and native Chrome returned `cgWindowNotFound`; interactive navigation, focus and responsive/PDF-canvas appearance have **not** been visually accepted. API and server-render checks supplement this walkthrough, not replace it.

## Offline verification

```sh
LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=runtime/pytest-b14-final
npm --prefix frontend run build
npm --prefix frontend run lint
npm --prefix frontend test
node frontend/scripts/check-section-editor.mjs runtime/pytest-b14-final/test_editor_api_save_confirm_l0/editor-draft.json runtime/pytest-b14-final/test_computed_editor_sources_r0/editor-computed.json
```

The last command uses Vite's existing compiler, server-renders real API snapshots for sections 8/2/10/12, and checks editable/read-only claims, read-only textareas, exact saved text, source/page/public/synthetic labels and escaped markup. It writes review HTML beside the JSON in ignored runtime storage. Pytest validates the save/confirm/late-source/redraft chain, both PDF and normalized-source resolution and historical preservation with sockets/DNS blocked. Node tests cover edit filtering, protected claims, all three concurrency tokens, HTTP conflict details and distinct PDF/normalized/region page labels.
