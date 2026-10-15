# Methodology and evidence safeguards

## Review type and scope

This release is a **selected living evidence map**, not a completed systematic review. Its 26-paper seed was assembled to exercise enzyme discovery, engineering and design use cases, including historical experimental work and newer computational approaches. The seed does not estimate field prevalence, use an exhaustive screening denominator, or claim independent double-screening. Bas van der Velden's source platform supplied the architectural starting point, not enzyme inclusion decisions.

Enzyme-level discovery can occur in natural or non-natural sequence space. Engineering modifies a known scaffold. Design uses explicit functional or structural specifications to construct candidates. These axes are non-exclusive. Engineering a production pathway is not automatically enzyme-sequence engineering. General protein methods belong only where enzyme applications or enabling enzyme-analysis tools justify inclusion.

## Initial source checks

Each seed row provides its DOI, publisher/primary bibliographic source, access date, abbreviated attribution, date precision, original summary, evidence note and the basis of the annotation. The initial annotations use titles, abstracts and source metadata, not a complete independent full-text extraction. “Curated” is displayed as **Source-checked seed · AI-assisted**, not “expert verified”. The experimental evidence label is study-level and may refer to a selected validation subset. Resource links were included only when associated with the source record; code availability is not a licence audit.

No sequence accessions, reaction identifiers, kinetic constants, substrate structures or quantitative performance claims are invented to fill empty fields. Metadata that has not been extracted stays empty or “Not assessed”. The first-online/issue distinction is retained for sources where it changes the year; uncertain first-online days remain year precision. Bibliographic exports disclose incomplete author metadata.

## Search protocol

`config/searches.json` is a versioned list of independent query blocks. Europe PMC provides a life-science source, including PubMed-indexed records and preprints represented by the provider. OpenAlex adds broad scholarly coverage as an optional provider. Neither service is a substitute for all specialist/engineering databases. PubMed is substantially represented within Europe PMC; treating both as statistically independent coverage would be misleading.

The blocks cover discovery/function prediction, engineering, design, metagenomics, protein language models, active learning, terpene synthases, P450s, transferases and biocatalysis. Provider translations are not logically equivalent: Europe PMC uses fielded Boolean queries; OpenAlex uses deliberately broader text searches. Neither retrieval recall nor classifier precision was benchmarked on an independent gold standard in this release. Queries require iterative validation with a domain librarian and reviewers before supporting a systematic-review claim. Relevant work can be missed when terminology, source coverage or indexing differs.

For incremental Europe PMC retrieval, either the first publication date or first indexing date can fall within the lookback; a maximum publication date avoids future records. OpenAlex uses a publication-date lookback, so delayed indexing outside that interval requires periodic historical reconciliation. A historical request is split by calendar year. Per-query reports retain the query text, time window, retrieved and reported counts, page cap, invalid records and truncation status. The search configuration hash and classifier version are retained.

Complete pagination means **complete within the selected provider query at that retrieval time**, not complete literature coverage. No query success is inferred from a malformed/error response. The default preserves valid candidates and visibly reports truncation; strict mode aborts on any capped or invalid result window. Retrieval failure leaves the canonical dataset unchanged. Review decisions and exclusions persist through repeated searches.

## Deduplication and versions

Normalized DOI is the canonical identifier when available. Otherwise a provider namespace and stable ID are used. Duplicate DOI matches are merged without replacing curated annotations. Multiple provenance events can be retained. Title similarity is not used as an unrecorded merge criterion. Cross-provider no-DOI duplicates and later DOI assignment need reconciliation. Preprints and journal articles with different DOIs are version-linked via `related_ids` when established; they are not counted as independent experiments without review.

## Screening and synthesis

All structurally valid retrieved records enter a candidate queue. Keyword matching suggests labels but never silently rejects a result or infers experimental validation. Optional LLM tagging sends only metadata, treats the text as untrusted evidence, constrains outputs and leaves status/evidence unchanged. Prompt/input hashes and model identifier support audit, not scientific calibration. There is no fabricated confidence probability.

A human decision requires stable ID, reviewer name, timestamp, inclusion/exclusion/needs-review status, actual material reviewed, and reason. These are self-attested audit fields, not authenticated reviewer identity or a cryptographic approval. The static application stores only local drafts. A validated import updates the canonical dataset and appends review history. Taxonomic corrections can be edited in the versioned JSON and reviewed in a pull request; the initial browser review form changes status/reason, not every scientific field.

No automated narrative synthesis, method superiority claim or cross-assay kinetic ranking is generated. Charts count selected papers or filtered intersections. Overlapping labels can increase cell totals, and sparse curated coverage is not evidence that a field has little research.

## Sources and contracts consulted

- Upstream project: https://github.com/basvandervelden/ai_food_safety_review
- Europe PMC API: https://europepmc.org/RestfulWebService
- OpenAlex API and authentication: https://help.openalex.org/api/ and https://help.openalex.org/api/authentication/
- GitHub CLI fork: https://cli.github.com/manual/gh_repo_fork
- OpenAI structured-output interface: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

Consulted 15 October 2026. External contracts and quotas can change. The API adapters have fixture tests, but live external endpoint execution was not possible in the build environment; see validation report. The cited primary source links in each paper, not this general methods document, support its scientific annotation.

## Recommended next scientific gate

Before expanding claims, have independent reviewers assess the seed classifications and a representative candidate sample, calibrate search blocks against known positive studies, audit false exclusions/missed records, extend full author metadata, and establish full-text inclusion/extraction criteria. Then perform a historical backfill with explicit recorded coverage limits. This is a substantive review task, not something the website skin or passing software tests can replace.
