# Start here

**Existing fork:** [AurinVos/EnzyDesign-Lit](https://github.com/AurinVos/EnzyDesign-Lit).
This is a genuine fork of
[Bas van der Velden's AI food safety review](https://github.com/basvandervelden/ai_food_safety_review).
The derivative is titled **Enzyme Evidence Atlas**; original MIT attribution is retained.

**Offline use:** open `Enzyme_Evidence_Atlas.html` (self-contained) or serve
`index.html` from a local HTTP server. The 26-paper starting collection is
source-checked with AI assistance, not an independently expert-reviewed
systematic review.

## Enable hosting and literature refresh

1. Go to **Settings → Pages** in `AurinVos/EnzyDesign-Lit`; set
   **Build and deployment → Source: GitHub Actions**.
2. Under **Settings → Secrets and variables → Actions → Variables**, create
   `PUBLISH_PAGES=true` and `ENABLE_REFRESH=true`.
3. Under **Actions**, enable workflows if prompted. Manually run
   **Publish evidence map** on `main`; inspect the build and deployment jobs.
4. Manually run **Refresh enzyme literature** with `provider=europepmc`;
   inspect the retrieval report, new candidate records, and generated site.
   This does not require an LLM key.
5. Optional: set `OPENALEX_API_KEY` as a **repository secret** to enable
   OpenAlex retrieval. Do not commit credentials.

A push of code alone does not prove that hosting or retrieval succeeded.
GitHub can disable scheduled Actions workflows on forks or inactive projects.
No model-assisted screening is activated by default.

## For an entirely new fork

On an authenticated workstation with Git, GitHub CLI, Node 22, and Python 3.11+:

```bash
gh auth login
bash scripts/fork-and-publish.sh --name a-new-repo-name
```

The publisher first tests the project, creates a genuine GitHub fork of Bas's
repository, retains its Git ancestry, overlays this adaptation, pushes without
force, and optionally configures GitHub Pages. The script refuses an existing
repository by default. The `--update-existing` option is potentially
destructive; never use it without inspecting and backing up remote changes.

For known limitations and the offline test record, see
[docs/VALIDATION.md](docs/VALIDATION.md). Scientific classifications should
be independently checked before they are used as evidence for a review.
