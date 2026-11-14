# B25 pre-submission checks (backend/API)

Task 0026 implements checks and reviewable snapshots. The SubmissionChecks screen
awaits Sheryl's review; B16 implements the [submission/return/question transitions](workflow.md). These
routes do not change workflow state, lock content or set the active ES pointer.
A passed result describes completeness for submission, not a credit decision.

## API

All routes are under `/cases/{case_id}/submission-checks`:

| Method/path | Result |
|---|---|
| `GET /preview` | Recalculate current sections and mandatory gaps; return a deterministic `preview_token`, `summary`, `passed`, `can_submit` and future-panel data. |
| `POST` | Record the current checks, including open items and supplied reasons, against an immutable working ES snapshot. |
| `POST /validate` | Enforce all checks; 409 with the open report if anything remains open. Success records an immutable ES snapshot with purpose `submission`, for review; the workflow always reruns the gate in its own transaction. This route does not submit the case. |
| `GET` | Historical immutable checks with actor/time, ES version, section confirmations, named gaps and reasons. |
| `GET /{check_id}` | One check scoped to the case. Old results remain historical after edits or late evidence. |

Both POST routes accept only:

```json
{
  "actor": "demo-ca",
  "role": "CA",
  "expected_preview_token": "<from current preview>",
  "mandatory_gap_reasons": {
    "<expected-document id from mandatory_gaps>": "Evidence requested from its owner; review remains pending."
  }
}
```

Reasons must be nonblank (trimmed, at most 10,000 characters). Unknown, closed,
optional and other-case gap IDs are rejected. Reasons are saved in both the ES
snapshot and check; the complete gap label, catalogue ID, owner, sections, search
status and dismissal remain in `report.mandatory_gaps`. A passed gap check means
**a reason was recorded**, not that the document was supplied. The underlying gap
and section completeness do not change. GET preview starts without reasons;
clients can read a prior check and explicitly resupply relevant reasons for review.
There is no automatic carry-forward of an old exception.

Requests use SQLite `BEGIN IMMEDIATE` to serialize refresh, token validation and
snapshot persistence. An upload, edit, redraft, confirmation, dismissal or relevant
case-state change invalidates the token. Invalid/blank requests are 422; stale or
locked requests and failed validation are 409; an unknown case is 404 and missing
storage configuration is 503. Prototype CA roles are request validation, not real
authentication. Draft and recorded Returned to CA states can record new checks.
During the question cycle, only the workflow answer/resubmit action can record a
passing check.

## Rules and integration

Every configured section is checked (all 14 for FIG). An applicable section needs
its current draft, matching input fingerprint, fresh source references, `CA
confirmed` readiness, matching confirmation pointer and the corresponding immutable
CA confirmation event/revision. A Stale section fails even if it retains a historical
confirmation pointer. Rule-derived Not applicable requires a nonblank reason;
there is no new endpoint for marking an otherwise applicable section N/A.

Mandatory document gaps reuse the existing catalogue/applicability/alternative
rules. Confirmed annual-report evidence can satisfy the financial-statements
alternative. An unconfirmed public find, partial public valuation/lease disclosure,
external rating, generation offer or dismissal cannot silently satisfy a required
input. A separate reason is needed for each returned open mandatory item, including
both alternatives when neither is satisfied. A document-gap reason never waives a
section confirmation or N/A reason.

`summary.total/passed/open` counts sections and mandatory-gap reasons only. Content
gaps remain visible for CA review; this block does not add a new content-completeness
policy beyond confirmation and mandatory-document reasons. Template pins must agree
before an ES snapshot is recorded. This is separate from Word mapping validation.

B16 calls `SubmissionChecksService.require_passed` **inside the same write
transaction as the workflow transition**, with a freshly reviewed token and
reasons; it then records that evaluated report and the new ES atomically. Its
explicit allowed-state parameter supports the answer-only question cycle. Do not treat a
previous check ID, `passed` flag or `can_submit` response as permission to submit
later. `SubmissionCheck.report` is an additive JSON column: legacy records keep an
empty report, never invented historical results. Repository and SQLite triggers
protect the check and ES snapshots from updates/deletes.

## Future credit master panel

`future_credit_master.label` is exactly:

> Not connected: assumed consistent for this prototype

It has `status: "not connected"`, `included_in_pass_count: false`, and no `passed`
field. No balances are fetched, fabricated or compared. Saved section-2 Python
exposure cells supply existing limit, outstanding and proposed limit per facility,
with currency, unit, period, synthetic flag, computation ID and original document/
page operand sources. The table is checked against its immutable computation.
The panel identifies its draft and current section readiness; stale figures remain
labelled as belonging to that saved draft. A missing draft/table/source produces a
named gap, never a zero balance. Explicit new-to-bank nil exposure retains its CA
case-input basis and does not invent facilities or proposed limits.

## Offline demo verification

The real three-tranche API test uses saved public evidence, explicit public
confirmation and the validated mock spread. Before drafting, industry mapping
(catalogue 19) remains the sole mandatory gap. All 14 drafted but unconfirmed
sections produce 15 open checks. Confirming all 14 yields 14 passed/1 open;
recording a gap-specific reason yields 15 passed/0 open. No workflow event occurs.

Section 2 lists TL-01 with SGD 45m existing / 42m outstanding / 60m proposed and
RCF-01 with SGD 10m / 4m / 15m, all labelled synthetic. The future panel remains
not connected at every stage. The real revised valuation opens sections 8, 9, 11
and 14; the prior passed snapshot/reasons remain unchanged after restart.

Run `tests/test_submission_checks.py` with the offline pytest flags documented in
BUILD_STATE. Tests also cover every section's state matrix, blank reasons,
dismissals, alternatives/public confirmation, absent/corrupt sources, cross-case
IDs, role/state locks, stale tokens and immutable records. No network, paid calls,
new dependencies, template changes or frontend changes are required.
