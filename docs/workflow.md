# B16 workflow API

B16 implements the human workflow at backend/API level. B17 reviewer screens await
Sheryl's review. Roles come from the case's pinned team configuration. The caller
supplies an actor and prototype role; these fields are **not authentication or bank
entitlements**. Models never select an approval outcome or the CA's position.

All paths below are relative to `/cases/{case_id}/workflow`.

| Method/path | Contract |
|---|---|
| `GET /` (without the trailing slash) | State, active ES version, latest event ID, configured roles, available actions, editing scope, immutable events and question history. Available actions still require their listed checks/payloads. |
| `POST /transitions` | Perform one configured human action in a serialized SQLite transaction. |
| `GET /snapshots/{es_id}` | Case-scoped ES, exact saved section drafts/source registers/computed-value references, originating B25 check and events referencing that ES. Historical retrieval never substitutes current working sections. |

Every transition request contains:

```json
{
  "actor": "synthetic-ca",
  "role": "CA",
  "action": "submit",
  "expected_state": "Draft",
  "expected_event_id": null,
  "expected_es_version_id": null,
  "expected_preview_token": "token from /submission-checks/preview",
  "mandatory_gap_reasons": {"current-gap-id": "Recorded CA reason for reviewer consideration."}
}
```

Copy the state/event/ES tokens from `GET /workflow` before each action, including
explicit nulls before the first submission. After a return or question, use the new
tokens and reload the B25 preview. A stale request, duplicate click, or action from
a previous review cycle returns 409, including when the state name matches again.
Unknown actors/roles or malformed payloads return 422; a configured action attempted
by the wrong role returns 403. Unavailable/disabled/final-state actions and locked
mutations return 409. Unknown cases return 404. Failed transactions leave no event,
question, check, snapshot or active-pointer change.

## Configured actions

| State | Role/action | Payload and result |
|---|---|---|
| Draft or Returned to CA | CA `submit` | Current B25 token and gap-specific reasons; creates a submission ES and check, then moves to Submitted to Credit Head. |
| Submitted to Credit Head | Credit Head `support` | Moves to Supported, keeping the submitted ES. Optional comment. |
| Supported | Credit Head `handoff` | Moves to With Credit Approver as a separate recorded event. |
| Submitted to Credit Head | Credit Head `return` | Nonempty unique `section_ids` and nonblank `comment`; moves to Returned to CA. |
| With Credit Approver | Credit Approver `return` | Same named-section/comment requirement; revisions must follow the Credit Head route again. |
| With Credit Approver | Credit Approver `approve` | Creates a distinct immutable Approved snapshot. |
| With Credit Approver | Credit Approver `approve_with_conditions` | Nonempty `conditions` list of nonblank strings; distinct Approved with conditions snapshot. Configurable, enabled by default. |
| With Credit Approver | Credit Approver `decline` | Distinct immutable Declined snapshot, final. Optional comment. |
| With Credit Approver | Credit Approver `question` | Nonblank `question`, optional configured `section_ids`; records the question and moves to Question to CA. |
| Question to CA | CA `answer_resubmit` | Current `question_id`, nonblank `answer`, B25 token and the original gap reasons; records the answer and resubmits directly to the approver. |

Optional comments are retained in append-only event payloads and version-bound
comment rows. A return records its named sections and comment; dependency repair
does not rewrite that reviewer request. Every event records actor, role, UTC time,
from/to state and ES version. Conditions are immutable event content, not generated
model wording. Answer/resubmit is one atomic action: there is no separately saved
editable answer draft. Repeated question cycles retain every question and answer.

## Locks and returns

Submitted to Credit Head, Supported, With Credit Approver, Question to CA and all
final outcomes lock section drafts, edits, confirmations, chat proposals/decisions,
model selection/comparison, financial spreading, analytics, search, evidence
confirmation and gap dismiss/restore operations. Upload/folder intake is also
blocked during reviewer/question custody. Existing read/source/history APIs remain
available. Automatic proposal-staleness bookkeeping does not accept a proposal or
change ES content.

A recorded return permits edits to the named sections and their transitive
configured dependants. Those sections lose confirmation and need explicit CA review
before resubmission. If new inputs during a return make other working sections
Stale, those sections and their dependants also become repairable; otherwise B25
would block a case whose stale sections could not be fixed. Unaffected, unreturned
sections remain protected. Source input actions are case-wide during a return;
normal freshness propagation and the complete B25 gate still apply.

A question permits only an answer. Draft/template pins and mandatory-gap reasons
must equal the questioned submission. All 14 checks are rerun in the same transaction
as resubmission. B25 `can_submit` remains false in Question to CA because it denotes
the ordinary CA-to-Head submission; this configured answer route requires `passed`. Substantive ES revisions require an approver return and the Credit
Head review path. Passing a previously saved check ID or a client `passed` flag is
not supported.

## Snapshot and configuration boundaries

Submit, including resubmission, creates a new immutable ES with its parent and an
immutable B25 check. Support/handoff/question retain the reviewed ES. Final decisions
copy its exact section-version map, configuration hash, template pin and gap reasons
to a separate final ES, and record the human decision in an immutable event. The
active pointer changes atomically. SQLite triggers also prevent updates/deletes of
ES/draft/event/check records, question text, and completed answers.

Late uploads after a final outcome can mark working content Stale. They never reopen
the case, change its active final ES, mutate its evidence versions, or replace its
saved source registers. No final-outcome reopen/override action is provided. New
working-cycle creation and approved DOCX rendering/acceptance remain later Gate 3
integration work. Existing Word creation is still explicitly a **draft export**,
now available in a recorded return as well as Draft; historical artifacts remain
unchanged. Final snapshots can be retrieved as JSON through this API.

The case pins `workflow.yaml` with its other team rules; later YAML edits do not
silently change an existing case. Disabling `approve_with_conditions` removes that
action. Validation prevents configurations from unlocking reviewer/final states,
removing finality, assigning an outcome to an inappropriate role, or dropping the
required B25/return/question/conditions evidence.

S06 remains disabled in FIG. The reserved configuration seam allows
`credit_admin_support_enabled: true`, a `credit admin support` role, and assigning
that role the handoff from Supported. This holds the ES for an intervening admin
step without changing the execution engine. No admin checks, key-in records,
integration claims or screen are implemented by B16.

## Verification

`tests/test_workflow.py` covers the complete disallowed state/role/action matrix,
each successful outcome, concurrent duplicate submissions, stale preview/event/ES
tokens, B25 rechecks, return/reconfirmation, repeated question cycles, conditions,
API and repository lock bypasses, SQL immutability, configuration toggles, case
isolation and restart. Small labelled workflow fixtures use the real B25 evaluator;
they are supplemented by the actual three-tranche demo with saved public evidence,
mock spreading, sourced drafts, Credit Head return/redrafts, question/answer,
conditional approval and late valuation. All tests block sockets and DNS.
