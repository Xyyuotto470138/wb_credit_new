# WB Credit

A working prototype that helps a credit analyst prepare an Executive Summary (ES) for a wholesale credit paper. It reads the deal papers and public documents, drafts each ES section with its sources, calculates the tables in code, and exports the ES into the Word template. The analyst reviews, edits and confirms every section. A reviewer checks it.

**Status, 14 Nov 2026: prototype for demonstration.** It runs on one laptop with synthetic deal papers and saved public documents. It is not connected to any bank system, has no login, and has not been validated for production use. Drafts are for analyst review. Credit decisions are made by the approving officers.

## What it can do today

Everything below works in the app now and can be seen on the saved demo paper with no API key.

| Capability | What you see | Screen |
|---|---|---|
| Files and checklist | Add files by upload or folder scan. The app classifies each one, shows what is received, what is still missing and which sections can start. | [live_01](docs/screens/live_01_inputs.png) |
| Section drafting with sources | Each of the 14 ES sections is drafted by the model from the papers. Every statement carries a numbered citation that opens the source page. A statement without a source is withheld and shown as a gap. | [live_04](docs/screens/live_04_section_4.png) |
| Tables calculated in code | Lease expiry, top tenants, debt service, stress cases, covenant headroom and loan to value are calculated by Python. Figures copied from financial statements are checked in Python against the cited line. The model never writes a calculated figure. | [live_06](docs/screens/live_06_section_10.png) |
| Edit, confirm, version history | The analyst edits wording, redrafts a section, and confirms it. Every change is a new saved version. | [live_05](docs/screens/live_05_section_8.png) |
| Analyst added content | Paste a table from Excel or Word, add a screenshot or a paragraph anywhere in a section. It is labelled as analyst added, kept across redrafts and exported in place. | [enh_02](docs/screens/enh_02_section_with_added_content.png) |
| Model sense check | For tables that code does not check, the model suggests what a person should recheck. It never changes a value and is not a pass. | [enh_03](docs/screens/enh_03_sense_check.png) |
| Several papers | A papers list with stage, whose turn it is and attention items, and a paper switcher. | [enh_06](docs/screens/enh_06_papers_list.png) |
| Maker and checker | The maker submits. The checker marks sections reviewed or raises a query and returns them. The maker changes only what was returned and resubmits. Each step is recorded in a review trail. | [enh_12](docs/screens/enh_12_checker_review_with_query.png) |
| New information update | When a revised document replaces an earlier one, a "What changed" page lists the affected sections. For each, the system proposes an update: figures before and after, wording as tracked changes. The maker accepts or keeps each part and applies it. | [enh_20](docs/screens/enh_20_what_changed.png), [enh_21](docs/screens/enh_21_proposal_figures.png) |
| Comments between roles | Either role opens a comment thread on a section or one part of it, replies, and resolves it with a conclusion. Comments never change the ES. | |
| Edit in Word and bring it back | Export the ES, edit the wording in Word, upload it. Changed paragraphs are shown as tracked changes and the analyst chooses which to take. Changed figures are never taken. Word comments can become comment threads. | |
| Word export | The ES is written into the Word template with tables, images, citations and a list of open items. | [ES as drafted](docs/demo/Keppel_REIT_ES_live.pdf), [ES after the update](docs/demo/Keppel_REIT_ES_after_update.pdf) |

## What it does not do

- **No real login or permissions.** The sign-in page checks made-up demo accounts and sets the role on the screens only. The back end does not check who is calling it.
- **No bank systems.** Limits, ratings and account conduct come from synthetic files, not from a master system.
- **One team, one template.** The specification driven path covers the FIG template for a REIT borrower. The second demo paper runs on an earlier path with fixed mock wording.
- **Live drafting needs your own key and costs money.** Without a key you can open, edit, confirm, review and export the saved paper, but not draft new wording.
- **The Credit Assistant panel is a mock** on both papers. It takes typed notes, not open questions.
- **Tracked changes are on screen only.** The Word export holds the applied text.
- **Not built yet:** comments anchored to an exact sentence or cell, reading tables back from an ES edited offline, calculated tables defined in configuration, template upload. See [docs/enhancement_plan.md](docs/enhancement_plan.md).

## Run it

### 1. Requirements

- macOS or Linux, Python 3.12, Node.js 20 or later.
- Optional: LibreOffice (to render the Word ES to PDF), Google Chrome (to regenerate screenshots).

### 2. Install (once)

```bash
python3.12 -m venv .venv
```

```bash
.venv/bin/python -m pip install -r backend/requirements.txt -r requirements-test.txt
```

```bash
npm --prefix frontend install
```

### 3. Open the saved Keppel REIT paper (recommended, no key, no cost)

The repository carries a packed copy of a paper whose 13 applicable sections were drafted with the live model. Restore it once:

```bash
.venv/bin/python scripts/demo/saved_case.py restore
```

Then start the app:

```bash
scripts/demo/serve.sh --keppel
```

Open http://127.0.0.1:15300. Stop with Ctrl+C. The first start takes about a minute while it prepares the second paper.

What to try:

1. **Papers** in the top bar: two papers, Keppel REIT (new to bank) and ESR-REIT (renewal).
2. **Full ES** in the left rail: the whole paper. Open a section and click a citation number to see the source page.
3. In a section: **Edit text**, **Confirm section**, **History**, and the **+** marks to paste a table or add a screenshot.
4. **Export ES to Word** on the Full ES page.
5. Switch the role in the top bar to **Credit Head** and open **Review**.

### 4. See the new information update

To see the same paper after four revised documents arrived and every affected section was updated:

```bash
.venv/bin/python scripts/demo/saved_case.py restore --after-update --replace
```

```bash
scripts/demo/serve.sh --keppel
```

Open **What changed** in the left rail. `--replace` moves the case that is there aside under `runtime/demo_live/`; it does not delete it. Run the restore command in step 3 with `--replace` to go back.

To run the update yourself you need live calls (step 6): restore the first case, open **Files**, scan the "Late update" folder, then open **What changed**.

### Sign in, and give the checker a paper to review

The app opens on a sign-in page. The demo accounts are in [config/demo_users.yaml](config/demo_users.yaml): `demo.analyst` (maker) and `demo.head` (checker). They are made-up accounts; the prototype is not connected to a staff directory. After sign-in the maker sees the papers list and can open a paper or start a new one; the checker sees the papers waiting for review.

Both demo papers start in drafting, so the checker's list is empty. To start with the Keppel REIT paper already submitted for review:

```bash
scripts/demo/serve.sh --keppel --submitted
```

This confirms every section as the maker and submits the paper. It stays submitted on later starts; run the restore command in step 3 with `--replace` to go back to the drafting state.

### 5. Start from an empty case (mock provider, no key)

```bash
scripts/demo/serve.sh --fresh
```

This opens the ESR-REIT renewal with nothing loaded. Scan the three tranche folders on the Files screen, generate the spread, and start drafting. Wording on this path is fixed mock text, so it shows the workflow, not drafting quality. Add `--prepared` to start with files loaded and sections drafted.

### 6. Live model calls (optional, costs money)

```bash
cp .env.example .env
```

Put your Anthropic API key in `.env` (see [.env.example](.env.example) for what each entry is for). Then:

```bash
scripts/demo/serve.sh --keppel --live
```

Drafting a section, an update proposal and a sense check now call the model. Rough cost: USD 0.50 to 1.20 per section call, USD 15 to 20 for a whole ES. Every call is recorded in `runtime/costs/ledger.jsonl`. Without `--live` the app never makes a paid call, even with a key present.

### 7. Tests

All tests are offline and use a stub in place of the model.

```bash
scripts/run_tests.sh --all
```

```bash
npm --prefix frontend test
```

`scripts/run_tests.sh` without `--all` skips the slower end to end tests. On a 14 core laptop the full run takes about four minutes.

## How it is built

- **Back end:** Python, FastAPI, SQLite ([backend/app](backend/app)). `es2/` is the specification driven ES engine: drafting, calculations, figure checks, analyst content, sense check, updates and Word export.
- **Front end:** React and Vite ([frontend/src/workbench](frontend/src/workbench)).
- **ES specification:** one file, [config/teams/fig_re/es_spec.yaml](config/teams/fig_re/es_spec.yaml), defines every section and part: who fills it (model, Python, case input, analyst), its columns and its guidance. The Word template, the prompts, the screen layout and the export all read it.
- **Lending types:** [config/lending_types.yaml](config/lending_types.yaml) lists the lending types offered when a paper is started and what the drafting model is told to emphasise for each. It sets emphasis only; the template, the calculated tables and the document checklist stay those of the FIG specification.
- **Model:** Claude, called directly at Anthropic, by default. A GPT model direct at OpenAI, or another model through OpenRouter, can be used instead: enable its entry in [config/models.yaml](config/models.yaml) and set its key and `WB_CREDIT_MODEL` in `.env` ([.env.example](.env.example) has the steps). The prompts and checks were tuned on Claude; other models are connected, not tuned.

Rules the build follows:

- Python does arithmetic. Models do judgement.
- Every drafted statement carries its source. A missing document is a gap, never a fact.
- Anything a model proposes is a suggestion the analyst accepts or rejects.
- Synthetic files are labelled SYNTHETIC DEMO DATA.

## Repository map

| Path | What it holds |
|---|---|
| `backend/` | API, services, ES engine, export |
| `frontend/` | The web app and its tests |
| `config/` | Team configuration, ES specification, model registry |
| `templates/` | The Word ES templates. Version 1.0 is active. |
| `demo/synthetic_keppel/` | Fictional deal papers for the Keppel REIT case, including `late_update/` |
| `demo/synthetic/` | Fictional deal papers for the ESR-REIT renewal |
| `demo/public_pack/` | Saved public documents of the two borrowers (annual reports, results) |
| `demo/saved_cases/` | Packed copies of the saved Keppel paper, restored by `scripts/demo/saved_case.py` |
| `scripts/demo/` | Start the app, restore a saved case, run live drafting |
| `scripts/screens/` | Regenerate the screenshot pack |
| `tests/` | Back end tests |
| `docs/` | Documentation, screens and demo outputs |
| `runtime/` | Created when the app runs. Case data, cost ledger. Not in git. |

## Documents

| Read this | For |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | What changed after the first commit, newest first |
| [WB_Credit_PROJECT.md](WB_Credit_PROJECT.md) | Requirements |
| [docs/es_spec.md](docs/es_spec.md) | How the ES engine works, part by part, and its limits |
| [docs/new_information_spec.md](docs/new_information_spec.md) | The update after new documents |
| [docs/enhancement_plan.md](docs/enhancement_plan.md) | What is built and what is next |
| [docs/cost_log.md](docs/cost_log.md) | Every live model call made so far and its cost |
| [docs/screens/](docs/screens) | Screens. `live_*` and `enh_*` are current; numbered files are an earlier pack. |
| [docs/history/](docs/history) | Build plan and build log, in date order |

The other files in `docs/` describe individual back end parts from the first build phase (intake, readiness, evidence, workflow, exports). They are accurate for the back end but describe earlier screens.

## Data

- The two borrowers are real listed trusts, described only from their public documents saved in `demo/public_pack/`.
- Every deal paper, facility, tenant, rent, valuation, rating and projection is fictional and labelled SYNTHETIC DEMO DATA. No real lending relationship is implied and no real bank data is used.
- Do not load real customer or bank internal documents into this prototype.
