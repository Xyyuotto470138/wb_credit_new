# B11/B12 section drafts

`POST /cases/{case_id}/drafts/sections/{section_id}` accepts `actor`, `role: CA`, optional `template_version_id`, optional B10 `computation_id`, and `confirm_unsecured` (default false). All 14 sections are supported by the API; sections 9, 11 and 14 enforce the synthesis gates below. A case must be in Draft state, the section applicable, and its first draft absent. An active or explicitly selected team template must exist with intact stored bytes. Writes are serialized; failed requests roll back. Section edits/redrafts/confirmation remain B13/B14; this service never changes an existing draft, confirmation, ES snapshot or workflow event.

`GET /cases/{case_id}/drafts`, `GET /cases/{case_id}/drafts/{draft_id}` and `GET /cases/{case_id}/drafts/{draft_id}/preview.txt` retrieve immutable snapshots. The dashboard now uses the B14 [section editor](section_editor.md): editable narrative/facility claims, read-only computed and supplied claims, cited source pages, named gaps, an explicit unsecured-description checkbox and a saved-text download. The preview is not a complete ES or Word document. B18 owns filling the pinned owner template.

## Offline support boundary

`backend/app/fixtures/first_drafts.json` contains authored, reviewed mock claim/evidence pairs for the supplied demo pack. Each prose claim pins the borrower, source hash, reporting metadata, physical page and exact normalized quote checks. B08's current-document selection and section support map gate use. New/changed/unknown sources produce gaps rather than adopting old prose. This is a deterministic offline demonstration, not evidence of live model quality or a general semantic entailment validator.

The service assembles an exact-request `MockProvider` fixture from eligible reviewed claims. An injected `drafting_provider` must also report mock. The strict response schema allows only reviewed claim IDs and their unchanged text; unknown IDs, added fields, new numbers, altered assertions and duplicates are rejected with named gaps. Missing/malformed injected fixtures have no live fallback. Public/uploaded text never changes the prompt or authorizes actions. Prompt hash, pinned configuration, fixture version and provider/model identity are saved. Existing case configuration pins remain unchanged when FIG prompt defaults advance.

The supplied internal rating is adopted only from the current internal-rating source; historical prior-ES grades and external agency reports cannot fill it. The reviewed mock separately cites the dated Fitch action from the saved public release; it cannot fill the mandatory internal-rating input or establish that no later action occurred. Unsecured wording in sections 7/8 needs explicit CA confirmation, recorded with actor, source hash and draft timestamp. Missing security evidence never implies unsecured status or legal perfection. Industry-code confirmation remains a named gap.

## Computed data

Sections 2/9/10/13 consume immutable B10 values and retain their IDs, operands, source labels, scope, period, units, formulas/threshold metadata and proxy flags. The provider never receives authority to change the computed values or tables. Superseded sources withhold their values; content-integrity failures reject use. Exposure nil requires the explicit new-to-bank case input; missing conduct never implies satisfactory conduct.

For offline convenience, when no B10 computation is selected the service runs the existing B10 engine on exact-hash reviewed demo worksheet mappings (exposure, property projections, conduct, contractual covenants) or FY2025 annual-report p59 disclosures (leverage, ICR, fixed-rate share, debt cost/maturity). These are saved-pack bindings, not arbitrary workbook or PDF extraction. Source totals are not copied into generated arithmetic. Dates and scope remain those of each source: public FY2025 values do not become current November values. Other metrics remain named gaps. Conduct averages retain their twelve month-end sample basis and the narrative retains excess/late-payment exceptions.

Section 10 also consumes the latest already validated B09 spread with current evidence and matching configuration; it does not run spreading automatically. The B09 fixture generation/API remains the route for that separate step. A missing spread is explicit. These draft computations do not satisfy B05's financial-spread input requirement.

## Persistence and downstream contract

`DraftVersion.text` starts with **MOCK DRAFT** and includes source markers, public URLs/retrieval dates, synthetic/public/proxy labels and `[GAP]` lines. Downloads use these exact bytes. `claim_spans[0]` is `kind: draft_metadata`, including mock label, source register, B10 computation ID/tables and mode; remaining entries are narrative, facility, computed, computed_summary or explicit case_input claims with text offsets and evidence references. Citation records bind each factual claim to immutable page evidence. Facility entries contain `facility`/`field`; computed claims carry canonical value IDs; summaries reference those same values. The case-input nil row explicitly identifies the case.

B14/B18 consumers must preserve the mock label, cite each claim/table, and retain gaps and source labels. A `Drafted` display state does not mean complete evidence, confirmed content, passed legal checks or approval. Current source confirmation changes may mark a saved draft Stale through the existing readiness fingerprint; historical draft text/labels are not rewritten. Interactive visual acceptance and Word template/render acceptance remain their later gates.

## B12 synthesis ordering and CA position

Draft prerequisites before synthesis: 7 and 10 → 9; applicable 3–10 → 11; all mandatory applicable 1–13 → 14. The case-pinned `dependencies` configuration drives these checks, including `applicable_only` and `mandatory_only`. A required dependency needs usable input and an existing, current structured draft. Missing drafts, blocked inputs (including unavailable supplied internal rating), Stale drafts, cross-section/case/config pointers, changed ancestor draft versions, superseded/corrupt evidence and unreviewed CA-edited dependency text cannot be consumed. No prerequisite is generated or overwritten implicitly. A partial prerequisite is allowed and its named gaps propagate; this is first-draft generation, not submission approval.

Section 14 accepts optional `ca_position` in the existing POST body, for example `{"actor":"demo-ca","ca_position":"Defer pending evidence of additional repayment funding."}`. Otherwise it requires and reaffirms the nonblank position already recorded on the case. RM support, prior approval wording, a model response and template examples cannot supply this position. The exact statement is prefixed **CA-stated position (verbatim)**, outside the provider response, with CA actor, UTC time, case ID and statement hash in the immutable draft. It is labelled CA input and not independently verified. The request saves the current case position only on successful generation; API failures roll back. This version-bound case-input snapshot does not fabricate a chat message or claim a B24 CAInput record. Changes to the mutable case position do not rewrite historical drafts; existing readiness fingerprints mark the conclusion Stale.

`backend/app/fixtures/synthesis.json` contains hash/page/quote-bound property assumptions, rent-roll/lease observations and pricing gaps. Reviewed risk wording additionally requires every named source claim from the prerequisite drafts. Risks distinguish indicative security, floating pricing, maturities and uncommitted renewals/refinancing from verified mitigants. Review actions remain proposed, with no assertion of perfected security, secured refinancing, adequate group cash flow or an AI recommendation. Unknown sources retain gaps under the same B11 mock boundary.

The Python B10 projection adapter supplies immutable property cash/debt-service/DSCR values. A deterministic comparison flags each validated DSCR below one and preserves its computed-value ID and operands. The aligned demo remains insufficient on property-only debt service in every projected year; no optimistic cash flow or refinancing receipt is invented. These facts, all supported prerequisite claims and their gaps are carried outside model selection, so an omitted/rejected mock risk paragraph cannot erase adverse evidence. Missing projections remain gaps and do not create an insufficiency finding. Source dates and property/group scope remain visible.

Synthesis metadata pins direct prerequisite draft IDs, completeness, fingerprints, template versions and gaps, plus synthesis/fixture versions and CA position snapshot. Claims carry their dependency section/draft/claim IDs and original page evidence; numeric IDs remain unchanged. Repeated supported observations are deduplicated while retaining original claim aliases for rule matching. `dependency_input_completeness` records full/partial source readiness; `dependency_completeness` also reflects unresolved draft coverage gaps. Full input readiness is not a complete or confirmed narrative. Inherited computed claims retain their canonical IDs; upstream table layouts stay on their pinned drafts, while section 9's own projection table is included locally.

The B14 editor exposes all section entry points, including synthesis with prerequisite gates and an explicitly entered CA position. B13/B14 provide editing, redraft and version-conflict recovery. B24 provides [typed section chat](section_chat.md); the combined dashboard and workflow remain later blocks. B18 provides [template-filled draft exports](exports.md). Older case configuration pins are preserved; new cases receive FIG prompt v3. Tests exercise actual source packs, B09/B10/full and partial chains, mandatory and N/A gates, source integrity, unsupported provider assertions, immutable persistence, HTTP rollback and exact-text export without network access.

B13 now supplies explicit [section save/redraft/confirm and history APIs](versions.md). Structured CA wording edits retain their source links and visible actor/time attribution through synthesis; unstructured edits remain rejected. Upstream draft-pointer changes now mark downstream content Stale. B14 connects these APIs to the editor UI. B24 provides [typed section chat](section_chat.md), and B18 provides [template-filled exports](exports.md). Workflow transitions remain B16.

## 0020a reviewed credit write-up

New mock drafts use the owner template's sub-parts as coverage headings, with
specific gaps for unsupported classification decisions, subsequent changes, stress
assumptions and sign-off. Request rationale, facility
increases/maturities, detailed terms, insurance, public portfolio occupancy/WALE,
management roles, trustee identity, dated Fitch action, tenant concentration and
contractual buffers are authored against the saved pack.
Section 14 still starts with the exact CA position; supporting risk/condition
wording cannot supply a recommendation or select a decision checkbox.

`first_drafts.json` now carries reviewed `numbers` bindings and a `subparts`
coverage inventory. `services/draft_values.py` validates every binding against
the selected source's exact normalized quote and token, renders reported values
with Decimal, and calculates only the explicitly authored ratio, difference, share-of-sum and
LTV-headroom formulas. Each reported quantity and derived result has an immutable
`ComputedValue`, operand citations and formula version. The provider may select
the resulting reviewed wording but cannot change it. Dates, periods, addresses,
facility IDs and rating codes remain cited metadata, not arithmetic quantities.
These saved-pack mappings are not an arbitrary PDF extraction facility, a
financial spread, or an extension of the live analytics API.

For the initial appraisal, the fully drawn TL uses the valuation report's stated
SGD 60m debt and SGD 112m market-value operands: 53.57% LTV and 1.43 percentage
points to the fictional 55% ceiling. The revised report computes 57.69% and
negative 2.69 percentage points from SGD 104m. These are proposed fully drawn
LTVs; the existing drawn-loan covenant test remains separate. The certificate's
44.1% leverage and 2.6x ICR retain their September observation date and October
test context, giving contractual buffers of 0.90 percentage points and 0.60x.
Property tenant/lease shares are recomputed from the complete saved rental and
area components, including vacant area in the NLA denominator; stored source
percentages are not used as results. Public portfolio figures retain FY2025 dates
and do not become property-level
figures or a November group forecast. Reinstatement insurance is not market value.

Numeric prose is protected by the existing edit API just like computed tables.
Source changes still require explicit redraft, with new evidence/value references;
saved drafts, confirmations and exports remain immutable. Rejected model text
never acquires these claims. A missing/mismatched source withholds the claim and
leaves a named sub-part gap. Normalized column ordering on the annual report's
management/structure/lease pages is explicitly reflected in the reviewed quotes.

All sub-parts are represented in draft content or named gaps; this does not make
unsupported template cells complete. The existing export adapters retain richer
claims in section narrative and preserve their value references in the manifest.
This task does not change owner template bytes, export layout or activation rules.
For an existing demo case, use explicit redraft in dependency order to see the
new wording. `tests/test_richer_drafts.py` exercises all sections and the late
valuation; ignored `runtime/0020a/` contains the resulting review previews.
