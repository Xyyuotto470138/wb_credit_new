# Keppel REIT public evidence pack: notes

Borrower: Keppel REIT (SGX-listed). Financing object: Ocean Financial Centre (OFC), 10 Collyer Quay, Singapore 049315.
Built 12 Nov 2026 from public sources only. Nothing here is CA confirmed. No bank internal data.

## What was downloaded

| File | Source | Pages |
|---|---|---|
| annual-report-2025.pdf | keppelreit.com, Publications | 228 |
| financial-statements-1h2026.pdf | keppelreit.com, Financial Results (unaudited, 29 Jul 2026) | 34 |
| results-presentation-1h2026.pdf | keppelreit.com, Financial Results (29 Jul 2026) | 40 |
| business-update-presentation-3q2026.pdf | keppelreit.com, Financial Results (28 Oct 2026) | 36 |
| media-release-3q2026.pdf | keppelreit.com, Financial Results (28 Oct 2026) | 5 |
| announcement-sp-rating-withdrawal-20150910.pdf | links.sgx.com | 2 |
| announcement-moodys-rating-withdrawal-20160930.pdf | links.sgx.com | 2 |

Also: `photos/` (3 Wikimedia Commons photographs, `credits.yaml`), `map/` (OneMap geocode and location map, `location.yaml`),
`manifest.yaml` (hashes, URLs, page counts, evidence pages), `search-index.yaml`, `facts.yaml`.

FY2025 is the latest annual report listed on the Keppel REIT site. The 3Q 2026 update is the latest results item.

## Credit rating: the expected "S&P BBB" could not be verified

- No current public issuer rating was found. The FY2025 annual report, 1H 2026 statements, the 2026 presentations and the June 2025 information memorandum (searched, not saved) state no rating.
- The issuer's own SGX announcements show both agency ratings were withdrawn at the Manager's request:
  - S&P: final "BBB", stable outlook, withdrawn 10 Sep 2015.
  - Moody's: "Baa3", stable outlook, withdrawn 30 Sep 2016 (it was "Baa2" stable on 10 Sep 2015).
- A Phillip Securities (POEMS) bond note of 26 Feb 2026 says Keppel REIT "is rated BBB (S&P)". That conflicts with the 2015 withdrawal and is not supported by any Keppel REIT document. It is treated as stale. It was not saved.
- Not checked: the S&P, Moody's and Fitch websites directly (login walls). A new rating assigned after 2016 and never mentioned in issuer documents cannot be fully excluded, but nothing found suggests one.
- Wording to use: "Keppel REIT has no current public issuer credit rating that could be verified; S&P BBB (stable) and Moody's Baa3 (stable) were withdrawn in 2015 and 2016."

## Could not verify or not disclosed

- OFC completion year: not in the saved documents. Secondary web sources say 2011. Recorded as `not_found`.
- OFC WALE: not published per building. Only the OFC lease expiry profile and portfolio WALE are disclosed.
- OFC net lettable area at 100%: only "approximately 871,000 sf of premium office space" is stated. Attributable NLA is exact (695,996 sf at 31 Dec 2025; 697,194 sf at 30 Sep 2026).
- Whether OFC is encumbered: the annual report says "certain investment properties" secure S$468.9 million of bank loans but does not name them.
- Percentage of fixed-rate borrowings at 31 Dec 2024: not restated in the FY2025 report.
- 3Q 2026 is a business update: no balance sheet, NAV or DPU. Latest balance sheet is 30 Jun 2026.
- Annual report release date: the manifest uses the PDF creation date (16 Mar 2026); the SGX release date was not checked.
- SGX code K71U comes from web search result titles; it is not printed in the saved PDFs.

## Points that are easy to get wrong

- OFC valuation: S$2,301.1 million is Keppel REIT's 79.9% share; S$2,880.0 million is the 100% carrying value. Valuer CBRE Pte. Ltd., 31 Dec 2025. Capitalisation rate 3.40%.
- OFC ownership: about 79.9% through Ocean Properties LLP; Allianz Real Estate 20.0%; Avan Investments about 0.1%. The interests were acquired for 99 years from 14 Dec 2011 with S$1.00 call options back to the vendors after that period, a right of first refusal, and a carve-out right on specified events (annual report pdf page 145). Read that footnote before describing title or security.
- OFC occupancy: 96.0% (31 Dec 2025), 96.5% (30 Jun 2026), 95.2% (30 Sep 2026). The occupancy bar chart on annual report pdf page 42 loses its label order in the text layer; the property table on pdf page 44 was used.
- Aggregate leverage: 47.9% actual at 31 Dec 2025 (equity bridge loans), 40.4% pro forma, 40.0% at 30 Jun 2026, 40.5% at 30 Sep 2026. The 39.2% on the 3Q slide is pro forma for a proposed acquisition.
- Borrowings come in three bases: balance sheet carrying amount (S$3,756.7 million), gross excluding associates and joint ventures (S$3,761.7 million), and gross including Keppel REIT's share of associate and joint venture debt (S$5,668.0 million, used for aggregate leverage). All at 31 Dec 2025.
- Property income excludes MBFC, One Raffles Quay, 8 Chifley Square and David Malcolm Justice Centre, which are equity-accounted.
- Interest coverage ratio follows the MAS CIS Code definition and includes distributions on hybrid securities. The documents do not call it "adjusted".
- Portfolio changed in 2026: KR Ginza II (Tokyo) sold 17 Aug 2026; T Tower (Seoul) sale announced, completion expected 4Q 2026; 51.0% of Keppel South Central proposed, completion expected 2Q 2027. The annual report describes 14 assets in four countries; the 3Q 2026 update shows 13 assets.
- Debt maturity percentages and the OFC lease expiry percentages are chart labels. They were confirmed by viewing the rendered pages (`read_from_chart: true` in `facts.yaml`).
- Annual report pdf pages 6, 9, 10, 11, 12, 67 and 68 are two-page spreads, so printed page numbers do not map one-to-one. `facts.yaml` gives both.
- The 2026 fact sheet PDF on the Keppel REIT site has no text layer. It was not saved.

## Licence and attribution obligations

- Photos (details in `photos/credits.yaml`):
  - `ofc-exterior-collyer-quay-2026.jpg`: RFNirmala, CC BY 4.0. Credit the author, link the licence, state changes (downscaled).
  - `ofc-exterior-2016.jpg`: Mike Cartmell, CC BY 2.0. Same obligations.
  - `ofc-exterior-ground-level-2025.jpg`: DvTor8303, CC0. No obligation; credit given as a courtesy.
  - Licences are as shown on Wikimedia Commons on 12 Nov 2026 and were not verified with the authors.
- Map: keep the line "OneMap | Map data (c) Contributors, Singapore Land Authority" visible. The image is four OneMap 512x512 tiles joined locally because OneMap caps static images at 512x512; the red pin was drawn locally. No key or token is stored in the pack.
- Keppel REIT and SGX documents are the issuer's copyright. They are saved as source evidence for internal demo use; quote short extracts with page references and do not republish them.

## Repository note

`tests/test_public_pack.py::test_all_saved_pdfs_are_manifested` compares every PDF under `demo/public_pack/` with the ESR and research manifests only. The seven PDFs here are not in those manifests, so that test fails until the test is taught about this pack. No test or other pack was changed.
