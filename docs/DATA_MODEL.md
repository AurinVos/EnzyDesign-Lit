# Data model, v1.0.0

`data/papers.json` contains `schema_version`, `meta` and an array of `papers`. A paper is the unit of the current literature map, not an individual enzyme, reaction or assay. One paper can describe many sequences and experiments. A future enzyme/assay database should introduce separate entities rather than place multiple incompatible kinetic records into one paper field.

| Field | Meaning |
|---|---|
| `id`, `doi` | Stable identifier; normalized DOI preferred, provider identifier otherwise. |
| `title`, `citation`, `journal` | Bibliographic display metadata. `citation` may be abbreviated. |
| `authors`, `authors_complete` | Seed full author lists are not extracted; empty/false is explicit. |
| `published_date`, `date_precision`, `year`, `issue_year` | Calendar date at supported precision; issue year is optional and separate. |
| `objectives[]` | Discovery, Engineering, Design; independent and non-exclusive. |
| `methods[]` | Controlled method labels from `config/project.json`. |
| `enzyme_families[]` | Practical browsing groups, not an asserted EC or phylogenetic ontology. |
| `sequence_space` | Natural, Engineered variants, De novo / generated, Mixed / general, Not assessed. |
| `validation` | Experimental assays reported, Computational evaluation, Review / perspective, Not assessed. |
| `status` | `curated`, `candidate`, `verified`, `excluded`; evidence and review status are separate. |
| `summary`, `evidence_note` | Original concise scope summary and qualifications. |
| `abstract` | Optional provider abstract. Empty in the bundled seed. Respect source terms before redistribution. |
| `source_url`, `provenance[]` | Original source, retrieval/access date, source identifier and basis. |
| `classification` | Keyword/model/AI-assisted seed method and provenance. Never an expert approval. |
| `resource_links[]` | Explicit linked code/data resources with label, kind and URL. |
| `related_ids[]` | Confirmed related versions/identifiers, not inferred from title alone. |
| `targets[]`, `annotations` | Extension points; no extraction is implied by their existence. |
| `review`, `review_history[]` | Latest imported human decision and append-only decision history. |

`meta.last_search` is null until an external retrieval has actually completed and been committed to this dataset. `meta.last_operation` distinguishes live search, offline import and review import. Tests using synthetic fixtures do not change the released dataset or create a fictional live-search timestamp.

## Review import

```json
{
  "schema_version": "1.0.0",
  "decisions": [
    {
      "id": "doi:10.1371/journal.pcbi.1008197",
      "status": "verified",
      "reviewer": "Your actual name",
      "basis": "title_abstract",
      "reason": "Your actual inclusion reason and limitations.",
      "reviewed_on": "2026-10-15T12:00:00Z"
    }
  ]
}
```

This is a format example, **not a review performed for the seed**. Valid `basis` values are `title_abstract` and `full_text`; record only the material actually inspected. Valid decision statuses are `candidate`, `verified`, `excluded`. Imported decisions require a known, unique ID and non-empty reviewer/reason. A malformed decision batch is not partially applied.

## Source and derived files

Edit `data/papers.json` and the configuration, then run `python -m agent.render_static`. The renderer writes `index.html`, `data/papers.js`, `data/papers.csv`, `Enzyme_Evidence_Atlas.html` and `_site/`. The public `_site` directory excludes tests, GitHub secrets, review drafts and full retrieval logs. Provenance and already-imported reviewer names are public in the paper dataset; do not record private information there.

CSV injection prefixes are escaped for safe spreadsheet opening. The JSON export preserves the structured arrays, metadata and provenance. BibTeX export uses unique keys within an export and omits incomplete author fields; it is a reading-list export, not submission-ready bibliography metadata.
