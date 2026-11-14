# Template registry, parser and comparison (B22)

The registry stores exact owner/uploaded DOCX bytes and an immutable parse report. The active version is the end of the append-only `TemplateActivation` chain. Each future draft/ES must pin its `TemplateVersion.id`; retrieve that version's bytes and report, never substitute the current active template. Template-filled draft export is implemented by B18; see `docs/exports.md`. B22 comparison, classification and IT change-list export are available at API level. Admin confirmation/activation and the admin screen remain B23.

`create_local_app()` seeds owner templates on explicit local startup under `runtime/gate1/templates/`, using the existing SQLite database. The factory `create_app()` remains side-effect free and accepts a separate `template_storage_root`. Only v0.1 was present for task 0011, with SHA-256 `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.

For a fresh registry, `TemplateRegistry.seed_owner_templates(team_id, project_root)` registers the configured default and newer matching owner files in numeric version order, preserving parents, and records bootstrap activations through the latest version. This operator-only bootstrap is authorized by task 0011. It is not exposed over HTTP. If active history already exists, restart preserves it: newly discovered owner files register as candidates for the future G3 workflow. A seeded template with gaps remains inspectable and active, but its report is incomplete; B18 must block complete/final export. Owner files are never edited.

All service writes run in the caller's transaction. Use `BEGIN IMMEDIATE` before registration/seeding to serialize deduplication and activation. The API and local startup do so. Content-addressed blobs are written exclusively; a rolled-back transaction may leave an unreferenced immutable blob, safe to reuse. No cleanup deletes historical versions. Identical team/display-version/bytes return the existing record; different bytes under an existing display version are rejected. A new display version may reuse identical bytes. Parsed records retain the parser version and mapping configuration hash even after configuration changes; re-registration never reparses old history.

## Mapping contract

`config/teams/fig/template.yaml` carries ordered table headers, complete seed row labels, physical cell spans, table kind, repetition policy and source policy. Optional schema fields preserve old case configuration snapshots unchanged. Core parsing uses configured section names and IDs, without FIG branching.

The actual v0.1 inventory has 14 numbered Heading 1 sections, 15 outer tables and 28 nested tables, 29 configured content-table anchors, 14 wrapper bindings, 19 narrative anchors, and 133 text fill points. It parses without mapping gaps. A gap-free parse confirms supported anchors only, not evidence completeness, calculations, visual fidelity or suitability for final export.

- `sections` always includes every canonical configured section, even when the source heading is absent, duplicated or renamed. Display text is retained; lookup normalizes case, whitespace, tabs and decorative ⓘ.
- `tables` recursively inventories physical cells once, with XML locations, row/cell indices, grid columns/spans, vertical merges and original text. `bindings` includes only uniquely matched headings/wrappers and tables. Ordered headers, row labels and configured cell spans must match; changed shapes are gaps, not inferred mappings.
- Mapped cells have unique keys, row labels, column-header context, roles and `requires_sourced_value`. Key/value first-row values, blanks, sample defaults and record cells are explicit targets. Merged cells retain their physical span rather than duplicate grid aliases. Header period fills remain separate fill points.
- `fill_points` identifies italic bracketed text across runs, FY periods, explicit date tokens and checkboxes. Each carries section/table/cell identity, occurrence, paragraph offsets and run-local spans. Effective italics include document defaults, paragraph/character style inheritance, base table styles and direct overrides. Conditional table-style italics produce a named manual-mapping gap. Nonitalic bracket text is retained as an unmapped gap. New or missing wrapper narrative anchors are gaps.
- Locations are zero-based XML child-index paths from `word/document.xml`'s body in the exact hash-pinned package. They are not page numbers and must not be used against different bytes. Text offsets are Unicode character indices. Styles, tables, headers and footers are never rewritten by this parser.
- Repeat policies describe future row/column growth, including facility columns and covenant rows. They do not clone rows, calculate totals or determine which data to use. B18 must keep fixed labels/totals/regulatory rows separate, fill only sourced values, clear sample defaults, and preserve all sections. Section 14 wording requires the CA's stated position; signoff requires actual human workflow events.

Template guidance is never evidence. Blank cells, instructions, sample borrowers, checked/unchecked boxes and numeric defaults cannot establish facts. B18 should display section/anchor-named parse gaps in the preview/manifest and block complete/final export when `complete` is false. Missing document evidence must remain a separately named input gap, never a finding.

Malformed, encrypted, macro-bearing, duplicate-part and oversized packages are rejected. XML declarations with entities/DTDs are rejected; no external relationships are resolved. Unsupported content controls, text boxes, tracked changes, embedded content and header/footer fill points produce named mapping gaps. Conditional formatting and physical pagination require manual review. Rendering and zero/one/many-row export fidelity are B18 acceptance work, not claimed here.

## HTTP API

These endpoints are prototype registry operations, not production entitlements. There is no activation endpoint. Upload, comparison and export never activate a candidate or update prompts/code.

| Method/path | Result |
|---|---|
| `GET /templates/{team_id}` | All immutable versions and parse reports |
| `GET /templates/{team_id}/active` | Active version, or null before bootstrap |
| `GET /templates/{team_id}/{version_id}` | Team-scoped historical version/report |
| `GET /templates/{team_id}/{version_id}/source` | Hash-verified exact DOCX bytes |
| `POST /templates/{team_id}?display_version=v0.2&filename=candidate.docx&parent_id=...` | Raw DOCX body; register/parse only, never activate |
| `POST /templates/{team_id}/{version_id}/compare?expected_active_id=...` | Persist a classified comparison against the current active version; optional expected ID rejects a stale baseline |
| `GET /templates/{team_id}/{version_id}/comparisons/{comparison_id}` | Immutable comparison snapshot as JSON |
| `GET /templates/{team_id}/{version_id}/comparisons/{comparison_id}/it-change-list` | Download UTF-8 prompt/code change list with before/after, reasons and files to review |

The source endpoint rejects corrupt, unavailable or out-of-storage bytes with 409. Unknown/cross-team versions return 404; invalid uploads return 422 (oversized streaming bodies: 413); missing injected persistence returns 503. Storage paths are internal local prototype metadata. `status: mapped` means a complete parse, not active status or admin approval; active status comes only from the activation chain.

Offline verification: `LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`. No model calls, external lookup, new dependencies or renderer are needed for the parser.

## Backend comparison and IT review (task 0025)

Register a candidate, call its `compare` route, then use the returned comparison
`id` to retrieve the JSON snapshot or download the IT list. `parent_id` describes
upload ancestry; the comparison baseline is always the current active template,
not an arbitrary parent. No active version returns 409; comparing the active
version to itself returns 422. A mismatched `expected_active_id` returns 409.
Unknown/cross-team candidates and mismatched comparison/candidate IDs return 404.

Comparison verifies both stored hashes and reparses both packages with the same
current configuration using the export parser. Historical parse maps are retained.
A parser/mapping revision since either registration produces an explicit code
review item. Each immutable `TemplateComparison` stores the candidate and baseline
IDs/hashes, classifier/parser/mapping versions, complete parse gaps, per-change
categories/reasons, exact before/after values, XML locations and suggested files
to review. New storage is additive; existing SQLite databases acquire the table
and update/delete protection through `create_database()`. Retry/concurrent calls
with identical inputs reuse the snapshot. A changed active version creates a new
snapshot; earlier comparisons and exports remain readable. Historical retrieval
does not revalidate source bytes; creation of a comparison always does.

The deterministic classifier uses expanded XML names, so ZIP timestamps,
compression, namespace prefixes and attribute serialization order are not changes.
It compares every package part without executing instructions, dereferencing
relationships, or calling a model. Matched unchanged XML siblings prevent a section
insertion from falsely reporting subsequent sections as changed. Each difference
has separate before/after locations, relative to `document/body` for document
content and the part root elsewhere. Unknown numbered headings are retained in
the shared parser inventory for attribution. Locations are not print pages.

- `formatting`: only allowlisted visual properties, including fonts, colours,
  spacing, borders and page dimensions. Text and structure are compared separately.
- `prompt`: a text edit inside an existing mapped narrative placeholder that stays
  bracketed, without a numeric/calculation instruction. IT reviews both prompt
  wording and the configured literal narrative anchor. Changed guidance can thus
  have prompt classification and mapping gaps; it always remains inactive.
- `code`: renamed table headers, new/removed columns, fields, tables or sections,
  changed labels/sample values, formula/numeric instructions, ambiguous structures,
  changed mapping-sensitive styles/italics, relationships and unsupported parts.
  A header rename needs review because export uses its exact configured header.
  Unsupported changes are not inferred to be harmless.

A mixed candidate inherits `code` over `prompt` over `formatting`. Identical XML
content returns `unchanged`, including when ZIP bytes differ. `formatting_only` is
true only for visual changes with complete baseline and candidate maps;
`requires_it` also remains true for inherited mapping gaps. All comparisons report
`activation_available: false`. There is no partial activation or automatic prompt,
configuration or code edit. Future B23 must recheck the active ID, candidate hash,
current mapping and complete comparison before explicit admin confirmation.

The text export contains only prompt/code change items, with their full values,
reasons and suggested files, plus both templates' mapping gaps and provenance.
The JSON snapshot also includes formatting items. For binary package parts the
values are byte counts and SHA-256 hashes; exact bytes remain downloadable through
the version source endpoint. For unsupported XML parts the values include XML.
Formatting-only/unchanged comparisons export an explicit empty IT item list.
Treat all before/after template strings as untrusted display data in the future UI.

This is a conservative review aid, not semantic equivalence or visual acceptance.
Run splitting/rearrangement, ancillary settings/media edits and unsupported style
changes can require code review even when they appear visually similar. Generated,
labelled fixture copies cover all required variants and mixed changes without
editing `templates/`; no rendering, frontend change, paid call or new dependency
is involved in this backend task.

## Template v0.3 (12 Nov 2026)

The active FIG template is `templates/ES_Template_FIG_draft_v0.3.docx`. `scripts/build_template_v0_3.py` builds it from the owner's v0.2, which is read only: it keeps her section 1 to 4 edits and replaces her section 10 notes with the tables they ask for (major changes, segmental and geographic performance, an Analytics heading, cash flow base case, stress cases, assumptions, inter-company debts, FX risk checklist), with amounts in SGD'000. `scripts/map_template_v0_3.py` regenerated the changed and new table anchors in `config/teams/fig/template.yaml` from the file itself. v0.3 parses complete: 56 tables, 187 fill points, no gaps.

Export changes for v0.3: the exposure table's new limit cap column is a named gap; section 3 updates stay in the section narrative because the developments table was replaced by a Y/N matrix; the section 4 narrative goes into the Overview box; the section 10 financial table shows SGD thousands. New tables have no sourced values yet and export as named gaps.

Seeding registers every owner file in `templates/` in version order and activates the highest. v0.1 and v0.2 therefore appear in the registry as "review required" (they do not match the v0.3 mapping) and v0.3 is active. A newer owner file dropped into `templates/` before a fresh database is seeded would become active without a matching mapping; that is open for the template admin step.
