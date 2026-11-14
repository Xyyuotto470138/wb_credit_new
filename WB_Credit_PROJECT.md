# WB Credit: Project File

Status: requirements captured, input document list received (partial), peer research complete, effort and timeline estimated (section 13). Detailed build plan not yet written.
Last updated: 11 Nov 2026
Build folder: `~/llm_projects/aiagent_project/codex_public/wb_credit`
Delivery: Codex builds; the Claude chat session orchestrates (section 14)

How to read this file: **[Business]** means stated by the business or project owner. **[Proposed]** means a working assumption to validate. Nothing marked [Proposed] has been confirmed by the FIG team.

---

## 1. What this is

**[Business]** An end to end prototype for Wholesale Banking (WB) credit analysts. It is Phase 2 of the Financial Spreading Tool. It takes a deal from raw inputs to a full credit report (ES) and tracks that ES through approval.

**[Business]** The prototype does not prove system integration. All required data is assumed ready, supplied by upload or from a provided folder.

**[Business]** First team is FIG. WB also has CBK and CMB, whose process and requirements may differ.

**Hard stop:** 27 Nov 2026. The build must be handover ready by then.

---

## 2. Core requirements

### 2.1 Progressive input [Business]
Input files may not all be ready at one go, so the system must accept them over time. At any point it must show:
1. What has been provided
2. What is missing
3. Which ES sections can be drafted from what is provided

### 2.2 ES template, FIG [Business]
14 sections, listed in section 3.

### 2.3 Approval flow [Business]
Credit analyst (CA) prepares → Credit Head reviews and supports, acting as checker and aligning on the facility structure and recommendation → Credit Approver gives final approval. The approver can raise questions, decline, or return the ES to the CA for adjustment.

Other steps exist in the real process. The credit admin support step is a stretch goal (section 2.12); the rest are left out to streamline the prototype.

### 2.4 ES status tracking [Business]
There must be a clear track of the ES status.

### 2.5 Team differences [Business]
FIG, CBK and CMB can differ. **[Proposed]** Template, required inputs and analytics sit in per team configuration, so CBK and CMB can be added without code changes to the core.

### 2.6 Data constraint [Business]
The real ES template, sample reports and other internal data cannot be shared with this build. The project owner has provided the input document types (section 3.2). Actual file contents and the build itself use industry standard assumptions.

**[Proposed]** What follows from this:
- Section content follows the 14 FIG section names, with structure and wording based on common wholesale credit memo practice. It is not a copy of the bank's template.
- Template, input list and section prompts sit in configuration, so the bank's team can swap in the real template after handover without changing the core.
- Build and demo data are public documents, plus synthetic files for the document types in section 3.2 that come from the client or from internal teams.
- Every synthetic file is labelled as synthetic, and so is any figure that comes from one.
- Fit against a real ES cannot be shown in this build. It needs to be tested by the bank's team after handover.

### 2.7 Missing data suggestions [Business]
The AI agents must suggest which data or supporting files are missing, and which of those could not be found online from public information. Design in section 4.2.

### 2.8 Pre-submission checks [Business]
Before the CA can confirm and submit the ES:
1. All 14 sections must be filled. **[Proposed]** "Filled" means CA confirmed, or Not applicable with a reason. Submit stays disabled until this passes, and the check lists what is still open. Open mandatory document gaps can still be submitted with a recorded reason, which reviewers see.
2. In future, the ES figures (for example limits and loans outstanding) will be checked against the latest balances in the credit master system. For the prototype this is assumed: a clearly labelled future capability panel lists the figures it would compare and states "Not connected: assumed consistent for this prototype". It is never shown as a passed check.

### 2.9 ES output format [Business]
The ES format is fixed by the business. The output must look exactly like the bank's ES template: no formatting drift and no section left out. The template changes about once or twice a year. The format must not be fixed into the code: the system fills the uploaded Word template.

**[Proposed]**
- The default template is `templates/ES_Template_FIG_draft_v0.x.docx`. The project owner built it from the bank's format screenshots and owns it; Codex does not edit `templates/`.
- The system finds sections by their numbered Heading 1 headings, tables by their header rows, and fill points by italic [bracketed] placeholders. A mapping it cannot find is shown as a named gap; the section is never dropped.
- Each ES records the template version it used. An exact match to the bank's live template comes when the bank loads its real template through the admin module (section 2.10) after handover.

### 2.10 Template admin [Business]
A credit department admin can upload a new ES template. The system compares it with the current one and suggests, for each change, whether it is formatting only (no IT involvement), needs prompt changes, or needs code changes. This is modelled on the policy studio in the AML SOW prototype.

**[Proposed]** Formatting-only changes go live after the admin confirms. Prompt and code changes produce a change list for IT. All template versions are kept.

### 2.11 Section chat [Business]
Each of the 14 sections has a chat box. If the user is not happy with a section, or has more information to add, they type it in and the system revises that section. Typed input only in this phase; no voice. Each chat turn is model calls, not code changes.

**[Proposed]**
- The system shows the revised text for the CA to accept or reject; it does not replace the text directly.
- Facts the user types are cited as CA input.
- Chat cannot change a computed table directly. It can add an input, which triggers a recompute.

### 2.13 Multi-model choice [Business]
The user can choose which model drafts, for example Claude Opus 5.5, GPT 6.1, GPT 5.6, Qwen 3.6, Qwen 3.8, Kimi or GLM, to demonstrate the differences between models.

**[Proposed]**
- **Model registry in configuration:** display name, provider type (Anthropic native or OpenAI compatible), endpoint, model ID and API key variable. Adding a model is a configuration change.
- **Choosing a model:** a case-level default, plus a model choice when redrafting a section. Every draft records the model it used.
- **Compare view:** the same section drafted by two models side by side, using the same evidence and prompt. It shows citation coverage, unsupported claims rejected, gap markers, latency and estimated cost. Computed tables are identical across models by design, because numbers come from code.
- **Live calls:** each needs an approved budget, and the estimated cost is shown before a run.
- **Data:** demo data is public or synthetic, so any provider can be used in the prototype. In the bank environment, only approved models apply.

**[Business]** The bank already has Qwen 3.6 and Qwen 3.8. More models can be introduced if they are proven to work, and open-source models are easier for the firm to introduce. The demo should therefore show the Qwen models the bank runs alongside the others.

### 2.14 CA workbench redesign [Business]
Decided 11 Nov 2026 after the project owner reviewed the first screens. The tool must be easy to use, look like a credit analysis workbench, and follow the CA's current workflow.

**Inputs screen (separate from the workbench)**
- The CA uploads files or scans a folder.
- Straight after, the system shows a checklist: what has been uploaded, what is still missing, and which sections can start drafting.
- It checks whether each file belongs to the target borrower or borrowers, and flags any that do not.

**ES workbench (main screen)**
- **Top bar:** UOB logo at the top left; the ES status, for example "Drafting, open 5 days, 3 inputs pending"; and a button back to the Inputs screen.
- **Left rail:** one tab per ES section with a clear status indicator, plus one Full ES tab that shows the whole ES.
- **Centre:** the ES shown section by section in the template's layout, with a Confirm button on each section.
- **Right panel:** the Credit Assistant, a chat box the CA can open to type changes or ask questions.

**Credit Assistant scope**
- On a section tab, the assistant treats every message as being about that section and changes only that section. It can read all related sections, because sections are linked: for example, the recommendation draws on the sections above it, and on the risks and the financial analysis.
- On the Full ES tab, comments are about the whole ES. The assistant works out which section the user most likely means, and confirms with the user before suggesting or updating if that is unclear.

**Changes and versions**
- Any update to a drafted section shows added text highlighted and deleted text struck through, and asks the user to confirm.
- All changes and versions are saved in the system. The user can roll back to earlier versions.

**Reviewers**
- The Credit Head and Credit Approver use the same workbench, read only, with their action buttons.
- They can comment on each section.
- The Credit Assistant is available to them, so they can ask it questions before raising them with the CA.

**Theme:** UOB brand blue, `#005EB8`, with the UOB logo at the top left.

**[Proposed]**
- **Section status:** Not started, Pending inputs, In progress, Update required, Confirmed, Not applicable.
- **Document status:** Received, Sourced publicly, Can be generated, Outstanding, Suggested, Not applicable, Waived.
- **ES status:** Drafting, Submitted for support, Supported, Pending approval, Query raised, Returned for rework, Approved, Approved with conditions, Declined.
- **Sources:** clicking a citation number opens the source page in the right panel, as a tab beside the Credit Assistant.
- **Direct typing:** the CA can also type directly into a section. Manual edits save as a version with no confirm step; tracked changes with confirm apply to AI changes.
- **Model picker and compare view:** moved to a settings page.

### 2.12 Stretch goal: credit admin support step [Business]
If time allows, capture the full flow, with a credit admin support step between Credit Head and Credit Approver (administrative checks and system key in). Otherwise it goes on the roadmap.

**[Proposed]** Workflow steps and roles sit in team configuration, so this step is configuration plus one screen.

---

## 3. FIG template and input map

Section names and the descriptions in brackets are **[Business]**. Document types come from the business list in section 3.2. Which document feeds which section, case rules and draft mode are **[Proposed]**.

### 3.1 Sections

| # | Section | Main inputs | New vs renewal | Draft mode |
|---|---|---|---|---|
| 1 | Request / Purpose (the client's request for the deal) | CAS, term sheet, RM business support email, information memorandum | Both | Extract and summarise |
| 2 | Summary of current client group exposure (existing limits approved and taken) | CAS, prior ES; limits and utilisation extract if suggested | Renewal or existing client; nil if new to bank | Computed table |
| 3 | Key updates (latest developments that may affect the assessment; more important for renewals) | Prior ES, credit comments or prior approval conditions, covenant monitoring report, annual reports, credit rating report, public news | Key for renewal; optional if new | Synthesis |
| 4 | Business background | Annual reports, information memorandum or fund report, prior ES, industry code mapping | Both | Extract and summarise |
| 5 | Shareholding structure | Shareholding structure, annual reports | Both | Extract, chart if available |
| 6 | Key management and stakeholder | Annual reports, information memorandum or fund report | Both | Extract and summarise |
| 7 | Facility structure | Term sheet, CAS, pricing report, prior ES | Both | Extract into table |
| 8 | Security support | Term sheet, valuation report, insurance report | Both | Extract; "unsecured" needs CA confirmation |
| 9 | Source of repayment | Sections 7 and 10, financial projections, rent roll, lease profile | Both | Synthesis |
| 10 | Financial highlights and analytics | Financial spread, financial statements, annual reports, financial projections, compliance certificate | Both | Computed figures with AI commentary |
| 11 | Key credit risks and mitigates | Sections 3 to 10, covenant monitoring report, credit bureau report | Both | Synthesis, CA to edit |
| 12 | Credit rating | Credit rating report | Both | Input only, never inferred |
| 13 | Conduct of Account (past repayment record of existing customers) | Account conduct report, covenant monitoring report, compliance certificate, credit bureau report | Existing clients only | Computed table plus summary |
| 14 | Recommendation: conclusion | All mandatory sections, credit comments or prior approval conditions, pricing report, RM business support email, CA position | Both | CA led; AI drafts wording only |

**Section dependencies [Proposed]:** 9 needs 7 and 10. 11 needs 3 to 10. 14 needs everything mandatory, so it is always last.

**FIG analytics [Proposed]:** section 10 uses measures that fit the borrower type, set in configuration. For the REIT demo: aggregate leverage, interest coverage, debt maturity profile, share of fixed rate debt, occupancy, WALE, net property income, distribution per unit, portfolio valuation and capitalisation rates. It also shows headroom to the MAS limits for all REITs: aggregate leverage of 50% and minimum interest coverage of 1.5 times (from 28 Nov 2024), and flags interest coverage below 1.8 times, where MAS expects the manager to have improvement plans. Bank measures stay in configuration for bank borrowers. Confirm the list with FIG.

### 3.2 Input document catalogue

The document types are **[Business]**, from a list the business says is not complete. Usual source, public availability, case rule, sections fed and mandatory flags are **[Proposed]** industry standard assumptions. The catalogue sits in configuration, so types can be added without code changes.

| # | Document type | Usual source | Found publicly? | Applies when | Feeds sections | Mandatory |
|---|---|---|---|---|---|---|
| 1 | Credit application summary (CAS) | RM | No | All cases | 1, 2, 7, 14 | Yes |
| 2 | Term sheet | RM, agreed with client | No | All cases | 1, 7, 8, 9 | Yes |
| 3 | Prior approved executive summary (prior ES) | Internal | No | Renewal or existing client | 2, 3, 4, 7 | Renewal |
| 4 | Annual reports | Client or public | Yes, if listed or publicly reporting | All cases | 3, 4, 5, 6, 10 | Yes, this or 6 |
| 5 | Information memorandum or fund report | Client, arranger or fund manager | Sometimes, for listed funds | Fund borrowers, or deals with an IM | 1, 4, 6, 9 | Conditional |
| 6 | Financial statements (audited and interim) | Client or public | Yes, if listed | All cases | 10 | Yes, this or 4 |
| 7 | Financial spread | Generated by Phase 1 from 4 or 6 | Generated | All cases | 9, 10 | Yes, can be generated |
| 8 | Compliance certificate | Client | No | Existing facilities with financial covenants | 10, 13 | Conditional |
| 9 | Valuation report | Client or valuer | Summary values only, in some annual reports | Property or asset security | 8 | Conditional |
| 10 | Credit rating report | Internal rating; external agencies | External rating actions often public; internal rating no | All cases | 12 | Yes, internal rating |
| 11 | Pricing report | Internal | No | All cases | 7, 14 | No |
| 12 | RM business support email | RM | No | All cases | 1, 14 | No |
| 13 | Insurance report | Client or broker | No | Insured security or assets | 8 | Conditional |
| 14 | Financial projections | Client or RM | No | New money, term or acquisition financing | 9, 10 | Conditional |
| 15 | Rent roll | Client | No | Repayment from property income | 9 | Conditional |
| 16 | Lease profile | Client | Partly, lease expiry profiles in some annual reports | Repayment from property income | 9, 11 | Conditional |
| 17 | Account conduct report | Internal | No | Existing client | 13 | Existing client |
| 18 | Credit bureau report | Internal, pulled from a bureau | No | Borrower or guarantor covered by a bureau | 11, 13 | No |
| 19 | Industry code mapping | Internal | No, but the tool can suggest a code from the business description for CA confirmation | All cases | 4 | Yes |
| 20 | Shareholding structure | Client or public | Yes, if listed | All cases | 5 | Yes |
| 21 | Covenant monitoring report | Internal | No | Existing facilities with covenants | 3, 11, 13 | Conditional |
| 22 | Credit comments or prior approval conditions | Internal | No | Renewal or existing client | 3, 14 | Renewal |

"Conditional" means mandatory once its "Applies when" rule is met.

**Possible additions the agent may suggest [Proposed]:** limits and utilisation extract (if the CAS has no exposure table), security or guarantee documents, regulatory capital and liquidity disclosures for bank borrowers (public), external rating agency releases (public), recent news and exchange announcements (public). These show as Suggested, not Required.

---

## 4. Progressive input logic [Proposed]

### 4.1 Readiness

**On each upload or folder scan:**
1. Classify the document (type, entity, period)
2. Tick it against the catalogue items that apply to this case (section 3.2)
3. Recalculate readiness for every section
4. Flag conflicts, such as a wrong entity or an older period than the file already held

**Section readiness states:**

| State | Meaning |
|---|---|
| Waiting for input | Nothing usable yet; shows the missing items |
| Can draft (partial) | Enough for a draft, with named gaps marked in the text |
| Can draft (full) | All mandatory inputs present |
| Not applicable | Case type rule, such as Conduct of Account for a new client |
| Drafted | AI draft exists |
| Stale | A newer input affects this section |
| CA confirmed | CA has accepted the content |

**Rules:**
- New inputs never silently overwrite text a CA has edited. The section is marked Stale and the CA chooses whether to redraft.
- A missing file is shown as a gap. It is never treated as a fact, for example no security document does not mean the facility is unsecured.
- Gaps stay visible inside the draft, and the gap list (section 4.2) can be exported as a request list for the RM, client or internal teams.

### 4.2 Missing data suggestions [Proposed design]

Meets requirement 2.7. Runs after each upload or folder scan.

1. **Build the expected list.** Take the catalogue items whose "Applies when" rule fits the case: case type, borrower type, facility type and security.
2. **Add triggered suggestions.** Read what has been provided for signals that call for other documents. For example, property security in the term sheet calls for a valuation report and an insurance report; financial covenants call for a compliance certificate and a covenant monitoring report; prior approval conditions call for evidence that each condition is met.
3. **Try to close each gap.**
   - If the tool can generate it, offer to: the financial spread from an annual report, or a suggested industry code.
   - If the type can be found publicly and the borrower is a public entity, search public sources: company website, exchange filings, regulator disclosures, rating agency releases and news.
   - Otherwise, or if the search finds nothing, mark it Missing.
4. **Produce the gap list,** grouped by who to ask: RM, client, or internal team. Each line names the document, why it is needed, which ES sections it holds up, and whether a public search was tried.

**Status of each expected document:**

| Status | Meaning |
|---|---|
| Provided | Uploaded or found in the case folder |
| Found publicly | Retrieved from a public source, with link and retrieval date; CA to confirm |
| Can generate | The tool can produce it from what is already held |
| Missing | Not provided and not found publicly, or not a public type; shows who usually holds it |
| Suggested | Not in the catalogue, but signals in the case point to it |
| Not applicable | Its rule does not apply, with the reason |
| Dismissed | CA has dismissed it, with a reason |

**Rules:**
- Internal and client document types are never searched online. They go straight to Missing.
- Public searches use only the borrower's public name and identifiers, never deal details.
- A public find can be used for drafting and is marked as public in the text. It counts toward Can draft (full) only after the CA confirms it.
- Public search can be switched off where there is no web access. The gap list then says the search was not run, rather than reporting the document as not found.
- The agent never states that a document does not exist. It reports only what was provided, found or not found.

---

## 5. ES status flow

**[Business]** path, with **[Proposed]** states and return paths:

```
Draft → Submitted to Credit Head → Supported → With Credit Approver → Approved
              ↓                                    ↓  ↓  ↓
        Returned to CA                Returned to CA  Question to CA  Declined
```

- **Approver outcomes:** approve, raise a question, decline, or return to the CA [Business]. Approve with conditions is a configurable outcome, on by default until confirmed [Proposed].
- **Questions:** a question goes back to the CA, who answers and resubmits to the approver [Proposed].
- **Records:** each move records who, when, and the ES version.
- **Comments and returns:** reviewers comment per section, and a return names the sections to fix.
- **Locking:** the ES is locked while with a reviewer; a return unlocks it.
- **Read view:** each stage shows the source behind each claim and what changed since the last version.
- **Before submission:** the checks in section 2.8 apply.
- **Roles:** the prototype uses a role switcher (CA, Credit Head, Credit Approver, template admin), with no single sign on.

---

## 6. Design principles

**Carried from Phase 1:**
- AI handles judgment, Python handles arithmetic, and every step has a validation gate. Exposure totals, ratios and conduct tables are computed, never written by a model.
- Decisioning safe language: never imply that AI approves credit, never claim a "full audit trail", never say "same day decision".
- Keep two tiers of value claims: Destination (aspirational and labelled) and Proven (witnessed and locked).

**From the peer research (section 8):**
- Retrieve for usefulness per section, not only similarity
- Every claim links back to a document and page
- Complex tables keep their source reference for manual checking
- Team knowledge sits in editable playbooks
- Measure the review step, not only the draft

---

## 7. Phase 1 reuse

| Asset | Detail |
|---|---|
| Stack | FastAPI, SQLAlchemy, SQLite, Pydantic, PyMuPDF, pdfplumber, Pandas, OpenPyXL; React 19, Vite, AG Grid, react-pdf, react-dropzone |
| Pipeline | Upload, metadata, extraction, spreading, ratios and export |
| Extraction | Self correcting 3 iteration loop with a deterministic validator and fallback |
| Pipelines | Dual: fast metadata and ratios, plus full extraction |
| Models | Model agnostic adapter across 7 providers |
| Known quirk | DBS Annual Report 2025 is a dual page spread where pdfplumber drops numbers; use PyMuPDF |
| Known method | NIM uses PDF search, then web search, then a labelled estimated proxy |
| Proven claim | About 400 pages to credit ready draft in under 5 minutes of AI prep, analyst review following. Do not inflate. |

Repo path: `~/llm_projects/aiagent_project/codex_public/financial-spreading-tool`. Folder confirmed present on 7 Nov 2026, with backend, frontend and demo folders. Code state not checked.

---

## 8. Peer research: DBS and OCBC

Public sources only, as at 6 Nov 2026.

### DBS: agent chain to a first draft
- Announced 19 Aug 2026. Moved from a 150 user pilot to about 1,500 RMs and credit risk managers globally, for large and mid sized corporates.
- Specialised agents cover 70+ tasks and turn annual reports, industry research and internal records into a review ready first draft.
- Users iterate with the agent for deeper research and add client and industry knowledge. The credit manager makes the final call.
- Positioned as capturing the knowledge of its best RMs and credit risk managers.
- Credit memo and related work is up to 40% of RM time. The goal is at least 30% less. **This is a target.** No measured pilot result has been published. One outside analysis works out that this is about 12% of an RM's role at most.
- Governance: agent registry, guard rails, accountability, observability, traceability and agent evaluations.
- Source wording differs on "70 tasks" and "70 agents", so treat 70 as a rough scale.

### OCBC: a reusable copilot and a published evidence retrieval design
- RM Credit Copilot won two Asian Banker AI awards in May 2026. It grew from one automation tool into a reusable capability across several use cases.
- OCBC AI Lab published its retrieval design in May 2026. Standard RAG finds passages that are on topic but not useful for a credit decision.
- The paper does not name the RM Credit Copilot. Treating the design as part of the copilot is an inference, based on team posts that describe the same credit proposal work. It is not confirmed.
- The design has five stages: structured ingestion, hybrid keyword and embedding retrieval (top 50), a light model filtering for relevance and support, a stronger model scoring usefulness, then context aware extraction.
- Simple tables are parsed. Complex tables are kept whole with document and page reference for manual checking. Intermediate results are stored for traceability.
- Runs fully on premise with self hosted open source models, and handles multiple languages.
- Reported result: over 800 analysts, document review from several hours to about 3 minutes. **This covers document review, not the full memo**, and the evaluation data is not public.
- A secondary source, citing an OCBC filing, reports credit prep time down by up to 30%. Primary filing not read.
- Built jointly by the AI Lab, the wholesale banking platform team and the Digital Transformation Office.

### What this means for WB Credit

| Finding | Implication |
|---|---|
| DBS states that bankers own the final memo and that the credit manager makes the final call. OCBC's paper describes decision support with manual verification, but does not address memo ownership | Keep AI at draft level; approval stays human |
| Public accounts focus on the draft | Section readiness and ES tracking are where this prototype can show something different. This research found no public description of either at these banks, which does not mean they lack them |
| DBS and the OCBC copilot are framed around RMs, though DBS also covers credit risk managers and OCBC's paper refers to analysts; ours is CA led | Design for CA, Credit Head and Credit Approver rather than copying an RM copilot |
| DBS captures its best people's knowledge | Per team playbooks, starting with FIG |
| OCBC found similarity is not usefulness | Section specific retrieval with a usefulness check |
| OCBC keeps complex tables whole | Numbers come from Phase 1 spreading; narrative cites the source table and page |
| The DBS figure is a target, and the OCBC figure covers one step | Quote each exactly as labelled, and capture our own baseline |

---

## 9. Prototype measures [Proposed]

Captured by the workflow itself:
- Time from first upload to first full draft
- CA edit distance per section, draft vs final
- Return count and which sections are returned
- Share of claims with a source link
- Share of gaps closed from public sources, and how many of those the CA confirmed
- Baseline for comparison: manual hours per ES, only if the team can share it. If not, the baseline stays blank rather than using an assumed number

---

## 10. Demo scenario [Proposed]

Borrower: an SGX listed REIT with a recent annual report and an external credit rating (Business decision, 10 Nov 2026; shortlist in Codex task 0002). The borrower is ESR-REIT (Business decision, 10 Nov 2026), on condition that the demo is built around a specific target building as the financing object. That building is 16 Tai Seng Street, a property in ESR-REIT's public annual report. The facility is synthetic: renewal and upsize of a secured term loan against that building, plus an unsecured revolving credit facility. Property-level documents are synthetic but consistent with the public figures. This brings the property documents into scope and gives covenants to monitor.

Inputs arrive in three tranches:
1. **Term sheet and RM business support email.** The agent finds the annual report, unitholding and sponsor structure, a rating agency release and recent exchange announcements publicly, and Phase 1 spreads the financial statements. From the annual report it also finds summary valuations and the portfolio lease expiry profile, labelled public and partial. Sections 4, 5, 6, 7 and 10 become draftable, with 8 and 9 partial. The gap list asks the client for the full valuation report, insurance report, rent roll, lease profile for the secured property and financial projections; the RM for the CAS and pricing report; and internal teams for the prior ES, prior approval conditions, covenant monitoring report, account conduct report and internal rating.
2. **CAS, prior ES, prior approval conditions, covenant monitoring report, compliance certificate, pricing report, valuation report, insurance report, rent roll, lease profile and financial projections added.** Sections 1, 2 and 3 complete, 8 and 9 become full, then 11 opens.
3. **Account conduct report and internal credit rating report added.** Sections 12 and 13 complete, then 14.

Then: CA submits, Credit Head returns section 9 with a comment, CA fixes and resubmits, Credit Head supports, Credit Approver approves. A revised valuation report arriving after the CA has edited section 8 shows the Stale behaviour.

---

## 11. Scope

**In:** one FIG case end to end, upload and folder intake, missing data suggestions with public search, gap analysis, 14 section drafting with sources, section level editing and section chat (typed), pre-submission checks with a labelled credit master future capability panel, three role approval flow with approver question and decline, ES status tracking, ES export filled from the uploaded Word template, template admin with change classification.

**Out:** live system integration (including the credit master system check), real entitlements and single sign on, automated credit decisions, voice input, CBK and CMB content for now.

**Stretch, otherwise roadmap:** credit admin support step (section 2.12).

---

## 12. Open questions

Defaults below are **[Proposed]** and apply unless the project owner says otherwise.

1. **Input document types:** received 10 Nov 2026, not the full list. The catalogue in section 3.2 is open for additions.
2. **Environment:** the build folder is `wb_credit`. Web access is available, so public search is on (Business, 10 Nov 2026). Still open: where the handed over version runs, and which model is approved there.
3. **Mandatory inputs:** confirm the mandatory flags in section 3.2. Default: as assumed there.
4. **Case types:** new and renewal only, or also amendments and annual reviews? Default: new and renewal only.
5. **Rating and recommendation:** confirm rating is input only, and whether section 14 starts from the CA's stated position. Default: yes to both.
6. **Approver outcomes:** approve, question, decline and return are confirmed (10 Nov 2026). Is approve with conditions a separate outcome? Default: yes, configurable.
7. **Export format:** Word, filled from the uploaded template (10 Nov 2026).
8. **CBK and CMB:** are their templates coming now, or is configurability enough for this phase? Default: configurability only.
9. **Phase 1:** repo folder confirmed present. Is it the version to extend?
10. **Handover:** who owns this after 27 Nov?
11. **Demo borrower:** ESR-REIT, with 16 Tai Seng Street as the financing object (Business, 10 Nov 2026).
12. **Section chat:** confirm that the CA accepts revised text before it replaces the section. Default: yes.
13. **Template admin:** confirm that formatting-only changes go live after admin confirmation, and that prompt and code changes become a change list for IT. Default: yes.

---

## 13. Effort and timeline [Proposed]

**Assumptions:** one builder using AI assisted coding, extending the Phase 1 codebase, on public and synthetic data. A build day is one focused working day on this project.

| # | Workstream | Build days | Tier |
|---|---|---|---|
| 1 | Setup: extend Phase 1, data model (case, document, section, version, event, comment), FIG configuration | 0.5 to 1 | Core |
| 2 | Demo data pack: public documents for the borrower, synthetic files for about 12 client and internal document types, and a late update | 1.5 to 2 | Core |
| 3 | Intake, readiness and missing data suggestions: upload and folder scan, classification, catalogue and case rules, triggered suggestions, public search with labelled finds, gap list by who to ask | 2 to 3 | Core |
| 4 | Evidence retrieval with document and page citations | 0.5 to 1 | Core |
| 5 | Drafting all 14 sections: prompts, computed tables for 2 and 13, Phase 1 figures for 10, gap markers, Stale handling | 2.5 to 3.5 | Core |
| 6 | CA workspace: case dashboard, section editor with source panel, redraft and confirm | 2 to 2.5 | Core |
| 7 | Approval flow: role switcher, states, lock, return naming sections, version history | 1 to 1.5 | Core |
| 8 | Word export | 0.5 | Core |
| 9 | End to end test on the demo scenario, fixes, reset script | 1 to 1.5 | Core |
| 10 | Handover pack: setup guide, how to swap in the real template, demo script, known limits | 0.5 to 1 | Core |
| | **Core total** | **12 to 17.5** | |
| 11 | Usefulness check on retrieved passages | 0.5 to 1 | Should |
| 12 | Per section comment threads and version diff view | 1 | Should |
| 13 | Measures capture | 0.5 | Should |
| 14 | UI polish | 0.5 to 1 | Should |
| | **Full scope total** | **14.5 to 21** | |

**Calendar:** 14 working days, Tue 10 Nov to Fri 27 Nov 2026. Mon 9 Nov is the Deepavali holiday in lieu.

**Delivery change (10 Nov):** the estimates above assumed one builder. Codex now builds through the mailbox (section 14) and can run outside office hours, so build hours are less of a constraint. The limits now are review and decisions, and how much the Codex plan allows.

**Scope added 10 Nov (evening):** template-filled export, template admin, section chat and pre-submission checks add roughly 3 to 5 builder days. Codex finished tasks 0001 and 0002 in about 10 minutes each, so build effort is not the binding constraint. Review, decisions and live-run approvals are.

**Reading:** with missing data suggestions added, the core is 12 to 17.5 days against 14 working days. It fits only with a second person on workstreams 2 and 9 (about 2.5 to 3.5 days), or if this project gets all 14 days and lands near the low end. The full scope does not fit for one person in this window. If time runs short, Should items go first. Stale handling, section level returns and the gap list stay in the core because they carry the business asks.

**Gates:**

| Window | Work | Gate |
|---|---|---|
| Tue 10 to Fri 13 Nov | Setup, demo data pack, intake, readiness and missing data suggestions | Three tranche uploads show provided, found publicly, missing and draftable correctly |
| Mon 16 to Fri 20 Nov | Retrieval, 14 section drafting, CA workspace | Full draft of the demo case with sources, editable. Go or no go on Should items |
| Mon 23 to Wed 25 Nov | Approval flow, Word export, end to end test | Demo scenario runs start to finish. Code freeze Wed 25 Nov |
| Thu 26 to Fri 27 Nov | Handover pack and walkthrough | Handed over to a named owner |

**Schedule risks:**
- **Environment and model:** if the prototype must run inside the bank on an approved model, access and setup could take several days. Decide this week.
- **Public search:** web access is available. A saved public pack is still kept for repeatable tests and as a fallback.
- **No real template:** drafts follow common practice. A 30 minute screen walkthrough with a FIG CA in the week of 16 Nov, using synthetic data only, would catch the largest mismatches.
- **Handover owner:** not yet named. Without one, handover is documentation only.
- **Phase 1 code state:** folder confirmed present, code not checked. If it does not run cleanly, add about 1 day.

---

## 14. Delivery model [Business]

Decided 10 Nov 2026, to keep within the project owner's Claude usage limits.
- **Until 11 Nov 2026:** Codex built the back end, tests and export through the mailbox, with the Claude chat session orchestrating.
- **From 11 Nov 2026:** a Claude build session (Fable 5.2) builds, starting with the workbench redesign in section 2.14. Its rules are in `CLAUDE.md`, and the build order is in `collab/HANDOVER_BUILD.md`.
- **Codex is the independent reviewer.** It runs regressions and reviews on request, and writes no application code (`AGENTS.md`).
- **Drafting model:** Fable 5.2 is also the first drafting model for live tests inside the app.
- **Mailbox:** `collab/queue/` holds tasks from the orchestrator and `collab/replies/` holds Codex's replies. A launchd watcher on the Mac runs `codex exec` when a task is open, on the ChatGPT subscription and never on an API key. The protocol is in `collab/README.md`, and the check-in procedure in `collab/ORCHESTRATOR.md`.
- **Escalated to the project owner:** paid runs, changes to [Business] items, choices only she can make, and the gate reviews on 13, 20 and 25 Nov.

---

## 15. Sources

- [DBS release, via The Asian Banker (19 Aug 2026)](https://www.theasianbanker.com/press-releases/dbs-rolls-out-agentic-ai-tool-to-support-corporate-credit-assessment-process)
- [CEO Tan Su Shan interview, The Business Times, on dbs.com](https://www.dbs.com/media/features/ceo-tan-shu-shan-on-how-agentic-ai-is-transforming-the-bank.page)
- [Analysis: target vs measured result, The Daily Brief](https://www.beri.net/article/dbs-agentic-credit-memo-1500-bankers-target-not-measured-result)
- [OCBC AI Lab paper, arXiv (May 2026)](https://arxiv.org/html/2605.20684v1)
- [Asian Banker AI Excellence Awards 2026](https://www.theasianbanker.com/updates-and-articles/ocbc-pudao-credit-kasikornbank-bank-mandiri-and-atmaal-recognised-for-excellence-in-ai-deployment-across-asia-pacific)
- [OCBC AI use case summary, secondary source](https://www.bankingnewsai.com/banks/ocbc)
- [OCBC team post on the credit proposal journey, LinkedIn](https://www.linkedin.com/in/ezekiel-tee-9635a079/)
- [MAS: leverage requirements and disclosures for REITs (28 Nov 2024)](https://www.mas.gov.sg/news/media-releases/2024/mas-rationalises-leverage-requirements-and-introduces-additional-disclosures-for-reits)
