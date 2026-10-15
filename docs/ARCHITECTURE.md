# Architecture and maintenance

## Data flow

`config/searches.json` → `agent/providers.py` → normalized candidate records → `agent/update.py` → `data/papers.json` → `agent/render_static.py` → `_site/` and self-contained HTML.

A separate review path runs from the browser's local draft store → exported review JSON → validated `agent.update --decisions` import → the same canonical paper dataset. Optional `agent/llm.py` supplies suggestions only; it does not approve papers. `agent/common.py` centralizes identifiers, safe serialization and validation. `agent/classify.py` holds the conservative keyword suggestion rules. `agent/seed.py` is a reproducible initial selection, not an update job.

## Operational boundaries

The public application is static. It never holds an API secret and does not send reviewer notes or shortlists to a server. The Python process or GitHub Actions job retrieves metadata. Model calls are explicit and off by default. The current browser reviews are not a collaborative online review database. Imported reviewer metadata becomes part of the public record, so avoid private information.

The canonical paper dataset is validated before replacement. Every output file is written atomically. Retrieval and review errors before commit preserve the old canonical dataset, although a crash between a log write and data write can leave a report not associated with the current dataset. GitHub refresh only commits after the tests and static build complete. Non-fast-forward pushes fail; the workflow does not force-reset maintainers' changes.

`_site/` contains an explicit allow-list of public files. Workflow logs and repository data still need ordinary access-control care: a public repository makes tracked provenance and imported review identities public even when a file is not copied into `_site/`.

## What changes when adapting the schema?

Change the controlled vocabulary in `config/project.json`, the candidate rules, source normalizers as needed, the corresponding UI labels/chart method list, and tests together. The data schema has an explicit version. The current release does not silently migrate unknown versions. Arrays of objectives/methods allow overlaps; publication type, evidence and review status remain separate dimensions.

New biological entities (individual enzymes, sequences, reactions, assays, host contexts) should be introduced as stable-ID tables linked to publications, not inferred from publication-level tags. Numerical outcomes should preserve units, assay conditions and provenance at their own entity level. Similarity networks and domain mappings are useful extensions but are not already implemented here.

## Reuse and attribution

Bas van der Velden's original evidence map supplied the open foundation, UI/publishing concept and source-linked review architecture. This adaptation keeps its MIT attribution and records the inspected upstream tree in `config/project.json` and `NOTICE.md`. Its enzyme taxonomy, broad source retrieval, provenance handling and frontend have been substantially rewritten. No upstream authorship or endorsement of the new scientific annotations is implied.
