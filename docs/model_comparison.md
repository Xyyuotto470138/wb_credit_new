# B26 model selection and comparison

Gate 2 extension, task 0021. No live model calls; no model ranking or quality
claim. The two mock profiles are deterministic selection/reordering fixtures.
Their different outputs demonstrate validation and comparison, not general
free-form drafting. Section 12 still requires a supplied internal rating;
section 14 still words only the CA's stated position.

## API and invariants

- `GET /models`: configuration registry, route metadata, enabled/runnable states,
  disabled reason and offline estimate. Returns environment variable names only,
  never key values; it performs no provider discovery/network call.
- `POST /cases/{case_id}/model`: `actor`, CA `role`, `model_id` and
  `expected_model_id`. Draft-only, with optimistic conflict detection. Does not
  change saved sections or their evidence fingerprints.
- First-draft and explicit redraft requests accept optional `model_id`. Omission
  uses the current case default; an override does not change that default.
  Every generated draft records the concrete provider model in `model_version`
  and the registry entry snapshot/ID in its metadata. Human wording revisions
  retain their base model provenance. Typed chat continues to record its own
  B24 operation model; this task's picker controls first drafts and redrafts.
- `POST /cases/{case_id}/sections/{section_id}/compare`: draft options plus
  two distinct `model_ids`, `expected_draft_id` (nullable for first drafts),
  `expected_revision` and `expected_input_fingerprint`. CA/Draft guards and
  dependency/source/template checks match drafting. Unknown, disabled or live
  models fail closed; request-supplied budget fields are rejected.

Comparison holds one SQLite write transaction, reruns preparation over the same
current inputs and verifies matching full source and exact prompt hashes. It
reuses the first run's Python computation for the second model, then checks exact
table and computed-metric values/IDs. It returns neither output if inputs diverge.
Evidence indexes and computation records persist for source resolution; no
DraftVersion, citation-to-preview, confirmation, case position, approval pointer
or working-section version is written. Normal readiness refresh can reflect
already changed evidence. Preview UUIDs are not persisted draft IDs and cannot
be adopted/confirmed/downloaded via the saved-draft routes. Use explicit redraft
after review; this also rechecks current evidence and revision tokens.

Both models receive the same prompt, reviewed candidate claims and source excerpts.
Computed/inherited content and protected CA position remain server-owned. Rejected
claims never enter displayed text. Saved sources retain document/page or explicit
CA-input identity, public URL/retrieval date, and synthetic/proxy labels.

## Measurement definitions

Citation coverage = displayed claims with source references or explicit human/case
input divided by all displayed claims. No claims means N/A, not 100%. This is
reference coverage, not semantic source verification. Typed assertions remain
labelled as unverified CA input. Rejection count counts each invalid returned row
before gaps are deduplicated; omitted claims and malformed response are separate
fields. Gap markers are the actual merged named gaps on each preview. Latency is
elapsed local provider response/validation time; excludes intake, preparation,
computation and rendering, and is not a hosted model benchmark. Estimated cost is
US$0 for mock fixtures; live costs are unknown/blocked, not displayed as free.

Table equality compares complete structured Python tables, including operands'
value references and gaps. The response also compares computed metric snapshots;
section 10 uses metrics even when its table count is zero. Zero tables is explicitly
shown as none, not proof of numerical coverage. Shared hashes make comparison
inputs reviewable; they are not a production audit guarantee.

## Offline review walkthrough

Start the local demo as described in `setup.md` and load its saved tranches.
Choose Mock B as the case default; create a first draft and inspect the recorded
model. Choose Mock A as the section override and redraft: a new version is appended
and the case default remains Mock B. Earlier wording and model IDs remain visible
in version history. Saving a default alone preserves confirmations.

On section 1, compare Mock A and Mock B. Review reversed supported claim order,
Mock B's one rejected fixture claim, citations, gaps, latency and zero cost. On
sections 2/13, verify identical nonempty tables; on section 10, verify identical
computed metrics. Confirm a section, compare again, and check that its confirmation
and saved text remain. Ingest the late valuation: reload current section inputs,
compare again, and verify the old saved draft remains Stale until explicit redraft.
On section 14, supply the human position; comparison must not save that position.
Try a locked workflow state: selection/compare controls and API mutations block.

The automated tests block sockets and DNS. Frontend checks render real API preview
snapshots as static HTML and verify labels/escaping and disabled actions. Interactive
keyboard, responsive layout and source navigation still need manual review; static
rendering is not browser interaction acceptance.
