# B18 rendered review — 11 November 2026

Rendered with the documents skill's `render_docx.py --emit_pdf` and bundled LibreOffice. Inspected every page of the following final artifacts, against every page of the untouched owner template (8 pages). Runtime files are local review artifacts, excluded from Git.

| Artifact | Pages inspected | Result |
|---|---|---|
| `runtime/b18/verified/render/draft.pdf` | 1–18 | All 14 headings and section contents retained; exposure totals, facility terms, projections, financial measures, risk rows, rating, conduct and CA position readable. |
| `runtime/b18/fixtures/final-zero/zero.pdf` | 1–9 | Absent drafts/values explicitly marked; nested rating/risk tables and sign-off retained. |
| `runtime/b18/fixtures/final-one/repeat-1.pdf` | 1–9 | Long synthetic row wraps inside its cell; three facility columns fit and continue with headers. |
| `runtime/b18/fixtures/final-many/repeat-12.pdf` | 1–10 | All twelve synthetic rows present; three facility columns readable; subsequent sections/sign-off intact. |

Final demo DOCX SHA256: `daaaa45708fe77693eb6e7016d031f62e2a9d33bdcd310dbdd12de7bc8140948`.
Owner template SHA256: `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.

No clipped text, overlapping cells, dropped sections or broken tables observed in these final exports. Existing blue headings, gray table headers, borders, section breaks and paragraph/run styles remain. All 43 table containers remain; package parts outside `word/document.xml` are byte-identical. Long text flows across pages and row headers repeat. Some pages have substantial whitespace because owner section breaks remain; placeholder italics also remain. Narrow “No.” cells wrap the closing bracket of `[GAP]` to a second line without clipping.

Differences from the unfilled template are intentional: added source/draft/gap wording; repeated rows; facility width divided across supplied columns; explicit periods/units; expanded pagination. Five leading nested tables receive a one-point keep-with-next paragraph in their wrapper cells. This corrects a LibreOffice page-boundary omission reproduced in the untouched template (risk table) and the initial empty export (rating table). Owner files are never modified. Final sparse and full exports were rerendered after this correction.

The demo uses the saved public/synthetic pack and offline mock drafts; it leaves absent B09 spreads and unsupported mappings visible as gaps. B09 scaling is tested separately. Public URLs/retrieval dates, complete exact drafts and field-gap details travel in `manifest.json`; use the bundle for review. This is draft export acceptance for v0.1, not approved-workflow or future-template visual acceptance.

# Task 0022 presentation review — 11 November 2026

Delivered render: [gate2_export_sample.pdf](gate2_export_sample.pdf), **16 pages**, copied byte-for-byte from `runtime/0022/final-review/render/draft.pdf`. Every final page was inspected against the eight owner-template pages. Rendered with the documents skill's bundled Python/LibreOffice using `render_docx.py --emit_pdf`; no application renderer or dependency added.

The fresh case holds all three tranches, confirmed saved public evidence, a validated saved B09 spread and the 0020a drafts. Case `9afdd950-b553-4c0f-b5b3-d5252d3847c8`; final immutable export `b335fa88-fb71-40ab-a731-be77111fbcb1`. The local DOCX/manifest/checks are in `runtime/0022/final-review/`; the case database and immutable stored bundles are in `runtime/0022/delivery/`. Reproduce using the command in [exports.md](exports.md#task-0022-presentation-contract).

| Page | Inspected result |
|---|---|
| 1 | One draft/mock/synthetic status block; request and justification in their slots; unknown classification remains a named gap. |
| 2 | Exposure and Python totals readable; sourced developments in their table. |
| 3 | Prior conditions and acceptance outstanding; owner page flow leaves whitespace. |
| 4 | Business, listing, sponsor/manager, trustee and portfolio populated; industry-code gap retained. |
| 5 | Substantial holders and trust-structure wording; overlapping interests explicitly not additive. |
| 6 | Five management rows, known tenure and stakeholders; facility table starts with borrower/type/purpose. |
| 7 | Facility terms continue with repeated header; security, valuation, LTV and insurance readable. The security-gap prefix was also checked in a high-resolution PDF crop. |
| 8 | Insurance continuation; owner page flow leaves whitespace. |
| 9 | Three repayment sentences; historical Group figures distinguished from property projections; debt service, tenant shares and lease expiry all fit. |
| 10 | FY2024/FY2025 financial grid, supported ratios and regulatory thresholds; unsupported fields named by row/column. |
| 11 | Contractual headroom, sensitivity gaps, human-readable additional figures and concise financial gap notes. |
| 12 | Nine actual credit risks and mitigants, including LTV, tenant concentration, refinancing and interest rate. |
| 13 | Internal and external ratings; conduct commentary begins. |
| 14 | Conduct/covenant tables; human position verbatim at start of section 14. |
| 15 | Pending conditions and sign-off; no inferred decision. Narrow No. cell wraps the gap bracket without clipping. |
| 16 | Sources appendix: all 33 markers resolve to document/page/labels, with public URLs and retrieval dates. |

No clipping, overlapping cells, missing headings or lost tables observed. Template typography, borders, section breaks, headers/footer and all 43 table containers remain. All 14 heading structures match the owner template; every package part outside `word/document.xml` is byte-identical. Status and Sources paragraphs are the explicitly requested additions. Sparse pages reflect preserved owner flow; no new layout was substituted.

Final DOCX SHA256: `82dfe438376569b0b6eaa196f0738087f55f529c64fc6e0c7ef1fb3b7cd0dcca`.
Delivered PDF SHA256: `96f97656e382854331a2493f35a266279d9630a9b50ed7f9a6b6f5da0b7e411d`.
Owner template SHA256 remains `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.

The sample uses the original SGD 112m valuation (53.57% fully drawn LTV; 1.43 percentage points headroom). The separate regression covers the late SGD 104m revision and explicit redrafts (57.69%; −2.69 points), and explicit CA classification N/A. Neither a revision nor a classification decision is invented for the three-tranche sample. Remaining fields need validated matching inputs; this visual acceptance does not imply evidence completeness or credit approval.

# Task 0023 polish review — 11 November 2026

Delivered [gate2_export_sample.pdf](gate2_export_sample.pdf): **15 pages**. The
verified immutable DOCX and manifest are in `runtime/0023/verified/`; the case
store and original export history remain in `runtime/0023/delivery/`.
Case: `0bb65f27-257a-49b7-9d43-0cba44417ecc`.
Final export: `1616a8f6-a469-4697-9310-ab0b112ad537`.

Rendered with the documents skill's `render_docx.py --emit_pdf`, bundled Python
and bundled LibreOffice. Final DOCX bytes equal the reviewed pagination artifact
in `runtime/0023/pagebreak/`; the delivered PDF equals that render byte-for-byte.
Every final page was inspected. Pages 1–6 and 10–15 are byte-identical PNGs to the
preceding inspected render; pages 7–9 were reinspected after the pagination fix.
The regenerated one-page synthetic CAS was also visually inspected.

| Page | Inspected result |
|---|---|
| 1 | ESR Group / Singapore with public sources; Pass classification N/A cells; current DPD question answered No with CAS marker; Arial gap/checkbox text. |
| 2 | LOD N/A continuation; exposure amounts at two decimals and utilisation percentages at one; developments table begins. |
| 3 | Developments and prior conditions; business table and portfolio valuation use consistent amounts and body font. |
| 4 | Holder percentages at one decimal; overlapping interests remain not additive; structure and source markers readable. |
| 5 | Management and stakeholders; facility limits and terms fit. |
| 6 | Facility continuation, security and LTV rounded for display; insurance begins; no source/qualification lost. |
| 7 | Insurance continuation; repayment, DSCR n.m. and cash-bullet/no-refinancing note; tenant and lease percentages readable. |
| 8 | Complete FY2024/FY2025/interim financial grid, all requested rows populated where disclosed; unused annual column labelled; compact Remarks markers; regulatory and contractual headroom begins. |
| 9 | Headroom continuation, sensitivity gaps, four trend sentences on distribution/leverage/ICR/occupancy, short basis and remaining gaps; no raw Group lists. |
| 10 | Nine risk/mitigant rows; initial fully drawn LTV 53.6% and 1.4 percentage points headroom for display. |
| 11 | Internal/external ratings; three conduct-summary sentences retain both historical exceptions; conduct table begins. |
| 12 | Conduct/covenant continuation; exact conditional-support position followed by Credit Analyst, 10 Nov 2026; conditions remain pending. |
| 13 | All three human sign-off roles remain; no inferred signature or decision. |
| 14 | Sources 1–35, readable file/page labels and public URLs with human retrieval dates. |
| 15 | Sources 36–39; complete source register retained. |

No clipping, overlap, missing financial cells or lost tables in the final render.
All fourteen heading elements and forty-three table containers remain. Every ZIP
part outside `word/document.xml` is byte-identical to the owner template. Inserted
runs explicitly use template Arial in every script slot; the bundled renderer
substitutes Liberation Sans. The only Libertine glyphs are the owner's unchanged
heading information symbols, not inserted gap or checkbox text.

A short DSCR note exposed a LibreOffice nested-table pagination defect: the grid
was in DOCX XML but vanished in the PDF when its header landed at the page foot.
Keeping rows together did not solve it. The final export inserts an empty
page-flow anchor before section 10, leaving the owner's heading XML, table layout
and section geometry unchanged. Visual review and PDF value checks verify the
entire grid after this correction. This intentional pagination change is the only
new flow adjustment beyond the existing exporter anchors.

Financial values retain full stored precision; output uses S$m two decimals,
percentages one and ratios two. Monetary utilisation follows the S$m convention;
utilisation percentages use one decimal. DPU keeps disclosed three-decimal cents.
Gross debt is distinguished from net borrowings, and investment properties exclude
assets held for divestment. The update is not complete interim accounts, so its
undisclosed DPU/investment-property/assets/unitholder-funds fields stay gaps.
Detailed debt maturity buckets, matched stress inputs and other unsupported fields
remain visible as gaps; weighted average maturity and fixed-rate share are filled.
The extra third annual column is unused rather than an assertion of missing data.

Current Pass/DPD 0 comes from the revised synthetic CAS and does not erase the
historical conduct exceptions. The fictional CA position is quoted verbatim; all
technical actor/message IDs and ISO timestamps remain in the manifest. Approval,
legal perfection and refinancing commitments are not inferred. Owner templates,
public source bytes and historical exports were not edited.

Final DOCX SHA256: `d1ff39f5f3f51482f922c2d56681ea9566798301c8ee2cff66a74587c9a1ee9b`.
Delivered PDF SHA256: `4511f9bdcf3230340668d5bfe3d696a008ecef992f9bc98223392c0d6814c590`.
Owner template SHA256: `9e810fe363c3dc3ab038a60135e3b0467cbc3eee37c1d74a88f1a4a85ed6ef21`.
CAS SHA256: `21688e5103e9173f30c125124a170b2bcdb844f0ea65027e5e1c87f319e77c63`.
