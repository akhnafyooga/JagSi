# JagSi MCU intake and onboarding PRD

Status: Proposed. Documentation milestone before feature implementation.

## Product scope

Every new account completes MCU intake for the person wearing the band. The first and primary action is **Upload MCU report (PDF or photo)**. Uploading is optional. Directly below it, show **Enter results manually**, followed by **No results available yet**. Either alternative can complete intake without an upload. The no-results path stores zero observations. Keep manual entry available when processing fails or a report is unreadable. Users can add or replace reports later. The caregiver account, monitored person, and device have separate identifiers.

The first release extracts printed laboratory rows from reports. Handwritten narrative, diagnoses, radiology interpretation, and ECG interpretation are outside the extraction contract. Unsupported sections remain visible in the source preview with a manual entry option. MCU data supplies dated context to the AI summary. Sensor alerts and fall detection retain their own rules and inputs.

## How the source report is produced

An examination or order identifies the requested tests. A lab records specimen collection when applicable, performs measurements, reviews the results, and issues a report. A corrected report can supersede an earlier version. A multi-page MCU can group several panels, draw times, and specimen types. The date printed next to “issued” can differ from the clinical observation date. Preserve each independently. This is a model for JagSi intake based on SATUSEHAT’s laboratory data model, not a requirement that source reports follow a single template.

| Input | Store and validate |
| --- | --- |
| Monitored person | Required profile selection or creation. Ask caregiver to confirm it is the correct person's report. Store the owner link, not an OCR-derived identity. |
| Examiner or laboratory | Optional issuer name and report number. Keep the report number scoped to the issuer. |
| Encounter date | Optional date or timestamp of examination. Separate from sample collection and report issue. |
| Collection and result dates | Optional per observation or specimen. Capture collection time and observation date if present, along with date precision, original string and explicit timezone when known. |
| Report issue date | Optional document version date. Keep separate from app upload and confirmation times. Never substitute the upload date. |
| Test and group | Original printed label, English display label, internal code, optional validated LOINC mapping, panel name and specimen if stated. |
| Result | Numeric decimal, comparator, qualitative text or explicit missing reason. Preserve original text. Keep a separate optional unit and original unit string. |
| Context | Explicit fasting, random, post-meal or unknown for glucose. Preserve report-provided ranges and flags as printed, including sex- or age-specific notes if applicable. |
| Traceability | Source mode, document/page and bounding box or PDF token span, parser/model version, review state and correction history. Manual rows have entry provenance and no page reference. |

Ambiguous dates such as 05/06/2026 require review when the format cannot be established. Parse Indonesian month names and explicit offsets. Accept date-only values without assigning a clock time. On inconsistent dates, show both source labels and ask for confirmation. Support decimal commas, decimal points, inequalities, qualitative values and absent units. Do not infer a unit, fasting state, range, or date from neighboring pages without evidence.

## English result sections

| Section | Example source label and English output |
| --- | --- |
| Blood glucose | Gula darah puasa → Fasting blood glucose. Gula darah sewaktu → Random blood glucose. HbA1c remains a separate result. |
| Lipid profile | Kolesterol total → Total cholesterol. Trigliserida → Triglycerides. Preserve HDL and LDL as separate tests. |
| Complete blood count | Hemoglobin, white blood cell count, platelet count. Preserve multipliers such as ×10³/µL. |
| Kidney panel | Kreatinin → Creatinine. Ureum → Urea. Preserve eGFR separately. |
| Liver panel | SGOT → AST and SGPT → ALT when the mapping is unambiguous. |
| Other results | Keep printed text and a reviewable English label for unfamiliar rows. Never force an unknown test into a guessed category. |

The result screen shows group, test, value, unit, report range, date and a link back to the highlighted evidence. A numeric value of 98 mg/dL is an extraction fixture only. JagSi does not judge the result from a generic threshold. Display flags explicitly attributed to the source lab.

## OCR and team-owned LLM

1. Validate PDF, JPEG and PNG by file signature and decoder. Proposed limits are 15 MB and 20 pages. Reject encrypted or invalid files with a manual fallback. Limit raster dimensions, memory, processing time and concurrent jobs. Keep parsing workers isolated and without outbound network access.
2. Extract embedded text and coordinates for digital PDFs first. For scans and photos, rasterize pages, correct rotation and skew, and run a locally hosted OCR engine. Benchmark OCR engines against the same bilingual fixture set before selecting one. Preserve word boxes and page order.
3. Detect header and table regions. Associate test names, values, units, ranges and flags by geometry. Preserve repeated headers and disambiguate multi-column panels. Create candidate rows with evidence IDs.
4. Run the team-owned LLM through a versioned private adapter. Send candidate structure and the minimum necessary redacted text. The LLM proposes English labels, panel categories and field associations under a strict JSON schema. It has no tools, user credentials, or access to unrelated records. Treat text from each document as untrusted data.
5. Validate every proposed observation. Require source evidence for values, comparators, units and dates. Prefer deterministic parsing for critical fields. Reject invalid JSON, unsupported categories and unsupported changes to source facts. Surface uncertain rows for review. On model timeout, show OCR drafts for manual correction.
6. Require explicit caregiver review. Highlight source next to each row, allow editing and deletion, and separate “needs review” from “confirmed.” Summary queries read confirmed observations only. Retain original and amended versions with a clear supersession history.

Start with the team model and glossary in benchmark mode. Record model ID, checkpoint, configuration, prompt version, OCR engine and schema. Fine-tune the LLM only if the error analysis shows a normalization or segmentation gap that layout parsing and the glossary cannot address. Use reviewed synthetic or authorized de-identified training examples. Hold out entire clinics/templates and document variants. Keep training and evaluation separate. Never use uploaded user reports for training by default. Model scores and accuracy claims require evaluation evidence.

## Services and AI summary contract

- Keep Next.js as frontend and FastAPI as API. Use durable background jobs with state persisted outside the worker. Use private object storage and a persistent database for deployed MCU records. Keep local SQLite suitable for development only. Do not store reports on Render’s ephemeral filesystem.
- Proposed endpoints under the monitored-person resource: create upload or manual draft, read processing state and candidates, confirm reviewed rows, record no-results completion, list confirmed reports, delete source/report where allowed. Require caregiver authorization against the monitored person for each operation. Use idempotency keys on creation and version checks on confirmation to avoid duplicate or overwritten reviews.
- Job states: queued, extracting, needs_review, failed, confirmed. Manual input enters needs_review directly. Store retries atomically. An unreadable file gives an actionable error and a manual path. Existing drafts resume after sign-in.
- Authenticate every report and onboarding route server-side. Authorize device binding and MCU ownership independently. Keep fixtures synthetic, reject unauthorized cross-account reads, and omit report data and public download URLs from logs. Define consent, deletion, retention and hosting approval before collecting real reports.
- Compose a two-part summary. Show the current sensor trend and a separate section with dated confirmed MCU facts. Report age and source stay visible. When the inputs disagree, show each reading with its time and source. With no confirmed observations, show “No MCU results provided yet.” The team LLM can phrase grounded summaries while numeric facts, warnings, and citations are validated by code. Keep urgent sensor alerts independent of MCU processing. Keep personalized diagnosis, treatment, diet or dosage advice outside this release.

## Onboarding and Figma handoff

Create editable mobile and desktop frames in the existing JagSi Ungu file before slicing new routes. Reuse Ungu typography and tokens. Prototype the happy path and failure paths with synthetic data.

| Screen | Required design and behavior |
| --- | --- |
| Landing | Reuse current landing. Add sign-in and registration entry points. Preserve existing caregiver navigation for signed-in users. |
| Sign in / Register | New route for forms, validation, duplicate account, failed sign-in, and in-progress continuation. Returning accounts with incomplete onboarding resume the saved step. |
| MCU submission | After confirming the monitored person, place the PDF/photo upload panel at the top, with the primary button “Upload MCU report” and a visible “Optional” label. Below it place “Enter results manually” and then “No results available yet.” Use this order on mobile and desktop, including keyboard and screen-reader order. Show progress, source preview, row grouping, correction, retry and confirm. No automatic submission. |
| Smartband guide | Dedicated screen with a left-wrist illustration and interactive donning and fit steps. Reveal the confirm control after three seconds. Announce availability without moving keyboard focus. Respect reduced motion. Confirm only advances after the user's action. |
| Completion | Show “Your loved one is now protected by JagSi” when the band connection is confirmed and monitoring is active. Otherwise show setup complete and the device connection status. “See live” goes to Beranda. |

Persist onboarding state server-side as account → MCU intake completed → guide confirmed → completion. Protect route transitions from refresh and direct URL entry. Keep MCU onboarding separate from verification that the watch is actually connected. Design reviews include focus, labels, reading order and viewport captures at 390 and 1440 px, plus tablet testing at 768 px.

## Validation and scoring

Proposed release targets below are acceptance gates. They are not measured results.

| Area | Gate and evidence |
| --- | --- |
| Corpus | Start with at least 200 synthetic or authorized de-identified reports, at least 2,000 labeled rows and at least 10 template families. Hold out at least 50 documents spanning unseen families. Report results by file type and scan quality, with sample counts and confidence intervals. Two reviewers resolve critical-field ground truth disagreements. |
| Extraction | Target ≥99% exact critical-field precision among accepted machine rows and ≥95% row recall on supported readable documents. Compare complete tuples of test, value, comparator, unit and date when present. Measure abstention and coverage to prevent a high score from accepting only easy rows. Target zero unsupported values or units in the blind set and report the actual observed count. |
| Segmentation | Target ≥98% correct English mapping and group assignment on supported rows. Report per-section scores and errors from fasting/random, decimal and mixed-unit examples. |
| Difficult input | Test rotated/blurry scans, shadows, mixed text/image PDFs, duplicate pages, ambiguous dates, missing ranges, split tables, multiple specimens, and document text that attempts to direct the model. Unreadable inputs reach review or manual entry. |
| End to end | Playwright verifies the upload-first order at mobile and desktop sizes and covers PDF, photo, manual, no-results, timeout/retry, review changes, resume after refresh, three-second guide, completion and See live. Verify uploaded results never appear in the summary before confirmation. Include Wokwi running concurrently and check alerts still arrive. |
| Regression and security | Check authorization boundaries, file parsing limits, duplicate/retried submissions, deletion, failed worker restart, wrong patient selection and stale device connection. Include keyboard navigation, mobile overflow and automated accessibility checks. |
| Performance | Proposed p95 ≤30 seconds for a clear two-page upload on the chosen deployment hardware. Measure from upload completion to review availability. Verify long files show progress and remain cancellable or replaceable. |

## Implementation order and deliverables

1. Document freeze and data contract. Deliver this PRD, the reviewed English glossary, machine schema, synthetic fixture manifest and signed-off evaluation set.
2. MCU scanner first. Deliver parser, OCR adapter, team LLM adapter, private processing jobs, review form, manual path and reproducible benchmark. Save evidence and failure examples without personal data.
3. Add summary integration. Deliver API tests demonstrating confirmed-only context and independent sensor alert behavior, plus screenshots of confirmed and no-results states.
4. Finish onboarding. Deliver editable Figma frames and prototype, responsive Next.js pages, server-side route guards, end-to-end tests and a linked PR. Include Figma links, browser captures and remaining deviations in the review.
5. Demonstrate with a synthetic report and Wokwi. Deliver a short demo script, final scores by input type, the model configuration used, and a list of known unsupported cases.

## Repository baseline

The checked frontend has a public landing page and caregiver routes for Beranda, Monitoring redirect, Riwayat, Profil and Darurat. It has no dedicated auth, MCU review, wrist guide or onboarding completion route. The dashboard AI summary consumes trend results. The backend also has a separate HealthAssistant implementation. Keep that distinction explicit when choosing the integration point.

## Sources

- [SATUSEHAT DiagnosticReport resource](https://satusehat.kemkes.go.id/platform/docs/id/fhir/resources/diagnostic-report/)
- [SATUSEHAT outpatient record and lab workflow](https://satusehat.kemkes.go.id/platform/docs/id/interoperability/rme-rawat-jalan/)

## Build handoff after the Quest spike

- Baseline: local PDF text and PNG OCR matched value, unit, range and flag on five selected rows of the Quest sample. This is a regression fixture, not a held-out benchmark. Keep the extraction evidence visible and require review. Run the broader corpus before release.
- Account and data boundaries: attach reviewed observations to the authenticated caregiver and selected monitored person. The demo telemetry device is shared. Keep lab records out of that device's public API, WebSockets and alert payloads. Query the lab context through a separate authenticated endpoint.
- Data collection: report upload stays first and optional. Preserve source date evidence and allow explicit examination, collection and issue dates. Date-only input stays date-only. Manual mode can record known observations or an explicit no-results outcome.
- Model integration: a team-owned model endpoint and model identifier must be supplied through server configuration. Use a schema-constrained adapter for approved row IDs, categories and English labels. Preserve numbers, dates, units, flags and evidence deterministically. Use glossary output when the model is unavailable. A fake model is acceptable only as a contract-test fixture.
- Release evidence: retain screenshots of desktop and mobile onboarding, a browser run for upload and manual paths, direct-route guard tests, an explicit test of the three-second guide timer, and report-to-summary provenance checks. Distinguish device readiness from setup completion. Real report processing remains gated until ownership, retention and deployment controls are verified.
