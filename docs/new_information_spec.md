# New information update: specification (rank 6, 13 Nov 2026)

Scenario agreed with Sheryl on 13 Nov: on the Keppel REIT case, an updated CAS and a revised valuation arrive after the ES is drafted.

## Actual state before this build

Checked in the code on 13 Nov.

| Assumed in the plan | Actual |
|---|---|
| A later document replaces the earlier one | Built. Intake links the new file to the one it replaces when the type, entity and scope match and the date is later. A same-date file with different content is held for review, not replaced. |
| Sections that depend on it are marked | Built. "Update required" follows the document's catalogue links and section dependencies. Confirmation of a section that cites a replaced document is refused. |
| Python recomputes | Partly. Calculated tables are rebuilt only inside a full redraft of the section, in the same step as the model wording. |
| A "What changed" view | Not built. |
| The model proposes changes to affected wording only | Not built. A redraft replaces every model written part of the section. |
| Analyst edits and added content are kept | Notes and added content are kept on a redraft. Edited wording is not. |

A section can also cite a replaced document without being marked, because every section may cite any document. Today that is only found at confirmation.

## The scenario documents

All fictional, labelled SYNTHETIC DEMO DATA, in `demo/synthetic_keppel/late_update/`, built by `scripts/build_keppel_pack.py`. No published figure of the real trust is changed.

| File | Dated | Replaces | Change |
|---|---|---|---|
| `cas.pdf` | 13 Nov 2026 | CAS of 10 Nov | TL-01 raised from SGD 600m to SGD 650m. Total limits SGD 750m. States that the pricing report and the support email still show the first amount. |
| `term_sheet.pdf` | 13 Nov 2026 | Term sheet of 10 Nov | TL-01 SGD 650m. Other terms unchanged. |
| `valuation_report.pdf` | 12 Nov 2026 | Valuation of 31 Oct | Market value SGD 2,750.0m (was SGD 2,880.0m). Capitalisation rate 3.55% (was 3.40%). |
| `financial_projections.xlsx` | 13 Nov 2026 | Projections of 31 Oct | Interest expense on the higher term loan. |

The term sheet and projections are included because a changed loan amount in the CAS alone would leave the papers disagreeing with each other.

## Behaviour

1. **Arrival.** The maker uploads the files or scans the "Late update" demo folder. Intake behaves as today.
2. **What changed page.** Lists the new documents and what each replaces, then every affected section with its state: waiting for another section, ready for a proposal, proposal ready, updated. A section is affected when it is marked "Update required" or its current version cites a replaced document.
3. **Order.** A section that reads another affected section waits until that one is updated. This keeps the risk and recommendation sections from being proposed against old figures.
4. **Proposal.** For one section, the system prepares a full candidate version against the current documents (Python calculations and the model, with the usual figure checks) and saves nothing to the section. It then compares the candidate with the current version, part by part, in Python.
5. **Figures.** Tables calculated by code and tables of figures copied from sources are shown cell by cell, before and after. They are taken together as a set when the proposal is applied, because they must agree with each other. A value that was sourced before and is not sourced now is flagged.
6. **Wording.** A wording part is proposed only when it is affected: it cites a replaced document, the candidate uses a new document, it refers to calculated figures that changed, or it draws on a section that changed. It is shown as tracked changes. The maker accepts or keeps each part. Parts that are not affected are kept as they are and are not shown, even if the model worded them differently.
7. **Apply.** Nothing changes until the maker applies the proposal. Applying saves a new version of the section: all figure tables from the candidate, accepted wording from the candidate, everything else from the current version. Analyst notes and added content are carried over. Any confirmation of the section is reset.
8. **Kept wording that cites a replaced document.** Allowed, and shown with a warning. The existing rule still applies: the section cannot be confirmed until that wording is updated.
9. **Analyst edits.** An edited part that is not affected is kept. An edited part that is affected is marked "includes your edit" so it is not accepted without a look.
10. **Dismiss or propose again.** A proposal can be dismissed, and a new one requested. A proposal is void once the section or its inputs change.

## Rules that hold

- A model never writes or changes a calculated figure. Figures copied from sources are checked in Python against the cited line, as in drafting.
- Nothing is applied automatically. The maker applies each section's proposal.
- A proposal is a model call. It runs only behind the live gate and is recorded in the cost ledger with purpose `draft`. Tests use a stub.

## Not in this build

- Tracked changes are on screen. The Word ES holds the applied result, without Word revision marks.
- Accept or keep is per part, not per sentence.
- A recalculation without the model is not offered: most figure tables depend on figures the model copies from the papers.
- The second paper (first generation path) has no proposals.
- A brand new document type that replaces nothing marks sections through the existing catalogue links only.
