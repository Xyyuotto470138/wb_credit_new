# Draft template exports (B18)

`backend/app/exports/` fills a copy of the immutable, pinned Word package. It never creates a replacement ES layout or edits `templates/`. B18 produces **drafts only**; B25 supplies submission checks and B16 supplies locked workflow snapshots; approved Word export acceptance remains B19. The full-draft dashboard download controls remain B15.

## Review and download

1. `GET /cases/{case_id}/exports/preview` returns all 14 section states, exact saved drafts, named mapping/input gaps, source register, request groups, template ID/hash/parser/mapping versions, filled-target manifest and a `preview_token`.
2. `POST /cases/{case_id}/exports` with `{"actor":"demo-ca","role":"CA","expected_preview_token":"..."}` creates an immutable `ESVersion` (purpose `export`) and `ExportArtifact`. Changed inputs/versions reject the token with 409. Only a working Draft or recorded Returned to CA case can create this export; no confirmations, workflow state or active ES pointer change.
3. Use the returned artifact ID with `/exports/{id}/bundle.zip` to download `draft.docx`, `manifest.json` and `request-list.txt`. The companion metadata is part of the export: it holds public URLs/retrieval dates, exact source locators, complete saved draft wording, computed IDs, dependency versions and gap details that have no template slot.

Individual routes are `/{id}/document.docx`, `/{id}/manifest`, `/{id}/request-list.txt`; `GET /exports` lists saved exports. The existing `/cases/{case_id}/request-list` remains the current, unsnapshotted request list. Both group by RM/client/internal team, with rationale, affected sections, public-search outcome, partial/public evidence, generation offers and mandatory dismissals. Export never initiates a search or provider call. Optional dismissed requests stay suppressed; mandatory dismissal does not waive a gap.

The prototype role field is not authentication. Invalid request roles/purposes/blank actors are rejected. Unknown case returns 404, unknown/cross-case artifact 422, hash/storage/preview/workflow conflicts 409, missing persistence 503. Failed database transactions roll back; content-addressed blobs written before a rollback can remain unreferenced, matching template storage behavior.

## Mapping and evidence boundaries

The B22 parse report resolves all XML locations before mutation. Mapped values are cleared first, including example entities, sample totals, dates and checkboxes. Fixed headings, business row labels, table properties, styles, section breaks, headers/footers and package parts outside `word/document.xml` remain unchanged. Paragraph and run styling comes from the fill point; placeholder italics remain italic. Repeated records clone styled detail rows, preserving separate headers/totals; facility columns share the template's original width, retaining the key-term width and cell properties. Excessive facility counts produce a named layout gap and retain all terms in narrative rather than dropping facilities.

Supported adapters fill exposure and Python totals (explicit SGD million units and existing maturity), facility terms, projected NPI/interest/DSCR for every supplied year, financial disclosures/regulatory headroom, B09 group revenue/NPI/assets scaled to S$m in Python, supplied internal rating, conduct and contractual covenants. Other supported claims remain verbatim in existing narrative/remarks cells. Section 11 uses its existing risk table because it has no narrative placeholder. Repeated dependency findings already represented elsewhere are cross-referenced to their pinned sections; exact original section text remains in metadata. Unsupported field semantics and unavailable values stay named field gaps. The task 0022 adapters below extend table coverage. No inferred chart, ownership sum, rating, security perfection or checkbox decision is created.

The copied template, not code, supplies the layout. Column/row adapters operate only on B22's unambiguously matched anchor shapes and row labels. Unknown/missing/ambiguous mappings are exposed in preview; Word creation is conservatively blocked when parsing has gaps because unmapped sample values cannot safely be delivered. A missing heading is never synthesized or silently omitted. N/A reasons and absent section drafts remain explicit. No complete/final export endpoint exists.

Every rendered assertion retains numbered source markers and proxy/CA-edit attribution. The Sources appendix resolves document/page and public/synthetic labels, URLs and retrieval dates; printed/normalized-page details remain in the manifest. Unfilled cells show `[Gap]`, named by their table/row/column in the manifest. Draft provenance labels use their saved confirmation state; a later CA confirmation does not rewrite history. Stale exports show **STALE DRAFT**, preserve prior wording/values and record source currentness; they do not imply current confirmation. The CA position stays verbatim and draft sign-off remains pending.

Mixed section template pins reject export. With consistent existing drafts, their pinned template wins over later activation; with no drafts, the active template is used. Downloads retrieve stored hash-verified bytes, so later edits, input changes or template activation cannot regenerate history differently. B18 checks draft claims against saved spans, case/config/section ownership, resolved source hashes and immutable computed values/tables before creating a snapshot. The additive `export_artifact` table has repository and SQLite append-only protection; existing schema/configuration pins require no migration rewrite.

## Offline reproduction and visual QA

```sh
LLM_PROVIDER=mock PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/export_demo.py --output runtime/b18/standalone
LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_exports.py -q -p no:cacheprovider --basetemp=runtime/pytest-b18
```

The standalone script uses only the saved public/synthetic packs, existing mock drafts and B10 computations. It leaves B09 generation explicit; its absent rows remain gaps. Tests separately exercise an actual validated B09 spread. Use a new output folder for each standalone run; the script never resets an existing case.

Tests generate `runtime/b18/demo/` and `runtime/b18/fixtures/{zero,repeat-1,repeat-12}.docx`. Render the owner template, full demo, and repeat fixtures with the documents skill's `render_docx.py --emit_pdf`, using the bundled runtime Python/LibreOffice, then inspect **every page**. Repeat fixtures contain synthetic values, a long paragraph and three facility columns. No renderer is added to runtime dependencies; automatic Word export does not launch LibreOffice.

The exported copy adds a one-point, keep-with-next paragraph before each leading nested table. This narrowly scoped flow correction prevents LibreOffice from dropping the table at a wrapper/page boundary; the same problem is reproducible in the untouched template. Table grids, borders, styles and owner package parts stay intact.

Pagination can grow with sourced text and repeated records. Existing template page breaks may leave white space; they are retained. Mapping completeness and passing tests do not prove a future template's rendering or live-bank fit. Record per-page visual acceptance separately in the task reply/build state.

## Task 0022 presentation contract

New exports use `template-export-v2`. One status line below the title identifies draft, template version, mock/live text and synthetic sources; section readiness stays in the app/manifest. A stale snapshot adds a document-level stale warning. Body citations are numbered `[1]` markers. The Sources appendix includes every saved evidence entry, document/page/revision, public or synthetic label, saved confirmation, URL and retrieval date, or full CA-input provenance. Historical stored exports are unchanged.

Additional bounded adapters fill business/listing/sponsor/trustee, portfolio summary, substantial holders, management/stakeholders, all supplied facility terms, insurance/security, lease expiry/tenant shares and external ratings. They decode reviewed saved claim formats, never raw document text. A changed or CA-edited claim stays verbatim with attribution when it cannot be safely decoded. Manager interests are distinguished from REIT units; overlapping deemed holdings are never summed. Remaining numeric gaps mean no validated matching value, even if an untranscribed source may contain one. In particular, B09 supplies only its validated core rows; NAV, distributions, investment properties and borrowings do not get inferred from differently defined figures.

Section 9 uses the template's primary/secondary slots, projected NPI/interest/DSCR plus cash/principal/debt service, historical Group NPI/reported ICR where available, and the property lease/tenant tables. Historical Group figures and the synthetic property forecast remain explicitly separate. Section 11 contains actual sourced risk/mitigant rows, including current saved LTV headroom, tenant concentration and regulatory headroom. Detailed source extracts, app readiness and duplicated dependency claims are not printed as narrative/risk rows. Exact draft content and detailed gaps remain in the companion manifest.

Watchlist/SM applicability is never inferred from absence. The demo CAS explicitly leaves classification open, so the sample retains that gap. A CA claim stating `The borrower is not classified as Watchlist or Special Mention.` resolves the conditional classification table to **Not applicable**; classification, rating and approval decisions are not invented by the exporter.

Reproduce the reviewed three-tranche sample including the saved B09 spread:

```sh
LLM_PROVIDER=mock PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/export_demo.py --output runtime/0022/reproduction --with-spread
```

`--with-spread` explicitly confirms this saved public demo pack and runs the same reviewed mock spread through the existing validator. It is an offline fixture workflow, not general automatic confirmation or extraction. Use a fresh runtime directory. The sample PDF is `docs/gate2_export_sample.pdf`; all 14 template sections and all 43 tables remain, plus the requested Sources appendix. Renderer is review tooling only, with no new application dependency.

## Task 0023 presentation rules

Export v3 rounds only the rendered paper: S$m amounts to two decimals,
percentages (including utilisation percentages) to one, and coverage ratios to
two. Monetary utilisation stays in S$m; counts/days remain integers. DPU retains
its disclosed three-decimal cents precision and NAV its two-decimal S$ precision.
The exact saved drafts, operands, ComputedValues and source records remain in the
immutable manifest. Human dates and the Credit Analyst role replace technical
actor/message IDs and timestamps in the paper, while the manifest retains them.

The CAS builder now supplies fictional Pass / no Watchlist or Special Mention /
current DPD 0. Its hash-pinned claim supports the classification N/A cells and the
DPD answer; absence of that claim cannot imply a classification. Public annual
report claims support the ESR Group and Singapore cover fields. The owner template
is read only. Inserted runs explicitly use the body font read from the template's
Normal style or document defaults, including gap and checkbox cells.

The reviewed financial bindings cover FY2024/FY2025 distribution, DPU, investment
properties, unitholders' funds and NAV, plus annual and September 2026 capital
metrics. The quarterly update also supplies YTD revenue/NPI/distributable income,
NAV, occupancy and WALE. All bindings check the saved file hash, entity, source
period, original PDF page, quote and numeric token before persisting a value.
Investment properties exclude assets held for divestment; total borrowings use
reported gross debt. Comparative DPU/NAV reflect the disclosed unit consolidation.
The unused third annual column is labelled Not used; unavailable interim fields
remain gaps, since the business update is not a complete interim balance sheet.
The new public-news section-10 association provides partial context only and does
not satisfy a mandatory financial-statement requirement.

Section 10 uses four trend sentences, with a short basis note; section 13 uses
three sentences and keeps the adverse conduct events. Section 9 shows `n.m.` in
the bullet-maturity years and explains that the Python computation assumes cash
repayment and no refinancing receipt. The 2028 coverage ratio remains visible;
no refinancing-adjusted capacity or funding commitment is assumed.

Reproduce the sample with a fresh `runtime/` directory:

```sh
LLM_PROVIDER=mock PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/export_demo.py --with-spread --output runtime/0023/reproduce
```

The script supplies the fictional CA's exact conditional-support wording and a
fixed 10 November 2026 drafting date. This clock is confined to the standalone
demo; normal application drafting records the actual date. The position is input,
not a generated credit recommendation. Render the resulting `draft.docx` with the
documents skill's bundled renderer and inspect every page. No network calls or
new application dependencies are needed.

A page-flow anchor before section 10 prevents LibreOffice from losing the nested
financial grid at a page boundary. It changes pagination only; all fourteen
heading elements, forty-three tables and package parts outside `document.xml`
remain intact. The delivered PDF was checked against the DOCX cell values as well
as visually, since valid OOXML alone did not reveal this renderer defect.
