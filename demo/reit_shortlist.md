# Demo REIT shortlist — task 0002

Recommendation: **ESR-REIT**, subject to Sheryl's veto. This selects a demo borrower, not a credit recommendation. Use **16 Tai Seng Street** as the proposed Singapore property reference; the future facility and all internal inputs must be explicitly synthetic.

Research cut-off and retrieval date for every linked source below: **10 November 2026**. FY2025 is the annual-report comparison baseline; newer updates remain separately dated evidence. All three issuer report indexes still list FY2025 as the latest annual report ([ESR](https://esr-reit.listedcompany.com/ar.html), [OUE](https://investor.ouereit.com/ar.html), [FCT](https://fct.frasersproperty.com/ar.html)).

“Mid size” is a demo-screening judgement here: approximately S$5–9 billion in reported assets/AUM and fewer than 250 physical annual-report pages. Assets and AUM have different scopes; these are scale indicators, not a like-for-like ranking. Page counts were measured with PyMuPDF, including covers and forms. All page references below are **one-based PDF pages**, with printed labels in parentheses.

| REIT; non-bank sponsor | FY2025 scale and SGX eligibility | Reported gearing / ICR; rating | Report size and demo assessment |
|---|---|---|---|
| **ESR-REIT**; **ESR Group Limited**, real asset owner/manager | S$5.9bn total assets; 70 properties. Listed on SGX since 2006. AR pp. 2, 12 (inside cover, 10). | **43.4% / 2.5x** at 31 Dec 2025; **Fitch BBB / Stable**. AR p. 59 (57); Fitch release p. 2 (agency 1/11). | **244 pages**. Best complete saved-source pack: agency-authored release is embedded in an exchange attachment. More property rows and currencies than the alternatives; preserve table spans and scope. |
| **OUE REIT**; **OUE Limited**, real estate and healthcare group | S$5.8bn AUM; six Singapore properties at FY2025. SGX listed since 2014. AR p. 4 (2). | **38.5% / 2.4x** at 31 Dec 2025; **S&P BBB− / Stable**. AR p. 41 (39); issuer rating-action announcement p. 1. | **182 pages**. Shortest report and compact portfolio. Hospitality master leases and partial ownership require care. Public issuer rating action saved; an agency-authored release was not retrieved in this run. |
| **Frasers Centrepoint Trust (FCT)**; **Frasers Property Limited**, property group | Approximately S$8.3bn AUM; nine retail malls and one office building; SGX listed since 2006. AR p. 4 (2). | **39.6% / 3.46x** at 30 Sep 2025; **Moody's Baa2 / Stable**. AR pp. 38–39 (36–37); historical Moody's action p. 1. | **222 pages**. Familiar Singapore retail properties and clear tables. Upper end of this size screen; joint ventures and different fiscal year complicate comparison. The saved agency release is historical (2020), not a current review. |

Sources for the comparison, all retrieved 2026-11-10:

- **ESR AR:** [Annual Report 2025, published 2 April 2026](https://links.sgx.com/FileOpen/ESR-REIT%20AR%202025.ashx?App=Announcement&FileID=881689). **Fitch:** [28 October 2025 agency release within 29 October issuer filing](https://links.sgx.com/FileOpen/News%20Release%20-%20Fitch%20Ratings%20Assigns%20BBB%20Rating%20with%20Stable%20Outlook%20to%20ESR-REIT.ashx?App=Announcement&FileID=865202), PDF pp. 2–12. [SGX listing identity, code 9A4U](https://links.sgx.com/1.0.0/corporate-announcements/AFZ4UOTXJEOSN1SM/).
- **OUE AR:** [Annual Report 2025, published 27 March 2026](https://links.sgx.com/FileOpen/OUE_REIT_Annual_Report_2025.ashx?App=Announcement&FileID=880688). **Rating action:** [issuer announcement, 30 October 2023](https://investor.ouereit.com/newsroom/20231030_181205_TS0U_2OI2YOWG2M8NNICP.1.pdf), p. 1. [SGX identity, code TS0U](https://links.sgx.com/1.0.0/corporate-announcements/2OI2YOWG2M8NNICP/). The old OUE Commercial REIT name is reconciled on AR p. 4 (2).
- **FCT AR:** [Annual Report 2025, published 23 December 2025](https://fct.frasersproperty.com/newsroom/20251223_072539_J69U_PRKHJYNC42NYLKEL.1.pdf). **Moody's:** [7 September 2020 agency release](https://fct.frasersproperty.com/newsroom/20200908_182944_J69U_WGU8PUCN944XHKLB.1.pdf), p. 1. [Current issuer rating page](https://fct.frasersproperty.com/credit_ratings.html), unpaginated, lists Baa2 / Stable with a 16 February 2026 rating date. [SGX identity, code J69U](https://links.sgx.com/1.0.0/corporate-announcements/WGU8PUCN944XHKLB/d3f8ccf2b59010953da384ee10eb4b5f7d5cb89cd22f090b90fcf49bb87d3587).

All three disclose the required property evidence:

| Annual report | Valuations | Lease expiry | Occupancy | Plausible Singapore property reference |
|---|---|---|---|---|
| ESR | pp. 49–50 (47–48) | p. 53 (51) | p. 50 (48) | 16 Tai Seng Street, pp. 72–73 (70–71) |
| OUE | pp. 42–52 (40–50) | pp. 34–35 (32–33) | p. 36 (34) | OUE Downtown Office, p. 46 (44) |
| FCT | p. 74 (72), plus other property profiles | p. 27 (25) | p. 29 (27) | Causeway Point, p. 74 (72) |

Property suitability is a **demo-design inference**, not evidence of available collateral, unencumbered title, lender consent or an actual financing request. In ESR's property table, names appear on the left page and values on the right: preserve pp. 72–73 together. Full property valuation, insurance and lease/rent-roll inputs remain gaps. The public external rating cannot fill the internal rating requirement.

The recommended pack is [public_pack/esr-reit/manifest.yaml](public_pack/esr-reit/manifest.yaml): six original PDFs, document dates, URLs, publishers, retrieval dates, physical page counts, SHA-256 hashes and page-level evidence pointers. The annual report supplies both the sponsor diagram and unitholder information; these are indexed without duplicating the PDF. Trust structure is dated 31 December 2025; unitholder statistics are dated 19 March 2026 (AR pp. 10, 229–231).

The [27 October 2026 business update](https://esr-reit.listedcompany.com/newsroom/20261027_070044_9A4U_YFZEGXW2FZEMWKRO.1.pdf), pp. 2–3, is newer than FY2025: reported gearing is 44.1%, ICR 2.6x, and tenant ACFS arrears A$2.8m. Do not replace actual gearing with its pro forma alternative, or interpret tenant rent arrears as borrower bank account conduct. The [6 October rent update](https://esr-reit.listedcompany.com/newsroom/20261006_172624_9A4U_V8TM4VE3R86VWL3G.1.pdf), p. 1, gives an earlier arrears position; retain both dates. The other saved exchange announcements cover [a public JPY facility](https://esr-reit.listedcompany.com/newsroom/20261012_200602_9A4U_6YZU3K7066VMMBD4.1.pdf), pp. 1–2, and [completed disposal of 30 Pioneer Road](https://esr-reit.listedcompany.com/newsroom/20261021_180024_9A4U_12QZMUTT9DQ1NP2I.1.pdf), p. 1. These support key updates and risk review; they are not the proposed synthetic deal.

[research/manifest.yaml](research/manifest.yaml) indexes the four comparison PDFs. Keep those out of the ESR case. No synthetic internal files, calculated credit ratios, or credit decision have been created.
