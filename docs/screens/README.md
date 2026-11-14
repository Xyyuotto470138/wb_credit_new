# WB Credit desktop screen review

[Open the 53-page PDF](WB_Credit_screens.pdf) · [Local HTML gallery](gallery.html) · [Capture instructions](../../scripts/screens/README.md)

Captured on 11 November 2026 with installed headless Chrome 157.0.8103.39, at **1440 × 900 CSS
pixels, device scale 2** (2880 × 1800 PNGs). The actual React UI ran against a
fresh, isolated mock case using saved public documents and synthetic demo inputs.
No live model/search calls were made. `capture.json` records the browser version,
capture time and ordered captions. The PDF was printed by Playwright `page.pdf`
from the local gallery, with one screenshot and caption per 15 × 10 inch page.

## Review and coverage

All 53 PNGs were visually inspected. The walkthrough covers the empty case,
three tranches, public review and citation dialogs, all fourteen section editors,
normalized workbook/CA-input sources, request download, chat proposal/rejection/
acceptance, version history, confirmation, draft export, model routes/comparison,
and the revised-valuation Stale/redraft chain. It verifies 7/11/14 saved sections,
then exactly sections 8, 9, 11 and 14 becoming Stale. Request-list and draft-bundle
downloads were saved successfully. The industry-mapping gap remains explicit.

Fixed and recaptured: the global `details input` width stretched the upload
classification checkbox and displaced its label. Checkbox sizing now overrides
that width. Capture also waits for section/chat loading to finish before saving.
No overlapping controls or horizontal document overflow remain at this viewport.
Browser page errors and external-origin requests are checked by the capture.
The final complete run passed both checks with zero errors/attempts and stopped
its two servers; raw logs and downloads are in `runtime/0024/capture-BTD4VA/`.
All 53 PDF pages were rendered and visually reviewed. Automated checks verified
53 matching captions, one uncropped screenshot per page, 2880 × 1800 PNGs and
1080 × 720 point PDF pages. Review renders are in `runtime/0024/pdf-review/`.

Retained limitations for Sheryl's review:

- This is a long, scrolling dashboard. Screens show selected viewport positions;
  long section lists, gap lists and drafts continue below the image. They are not
  compressed into unreadable full-page screenshots.
- Source PDFs scroll within their dialog. The annual-report cover is taller than
  its viewport; fitting the entire page is not implemented.
- The workbook source is normalized text, not an Excel grid. Its columns do not
  retain original cell alignment; the original-file download remains available.
- Technical model identifiers, metric/unit keys, dense gap lists and precise raw
  figures remain visible. This task does not redesign their wording or rounding.
- An intermediate recapture hit a SQLite lock when chat history overlapped a
  section-11 redraft. The capture now explicitly finishes initial chat loading
  before redrafting. Concurrent backend-request handling needs separate review;
  no database behavior was changed in this visual-capture task.
- Request export is a text download from the existing request panel (screen 08),
  not a separate application screen. The gallery is a review artifact only.
- Desktop Chrome only: mobile, keyboard and screen-reader acceptance are pending.
  Fixture review/confirmation clicks are synthetic; human gate acceptance and
  real credit decisions remain outside this capture. Unbuilt reviewer/submission
  workflows and template administration are not represented.

## Screenshot index

- [01_empty_dashboard.png](01_empty_dashboard.png) — Empty synthetic case: no inputs or saved sections; workflow remains Draft.
- [02_empty_progress.png](02_empty_progress.png) — Empty draft progress, tranche coverage and document intake.
- [03_intake_options.png](03_intake_options.png) — Upload classification hints and configured tranche-folder scan.
- [04_public_source.png](04_public_source.png) — Saved public PDF in the source dialog, with URL, retrieval date and explicit review action.
- [05_tranche1_overview.png](05_tranche1_overview.png) — Tranche 1 plus reviewed saved public evidence: provided, public and missing inputs.
- [06_tranche1_expected.png](06_tranche1_expected.png) — Expected-input table distinguishes full inputs from partial public context.
- [07_tranche1_requests.png](07_tranche1_requests.png) — Tranche 1 open requests grouped by RM, client and internal team.
- [08_request_export.png](08_request_export.png) — Request-list export action with the first request expanded; the download sends nothing.
- [09_generation_offers.png](09_generation_offers.png) — Validated saved mock spread generated; industry-mapping offer remains unavailable.
- [10_tranche1_drafts.png](10_tranche1_drafts.png) — Seven saved partial/full sections after tranche 1; saved drafts are separate from readiness.
- [11_section_editor.png](11_section_editor.png) — Section editor shows named gaps, sourced wording and original-page citation links.
- [12_cited_pdf.png](12_cited_pdf.png) — A section citation opens its original PDF page with public provenance.
- [13_tranche2_overview.png](13_tranche2_overview.png) — Tranche 2 adds property and renewal support; earlier affected drafts become Stale.
- [14_tranche2_drafts.png](14_tranche2_drafts.png) — Eleven saved sections after tranche 2; rating, conduct and conclusion remain outstanding.
- [15_chat_proposal.png](15_chat_proposal.png) — Section chat proposes a cited revision for review before it changes the saved draft.
- [16_chat_rejected.png](16_chat_rejected.png) — Rejected proposal stays in chat history; saved wording is unchanged.
- [17_chat_accepted.png](17_chat_accepted.png) — Accepted revision records the analyst and creates a new version with CA-input provenance.
- [18_accepted_note.png](18_accepted_note.png) — The saved section includes the accepted synthetic CA note and its source link.
- [19_ca_input_source.png](19_ca_input_source.png) — CA-input source panel records the note, actor and time without implying a document page.
- [20_version_history.png](20_version_history.png) — Read-only historical section version preserves its wording, model, template and sources.
- [21_tranche3_overview.png](21_tranche3_overview.png) — Tranche 3 supplies conduct and internal rating; missing-file count differs from mandatory gaps.
- [22_tranche3_complete.png](22_tranche3_complete.png) — All fourteen sections saved; the industry-mapping gap remains visible and no approval is implied.
- [23_all_sections.png](23_all_sections.png) — All fourteen built ES sections remain navigable with their readiness and gap counts.
- [24_section_01.png](24_section_01.png) — Section 1: Request / Purpose; saved sourced draft for CA review.
- [25_section_02.png](25_section_02.png) — Section 2: Summary of current client group exposure; saved sourced draft for CA review.
- [26_exposure_values.png](26_exposure_values.png) — Exposure figures are read-only Python computations with synthetic source citations.
- [27_workbook_source.png](27_workbook_source.png) — Normalized workbook source panel with original-file download and synthetic provenance.
- [28_section_03.png](28_section_03.png) — Section 3: Key updates; saved sourced draft for CA review.
- [29_section_04.png](29_section_04.png) — Section 4: Business background; saved sourced draft for CA review.
- [30_section_05.png](30_section_05.png) — Section 5: Shareholding structure; saved sourced draft for CA review.
- [31_section_06.png](31_section_06.png) — Section 6: Key management and stakeholder; saved sourced draft for CA review.
- [32_section_07.png](32_section_07.png) — Section 7: Facility structure; saved sourced draft for CA review.
- [33_section_08.png](33_section_08.png) — Section 8: Security support; saved sourced draft for CA review.
- [34_section_09.png](34_section_09.png) — Section 9: Source of repayment; saved sourced draft for CA review.
- [35_section_10.png](35_section_10.png) — Section 10: Financial highlights and analytics; saved sourced draft for CA review.
- [36_numeric_chat.png](36_numeric_chat.png) — Section 10 numeric chat requires explicit sourced operands for Python recomputation.
- [37_section_11.png](37_section_11.png) — Section 11: Key credit risks and mitigates; saved sourced draft for CA review.
- [38_section_12.png](38_section_12.png) — Section 12: Credit rating; saved sourced draft for CA review.
- [39_section_13.png](39_section_13.png) — Section 13: Conduct of Account; saved sourced draft for CA review.
- [40_section_14.png](40_section_14.png) — Section 14: Recommendation: conclusion; saved sourced draft for CA review.
- [41_confirmed_section.png](41_confirmed_section.png) — CA confirmation records review while keeping named gaps open.
- [42_draft_export.png](42_draft_export.png) — Draft Word export preview pins the template, saved section versions and visible gaps.
- [43_export_history.png](43_export_history.png) — Saved draft bundle offers Word, source manifest and request-list downloads.
- [44_model_picker.png](44_model_picker.png) — Case-level model picker exposes offline mock choices and keeps all live routes disabled.
- [45_model_routes.png](45_model_routes.png) — Configured model route list labels disabled providers and unconfirmed deployment details.
- [46_model_compare.png](46_model_compare.png) — Side-by-side offline model comparison uses the same evidence and identical Python tables.
- [47_compare_wording.png](47_compare_wording.png) — Comparison wording retains each mock model’s citations and gaps; previews do not save a draft.
- [48_late_valuation_stale.png](48_late_valuation_stale.png) — Revised valuation makes sections 8, 9, 11 and 14 Stale while retaining saved versions.
- [49_stale_editor.png](49_stale_editor.png) — Stale editor explains the choice to keep wording for review or explicitly redraft.
- [50_redraft_choice.png](50_redraft_choice.png) — Explicit redraft action preserves historical wording and confirmation; reconfirmation is disabled while Stale.
- [51_revised_security.png](51_revised_security.png) — Explicit redraft uses the revised synthetic SGD 104m valuation and retains source provenance.
- [52_refreshed_chain.png](52_refreshed_chain.png) — After ordered redrafts, the affected chain is current; previous versions and exports remain.
- [53_document_register.png](53_document_register.png) — Document register retains public/synthetic provenance and all twenty-three stored versions.

## Workbench screens (12 Nov 2026)

`wb_01` to `wb_13` show the rebuilt front end (project file section 2.14): Inputs, Full ES, a section, Sources, Edit text, a tracked change, version history, a confirmed section, section 10, a section waiting for inputs, and three phone-width screens. Refresh them with a prepared demo running:

```sh
scripts/demo/serve.sh --prepared --fresh
node scripts/screens/capture_workbench.mjs http://127.0.0.1:15300
```

The capture also checks that Edit text saves a new version, a citation opens Sources, a rejected change leaves the section unchanged, and Confirm turns the rail icon green.

Screens `01` to `53` and `WB_Credit_screens.pdf` show the first dashboard, which is now reachable only at `#/classic`. `capture.mjs` drove that dashboard and no longer matches the default screens.
