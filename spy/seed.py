"""Sample data so the dashboard is populated immediately. Competitors with kind='sample' are SIMULATED (their checks are generated
locally and clearly labelled); competitors a visitor adds are 'live' and are fetched for real."""
import random
import re
from datetime import timedelta

from .models import Competitor
from .util import now_utc

SAMPLE_COMPETITORS = [
    # name, website, strategy, enabled, flaky
    ("Acme Analytics", "https://blog.acme-analytics.example/", "rss", True, False),
    ("Northwind Commerce", "https://northwind-commerce.example/journal/", "atom", True, False),
    ("Globex Cloud", "https://globex-cloud.example/news/", "html", True, True),
    ("Initech Labs", "https://initech-labs.example/blog/", "rss", False, False),
]

# title, summary, tags
SAMPLE_ARTICLES = [
    ("How we cut dashboard load time by 60%", "A walk-through of the caching and query changes behind our faster dashboards.", ["performance", "engineering"]),
    ("Announcing the 2.0 release: what is new", "Workspaces, role-based access and a rebuilt reporting engine.", ["release", "product"]),
    ("Five signals your churn model is drifting", "Practical checks for data scientists before the quarterly review.", ["data", "ml"]),
    ("Customer story: scaling support with automation", "How a mid-size retailer halved first-response time.", ["case-study"]),
    ("Pricing changes for the coming year", "A simpler plan structure and what it means for existing customers.", ["pricing"]),
    ("Security update: SOC 2 Type II complete", "Our audit results and what we improved along the way.", ["security", "compliance"]),
    ("Inside our incident response process", "Roles, runbooks and the blameless review that follows.", ["engineering", "reliability"]),
    ("The state of e-commerce search in 2026", "Benchmarks across twelve storefronts and what shoppers click.", ["research", "e-commerce"]),
    ("Integrating with the new partner API", "Step-by-step guide with code samples and rate-limit tips.", ["api", "tutorial"]),
    ("Hiring: building a distributed data team", "What we look for and how our interview loop works.", ["culture"]),
    ("Open-sourcing our feed parser", "Why we released it and how to contribute.", ["open-source"]),
    ("Q3 product roadmap preview", "Themes for the next quarter and how to give feedback.", ["roadmap", "product"]),
    ("Zero-downtime migrations: lessons learned", "Patterns we use to change schemas without interrupting service.", ["engineering", "database"]),
    ("Webinar recap: forecasting with limited data", "Key questions from the live Q&A.", ["webinar", "data"]),
    ("A faster checkout: results of our A/B test", "Three variants, 40,000 sessions, one clear winner.", ["experiments", "e-commerce"]),
    ("Meet the team: platform engineering", "Introducing the group behind uptime and tooling.", ["culture"]),
    ("Handling rate limits gracefully", "Backoff strategies and idempotency keys explained.", ["api", "engineering"]),
    ("Trend report: AI assistants in analytics", "How teams use natural-language querying today.", ["research", "ai"]),
    ("Deprecation notice: legacy export endpoint", "Timeline, replacement and migration help.", ["api", "release"]),
    ("Behind the redesign of our mobile app", "Design principles, user research and what we measured.", ["design", "product"]),
]


def load_sample_data(store) -> None:
    rng = random.Random(42)                       # same sample data on every instance start
    now = now_utc()
    titles = list(SAMPLE_ARTICLES)
    rng.shuffle(titles)
    comps: list[Competitor] = []
    for name, site, strategy, enabled, flaky in SAMPLE_COMPETITORS:
        c = store.add_competitor(name, site, None, enabled, kind="sample", user=False, strategy=strategy, sim_flaky=flaky, baseline_done=True)
        c.created_at = now - timedelta(days=14)
        comps.append(c)

    # articles: older ones are 'baseline', newer ones were 'detected' with a measured delay
    delays = [38, 72, 95, 140, 215, 262, 298, 410, 1260, 88, 160, 55]
    i = di = 0
    for ci, c in enumerate(comps):
        n = [7, 6, 4, 3][ci]
        for k in range(n):
            title, summary, tags = titles[i % len(titles)]
            i += 1
            published = now - timedelta(hours=rng.choice([rng.randint(1, 30), rng.randint(2, 280)]))
            baseline = k >= n - 2                                   # the two oldest per competitor existed before monitoring began
            delay = None if baseline else float(delays[di % len(delays)])
            di += 0 if baseline else 1
            discovered = published + timedelta(seconds=delay) if delay else published + timedelta(hours=1)
            store.add_article(c, title=title, url=f"{c.website_url.rstrip('/')}/{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]}-{i}", summary=summary,
                              discovered_at=discovered, status="baseline" if baseline else "new", method=c.strategy, author=rng.choice(["Dana Lee", "Sam Ortiz", "Priya Nair", "Jon Weber"]),
                              published_at=published, delay_seconds=delay, tags=tags)

    # check history: mostly successful, a couple of failures for the flaky competitor
    for age_h in range(30, 0, -3):
        for c in comps:
            if not c.enabled:
                continue
            failed = c.sim_flaky and age_h % 9 == 0
            store.record_check(c, now - timedelta(hours=age_h, minutes=rng.randint(0, 40)), rng.randint(180, 1400),
                               "failed" if failed else "success", c.strategy, 0 if failed else rng.randint(6, 20), 0 if failed or rng.random() < 0.6 else 1,
                               "timeout: timed out after 8s (sample failure)" if failed else None)
    for c in comps:
        if not c.enabled:
            c.status = "disabled"
            continue
        c.checks_run = 10
        c.last_checked_at = now - timedelta(minutes=rng.randint(4, 55))
        if c.sim_flaky:
            c.status, c.consecutive_failures, c.last_error = "offline", 1, "timeout: timed out after 8s (sample failure)"
            c.last_success_at = now - timedelta(hours=3)
        else:
            c.status, c.last_success_at = "online", c.last_checked_at
