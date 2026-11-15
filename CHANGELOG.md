# Change log

Changes made to the WB Credit prototype after the first commit of 14 Nov 2026 ("WB Credit prototype, 14 Nov 2026"). Newest first. Each entry names the pull request that put it on `main`.

The project is still a prototype for demonstration. Nothing here connects it to a bank system.

## How to read this

- **Added** is a new capability. **Changed** alters something that was there. **Fixed** corrects a fault.
- "Not covered" lists what an entry leaves out, so nobody assumes more than was built.
- Tests: every entry was merged with the back-end tests passing. Entries that say "full run" include the tests marked slow.

---

## 15 Nov 2026

### Review threads, Word round trip, preview, Credit Assistant panel ([#8](https://github.com/Xyyuotto470138/wb_credit_new/pull/8))

**Added**
- **Comment threads between roles** (enhancement plan rank 7, first part). On each section, either signed-in role opens a thread about the whole section or one part of it, with the words referred to. Either role replies, resolves it with a written conclusion, and can reopen it. Threads change nothing in the ES and are open at every stage, including while the paper is with the reviewer. The papers list shows open comments.
- **Edit in Word and bring the wording back** (rank 8, first version). The Word export now marks every drafted paragraph with a bookmark. "Upload edited Word ES" on the Full ES page compares an edited copy with the sections as they stand and shows each changed paragraph as tracked changes. The analyst ticks the wording to take; it is saved as a new version of its section. Comments left in Word can be brought in as comment threads.
- **Preview.** The whole ES on one read-only page, with print or save as PDF. Reached from the Full ES page and from the submit page.

**Fixed**
- **The Credit Assistant panel could not be opened again after it was closed.** Its switch sits at the right end of the top bar, which had grown too wide and pushed the switch off the screen. The top bar now wraps on to a second line, and closing the panel leaves a "Credit Assistant" tab on the right edge that opens it again.

**Not covered**
- Rank 7: the assistant proposing a tracked change from a thread's conclusion; comments anchored to an exact sentence or cell; an RM role.
- Rank 8: tables are not read back, so a table edited in Word is ignored (the screen says so). A paragraph whose figures were changed is shown and never taken. Files exported before this change carry no markers and cannot be matched.
- The preview shows the ES as it appears in the app, not the Word layout.

Tests: full run, 602 passed. New: `tests/test_threads.py`, `tests/test_roundtrip.py`.

### New papers draft live; GPT and other models can be connected ([#7](https://github.com/Xyyuotto470138/wb_credit_new/pull/7))

**Fixed**
- **A paper started with "+ New paper" could not be drafted live.** It was left on the mock model, which the drafting engine cannot call. New papers now use the same drafting model as the saved FIG demo paper.

**Added**
- **A live route for GPT and other chat-completions models.** GPT direct at OpenAI, or another model through OpenRouter, with the same gate (`--live`), checks and cost ledger as the Claude route.
- **`WB_CREDIT_MODEL` in `.env`** names the model that live calls use in place of a paper's own. Papers on the mock provider are not redirected. The steps are in `.env.example`.
- `openai` added to `backend/requirements.txt`.

**Not covered**
- No real OpenAI call has been made. The GPT entries in `config/models.yaml` stay switched off until their model name and prices are confirmed.
- The prompts and checks were tuned on Claude. Other models are connected, not tuned.

Tests: 578 passed (slow tests left out). New: `tests/test_openai_route.py`.

### Files the app cannot classify are shown, and the analyst says what they are ([#6](https://github.com/Xyyuotto470138/wb_credit_new/pull/6))

**Fixed**
- **An uploaded file that the app could not recognise disappeared.** The app recognises a file only when its title or file name contains the document type and it carries a date. Any other file was stored and put on hold, and the workbench showed held files nowhere.

**Added**
- **"Files need your input" on the Inputs screen.** Each held file is listed with the reason in plain words. The analyst picks the document type and date and saves, or sets the file aside as not for this paper.
- A file given a later date than the one already held for its type becomes the current version. The Inputs screen then marks the drafted sections it affects as "Update required" and links to What changed.

**Not covered**
- The app still does not work out the document type by itself.
- A file with no readable text (for example a scan) stays held.
- Proposed updates on What changed need live model calls.

Tests: 574 passed (slow tests left out). New: `tests/test_held_files.py`.

### Delete a paper ([#5](https://github.com/Xyyuotto470138/wb_credit_new/pull/5))

**Added**
- **Delete on the papers list**, for the maker, on papers still in drafting. It asks for confirmation. A submitted paper and the two built-in demo papers cannot be deleted.

**Not covered**
- Delete removes the paper from every list; it does not erase its records, which stay in the database with who deleted it and when. There is no restore on the screens.

Tests: 572 passed (slow tests left out).

### Lending type ([#4](https://github.com/Xyyuotto470138/wb_credit_new/pull/4))

**Added**
- **Lending type on a new paper**, chosen from nine types in `config/lending_types.yaml`: property / IPRE, data centre, subscription line, NAV / fund-level, infrastructure / utilities / project, general corporate, working capital, contract / project-related, corporate card / programme.
- **The type's focus is given to the drafting model with every section**, with the instruction to leave out, or list as a gap, any point the documents do not cover.
- The lending type is shown in the papers list. Papers without one draft exactly as before.

**Not covered**
- The focus changes emphasis only. Every lending type still uses the FIG template, its calculated tables and its document checklist.
- No live draft was run, so the effect on the wording is not measured.

Tests: 571 passed (slow tests left out). New: `tests/test_lending_type.py`.

### Two-field new paper form; the ES template in the checklist ([#3](https://github.com/Xyyuotto470138/wb_credit_new/pull/3))

**Changed**
- **The New paper form asks only for the borrower name and the type**, "New to bank" or "Annual review". The other case facts take the standard values of a FIG REIT paper, the same as both demo papers.
- The two paper types read as "New to bank" and "Annual review" in the papers list and the top bar (they read "New" and "Renewal" before).

**Added**
- **An "Executive summary template" row at the top of the Documents panel**, showing the template in use, its version and a download link. It is read only.

### Papers landing page, new papers, a paper waiting for the checker ([#2](https://github.com/Xyyuotto470138/wb_credit_new/pull/2))

**Changed**
- **Sign-in lands on the papers list** instead of opening a paper. The maker sees every paper; the checker opens on "Waiting for my review".

**Added**
- **"+ New paper"** for the maker (`POST /papers`).
- **`scripts/demo/serve.sh --keppel --submitted`** confirms every section of the Keppel REIT paper and submits it at start-up, so the checker has a paper waiting. `scripts/demo/submit_for_review.py` does the same against a running back end.
- The scan folder card is hidden for a paper that has no prepared folder.

### Sign-in, one checklist panel, business unit picker ([#1](https://github.com/Xyyuotto470138/wb_credit_new/pull/1))

**Added**
- **A sign-in page** with the UOB logo. It checks made-up demo accounts in `config/demo_users.yaml`: `demo.analyst` (maker) and `demo.head` (checker). A sign-out link sits in the footer.
- **The role is fixed to the signed-in account.** The "Viewing as" switch is gone; to act in the other role, sign out and sign in with that account.
- **A business unit picker** (FIG, CBK, CMB) in the top bar. It filters the papers list. Only FIG is set up.

**Changed**
- **The checklist's "Uploaded" and "Still missing" panels became one Documents panel**, with groups: required and outstanding, received, can be generated, suggested, does not apply (each with the rule it fails), and public sources.
- The scan folder card says what it does.

**Not covered**
- The sign-in sets the role on the screens only. The back end does not check who is calling it, and the demo passwords are kept in plain text. It is a demonstration control, not access control.

---

## Still open

From `docs/enhancement_plan.md`:

- **Rank 7, second part:** the live Credit Assistant, and a tracked change proposed from a thread's conclusion.
- **Rank 8, remainder:** reading tables back from an ES edited in Word; turning new tables and images into analyst added content.
- **Rank 9:** calculated tables described in configuration. Needs a decision on which tables each lending type requires.
- **Rank 10:** uploading a revised template and adapting the structure. Needs a decision on the kind of template change expected.

Other limits are listed under "What it does not do" in the [README](README.md).

## Things that may surprise you

- **Older saved databases are upgraded at start-up.** New fields (`lending_type`, `deleted_at`, `deleted_by`) and the comment threads table are added automatically; no data is removed.
- **The project's own screenshot and video scripts** (`scripts/screens/`, `scripts/demo/record_*.mjs`) were written before the sign-in page and the new checklist. They stop at the sign-in page and need a sign-in step before they run again.
