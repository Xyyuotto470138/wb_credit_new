# Enhancement plan (13 Nov 2026)

Agreed with Sheryl on 12 and 13 Nov after feedback on the product video. This plan adds to `docs/history/BUILD_PLAN.md`; it does not replace the gates there. Sizes are estimates.

## Principles that stay

- Python does arithmetic. A model never writes or changes a computed figure.
- Anything a model proposes is a suggestion the maker accepts or rejects. Nothing is applied automatically.
- Analyst added content is labelled as such and is never presented as checked by code.
- A model sense check is a prompt for a human check, never a pass.

## Ranked builds

| Rank | Build | What it does | Size | Needs Sheryl first |
|---|---|---|---|---|
| 1 | Fixes | Section 10 marked for update when section 8 changes. Inputs screen checkbox follows the case, not the first demo. A redraft keeps accepted assistant notes. Old mock demo files relabelled. | 0.5 day | No |
| 2 | Free blocks | The analyst adds text, a pasted table (from Excel or Word) or a screenshot anywhere in a section, moves or deletes it. Kept across redrafts, versioned, exported to Word in place, labelled "Analyst added". | 1.5 days | No |
| 3 | Sense check | For every table not checked by code (model drafted tables and analyst added tables), a model call looks for values that do not look reasonable: totals that do not add up, units, signs, dates, figures that disagree with checked figures elsewhere in the ES. Each finding is shown as "Suggested check" with the reason. It never changes a value and never blocks. Mock provider in tests; live only behind the live gate, with cost logged. | 1 day | No |
| 4 | Papers list | Home page listing every paper: borrower, stage, whose turn, sections needing update, open comments. Switch paper from the top bar. | 1 day | No |
| 5 | Maker and checker | Role switch. Maker submits. Checker has a read view with sources, marks sections reviewed or returns a section with a comment. Maker sees returned sections, fixes and resubmits. Uses the existing workflow back end. Replaces the planned reviewer mode. | 1.5 days | No |
| 6 | New information update | Upload an updated document. Python recomputes. A "What changed" panel lists each affected figure and section, before and after. The model proposes redrafts of affected wording only, as tracked changes. Analyst edits are kept; confirmations on changed sections are reset. | 2 days | Yes: the scenario and its synthetic documents |
| 7 | Review threads and live assistant | Comments anchored to a sentence, cell or section, with replies between RM, CA and team lead. "Resolve with conclusion" asks the assistant for a tracked change that cites the thread. Needs the live Credit Assistant. | 2.5 days | Yes: who may comment and resolve |
| 8 | Offline round trip | Export carries a marker on every part. An edited Word file is uploaded, matched back, compared and saved as a new version. New tables and images become free blocks. Edited computed figures are shown as mismatches, never accepted silently. Word comments go into the review threads. | 2 days after free blocks | Yes: review of the first prototype |
| 9 | Computed tables in configuration | Ordinary calculated tables described in the specification file and run by one general engine. Complex ones stay as code. | 2 days | Yes |
| 10 | Template upload adapts the structure | A revised Word template is uploaded, differences are shown, the specification is updated after confirmation. Replaces the planned template admin step. | 2 days | Yes |

Still open from the handover list, after the above: rollback, checks panel, settings page with cost totals, scripted demo and reset, handover pack.

## Status, 13 Nov (after the overnight build)

Ranks 1 to 5 are built, tested and committed. Details, limits and screens are in `docs/history/BUILD_STATE.md` (overnight section) and `docs/es_spec.md`.

Rank 6 was built on 13 Nov (afternoon) as a first working version on the scenario Sheryl chose: an updated CAS and a revised valuation on the Keppel REIT case. Specification: `docs/new_information_spec.md`. Ranks 7 to 10 are not started.

## Overnight build, 13 Nov

Ranks 1 to 5, in that order. They are chosen because the behaviour is already agreed, they can be proven by tests and screenshots, and none needs a product decision. If time runs out, the build stops at the end of a finished rank; nothing is left half done on `main`.

Each rank ends with: tests for the change, `npm run build`, eslint, refreshed screens in `docs/screens/`, a small commit, and a note in `docs/history/BUILD_STATE.md`.

Live calls overnight: only the sense check on the saved Keppel case, once, to produce real findings for the screens. Expected cost under USD 5 on the default model. Everything else runs on the mock provider.

Stops and reports instead of improvising if: a change would alter a computed figure in the saved live ES, the saved live case cannot be restored, or an existing test fails for a reason outside the change.
