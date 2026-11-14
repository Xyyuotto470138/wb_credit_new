# Computed tables and REIT analytics (B10)

B10 computes immutable section 2 exposure, section 10 analytics and section 13 conduct/covenant values in Python. It also supplies property debt-service projections for section 9 and a scoped LTV calculation for section 8. There are no model calls, source searches, generated recommendations, spreadsheet writes or frontend changes. The existing B07 dashboard does not yet expose these controls.

## Inputs and API

`POST /cases/{case_id}/analytics` accepts an `AnalyticsRequest`:

```json
{
  "set_id": "reit",
  "period": "2026-10-31",
  "scope": "Group",
  "reviewed_by": "demo-ca",
  "review_note": "Reviewed source column, definition, scope and units",
  "metrics": {},
  "tables": [
    {"kind": "exposure", "evidence_ids": ["indexed-Exposure-sheet"]},
    {"kind": "conduct", "evidence_ids": ["indexed-Monthly-sheet", "indexed-Events-sheet"]}
  ]
}
```

An empty metric selection produces all configured metric slots with **named gaps**, never guessed values. POST creates an immutable computation snapshot; list/detail GETs use the same prefix and `/{run_id}`. API writes are serialized; service callers own commit/rollback. Invalid bindings fail with 422, foreign/unknown citations with 404, corrupt source bytes with 409, and unconfigured persistence with 503. No background work is started.

Each metric accepts either `bindings: {operand: [binding]}` or `spread_value_ids: {operand: [computed_value_id]}`. A binding contains `evidence_id`, exact `quote`, numeric `token`, zero-based token `occurrence`, `unit`, `currency` where applicable, `period`, `scope`, `basis`, and `context_quote`. Optional `item` identifies each asset, lease or debt tranche; `maturity` is an ISO date. `proxy` explicitly labels estimated inputs. The resolver checks original bytes, case/entity/current source, quote/token boundaries, and period/scope/item/date context. The source, binding, review actor/note and public URL/retrieval/confirmation labels remain in the snapshot. Source text is inert data.

These are **explicit reviewed source mappings**, not automated semantic extraction. The caller must review column selection, currency, date, ownership, regulatory definition and basis. Exact quote matching cannot prove that a number appearing elsewhere on the same page has the intended meaning. `validated` on a computed value means its arithmetic and declared input contracts passed; it does not certify the caller's semantic mapping. No route infers a verified basis from a document title or confidence score. The prototype actor field is not authentication; role enforcement belongs to the later workflow block.

B09 references must be validated values from a valid, current-source B09 spread, with the exact mapped account, period and scope. The `reported` operand selects a configured reported fallback; for example `npi: {spread_value_ids: {reported: [npi_value_id]}}`. This supports B09's signed financial statements without silently negating expense operands. Explicit NPI calculation instead requires positive expense magnitudes and a reported-NPI reconciliation operand. Other fallback examples are reported occupancy, WALE and fixed-rate share; their basis restrictions still apply. Maturity profiles require actual tranche dates and amounts, not a reported scalar total.

Units normalize thousands/millions to currency, cents/unit to currency/unit and fractions to percentages. Output values are exact Decimal strings; only `display` rounds to six decimal places. No FX is guessed: mixed currencies produce a gap. Supply an independently sourced, reviewed common-currency valuation dataset before summing; B10 has no automatic FX converter. Periods and scopes must match exactly. Separate requests preserve historical/interim/projected periods and Group/Trust/property scopes; no automatic period conversion merges them.

## Metric and template contracts

FIG `analytics.yaml` pins 22 metrics: the ten project REIT measures, nine further financial-template disclosures, two separate ICR sensitivity scenarios and scoped LTV. Every financial-template data row has a `template_rows` mapping; category headings have no value. The other section 9 debt-service rows come from the projection adapter. Missing years, interim inputs, valuation-rate ranges that cannot be mapped to a single disclosed rate, DSCR operands or sensitivity assumptions remain named gaps. For multiple properties/rates, use separate property/date-scoped requests; a portfolio average is not inferred. Template sample values are never read as evidence.

- Aggregate leverage and ICR use explicitly mapped regulatory disclosures. Generic debt/assets and NPI/finance-cost proxies cannot drive regulatory headroom. Computing regulatory ratios from unverified statement totals is deliberately unsupported.
- Maturity amounts need unique debt identities, dated buckets and exact reconciliation to total debt. Fixed/hedged share requires a non-overlapping definition and a matched denominator.
- Occupancy requires comparable area operands or a reported percentage. WALE uses unique paired leases and complete percentage weights on a single rental-income or area basis, or a reported figure. An unweighted average is never substituted.
- NPI checks positive expense sign and reconciles exactly to reported NPI, or consumes the reported B09 NPI. DPU normalizes cents; valuation sums require unique assets, matched ownership/date/currency. Disclosed capitalisation rates reject property-yield proxies.
- The EBITDA shock uses `0.9 × regulatory_ebitda / regulatory_interest`. The rate shock uses `regulatory_ebitda / (regulatory_interest + 0.01 × total_debt)` for a complete annual scenario. Inputs must carry the reviewed `MAS TTM complete sensitivity` basis, including fees/hybrid distributions in the denominator and full debt exposure. Missing assumptions stay gaps. It does not apply the shock only to floating debt or combine both shocks.

The computation snapshot stores formulas, thresholds, rule sources, source register and gaps. Each metric, headroom value and table numeric cell carries a `computed_value_id` linking an immutable `ComputedValue` plus citations to every operand source. Rule constants are pinned configuration, not claims about the borrower. Threshold metadata in the snapshot is the source for the limit constant. Public confirmation is preserved separately; computation does not confirm evidence or close the financial-spread readiness gap.

The existing `Spread` record stores the snapshot with `version=computed-tables-v1` and `validation_status=manual review`, distinguishing a reviewed mapping/computation report from a valid financial-statement spread. Individual arithmetic results may be validated even while unrelated slots have gaps. B11/B18 should use the snapshot and its value IDs, not treat a successful HTTP status as completeness. Historical GET preserves old results; source resolution verifies bytes and exposes currentness. B13 owns draft invalidation and B24 owns typed-input acceptance/recomputation. No CA draft, confirmation, ES pointer or workflow event is changed by B10.

## Workbook extract adapters and gold controls

Adapters consume whole indexed worksheets from the documented B03 formats, matched by exact headers. They do not open paths supplied by the request or trust a model-generated row list. Unknown layouts, formulas, currencies, malformed controls and inconsistent dates become named gaps. This is a source-format adapter, not a general bank-system integration; other extract layouts need a reviewed adapter.

Exposure is one borrower/source-currency snapshot grouped by facility, with source maturities/security, recomputed change, undrawn amount and utilisation, and reconciled source totals. Source amount units are SGD million. Gold totals: existing 55, outstanding 46, proposed 75, increase 20, undrawn 9 and utilisation 83.636364%. Missing evidence is not nil. Explicit new-to-bank case input can state nil **existing** exposure, while proposed facilities remain source-required.

Conduct requires 12 consecutive unique month ends and a complete events register from the same report version. Peak balances are independently reported peaks; average balances and utilisation use month-end samples, never a claimed daily average. Overlapping excess days are counted once, events separately; DPD is paid minus due date. Invalid, duplicate, out-of-window or incomplete observations produce a gap. Complete zero-event coverage can establish zero counts only if monthly peaks agree. TL gold is peak/mean 42, one late payment, max DPD 3. RCF gold is peak 10.5, mean 4.583333, one excess, two excess days and max excess 0.5. This does not infer an overall satisfactory-conduct finding or tick an adverse-findings checkbox.

Covenant limits remain contractual and distinct from MAS rules. Gold headrooms are 0.9 percentage points, 0.6 times and 17.5 percentage points. Actuals/test dates and source context stay attached; synthetic monitoring files retain synthetic labels even when they quote public observations. Property projections recompute NPI, available cash, interest plus principal and DSCR; projected DSCRs for 2027/2028/2029 are 0.043261/0.325000/0.012500. No refinancing receipt is assumed. The source projection is a property scenario, not a consolidated forecast.

Task 0013a aligns the property fixture to the public FY2025 baseline, documented with its source in [the synthetic pack guide](../demo/synthetic/README.md). Synthetic annual rent/NPI/cash for service are SGD 3.48m/1.68m/0.78m. Property-only debt service remains uncovered in all three projected years. Proposed TL LTV changes from 53.571429% at SGD 112m to 57.692308% at SGD 104m, exceeding the fictional 55% covenant. The late valuation's fictional non-renewal notice calls for reassessing the pre-notice projections; it does not supply a revised cash-flow model. B09's public group financial-statement operands remain unchanged.

## Regulatory verification record

Checked on **2026-11-10**, effective **2024-11-28**: the [MAS release](https://www.mas.gov.sg/news/media-releases/2024/mas-rationalises-leverage-requirements-and-introduces-additional-disclosures-for-reits) confirms the 50% maximum, 1.5 times minimum and improvement-plan expectation below 1.8 times. Headroom is percentage points or times, not borrowing capacity. Equality passes the configured comparison. A negative result is labelled **outside configured threshold**, without deciding legal exceptions or credit approval. Historical periods before the configured effective date remain gaps.

The [MAS response](https://www.mas.gov.sg/-/media/mas/resource/publications/consult_papers/2024/mas-response-to-feedback-on-proposed-amendments-to-reit-leverage-requirements.pdf), physical page 8, paragraphs 3.8–3.10, confirms separate scenarios and inclusion of fixed/hedged loans using weighted average interest cost. The [amendment annex](https://www.mas.gov.sg/-/media/mas/resource/publications/consult_papers/2024/annex-c---cis-code-amendments.pdf), physical pages 90–91, Appendix 6 section 9, supplies definition context: regulatory coverage uses trailing EBITDA with specified exclusions over interest, borrowing fees and hybrid distributions; leverage addresses borrowings/deferred payments, deposited property, hybrid treatment and proportionate SPV interests. It is a marked amendment document, so extracted old and new text must not be conflated. B10 therefore prefers reported regulatory disclosures over reconstructing these treatments from generic Phase 1 totals.

These are pinned implementation references, not a live regulatory update service. Runtime and tests make no network calls. Existing case snapshots retain their hashes; unverified old thresholds fail closed. Use a newly configured case to exercise B10; no implicit migration or demo reset occurs.

## Verification

`tests/test_analytics.py` exercises actual synthetic files against the independent B03 gold controls, actual ESR FY2025 public page 59 (43.4% leverage, 2.5 times ICR), validated B09 consumption, exact threshold boundaries, source/currency/scope/period/definition guards, proxy rejection, immutable persistence, APIs, stale sources, public/synthetic provenance, unsupported formats and missing inputs. A saved public transcription test is not a live-model accuracy claim. All tests block sockets/DNS; no new dependencies or paid calls are required.
