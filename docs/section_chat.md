# Typed section chat (B24)

Every applicable section with a current structured draft has typed chat in the editor. Save/discard local wording first. Enter the CA identity, choose the operation, type the message and request a proposal. Review the complete proposed text and sources, then accept or reject. Acceptance appends a parent-linked draft, resets confirmation and makes dependent drafts Stale. It does not approve credit, move an ES pointer or waive a document gap. Earlier drafts, confirmations, rejected proposals and messages remain available.

The offline model calls a saved operation fixture on every turn. Supported operations are adding a verbatim CA assertion, emphasizing an existing cited claim by moving it earlier, and previewing numeric recomputation. This is a constrained mock demonstration, not general free-form model rewriting or semantic validation. Unknown model operations, additional fields, claims, numbers and citations are rejected. Missing fixtures fail without live fallback. No paid adapters or new dependencies are enabled.

CA assertions have immutable input versions, actor/time, message and evidence IDs; they never acquire a fictitious document/page. The UI, text download, source viewer, downstream synthesis and export labels distinguish them from public/document evidence and retain synthetic labels. Plain facts are non-quantitative; enter quantitative inputs through the numeric form. The guard detects digit/number-word tokens, not every possible expression of a quantity. The provider never turns a CA assertion into an independently verified finding. Section 12's supplied rating stays protected. Section 14's position stays unchanged; use its dedicated position/redraft action to state a new position.

## Numeric review

Section 10 offers configured REIT metrics. Supply period, scope, definition/basis, units, currency and operands explicitly. Values use the displayed base units. The UI supports scalar formulas; array/item/maturity mappings for portfolio sums, weights and maturity profiles are available through the typed API. Exposure, conduct and projection worksheets still require revised source documents; chat cannot directly edit their cells. Unlisted formulas require configuration/implementation work through a separate task.

Preview uses the same B10 Decimal engine as acceptance. No computed records or section pointers change while a proposal is pending. The CA must additionally tick acceptance of the exact sourced operands. Acceptance reruns Python and compares its result with the preview, then atomically activates the pending input and persists the operands, result/gaps and draft. Missing/invalid operands yield N/A with named gaps, not invented values. Configured thresholds and headroom come from Python. CA input is an assertion even when arithmetic validates.

A new accepted input for the same metric/period/scope supersedes its earlier CA input. It replaces only that metric and its headroom in the working draft, retaining other metrics and all historical computations/tables. New scopes/periods are additive. Accepted inputs participate in readiness fingerprints, invalidate downstream sections, and survive explicit redrafts and synthesis. Changing source documents makes dependent drafts/proposals Stale; pending input alone does not change readiness.

## API and persistence

- `GET /cases/{case}/sections/{section}/chat`: messages/proposals; identifies stale proposals.
- `GET .../chat/metrics`: section 10's pinned metric definitions.
- `POST .../chat`: B13 actor/role and draft/revision/input tokens plus `message`, `mode` (`fact`, `emphasize`, `numeric`), optional `claim_id`, `synthetic` (default true), and `numeric`.
- `POST .../chat/{proposal}/decision`: `actor`, CA `role`, `action` (`accept`/`reject`), `accept_numeric_input` (explicit true for numeric acceptance).

`numeric` has `metric_id`, `period`, `scope`, `basis`, `synthetic`, and `operands` mapping names to lists of `{value, unit, currency?, item?, maturity?}`. For example, occupancy uses `occupied_area` and `lettable_area`, both in `sqm`, with basis `comparable lettable area`. Figures in a free-text request are context, not numeric operands or model outputs.

All writes serialize with SQLite `BEGIN IMMEDIATE` and roll back on failure. Acceptance checks the original proposal tokens, source/template integrity, applicability and Draft workflow state; clients cannot retarget a stale proposal with new tokens. Concurrent edits, confirmations, accepted proposals or late evidence require a new proposal. All reviewer/final states remain locked until B16 implements explicit workflow returns. Role switching remains prototype authorization, not production authentication.

The schema upgrade adds `section_proposal.payload` without changing historical content or configuration pins. Proposal content is immutable; only a pending proposal can transition once to accepted/rejected/stale. SQLite triggers also protect proposal content and resolved history. CA inputs/evidence/values remain append-only. Pending/rejected CA evidence resolves for review but is never a current analytics input. Older schema-only proposals without a payload become stale.

## Review walkthrough

Use a synthetic renewal case and create section 8. Add a legal-review note; verify the current saved text stays unchanged, reject it, then propose and accept it. Open its CA source and check actor/time/message without a PDF page. Confirm, then ingest the late valuation: the accepted wording remains and the section becomes Stale. Explicit redraft retains the CA note.

In section 10, propose occupancy using occupied area 50 and lettable area 80, in sqm with matching scope/period/basis. Preview must show 62.5%; acceptance requires the numeric checkbox and preserves old values in history. A zero denominator must show N/A and a named gap. Refresh sections 9/11/14 to see Stale; redraft them in order. Test a pending proposal against an edit in another browser: acceptance must conflict without replacing that edit.

Automated coverage includes actual all-section drafts, provenance, rejection, immutable values, concurrency, source integrity, workflow locks, restart, redraft/synthesis, numeric gaps, threshold calculations and frontend escaped proposal rendering. Interactive browser layout/focus review is a separate manual check.
