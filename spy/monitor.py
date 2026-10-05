"""Monitoring engine: check one competitor and record what was found.

Live competitors are fetched for real:
  1. the feed URL you gave, or a feed auto-discovered from the page (<link rel="alternate">) or from common paths (/feed, /rss.xml ...)
  2. otherwise the page itself: article-like links are extracted from the HTML (direct page monitoring)
Sample competitors are simulated (clearly labelled) so the demo works without any network access.

Detection delay = time the article was first seen - publication time given by the source (only when the source gives one).
"""
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit

import feedparser
from bs4 import BeautifulSoup

from .models import Competitor
from .net import FetchError, Fetcher
from .store import Store
from .util import now_utc, url_key

COMMON_FEED_PATHS = ["/feed", "/feed/", "/rss", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml", "/blog/feed", "/blog/rss.xml"]
CHECK_DEADLINE_SECONDS = 40            # one check never runs longer than this, whatever the site does
MAX_ITEMS = 60


@dataclass
class Item:
    title: str
    url: str
    published: datetime | None = None
    author: str | None = None
    summary: str = ""
    tags: list[str] = field(default_factory=list)


def _text(html: str, limit: int = 400) -> str:
    t = " ".join(BeautifulSoup(html or "", "html.parser").get_text(" ").split())
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------------------------------------------- feed parsing
def parse_feed(content: bytes, base_url: str) -> tuple[str, list[Item]] | None:
    parsed = feedparser.parse(content)
    version = parsed.get("version") or ""
    if not version or not parsed.entries:
        return None
    items: list[Item] = []
    for e in parsed.entries[:MAX_ITEMS]:
        link = e.get("link") or ""
        title = " ".join((e.get("title") or "").split())
        if not link or not title:
            continue
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        published = datetime(*stamp[:6], tzinfo=timezone.utc) if stamp else None
        summary = _text(e.get("summary") or (e.get("content") or [{}])[0].get("value", ""))
        items.append(Item(title, urljoin(base_url, link), published, (e.get("author") or None), summary,
                          [t.get("term") for t in e.get("tags", []) if t.get("term")][:6]))
    if not items:
        return None
    return ("atom" if version.startswith("atom") else "rss"), items


# ---------------------------------------------------------------------------------------------------- html fallback
_SKIP_PATH = re.compile(r"/(tag|tags|category|categories|author|authors|page|search|login|signup|contact|about|privacy|terms|cart|account)(/|$)", re.I)
_SECTION_ROOTS = {"blog", "news", "post", "posts", "article", "articles", "stories", "story", "insights", "journal", "press", "resources"}
_ARTICLE_HINT = re.compile(r"/(blog|news|post|posts|article|articles|stories|story|insights|journal|press|resources)(/|$)|/\d{4}/\d{1,2}/|-\w+-\w+", re.I)


def extract_page_items(content: bytes, page_url: str) -> list[Item]:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["nav", "footer", "aside", "header", "script", "style", "noscript"]):
        tag.decompose()
    host = (urlsplit(page_url).hostname or "").lower().removeprefix("www.")
    seen, items = set(), []
    for a in soup.find_all("a", href=True):
        url = urljoin(page_url, a["href"].strip())
        p = urlsplit(url)
        if p.scheme not in ("http", "https") or (p.hostname or "").lower().removeprefix("www.") != host:
            continue
        title = " ".join(a.get_text(" ").split())
        segments = [x for x in p.path.split("/") if x]
        if len(title) < 20 or len(title) > 200 or _SKIP_PATH.search(p.path) or not segments or segments[-1].lower() in _SECTION_ROOTS:
            continue                                                  # navigation, tag/author pages and section index pages are not articles
        if url_key(url) == url_key(page_url) or not (_ARTICLE_HINT.search(p.path) or p.path.strip("/").count("/") >= 1):
            continue
        key = url_key(url)
        if key in seen:
            continue
        seen.add(key)
        published = None
        holder = a.find_parent(["article", "li", "div"]) or a
        t = holder.find("time", attrs={"datetime": True})
        if t:
            try:
                published = datetime.fromisoformat(t["datetime"].strip().replace("Z", "+00:00"))
                published = published if published.tzinfo else None        # a date without a time zone is not trusted
            except ValueError:
                published = None
        items.append(Item(title, url, published))
        if len(items) >= MAX_ITEMS:
            break
    return items


def _alternate_feeds(content: bytes, page_url: str) -> list[str]:
    soup = BeautifulSoup(content, "html.parser")
    out = []
    for link in soup.find_all("link", href=True):
        rel = " ".join(link.get("rel") or []).lower()
        typ = (link.get("type") or "").lower()
        if "alternate" in rel and ("rss" in typ or "atom" in typ):
            out.append(urljoin(page_url, link["href"]))
    return out[:3]


# ---------------------------------------------------------------------------------------------------- discovery
def discover(comp: Competitor, fetcher: Fetcher, deadline: float) -> tuple[str, str | None, list[Item]]:
    """Returns (method, feed_url, items). Raises FetchError when nothing could be fetched at all."""
    def feed_from(url: str):
        """Fetch + parse a feed. Network errors propagate to the caller; returns None when the response is not a feed."""
        res = fetcher.get(url)
        return parse_feed(res.content, res.url)

    if comp.feed_url:                                        # configured by the user: report exactly what went wrong
        found = feed_from(comp.feed_url)
        if not found:
            raise FetchError("invalid", "The feed URL you provided did not return a valid RSS/Atom feed")
        return found[0], comp.feed_url, found[1]
    if comp.discovered_feed_url:                             # found earlier: reuse it; if it fails, discover again below
        try:
            found = feed_from(comp.discovered_feed_url)
            if found:
                return found[0], comp.discovered_feed_url, found[1]
        except FetchError as e:
            if e.kind == "blocked":
                raise
    page = fetcher.get(comp.website_url)                     # a failure here is the competitor being unreachable
    direct = parse_feed(page.content, page.url)              # the URL may itself be a feed
    if direct:
        return direct[0], page.url, direct[1]
    candidates = _alternate_feeds(page.content, page.url)
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(page.url))
    candidates += [origin + p for p in COMMON_FEED_PATHS]
    for cand in dict.fromkeys(candidates):
        if time.monotonic() > deadline:
            break
        try:
            found = feed_from(cand)
        except FetchError as e:
            if e.kind == "blocked":
                raise
            continue                                         # a guessed path that does not exist is normal
        if found:
            return found[0], cand, found[1]
    items = extract_page_items(page.content, page.url)
    return "html", None, items


# ---------------------------------------------------------------------------------------------------- the check
def check_competitor(store: Store, comp_id: int, fetcher: Fetcher | None = None, rng: random.Random | None = None):
    """Run one check. The caller has called store.begin_check(); this always clears the 'checking' flag and records the result."""
    comp = store.get_competitor(comp_id)
    started = now_utc()
    t0 = time.monotonic()
    new_count, found, method, error = 0, 0, comp.strategy, None
    try:
        if comp.kind == "sample":
            method, found, new_count = _simulate(store, comp, rng or random.Random())
        else:
            method, feed_url, items = discover(comp, fetcher, t0 + CHECK_DEADLINE_SECONDS)
            found = len(items)
            new_count = _store_items(store, comp, method, items, started)
            comp.discovered_feed_url = feed_url
    except FetchError as e:
        error = str(e)
    except Exception as e:                                    # never let one competitor break a check-all
        error = f"unexpected error: {type(e).__name__}: {e}"[:300]
    finally:
        with store._lock:
            comp.checking = False
            comp.last_checked_at = now_utc()
            comp.checks_run += 1
            if error is None:
                comp.status, comp.consecutive_failures, comp.last_error = "online", 0, None
                comp.last_success_at, comp.strategy, comp.baseline_done = comp.last_checked_at, method, True
            else:
                comp.status, comp.consecutive_failures, comp.last_error = "offline", comp.consecutive_failures + 1, error
    return store.record_check(comp, started, int((time.monotonic() - t0) * 1000), "failed" if error else "success", method, found, new_count, error)


def _store_items(store: Store, comp: Competitor, method: str, items: list[Item], now: datetime) -> int:
    new = 0
    for it in sorted(items, key=lambda i: i.published or now):          # oldest first, so discovery order follows publication order
        baseline = not comp.baseline_done
        delay = None
        if not baseline and it.published and it.published <= now + timedelta(seconds=60):
            delay = round(max(0.0, (now - it.published).total_seconds()), 3)
        art = store.add_article(comp, title=it.title, url=it.url, summary=it.summary, author=it.author, tags=it.tags,
                                published_at=it.published, discovered_at=now, status="baseline" if baseline else "new", method=method, delay_seconds=delay)
        if art is not None and not baseline:
            new += 1
    return new


# ---------------------------------------------------------------------------------------------------- sample (simulated) competitors
_SIM_TITLES = ["Introducing our new workflow automation toolkit", "What the latest benchmark tells us about reliability", "How customers use our reporting API",
               "Roadmap update: what is shipping this month", "Lessons from migrating a monolith step by step", "A practical guide to data quality checks",
               "Announcing regional hosting and data residency", "Five mistakes to avoid when launching a self-serve plan"]


def _simulate(store: Store, comp: Competitor, rng: random.Random) -> tuple[str, int, int]:
    if comp.sim_flaky and comp.checks_run % 2 == 0:
        raise FetchError("timeout", "timed out after 8s (simulated failure of a sample competitor)")
    now = now_utc()
    created = 0
    if rng.random() < 0.7:                                                # most checks find one new sample article
        title = rng.choice(_SIM_TITLES)
        delay = float(rng.randint(25, 420))
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
        art = store.add_article(comp, title=title, url=f"{comp.website_url.rstrip('/')}/{slug}-{int(now.timestamp())}",
                                summary="Simulated sample article generated by a demo check.", discovered_at=now, status="new", method=comp.strategy or "rss",
                                published_at=now - timedelta(seconds=delay), delay_seconds=delay, tags=["sample"], author="Sample Author")
        created = 1 if art else 0
    total = sum(1 for a in store.articles.values() if a.competitor_id == comp.id)
    return comp.strategy or "rss", total, created
