# Upload and folder intake (B04)

B04 persists versioned source documents. B05 refreshes expected inputs and section readiness after intake. Intake does not draft claims, create the B08 page index, resolve review flags, or change an ES/draft/approval snapshot. No model/search/network calls run during intake.

Configure persistence explicitly; app construction and `/health` still perform no database writes. The operator creates cases through `Repository` with a pinned configuration as documented in `setup.md`. The caller owns engine disposal; no background scanner starts.

```python
from pathlib import Path
from backend.app.database import create_database
from backend.app.main import create_app

Path('runtime').mkdir(exist_ok=True)
engine, sessions = create_database(Path('runtime/wb_credit.sqlite'))
app = create_app(
    sessions=sessions,
    storage_root=Path('runtime/documents'),
    intake_folders={'demo-tranche-1': Path('demo/synthetic/tranche_1').resolve()},
)
# Pass app to the application's ASGI host; engine.dispose() on shutdown.
```

API contract:

- `POST /cases/{case_id}/documents?filename=valuation.pdf`: raw file bytes, preferably `application/octet-stream`. Optional `metadata` query parameter is a URL-encoded JSON object. This avoids introducing `python-multipart`.
- `POST /cases/{case_id}/documents/scan`: JSON `{"folder_id":"demo-tranche-1","metadata_by_path":{}}`. Only operator-configured IDs are accepted; requests cannot select arbitrary local paths. Metadata keys are relative POSIX file paths within that folder.
- `GET /cases/{case_id}/documents`: all retained document versions with original provenance, review flags, reasons, and comparison IDs. No automatic current-document selection is implied.

Upload returns `{outcome, filename, document, explanations}`; scan returns a list of the same records. Outcomes are `created`, `duplicate`, or (for individual scan failures) `rejected`. A retained unreadable/unsupported file is `created` with `conflict_status: pending` and `intake.status: manual_review`; it is not usable classified evidence. Empty/oversize/path-invalid uploads return 422 (streaming uploads above 25 MiB return 413). Unknown cases return 404; an app without injected persistence returns 503. Successful creates and duplicates return 200.

Optional metadata: `catalogue_id` **or** configured `suggestion_id`, `entity`, `period`, `synthetic`, and `scope`. Example:

```json
{"catalogue_id":9,"entity":"ESR-REIT","period":"2026-10-31","synthetic":true,"scope":"16 Tai Seng Street"}
```

Hints are preserved in `document.intake.supplied`; they are not CA confirmation. Unknown configured types/suggestions are rejected. The classifier uses the case's pinned catalogue names, filename/title, explicit borrower labels/header cells and bounded primary period cues. It records observed metadata separately and flags supplied/detected disagreements. An entity mention in narrative is not identity evidence. An external/unspecified rating cannot silently become an internal rating. Unknown/ambiguous classification stays pending. Classification is deterministic and conservative; it is not general document understanding.

PDF previews inspect up to three pages; XLSX previews inspect up to three worksheets/30 rows/20 columns and use cached values only. DOCX text is read from its XML and headers; EML reads its plain-text body; TXT/CSV accept UTF-8. No macros, links, attachments, OCR or formulas are executed. Only bounded text is used for classification. Complex/unreadable/scanned files retain their original bytes and a named manual-review reason. XML/archive limits protect Office preview parsing. Source-page retrieval/normalization remains B08.

Periods accept ISO dates, calendar years, `FY2025`, or `2026-Q3`. Years/FY/quarters compare by calendar end date; supply the actual period-end ISO date for non-calendar fiscal years. For a valuation, use the **effective valuation date**, not the issue/retrieval date. Synthetic manifest ingestion should use `period_end` where supplied, falling back to `date`; some documents still require review because several dates have different meanings. Folder scanning does not automatically trust/ingest a manifest as metadata: a caller supplies selected metadata explicitly. Keep manifests outside source-only intake folders.

Deduplication is per case and SHA-256 content, independent of filename/route. Repeated intake returns the original document, without changing origin, flags, confirmation or hints. Stored duplicate bytes are checked for integrity. A duplicate cannot silently correct a pending classification; review/correction handling is a later explicit operation. The same bytes in another case get their own document record and may share immutable blob storage.

Versions are grouped by type, normalized entity and `scope` (default `default`). Set distinct scopes for distinct properties/facilities/reports of the same type. A newer conflict-free document links `supersedes_id` to the newest accepted period in that stream and increments the retained revision count. Old periods, changed bytes at the same period, wrong entities and unresolved classification receive review reasons and do not supersede accepted evidence. Confirmation is never inherited. If a scan sees the newest report first, an older report later is correctly retained as a pending historical input; use tranche folders for the intended progressive demo sequence. A same-name file whose bytes change is a new version.

API writes use SQLite `BEGIN IMMEDIATE` so simultaneous duplicate/version selection is serialized. Direct service callers must likewise serialize writes and own commit/rollback. Original bytes are stored by hash before the database record; a rollback may leave an unreferenced blob, which a retry can reuse. Missing/corrupted stored bytes fail integrity checking. Runtime storage is operator-controlled and separate from intake folders. Never expose it as executable/static web content.

Scans are explicit, recursive, deterministic and limited to 500 files; files above 25 MiB are rejected individually. Hidden entries are skipped, symlinks and non-regular files are rejected, and storage/intake roots cannot overlap. Renaming or moving a source within the configured folder does not create a duplicate version. API transaction failure rolls back the database scan; retained unreferenced blobs follow the retry behavior above.

`create_database()` additively upgrades B01 databases with immutable `Document.intake` JSON metadata; existing documents receive `{}`. This does not retrospectively classify or confirm them. Existing case configuration hashes remain unchanged. No schema/configuration or content in Phase 1 or `templates/` is changed.

B05 now recalculates expected inputs and section readiness after upload, duplicate intake and folder scan. See [readiness.md](readiness.md) for the snapshot API, dismissal and request-list export; stored draft text is preserved.
