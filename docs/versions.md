# Section versions and Stale (B13)

All endpoints use the existing configured local app, mock provider, SQLite database and template/blob stores. No paid or network calls. B14 provides the [editor UI and source panel](section_editor.md); B24 provides [typed section chat, CA facts and validated numeric-input recomputation](section_chat.md). Role fields are prototype controls, not authentication.

## API

- `GET /cases/{case_id}/sections` refreshes and returns section states.
- `GET /cases/{case_id}/sections/{section_id}/history` returns the state, immutable draft versions and immutable confirmation records, ordered by creation time/ID.
- `POST .../{section_id}/save` accepts `replacements`, a map of existing claim IDs to CA-edited narrative wording.
- `POST .../{section_id}/redraft` generates a new mock draft with the current draft as parent. Optional fields are `computation_id`, `confirm_unsecured` and `ca_position` (section 14 only). The parent's template remains pinned. A template change needs a later explicit working-version selection.
- `POST .../{section_id}/confirm` records the CA's acceptance of the exact current draft and inputs, even if named evidence gaps remain. B25 separately gates submission and gap overrides; confirmation does not waive a gap.

Each POST requires `actor`, `role: "CA"` (default), `expected_draft_id`, `expected_revision` and `expected_input_fingerprint`, taken from the latest section state. SQLite `BEGIN IMMEDIATE` serializes preparation, validation, append and pointer updates. Obsolete version/revision/input tokens return 409; malformed or unsupported edits return 422. Failure rolls back the entire operation. Readiness changes that invalidate content also advance the editor revision, so an upstream version change invalidates an open editor even without a document change.

Only a case in `Draft` can mutate content. Reviewer and final states, including approved/declined snapshots, remain locked. B16 owns named returns and explicit creation/reopening of a working version after approval; B13 never changes workflow state, active ES pointers or ES snapshots. Late input still refreshes working readiness in every state.

## Preservation and editing

Save and redraft append `DraftVersion` records and advance the current pointer/revision; they reset the current confirmation. Prior text, authors, timestamps, parent links, configuration/prompt/model/template pins, document/citation/computed IDs and confirmation records remain available. SQL triggers prevent updating or deleting versions and the new `SectionConfirmation` history table. Existing databases get this table additively through `create_database`; old confirmations are not fabricated with invented actors/times.

Save replaces only claim wording inside validated spans. It preserves source markers, URLs/dates, synthetic/public/proxy/mock labels, named gaps and computed blocks. Supplied internal ratings, unsecured confirmations, the CA-stated position, explicit case inputs and Python computed claims/summaries have dedicated inputs and cannot be edited here. Numeric-token changes are rejected; B24 owns new numeric inputs/recomputation. This token guard is not semantic validation of arbitrary prose. The CA remains responsible for edited wording and may not use it to introduce unsupported facts or change computed meanings.

Each edited claim carries an immutable `ca_edit` snapshot with actor, time, base draft, original and replacement wording. Text labels it as CA-edited wording, not independently verified; retained document links are review context. This is editing provenance, not a fabricated B24 chat/CAInput record. B12 can carry these structured edits with attribution, but does not treat edited claims as the original reviewed fixture facts when selecting risk wording. Unstructured historical edits still require a redraft. Section 14's CA position changes through explicit redraft, preserving its separate CA-input provenance.

## Freshness

Readiness checks source fingerprints, pinned prerequisite draft IDs and transitive dependency state. An edit/redraft upstream invalidates downstream drafts even when document inputs are identical. Stale is sticky until an explicit fresh redraft; repeated refreshes never create drafts or clear Stale merely because an input selection reverts. Saving edits on Stale content preserves the older fingerprint and remains Stale. Confirmation rejects Stale, superseded and corrupt source evidence.

A stale section may retain `confirmed_draft_id` as its historical confirmation pointer for compatibility. It is **not currently confirmed**: consumers must require `readiness == "CA confirmed"`, current draft equality and current inputs. New versions clear the pointer. The immutable confirmation list retains all B13 actor/time records.

New FIG cases add `freshness_requires: [8]` to section 9. Security changes therefore invalidate repayment without making a security draft an additional first-draft prerequisite: drafting still requires sections 7/10. The combined prerequisite/freshness graph is checked for unknown IDs and cycles. Old case configuration snapshots/hashes are unchanged and keep their pinned dependency rules; no implicit migration is performed. The actual revised valuation makes 8/9/11/14 Stale for new FIG cases while section 7 remains confirmed. Refresh/redraft in dependency order, starting with 8, then 9, 11 and 14.

The original first-draft API rejects existing drafts; it cannot be used to bypass explicit version conflict checks. Historical exact-text previews keep their original bytes. Word layout/export and full workflow acceptance remain B18/B16.
