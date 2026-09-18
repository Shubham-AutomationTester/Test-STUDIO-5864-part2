# Start here - STUDIO-5864 QA site

**Recommended: GitHub repository + Render static-site Blueprint.**

1. Extract the ZIP. Put the folder's contents at your GitHub repository root. Keep `render.yaml` and the `docs/` folder at that root level.
2. In Render: **New > Blueprint > connect repository > Deploy Blueprint**. The included configuration publishes `./docs` and supplies the actual X-Robots-Tag response headers.
3. Open the deployed site's root to use the dashboard. Copy a suite's crawl seed into SearchStax. Do not crawl the dashboard as the seed.
4. Use a dedicated QA app/index. Allow the site's `/suites/` and `/cases/` paths, depth >= 5, item budget >= 500, and no sitemap or independent target-URL discovery.
5. Start with `/suites/core/`, then `/suites/headers/`. Run `/suites/robots/` twice with fresh state: Ignore robots.txt OFF and ON. Record actual product evidence in the dashboard.

## Example: noindex is not nofollow

Crawl `/cases/m03/` only. The parent has `<meta name="robots" content="noindex">` and one ordinary link to its unique child.

Expected: parent is processed but not indexed; child is discoverable and can index. Parent marker: `QA5864M03P`. Child marker: `QA5864M03CHILD`.

Use `/cases/m04/` for the inverse: nofollow parent can index; its child must not be queued from that page.

## Local preview

From the extracted repository folder:

```bash
python3 tools/serve.py --port 8000
```

Open `http://localhost:8000/`. A cloud-hosted crawler cannot reach your laptop's localhost; use the deployed URL for SearchStax execution.

From a second terminal:

```bash
python3 tools/verify.py http://localhost:8000 --require-repeated
```

This command checks fixtures only. It does not run SearchStax.

## Before signing off

The shipped bot token `searchstax` is an unconfirmed placeholder. Confirm the actual meta-name mapping before grading matching-bot cases. Ten precedence/parsing behaviors need a product decision; they are visibly marked Confirm. Existing-document deletion under noindex is not assumed.

Use `README.md` for full hosting instructions, `qa/TEST-PLAN.md` for the execution strategy and `qa/testrail-cases.csv` for test-case import. All actual results start **Not run**.
