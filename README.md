# Enzyme Evidence Atlas

A source-linked literature map for **enzyme discovery, engineering and design**. Experimental methods are included alongside machine learning, protein language models, active learning, genome mining, simulation and generative design.

**Acknowledgement:** adapted from [Bas van der Velden's Living AI for Food Safety](https://github.com/basvandervelden/ai_food_safety_review). The original MIT copyright and licence are retained. See [NOTICE.md](NOTICE.md) for the exact attribution, adaptation scope and upstream tree provenance.

## Open the working version

Open **`Enzyme_Evidence_Atlas.html`** in a modern browser. It is self-contained: no installation, external fonts, JavaScript libraries, API key or backend is needed. The split-file site is `index.html` with `assets/` and `data/` beside it.

For a local server:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
# Open http://127.0.0.1:8000/
```

Browser security policies in managed institutional environments may block local-file scripts. Use the local server or GitHub Pages in that case. Local shortlists and review drafts are origin-specific; changing from a file to a server does not necessarily carry them across. Export drafts before switching.

## What is in v0.1.0?

The release contains **26 source-linked starting papers (1993–2026)**. Twenty-four report experiments, one is a review, and one describes a computational enabling tool. These are **AI-assisted, source-checked seed annotations**, not independent expert approvals or the result of an exhaustive systematic search. No automated retrieval run is falsely represented as completed in the bundled dataset.

The application provides searchable cards and evidence/provenance dialogs; filters for objective, method, enzyme family, sequence space, year and evidence; clickable timeline and method–objective intersections; local shortlists; filtered CSV/JSON/BibTeX export; and local review decisions with a reviewer, reason and review basis. The Python pipeline provides Europe PMC and OpenAlex adapters, bounded cursor pagination, query logs, persistent screening decisions, historical backfill, safe static rendering and optional structured-output model suggestions.

**Not included:** a comprehensive enzyme-sequence database, extracted reaction SMILES, automated kinetic comparisons, full-text systematic screening, authenticated multi-user review, paid database access, or a remotely running service. `targets`, `annotations`, `resource_links` and `related_ids` provide extension points; empty fields are not hidden claims of extracted data.

## GitHub fork and deployment

This enzyme-specific adaptation is maintained in
**[AurinVos/EnzyDesign-Lit](https://github.com/AurinVos/EnzyDesign-Lit)**,
a genuine fork of
[Bas van der Velden's source repository](https://github.com/basvandervelden/ai_food_safety_review).
The MIT licence and upstream commit history are preserved.

For a new fork under another GitHub account, the original publishing utility
(`bash scripts/fork-and-publish.sh`) remains available. It creates a **new**
destination by default, runs tests, overlays the enzyme files, and can configure
Pages. It refuses existing repositories without the explicit
`--update-existing` flag.

The code can be viewed without enabling Pages, but the public site and weekly
refresh workflow require configuration. In **Settings → Pages**, select
**GitHub Actions** as the build source. In **Settings → Secrets and variables →
Actions → Variables**, set `PUBLISH_PAGES=true` and `ENABLE_REFRESH=true`.
Enable the fork's Actions workflows if GitHub has disabled them, then run
**Publish evidence map**. Run **Refresh enzyme literature** with Europe PMC
to verify external retrieval; a successful site build does not prove data
collection ran successfully. See [START_HERE.md](START_HERE.md).


## Retrieval and review

Runtime code and unit tests use the Python standard library only. Node is used for a JavaScript syntax check, not for hosting or building the site.

```bash
# Validate and rebuild the existing source-checked collection.
python3 -m unittest discover -s tests -t . -v
node --check assets/app.js
python3 -m agent.render_static

# Keyless Europe PMC: publication dates OR newly indexed dates in the lookback.
python3 -m agent.update --provider europepmc --days 120 --max-pages 3
python3 -m agent.render_static

# Explicit historical backfill, split into calendar years.
python3 -m agent.update --provider europepmc --start-date 2000-01-01 --max-pages 10

# Strict retrieval completeness within selected queries, not completeness of the field.
python3 -m agent.update --query-id terpene-synthases --require-complete

# Preview without writing; this still makes network/API calls.
python3 -m agent.update --provider europepmc --dry-run

# Import a named human review exported by the browser.
python3 -m agent.update --decisions /path/to/review-decisions.json
python3 -m agent.render_static
```

Newly retrieved records are always **candidates**. The default public view includes only the source-checked seed and human-reviewed records. To inspect incoming papers, select “Automated candidates” or “All non-excluded records”. A successful search can therefore add candidates without changing the selected view.

The updater does not silently filter out records based on a keyword relevance score. All structurally valid query matches are retained as candidates. Truncated windows and malformed source records are counted in the search report. `--require-complete` aborts before dataset changes when these occur. Source failures or invalid review imports leave `data/papers.json` unchanged. Logs are individually written atomically before the dataset; a process crash between those writes can leave an orphan report and is not a completed dataset update.

Previously curated/excluded records are not relabelled by automated updates. The same DOI is deduplicated. A no-DOI record uses its stable provider ID. Cross-provider records without a shared DOI, preprint/journal versions and records that later acquire a DOI require reconciliation; they are **not guessed identical from similar titles**. Link known versions with `related_ids`.

### Optional providers and paid classification

OpenAlex cursor retrieval requires `OPENALEX_API_KEY`. Europe PMC does not require it. For OpenAlex:

```bash
export OPENALEX_API_KEY='your-key'  # Prefer a secret manager rather than shell history.
python3 -m agent.update --provider all
```

Optional LLM suggestions require both `OPENAI_API_KEY` and **an explicitly chosen** `OPENAI_MODEL` supporting Chat Completions structured outputs:

```bash
# Set OPENAI_API_KEY and OPENAI_MODEL through your secret manager first.
python3 -m agent.update --provider europepmc --llm
```

This sends titles/abstracts to the selected API and may incur charges. At most 50 new records are sent per run by default (`--llm-max-records` controls the explicit budget); remaining records retain keyword suggestions. It is **off by default** and is not enabled by the scheduled workflow. The model can suggest objective/method labels and a short summary. It cannot upgrade a record to human-reviewed or infer an experimental evidence label. Model, prompt hash and input hash are recorded. Failed/refused responses stop the update without committing the new dataset. Scientific correctness still needs human review.

## Automated workflows

`ci.yml` tests and builds without calling publication or LLM services. `publish.yml` deploys only when repository variable `PUBLISH_PAGES=true`. `refresh.yml` runs on Mondays at **07:15 UTC** and can be run manually, but only when `ENABLE_REFRESH=true`. GitHub may delay or disable schedules, particularly on forks/inactive repositories; inspect Actions rather than assume they ran. The publish script explicitly enables the workflow. Daylight-saving changes mean the UTC schedule is not a fixed Netherlands local time.

Refresh uses a 120-day lookback, three pages per query and 100 records per page. It commits candidates and search reports only after tests/build succeed, then explicitly invokes the reusable Pages workflow because bot commits do not start ordinary downstream push workflows. No force push or branch-protection bypass is used. On protected branches, use a maintainer-controlled import/PR workflow instead of granting the bot a bypass.

## Data and scientific interpretation

`data/papers.json` is canonical. The renderer derives `data/papers.js`, `data/papers.csv`, `index.html`, the self-contained HTML and `_site/`. Never edit generated JS/CSV in place. `agent/seed.py` can regenerate the initial selection, but refuses to replace existing data without `--reset`. That flag **destroys later records and decisions**, so it is not used in any scheduled workflow.

Objectives are non-exclusive and independent of sequence origin. A discovery in generated sequence space is still a discovery; engineering concerns changes to a scaffold; design concerns specifications/construction. “Enzyme family / group” is a practical browsing label, not a replacement for a formal EC, Pfam or phylogenetic classification. A paper can span multiple groups.

The timeline uses first-online dates when resolved; less precise dates retain their actual precision. Later issue years are separate. A paper count is not a measure of scientific progress, impact or total literature volume. “Experimental assays reported” does not mean every variant or prediction was validated. No across-study ranking of kinetic constants or titers is implied.

CSV exports neutralize spreadsheet formula prefixes. BibTeX export deliberately omits incomplete author lists and carries an explicit completion note; retrieve full author metadata from the DOI before manuscript submission. Publication links and source checks are included with each record. See [docs/METHODOLOGY.md](docs/METHODOLOGY.md), [docs/DATA_MODEL.md](docs/DATA_MODEL.md) and [docs/VALIDATION.md](docs/VALIDATION.md).
