# Validation report — v0.1.0

Prepared **15 October 2026**. This report separates observed local results from untested external operations.

## Observed results

| Check | Result | Evidence |
|---|---|---|
| Python unit and fixture integration suite | **77 tests passed** | `reports/unit-tests.txt` |
| Browser behavior and responsive rendering | **35 checks passed** | `reports/browser-smoke.json`, `reports/browser-run.txt` |
| JavaScript syntax | Passed `node --check assets/app.js` | Executed locally |
| Publisher Python syntax | Passed compilation | Executed locally |
| Publisher shell syntax | Passed `bash -n scripts/fork-and-publish.sh` | Executed locally |
| Workflow definitions | All three YAML files parsed with expected event/job keys | Static syntax check, not a live GitHub run |
| Dataset validation | 26 distinct DOI records; no test fixtures in released dataset | Python validator and seed tests |
| Embedded HTML build | Rendered without external script/style dependencies | Build tests and browser rendering |
| Upstream attribution | Present in website, README, NOTICE, LICENSE and citation file | Source/build checks and browser text checks |

Python tests cover identifier normalization, no-DOI stable IDs, provider null fields, date precision and future dates, invalid API shape versus empty results, retry handling, pagination caps, explicit malformed-record accounting, DOI deduplication, persistent exclusions, preservation of curated fields, named review requirements, immutable failed/dry-run updates, unsafe URLs, HTML/script escaping, CSV formula prefixes, optional model-output constraints, no fake live-search state, correct date/year distinctions, collection-filter markup, and publisher copying that retains the `.git` directory.

The browser tests cover initial rendering, pagination, author/objective/sequence-space/review filters, empty state, sorting, timeline/matrix clicks, shortlisting through the storage adapter, evidence dialogs, required reviewer fields, local draft handling, export serialization, dark mode, 390-pixel and 320-pixel viewports, keyboard Escape, no JavaScript exceptions, and the no-JavaScript static snapshot. A malformed collection selector was found and fixed; a regression test was added. Mobile statistics were changed to a two-by-two layout to prevent cramped date-range rendering.

## Important browser limitation

The managed Chromium environment blocked both file navigation and local HTTP navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. We did **not** bypass that restriction. Instead, the standalone HTML was loaded directly into a browser document through Playwright's content-loading interface. Local storage was explicitly emulated for the storage-dependent checks. The recorded run therefore verifies real browser DOM/JavaScript rendering and interaction, but **not** delivery over HTTP, native origin storage persistence, or operating-system download transfer. Export tests inspect the actual generated Blob contents while suppressing the final download anchor. Screenshots are actual Chromium renders, not mockups.

Environment: Python 3.13; Node 22; Playwright 1.57.0; locally available Chromium 144.0.7559.96. The GitHub CI configuration targets Python 3.12 and Node 22 but has not been executed remotely for this package. Browser smoke tests can be run in normal local-server mode on a workstation where navigation is allowed:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 -m agent.render_static
python3 tests/browser_smoke.py
```

The limited-mode local validation was run as:

```bash
python3 tests/browser_smoke.py --content-mode --chromium /usr/bin/chromium
```

## Not verified during this build

**At the original local-package validation stage**, no remote fork had been created; repository administration, GitHub Actions execution and Pages deployment had not been exercised. A fork was subsequently created by the repository owner at `AurinVos/EnzyDesign-Lit`, with confirmed GitHub fork ancestry and write permission. The original local testing claims remain restricted to offline code and browser checks. GitHub Actions deployment and live retrieval are **not** covered by this validation. The included publisher utility was tested locally but has not been exercised as an end-to-end remote publication mechanism in this environment.

The Europe PMC and OpenAlex adapters were tested using deterministic source-shaped fixtures, not successfully executed against their live endpoints from this environment. API syntax was checked against official documentation, but that is not an end-to-end proof. The released `meta.last_search` remains null. No scheduled retrieval is claimed to be active. Optional paid LLM requests were tested with fake responses only; no API key or charge was used.

There was no independent full-text scientific review, exhaustive search recall evaluation, quantitative extraction validation, external-link health sweep, security penetration test, multi-browser matrix or formal WCAG conformance audit. Passing software tests cannot establish these outcomes.

## Suggested acceptance sequence after deployment

First publish the existing source-checked collection and confirm it renders at the Pages URL. Then manually run a narrow Europe PMC query, inspect returned records and the actual search log, and check the candidate filter. Run the normal-mode browser tests against the same release on a workstation. Review a representative candidate sample before expanding the history window or enabling optional paid classification. Reconcile preprint versions and incomplete author metadata before using exports in a manuscript.
