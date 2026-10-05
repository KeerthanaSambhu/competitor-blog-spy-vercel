# Competitor Blog Spy

Monitor competitor blogs and see **new articles the moment you check, with the exact detection delay** (time first seen minus the source's publication time).
A small FastAPI app with a responsive dashboard, built from the start to deploy on **Vercel** with **no database, no external services and no environment variables**.

> **Live demo:** `https://<your-project>.vercel.app` (after you deploy, see [Deploy to Vercel](#deploy-to-vercel))

## Features

- **Dashboard** with real statistics: competitors online/offline, articles discovered, average / fastest / slowest detection delay, share within a 5-minute target, failed checks, articles per day, articles by competitor, latest articles, recent checks.
- **Competitor management:** add, edit, enable/disable and delete competitors (name, website/blog URL, optional feed URL), with validation and duplicate detection.
- **Monitoring checks** ("Check" per competitor, "Check all", optional auto-check every 5 minutes while the page is open). Live competitors are really fetched:
  1. your feed URL, or a feed discovered automatically (`<link rel="alternate">` on the page, then common paths such as `/feed`, `/rss.xml`, `/atom.xml`);
  2. if there is no feed, article links are extracted from the page itself (navigation, footer, tag and section-index links are ignored).
- **Article discovery and details:** list with search, competitor and status filters, paging, and a detail view (title, summary, author, tags, publication time, first-discovered time, exact delay, method, source link).
- **Baseline rule:** the first successful check of a competitor records the existing articles silently (status *baseline*, no delay); only articles that appear later are *new* and get a delay. A delay is only calculated when the source gives a trustworthy publication time (never invented).
- **Duplicate prevention:** URL variants (`http`/`https`, `www.`, trailing slash, `#fragment`, `utm_*`) count as the same article.
- **Failure handling:** timeouts, HTTP errors, invalid feeds and blocked addresses are recorded per check, mark the competitor *offline*, never affect other competitors, and recover automatically on the next successful check.
- **Demo data:** four sample competitors with articles, delays (including one over the 5-minute target) and a flaky competitor, so the dashboard is populated immediately. Sample competitors are **simulated and labelled `sample`**; competitors you add are labelled `live`.
- **Safe by design for a public URL:** only public `http(s)` addresses are fetched (localhost, private, link-local and cloud-metadata addresses are refused, including via redirects), responses are size-capped, and the number of competitors is limited.
- **Health endpoint** (`/api/health`), interactive API docs (`/docs`).

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3, **FastAPI** (one serverless function on Vercel) |
| Monitoring | `httpx` (HTTP), `feedparser` (RSS/Atom), `beautifulsoup4` (HTML link extraction) |
| Data | **in-memory** store (no database, no files) seeded with sample data |
| Frontend | one embedded HTML/CSS/vanilla-JavaScript page served by FastAPI (no build step, no CDN, no framework) |
| Hosting | Vercel (zero-configuration FastAPI, entrypoint `index.py`) |
| Tests | `pytest` (API, monitoring engine with a fake internet, Vercel-readiness) and an optional jsdom UI smoke test |

## How data is kept

There is **no database**: state lives in the memory of the server process and is seeded with sample data on first use. On Vercel an instance stays warm between requests but can be replaced (idle time, redeploy, scaling), after which the app starts again from the sample data.
To soften this, the browser keeps a small backup of **the competitors you added** (in `localStorage`) and restores them automatically if the server is back to the untouched sample state. Articles and check history of live competitors are rebuilt by running a check. Use **Reset demo data** (page footer) to return to the sample data.
This is a deliberate trade-off for a zero-setup demo: if you need durable history, add a hosted database (not included, see Limitations).

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn index:app --reload --port 8000
```
Open http://127.0.0.1:8000 (dashboard), http://127.0.0.1:8000/docs (API docs), http://127.0.0.1:8000/api/health. No `.env` file is needed.

## Run the tests

```bash
pytest                                # backend, monitoring engine, Vercel-readiness (no internet needed)
```
Optional browser-less UI check against a running server (needs Node.js):
```bash
uvicorn index:app --port 8000 &       # in another terminal if you prefer
cd tests/ui_smoke && npm install && node ui_smoke.js http://127.0.0.1:8000
```
The tests include a run of the whole app in a fresh process in which **every filesystem write, temp file and `sqlite3` import raises an error**, proving nothing is written to disk.

## Deploy to Vercel

The project is a single FastAPI app: `index.py` (project root) exposes `app`, `requirements.txt` lists the dependencies, `vercel.json` only adds security headers. There is nothing to configure and nothing to create beforehand (no database, no storage, no environment variables).

**1. Put the project on GitHub**
```bash
git init -b main
git add .
git status                           # check: no .env, no .venv, no node_modules
git commit -m "Competitor Blog Spy"
```
Create an empty repository on github.com, then:
```bash
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

**2. Deploy on Vercel**
1. Go to https://vercel.com/new and **Import** the GitHub repository.
2. Leave **Root Directory** as `./`. The framework is detected as **FastAPI** (if asked, choose FastAPI or "Other"). Do **not** set a build command or output directory and add **no environment variables**.
3. Click **Deploy**. When it finishes, open the production URL `https://<project>.vercel.app`.
4. Check it: `/` shows the populated dashboard and `/api/health` returns `{"status":"ok",...}`.

*Alternative (CLI):* `npm i -g vercel`, then `vercel --prod` in the project folder and accept the defaults.

**Troubleshooting**
- *Vercel says it cannot find an entrypoint:* `index.py` must be in the repository root and contain `from spy.main import app`.
- *Vercel asks you to log in to view the site:* in Project Settings -> Deployment Protection, make the production deployment public. Submit the production URL, not a preview URL.
- *A real website is not detected:* some sites block cloud IP addresses or require JavaScript; try the feed URL directly.

## Environment variables

**None are required.** The app starts and works with no environment variables set. Optional tuning (see `.env.example`; set them in Vercel under Settings -> Environment Variables if you want to change a default):

| Variable | Default | Meaning |
|---|---|---|
| `MAX_COMPETITORS` | 25 | upper limit of competitors (protects a public demo) |
| `REQUEST_TIMEOUT_SECONDS` | 8 | per-request timeout of live checks |
| `MAX_RESPONSE_BYTES` | 2000000 | largest response a check will read |
| `CHECK_CONCURRENCY` | 4 | competitors checked in parallel by "Check all" |
| `MAX_ARTICLES_PER_COMPETITOR` | 100 | keeps memory bounded |
| `ALLOW_PRIVATE_URLS` | false | local testing only: allow localhost/private addresses (keep `false` when public) |

No secrets are used anywhere; `.env` is git-ignored.

## Demo

1. Open the site: the **Dashboard** is already populated (sample data): statistics, charts, latest articles, recent checks.
2. **Competitors:** four sample competitors with `sample` badges and statuses (online, offline, disabled). Press **Check** on *Acme Analytics* (a simulated check, new sample article), press **Check** twice on *Globex Cloud* (the first check fails, the next recovers: failure handling).
3. **Add a real competitor**, e.g. name `PyPI`, website `https://pypi.org/`, feed `https://pypi.org/rss/updates.xml`; or any blog URL without a feed to see automatic discovery. Press **Check** (baseline: existing articles recorded silently), wait about 10 seconds, press **Check** again: new articles appear with their **real, exact detection delay**.
4. **Articles:** search and filter, then open one to see published time, first-discovered time, exact delay and method. Baseline articles show *n/a* (no delay is invented).
5. **Activity:** every check including failures.
6. **Try the safeguards:** add `http://127.0.0.1/` (refused at check time), a duplicate website (refused), an invalid URL (validation message).
7. Optional: tick *auto-check every 5 min*; use **Reset demo data** in the footer to start over.

## API

Interactive documentation: `/docs`. All responses are JSON.

| Method and path | Purpose |
|---|---|
| `GET /api/health` | health, version, storage kind, uptime |
| `GET /api/dashboard` | all dashboard statistics |
| `GET /api/competitors` / `POST /api/competitors` | list / create (`name`, `website_url`, optional `feed_url`, `enabled`) |
| `GET` / `PUT` / `DELETE /api/competitors/{id}` | read / update / delete (articles and checks are deleted with it) |
| `POST /api/competitors/{id}/check` | check one competitor now |
| `POST /api/check-all` | check every enabled competitor |
| `GET /api/articles` | list; filters `competitor_id`, `q`, `status` (`new`/`baseline`), `limit`, `offset` |
| `GET /api/articles/{id}` | article details including `detection_delay_seconds` |
| `GET /api/checks` | monitoring history (`limit`, `competitor_id`) |
| `GET /api/state`, `POST /api/state/restore`, `POST /api/demo/reset` | browser-backup support and demo reset |

## Project structure

```
index.py            Vercel entrypoint (exposes `app`)
vercel.json         security headers only
requirements.txt    runtime dependencies (fastapi, httpx, feedparser, beautifulsoup4)
requirements-dev.txt  + uvicorn, pytest for local work
spy/
  main.py           FastAPI app, error handlers, page and favicon routes
  api.py            JSON API routes
  monitor.py        feed discovery, HTML fallback, detection, delay calculation, simulation of sample competitors
  net.py            HTTP fetcher with timeouts, size cap and private-address protection
  store.py          in-memory store, statistics
  seed.py           sample data
  models.py         validation and record types
  ui.py             the embedded dashboard (HTML, CSS, JavaScript)
  config.py, util.py
tests/              pytest suite + optional jsdom UI smoke test
```

## Limitations

- **Not persistent:** data is in server memory (see [How data is kept](#how-data-is-kept)); a restart returns to the sample data (your competitors are restored from the browser backup, their articles are rebuilt by a check).
- **Checks run on demand** (buttons, or the auto-check toggle while a page is open). There is no always-on background scheduler, because a serverless function cannot keep one alive; the detection delay is therefore bounded by how often a check is triggered.
- **Sample competitors are simulated** (clearly labelled); only competitors you add are fetched.
- **Scope is intentionally small:** the app stores title, link, summary, author, tags and times. It does not capture full article bodies or images, does not read XML sitemaps, and has no multi-user accounts. There is **no login**: anyone with the URL can add competitors (mitigated by the competitor limit and the private-address protection).
- Sites that need JavaScript to render their articles, or that block cloud IP addresses, cannot be read.
- A public-address check resolves DNS before connecting; a determined attacker controlling DNS could still try rebinding tricks, so do not expose this app next to sensitive internal services.
