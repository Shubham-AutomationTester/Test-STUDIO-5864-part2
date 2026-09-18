# STUDIO-5864 - Robots Directive QA Lab

A ready-to-publish static site for testing SearchStax page-level robots directives. It includes a browser QA notebook, isolated crawl graphs, real HTTP-header deployment rules, same-URL lifecycle fixtures and a TestRail CSV.

**72 scenarios | 172 baseline fixture URLs | 51 defined-expectation cases | 7 conditional cases | 10 contract decisions | 4 lifecycle cases**

Actual SearchStax results are **Not run**. The included verification report checks the fixture package, not the product. No account credentials are needed to preview the site. Nothing in this package changes Jira or a SearchStax app.

## Start here

1. Extract the ZIP. Upload the **contents** of `studio-5864-robots-qa/` to a new GitHub repository. `render.yaml`, `netlify.toml`, `config.json`, `docs/`, `source/`, `tools/` and `qa/` should be at the repository root.
2. For complete HTTP-header coverage, deploy the repository using the **Render Blueprint** instructions below. Netlify is also supported.
3. Open the deployed site's root for the QA dashboard. Copy a **suite seed**, not the dashboard URL, into SearchStax.
4. Use a dedicated QA app/index. Verify the live fixture first, then execute the crawler and record actual evidence.

The site is prebuilt. No npm packages, framework, build dependencies, database or runtime backend are required. Python 3 is needed only for local tools or regenerating fixtures.

## Hosting options

| Host | Meta / link cases | Real X-Robots-Tag | robots.txt toggle cases | What to deploy |
|---|---|---|---|---|
| Render static site via Blueprint | Yes | Yes, from `render.yaml` | Yes, when deployed at host root | Entire repository; publish `./docs` |
| Netlify static site | Yes | Yes, from `docs/_headers` | Yes, when deployed at host root | Entire repository; `netlify.toml` publishes `docs` |
| GitHub Pages | Yes | Not supplied by these files; custom headers need a different hosting layer | Only if the host-root robots.txt contains the correct rules | `main` branch, `/docs` folder |
| Included local Python fixture server | Yes | Yes, including separate repeated field lines | Yes | Run from this repository |

A static HTML `<meta http-equiv="X-Robots-Tag">` is **not** a replacement for an HTTP response header. An `_headers` file works only on a host that implements that configuration format.

### Render - recommended full setup

1. Commit and push all extracted files, keeping the repository structure intact.
2. In the Render Dashboard, choose **New > Blueprint**, then connect the repository and deploy `render.yaml`.
3. Check the resulting service configuration:

   ```text
   Service:              Static site (runtime: static)
   Build command:        echo Static fixtures are prebuilt
   Publish directory:    ./docs
   Blueprint file:       render.yaml
   ```

4. Wait for the deployment status to complete, then open its assigned HTTPS URL.
5. Confirm the host's response-header rules were imported. **New > Static Site** alone does not automatically apply a repository's Blueprint header rules. For manual configuration, use the entries in `qa/render-header-rules.csv`, plus the global Cache-Control rule.
6. Do **not** add a catch-all rewrite to `/index.html`. It would turn missing fixture paths into dashboard responses and contaminate test outcomes.
7. Run the live verification command below before grading the crawler.

For Render and Netlify root hosting, keep `base_path` empty in `config.json`. The site has no start command and does not require a Python web service on either platform.

### Netlify

Connect the Git repository and retain the included `netlify.toml`. The publish directory is `docs`; its `_headers` file contains the real per-path response rules. For manual static deployment, upload the **contents of `docs/`**, preserving `_headers` and all subdirectories.

Repeated header values can be combined by a CDN. H07's strict physical-two-field variant should be tested using the included local fixture server or another environment verified to emit separate fields. A combined `noindex, nofollow` response is not evidence that the repeated-physical-field variant was exercised.

### GitHub Pages - partial coverage

In the repository, use **Settings > Pages > Deploy from a branch > main > /docs > Save**. The supplied `.nojekyll` preserves the static output.

Relative page, script and stylesheet paths work under a project prefix such as `/robots-qa/`. However:

- `docs/_headers` and `render.yaml` do not configure GitHub Pages response headers. Header-dependent cases must not be marked Passed there unless an independently configured proxy/host supplies the expected headers.
- A crawler consults the host-root `https://USER.github.io/robots.txt`, not `https://USER.github.io/robots-qa/robots.txt`. A project-repository robots file alone does not establish the R01-R06 precondition.

To prepare prefixed root-robots rules for a project repository, run:

```bash
python3 tools/build.py --base-path /robots-qa
```

Then **merge**, do not blindly replace, the generated `qa/robots-host-root-example.txt` entries into the host-root site's existing robots.txt. Obtain the root-site owner's approval. Publish the project and validate the root response. No changes are made to the host-root repository by this script.

Before switching this generated package back to a root-hosted Render/Netlify site, run:

```bash
python3 tools/build.py --base-path ""
```

## Local preview and fixture checks

From a terminal in the extracted repository:

```bash
python3 tools/serve.py --port 8000
```

Open `http://localhost:8000/`. The server supplies genuine GET and HEAD headers, preserves H07's repeated header fields, reloads generated files without a restart, and writes access events to `qa/requests.jsonl`.

The server binds to `127.0.0.1` by default. It is a local QA fixture server, not a production web server. A cloud-hosted SearchStax crawler cannot access your laptop's `localhost`; use the deployed public QA URL for end-to-end testing.

From a **second terminal**:

```bash
# Local fixture responses, source HTML, graph and host-root robots rules:
python3 tools/verify.py http://localhost:8000 --require-repeated

# Published full-coverage host:
python3 tools/verify.py https://YOUR-SITE.onrender.com \
  --report qa/live-fixtures.json

# A focused fixture check:
python3 tools/verify.py https://YOUR-SITE.onrender.com --case M03 --case H03

# GitHub Pages: intentionally skip unsupported custom-header/root-robots checks:
python3 tools/verify.py https://USER.github.io/REPO --profile github

# Offline structural graph audit only:
python3 tools/verify.py --structural-only
```

The verifier uses `STUDIO5864FixtureVerifier/1.0`. It intentionally requests otherwise suppressed URLs to verify their existence; these requests are **not crawler evidence**. Run it outside the crawler's evidence window. It does not inspect SearchStax, Solr, crawl queues or Datadog, and cannot report a product pass.

Do not use `python3 -m http.server` for full header coverage: it does not read the supplied header map. The custom `tools/serve.py` does.

## Which URL should I crawl?

Replace `BASE` below with the deployed origin and optional project prefix, without a trailing slash.

| Seed | Purpose |
|---|---|
| `BASE/suites/core/` | Generic meta, unrelated bot tags and link rules; no custom HTTP-header dependency |
| `BASE/suites/meta/` | 19 defined-expectation HTML-meta cases |
| `BASE/suites/links/` | 15 link-level and alternate-discovery cases |
| `BASE/suites/headers/` | 7 defined-expectation HTTP-header cases |
| `BASE/suites/robots/` | 6 robots.txt interactions; run OFF and ON with fresh state |
| `BASE/suites/bots/` | 6 matching-token cases, conditional on confirmed bot mapping |
| `BASE/suites/decisions/` | 10 exploratory cases pending a product decision; not release gates yet |
| `BASE/cases/h08/` | Plain-text control/restricted pair; establish .txt extraction support first |
| `BASE/cases/u01/` through `BASE/cases/u04/` | Same-URL lifecycle cases; use the phase sequence below |
| `BASE/cases/m03/` | Example: isolated noindex parent with a followable child |

**Scope must include both `/suites/` and `/cases/` under your site prefix.** Restricting traversal to the suite directory will prevent the actual test pages from being reached. For a single case, include that entire case directory, including its children.

Use depth at least 5 and an item budget at least 500, or an equivalent configuration that demonstrably does not truncate this graph. Disable sitemap discovery, URL imports and unrelated seeds. Do not seed target URLs. Exclude the operator dashboard, assets and 404 page from indexing.

Every target is case-local. No navigation, canonical tags, alternate tags, sitemap entries or global target list exposes it. L08-L11 deliberately introduce multiple paths **inside the same case**. R01-R06 use an allowed entry and blocked parent; the targets themselves are outside the robots-blocked path.

## Bot identity is intentionally unconfirmed

The ticket includes an unresolved example, `SearchStax Crawler/1.0 ???`. This package does not treat that as an established identifier. `searchstax` is the editable **placeholder meta-name token**, and `bot_mapping_confirmed` is false.

Capture the actual HTTP User-Agent from your crawl and confirm which meta-name token the implementation maps it to. The full HTTP User-Agent is not automatically the `name=` value.

After engineering confirms the token:

```bash
python3 tools/build.py --bot-name CONFIRMED_TOKEN --confirm-bot-token
```

Optionally document the captured HTTP User-Agent with `--user-agent "ACTUAL VALUE"`. This records metadata; it does not configure the product's requests. Rebuild and deploy the files **and** host-header rules. B05-B08, B10-B11 remain prerequisite-dependent tests even after the flag is set; H13's bot-scoped-header support remains an open scope decision.

## Same-URL lifecycle testing

Run each phase as a separate **build > deploy > inspect response > crawl > inspect evidence** cycle. Do not run all three commands back-to-back without crawling between them.

| Phase | Command | Expected observation |
|---|---|---|
| Baseline | `python3 tools/build.py --phase baseline` | Index V1 for U01/U02; discover old-child only for U03/U04 |
| Restricted | `python3 tools/build.py --phase restricted` | U01/U02 V2 must not add/update under noindex; U03/U04 newly introduced child must not queue from the restricted occurrence |
| Restored | `python3 tools/build.py --phase restored` | V3 can index; formerly suppressed new-child can be discovered through a permitted occurrence |

Keep the same URLs and existing index. Force re-fetch/full processing; verify a fresh 200 response and the current fixture version. Index retention, stale-document cleanup and conditional-fetch behavior can otherwise obscure the update assertion.

For U01/U02, the ticket prohibits adding/updating under noindex; it does **not** say whether an older indexed document must be removed. Record V1 retention or deletion separately, pending product agreement. V2 must not replace it.

U02 uses a neutral `X-Robots-Tag: index,follow` during baseline/restored, rather than silently removing the host rule. Render may preserve header rules omitted from a Blueprint; an explicit neutral replacement avoids an old noindex rule surviving a phase change. Inspect the live response every time.

The restricted/restored builds contain two additional new-child URLs (174 fixture URLs); the baseline contains 172. Rebuilding changes only the U-series behavior and any explicitly changed configuration, not the core test scenarios. Restore baseline before starting an unrelated clean regression run.

## Evidence, imports and files

The dashboard's actual-result fields are manual. They start **Not run** and persist only in that browser's local storage. Run label, environment, Ignore robots.txt selection and phase identify independent records. These controls do not change SearchStax. Export run evidence before clearing browser data, changing devices or discarding the run.

`qa/testrail-cases.csv` is one row per test with title, section, type, priority, preconditions, numbered steps, expected result, Jira reference and an unexecuted actual-result field. Import as a step/text template and map columns to your TestRail project's fields. Map `Actual Result` to an appropriate custom field or omit it; normal TestRail case imports do not create executed test results. Map priorities/types to values supported in your project.

```text
studio-5864-robots-qa/
  README.md                      Deployment and usage
  config.json                    Bot placeholder, phase and optional URL prefix
  render.yaml                    Render static-site Blueprint + HTTP headers
  netlify.toml                   Netlify publish configuration
  docs/
    index.html                   Operator dashboard, NOT a crawl seed
    robots.txt                   Host-root robots rules
    _headers                     Real Netlify header configuration
    assets/                      CSS, notebook JS, manifest, CSV
    suites/                      Curated parent-only crawl seeds
    cases/                       Static parent and isolated target fixtures
  source/cases.py                Human-editable fixture definitions
  tools/build.py                 Rebuild fixtures, host rules and test artifacts
  tools/serve.py                 Local header-aware static server
  tools/verify.py                Fixture verification, not product QA execution
  qa/TEST-PLAN.md                Senior QA execution and sign-off plan
  qa/testrail-cases.csv           Importable manual test-case definitions
  qa/expected-results.json       Machine-readable graph and conditional expectations
  qa/results-template.json       Unexecuted evidence template
  qa/render-header-rules.csv     Manual Render header setup reference
  qa/robots-host-root-example.txt Root rules, with configured project prefix
  qa/fixture-verification.json   Local fixture verification evidence
```

## Package validation scope

The supplied reports cover local GET/HEAD response checks, structural link isolation, author-time expectation consistency, baseline/restricted/restored regeneration, and a project-prefix fixture-server run. The delivered baseline passed 172 URL checks plus a host-root robots-rule check with no fixture failures.

The dashboard was also rendered at desktop and mobile sizes, with UI handlers checked using an offline DOM and local fixture binding. The build environment's managed browser blocked URL navigation; no browser policy was changed. Native browser storage across page reloads, live hosted navigation and real download dialogs were not exercised. See `qa/browser-verification.json` for the exact scope.

No report contains an executed SearchStax crawler case. Perform a live hosted smoke test and product execution before recording release results.

## Contract and technical references

The ticket and your agreed product decisions are the acceptance authority. External crawler behavior is background only. In particular, SearchStax-specific-over-generic precedence and head-only inspection follow this ticket, not Google's different merging/body-tag behavior.

- Ticket: https://searchstax.atlassian.net/browse/STUDIO-5864
- Render static response headers: https://render.com/docs/static-site-headers
- Render Blueprint specification: https://render.com/docs/blueprint-spec
- Netlify custom headers: https://docs.netlify.com/manage/routing/headers/
- GitHub Pages publishing: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- GitHub Pages header capability discussion (platform response): https://github.com/orgs/community/discussions/54257
- Robots meta/header background; explicitly Google behavior: https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
- Host-root robots placement: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- HTML rel-token parsing: https://html.spec.whatwg.org/multipage/links.html

No fixture validation constitutes a production certification, crawl run, Solr inspection or completed TestRail result.
