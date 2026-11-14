SYNTHETIC DEMO DATA, not a real record

# B03 three-tranche source pack

This is a fictional renewal/upsize involving the public borrower named in `case.yaml`. The lender is **the Bank**. No real lending relationship, tenant, internal rating, policy, valuation engagement or approval is represented. Public observations retain their original periods and sources; the synthetic deal never changes published consolidated figures.

`case.yaml` is the single borrower configuration point: identity, identifiers, public-pack path, property reference and borrower-specific public observations. If Sheryl changes borrower, update that file and point it to a separately verified public pack, then rebuild and re-review the derived files. Generated files and the manifest repeat the identity for ingestion; do not edit those copies independently. The fixture builders intentionally support this scenario, not arbitrary loan modelling or production template export.

| Arrival | Files | Purpose |
|---|---|---|
| `tranche_1/` | Term sheet PDF; RM support `.eml` | Start the request and public evidence steps |
| `tranche_2/` | CAS PDF; prior ES DOCX; prior conditions PDF; covenant monitoring XLSX; compliance certificate PDF; pricing PDF; valuation v1 PDF; insurance PDF; rent roll XLSX; lease profile XLSX; projections XLSX; limits/utilisation XLSX | Supply the client and historical internal inputs, plus the suggested exposure extract |
| `tranche_3/` | Account conduct XLSX; internal rating PDF | Supply current-period conduct and input-only internal rating |
| `late_update/` | Valuation v2 PDF | Supersedes v1; intended to invalidate sections 8, 9, 11 and 14 in B13/B19 |

Use the manifest's explicit file list for each arrival. Do not recursively ingest this whole directory at the start: that would expose tranche 3 and the late update early. `README.md`, `case.yaml` and `manifest.yaml` are pack metadata, not uploaded evidence. B03 does not implement readiness, extraction, workflow or Stale behavior.

## Values and scope

All monetary source extracts use SGD million unless a column states SGD or the prior ES states SGD'000. Existing limits are 45 + 10 = 55; October outstanding is 42 + 4 = 46; proposed limits are 60 + 15 = 75. The prior ES's April outstanding is 42 + 5 = 47, matching the separate April conduct sample.

The proposed TL's fully drawn LTV is 60 / 112 = 53.571429%. The late property value is 104, raising proposed LTV to 57.692308% against the fictional 55% contractual maximum. Headroom changes from 1.428571 to -2.692308 percentage points; the revised maximum loan is 57.2, requiring 2.8 less than the proposed draw. Drawn LTV is separately 37.5%, then 40.384615%; the unsecured RCF is excluded. Do not substitute the insured reinstatement amount of 90 for market value. The initial value is effective 31 October and issued 4 November; the revised report is effective/issued 9 November.

Public property facts are retained in `case.yaml` → `public_property`: high-specifications industrial, multi-tenanted, GFA 22,798 sqm, NLA 19,187 sqm, 30+30-year tenure expiring 3 July 2067. At 31 December 2025 the remaining lease was 41.5 years, occupancy 50.2%, valuation SGD 109.0m and FY2025 rent SGD 3.5m. Acquisition was 29 May 2012 at a purchase price/development cost of SGD 100.5m. Source: ESR-REIT Annual Report 2025, physical pp72–73 (printed pp70–71), row 5; [saved public source](https://links.sgx.com/FileOpen/ESR-REIT%20AR%202025.ashx?App=Announcement&FileID=881689), retrieved 10 November 2026. These historical figures are not claims about current occupancy or a fresh title search.

The fictional October tenant allocations occupy 9,632 sqm, giving 50.200657% occupancy (50.2% at the report's precision). The initial valuation is close to the public SGD 109m baseline. A fictional notice on 9 November says Demo Tenant A will not renew on 30 April 2027; the revised valuation allows for downtime, reletting costs and a higher yield. No real tenant event is asserted. The October rent roll remains a pre-notice snapshot. The revised report calls for reassessment of the 2 November projections, whose renewal assumptions are now outdated.

Group leverage 44.1% and ICR 2.6x are **public observations at 30 September 2026**, quoted in fictional monitoring/certification documents, with the public PDF page, URL and retrieval date. Contractual thresholds of 45% and 2.0x are fictional. They produce headroom of 0.9 percentage points and 0.6x. These source values are not a reconstructed regulatory calculation. B10 still owns definition verification and production analytics.

The synthetic annual rent run rate is SGD 3.48m, close to the public FY2025 rent; NPI is 1.68m; cash available for debt service is 0.78m after explicit reserves. Projections assume full draw and constant rents, including uncommitted renewals, conservative full-year interest in maturity years, and no refinancing receipt. DSCR is 0.043261/0.325000/0.012500 in 2027/2028/2029: the property alone does not cover debt service in any year. This weakness stays visible. Property NPI/interest is never labelled MAS ICR.

Conduct covers November 2025 to October 2026. Average utilisation means the arithmetic mean of **12 month-end balances**, not a daily average. Independent monthly peaks and an explicit event register show one RCF excess (SGD 0.5m over two inclusive calendar days) and one TL interest payment three days late. No event-free conduct is inferred from missing evidence.

The prior ES is an eight-page filled copy of the owner template, retaining all 14 headings and 43 tables. Its public FY2025 figures and roles cite annual-report-2025.pdf by physical page, resolved through `manifest.yaml` → `public_sources` for URL, retrieval date and hash. Historical inputs not reproduced in this demo copy remain labelled gaps; the fictional archival exception is explicit in section 14. Its six-month conduct excerpt and old internal rating do not satisfy the current tranche-3 documents. Its fictional human sign-offs do not supply the current CA position.

## Integration and verification

`case.yaml` → `app_case` contains B01-compatible Case attributes. Add borrower identity/public identifiers from `borrower` and the version/hash of the loaded FIG configuration. Leave `ca_position` null until the CA supplies it. `manifest.yaml` carries catalogue/suggestion IDs, entity, issue date, period end where needed, revision/supersedes links, source locators, sizes, hashes, and `synthetic: true`. Asset origin is `generated`; actual intake should record upload/folder origin while retaining the synthetic flag. Every document starts unconfirmed.

Industry mapping confirmation, generated financial spread, CA public-source confirmations and current CA position are later demo steps. The public pack's external rating and portfolio valuation/lease summaries cannot close the internal rating or full property-report requirements. Legal perfection evidence remains a suggested gap. No real bank data is needed.

Independent controls are in `tests/fixtures/synthetic_gold.yaml`. `tests/test_synthetic_pack.py` reads the delivered PDFs/DOCX/XLSX/email, checks the B01 contracts, tranche coverage, labels, immutable template parts, source provenance and reconciles exposure, LTV, covenants, conduct, rent, leases and projections. It does not import the builder to calculate expected answers. Gold values are deliberately maintained separately from generation. Ratios compare to six decimal places using Decimal ROUND_HALF_UP.

Run offline:

```sh
LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

The public-pack inventory check now scopes public/research directories; this suite separately enforces the synthetic inventory. Frontend build/eslint are inapplicable: no frontend code changes.

## Rebuild on this Mac

The saved files are the test/demo inputs; consuming them requires no artifact tool or rendering dependency. Authoring uses the existing bundled artifact runtime for spreadsheet generation and Word rendering, and approved project Python libraries for arithmetic/PDFs. No dependency was installed or added to the application.

```sh
artifact_deps=/Users/sheryld/.cache/codex-runtimes/codex-primary-runtime/dependencies
# If scripts/node_modules is absent, link the existing bundled tool dependencies.
test -e scripts/node_modules || ln -s "$artifact_deps/node/node_modules" scripts/node_modules
.venv/bin/python scripts/build_synthetic_pack.py
"$artifact_deps/python/bin/python3.12" scripts/fill_demo_prior_es.py
"$artifact_deps/node/bin/node" scripts/build_synthetic_workbooks.mjs
.venv/bin/python scripts/build_synthetic_pack.py --manifest
```

Before regenerating artifacts, follow the active document/PDF/spreadsheet skill's operation marker instructions. Builders produce intermediate specifications, inspection records and worksheet previews under ignored `runtime/b03/`. The ES filler fails if the owner template hash has changed; re-map and review a new template rather than bypassing the guard. It patches only document text, the required synthetic header and field-refresh setting; other package parts remain byte-identical. Page fields refresh when opened in Word.

For Word QA, use the documents skill's `render_docx.py` with the bundled Python and LibreOffice, output below `runtime/b03/`, and inspect every page. Render every PDF using PyMuPDF and inspect every workbook sheet using the artifact tool. Task 0005 inspected all eight reference/final ES pages, eleven report PDF pages and nine workbook sheets. This is fixture layout verification, not B18 production export acceptance or proof of fit to a live bank template.

### Task 0023 CAS classification

The current synthetic CAS explicitly records Pass, not on Watchlist or Special
Mention, and current DPD 0. That point-in-time statement does not erase the
historical three-day TL payment delay or the two-day RCF excess in the twelve-month
conduct register. The source builder, manifest hash and reviewed drafting claims
were updated together; the prior ES and owner templates remain unchanged.
