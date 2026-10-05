from datetime import timedelta

import httpx
import pytest

from helpers import atom, now_utc, rss
from spy.monitor import check_competitor, extract_page_items, parse_feed
from spy.net import Fetcher, FetchError, assert_public_url
from spy.store import store

SITE = "https://rival.test/"


def add_live(client, site=SITE, **kw):
    r = client.post("/api/competitors", json={"name": "Rival", "website_url": site, **kw})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def run(client, cid):
    r = client.post(f"/api/competitors/{cid}/check")
    assert r.status_code == 200, r.text
    return r.json()


def articles(client, cid, **q):
    return client.get("/api/articles", params={"competitor_id": cid, "limit": 200, **q}).json()


# ---------------------------------------------------------------- feeds: baseline, new article, exact delay, duplicates
def test_feed_first_check_is_a_silent_baseline_then_new_articles_are_detected_with_exact_delay(client, web):
    feed = SITE + "feed.xml"
    old = [("Old post one", SITE + "p/one", now_utc() - timedelta(days=3), "Ann", "<p>First</p>"), ("Old post two", SITE + "p/two", now_utc() - timedelta(days=9), None, None)]
    web.set(feed, rss(old), "application/rss+xml")
    cid = add_live(client, feed_url=feed)

    r1 = run(client, cid)
    assert r1["check"]["status"] == "success" and r1["check"]["method"] == "rss" and r1["check"]["items_found"] == 2 and r1["check"]["new_articles"] == 0
    base = articles(client, cid)
    assert base["total"] == 2 and all(a["status"] == "baseline" and a["detection_delay_seconds"] is None for a in base["items"])
    assert r1["competitor"]["status"] == "online" and r1["competitor"]["strategy"] == "rss" and r1["competitor"]["last_success_at"]

    published = now_utc() - timedelta(seconds=42)
    web.set(feed, rss(old + [("Brand new launch", SITE + "p/new?utm_source=feed", published, "Dana", "<p>Hello <b>world</b></p>")]), "application/rss+xml")
    r2 = run(client, cid)
    assert r2["check"]["new_articles"] == 1 and r2["check"]["items_found"] == 3
    new = articles(client, cid, status="new")["items"][0]
    assert new["title"] == "Brand new launch" and new["author"] == "Dana" and new["summary"] == "Hello world" and new["method"] == "rss"
    from datetime import datetime
    pub, disc = (datetime.fromisoformat(new[k].replace("Z", "+00:00")) for k in ("published_at", "discovered_at"))
    assert 41 <= new["detection_delay_seconds"] <= 50 and abs((disc - pub).total_seconds() - new["detection_delay_seconds"]) < 1.0     # delay = discovery - publication
    detail = client.get(f"/api/articles/{new['id']}").json()
    assert detail["detection_delay_seconds"] == new["detection_delay_seconds"]

    snapshot = (new["id"], new["discovered_at"], new["detection_delay_seconds"])
    r3 = run(client, cid)
    assert r3["check"]["new_articles"] == 0 and articles(client, cid)["total"] == 3                                  # nothing duplicated
    again = [a for a in articles(client, cid)["items"] if a["id"] == snapshot[0]][0]
    assert (again["id"], again["discovered_at"], again["detection_delay_seconds"]) == snapshot                      # first discovery never changes
    d = client.get("/api/dashboard").json()
    assert d["competitors"]["live"] == 1 and d["detection_delay"]["measured"] >= 1


def test_url_variants_are_the_same_article(client, web):
    feed = SITE + "feed.xml"
    t0 = now_utc() - timedelta(days=1)
    web.set(feed, rss([("A", SITE + "post/a", t0, None, None)]), "application/rss+xml")
    cid = add_live(client, feed_url=feed)
    run(client, cid)
    web.set(feed, rss([("A again", "http://www.rival.test/post/a/?utm_campaign=x#frag", now_utc(), None, None)]), "application/rss+xml")
    assert run(client, cid)["check"]["new_articles"] == 0 and articles(client, cid)["total"] == 1


def test_atom_feed_is_discovered_from_the_homepage(client, web):
    web.set(SITE, '<html><head><link rel="alternate" type="application/atom+xml" href="/atom/all.xml"></head><body>hi</body></html>')
    web.set(SITE + "atom/all.xml", atom([("Entry A", SITE + "e/a", now_utc() - timedelta(hours=5), "Lee", "sum")]), "application/atom+xml")
    cid = add_live(client)
    r = run(client, cid)
    assert r["check"]["method"] == "atom" and r["competitor"]["discovered_feed_url"] == SITE + "atom/all.xml" and r["check"]["items_found"] == 1
    web.set(SITE + "atom/all.xml", atom([("Entry A", SITE + "e/a", now_utc() - timedelta(hours=5), "Lee", "sum"), ("Entry B", SITE + "e/b", now_utc() - timedelta(seconds=75), "Lee", "sum")]), "application/atom+xml")
    r2 = run(client, cid)
    assert r2["check"]["new_articles"] == 1 and 74 <= articles(client, cid, status="new")["items"][0]["detection_delay_seconds"] <= 85
    assert SITE + "atom/all.xml" in web.requests[-2:] or SITE + "atom/all.xml" in web.requests                      # the stored feed is reused


def test_feed_found_at_a_common_path_when_the_page_does_not_link_it(client, web):
    web.set(SITE, "<html><body><h1>Welcome</h1></body></html>")
    web.set(SITE + "feed", rss([("Hello world post", SITE + "hello", now_utc() - timedelta(days=2), None, None)]), "application/rss+xml")
    cid = add_live(client)
    r = run(client, cid)
    assert r["check"]["method"] == "rss" and r["competitor"]["discovered_feed_url"] == SITE + "feed"


def test_url_that_is_itself_a_feed(client, web):
    web.set(SITE + "blog.xml", rss([("Direct feed item", SITE + "x", now_utc() - timedelta(days=1), None, None)]), "application/rss+xml")
    cid = add_live(client, site=SITE + "blog.xml")
    assert run(client, cid)["check"]["method"] == "rss"


# ---------------------------------------------------------------- direct page monitoring (no feed)
PAGE = """<html><body>
<nav><a href="/blog/navigation-link-that-is-long-enough">Navigation link that should be ignored here</a></nav>
<main>
 <article><h2><a href="/blog/how-we-scaled-our-search-platform">How we scaled our search platform to a billion queries</a></h2><time datetime="%s">x</time></article>
 <article><h2><a href="/blog/announcing-our-new-pricing-model">Announcing our new pricing model for teams</a></h2></article>
 <a href="/tag/python">Python related stuff for developers and others</a>
 <a href="https://other.test/blog/external-article-about-things">An external article that must not be picked</a>
 <a href="/blog/">All blog posts overview page link text here</a>
</main><footer><a href="/blog/footer-link-that-is-long-enough-text">Footer link text that is long enough though</a></footer></body></html>"""


def test_html_fallback_extracts_article_links_and_ignores_navigation(client, web):
    web.set(SITE, PAGE % "2020-01-01T10:00:00+00:00")
    cid = add_live(client)
    r = run(client, cid)
    assert r["check"]["method"] == "html" and r["check"]["items_found"] == 2 and r["competitor"]["strategy"] == "html"
    titles = {a["title"] for a in articles(client, cid)["items"]}
    assert titles == {"How we scaled our search platform to a billion queries", "Announcing our new pricing model for teams"}
    stamp = (now_utc() - timedelta(seconds=90)).isoformat()
    web.set(SITE, PAGE.replace("</main>", '<article><a href="/blog/a-brand-new-post-appears-on-the-page">A brand new post appears on the page today</a><time datetime="%s">now</time></article></main>' % stamp) % "2020-01-01T10:00:00+00:00")
    r2 = run(client, cid)
    new = articles(client, cid, status="new")["items"]
    assert r2["check"]["new_articles"] == 1 and new[0]["method"] == "html" and 89 <= new[0]["detection_delay_seconds"] <= 100


def test_no_delay_is_invented_without_a_trustworthy_publication_time(client, web):
    web.set(SITE, PAGE % "2020-01-01T10:00:00")                                   # a date WITHOUT time zone
    cid = add_live(client)
    run(client, cid)
    web.set(SITE, PAGE.replace("</main>", '<article><a href="/blog/zone-less-new-post-for-testing-purposes">Zone-less new post for testing purposes</a><time datetime="2026-01-01T10:00:00">x</time></article><article><a href="/blog/no-date-at-all-new-post-for-testing">No date at all new post for testing purposes</a></article></main>') % "2020-01-01T10:00:00")
    assert run(client, cid)["check"]["new_articles"] == 2
    assert all(a["detection_delay_seconds"] is None and a["published_at"] is None for a in articles(client, cid, status="new")["items"])
    feed = SITE + "f2.xml"
    cid2 = add_live(client, "https://future.test/", feed_url=feed)
    web.set(feed, rss([("Existing", "https://future.test/e", now_utc() - timedelta(days=1), None, None)]), "application/rss+xml")
    run(client, cid2)
    web.set(feed, rss([("Existing", "https://future.test/e", now_utc() - timedelta(days=1), None, None), ("From the future", "https://future.test/f", now_utc() + timedelta(days=2), None, None)]), "application/rss+xml")
    run(client, cid2)
    fut = articles(client, cid2, status="new")["items"][0]
    assert fut["title"] == "From the future" and fut["detection_delay_seconds"] is None                  # a future timestamp is never turned into a delay


# ---------------------------------------------------------------- failures are recorded, isolated and recoverable
def test_http_error_timeout_and_recovery_are_recorded(client, web):
    feed = SITE + "feed.xml"
    cid = add_live(client, feed_url=feed)
    web.set(feed, "boom", status=500)
    r = run(client, cid)
    assert r["check"]["status"] == "failed" and "HTTP 500" in r["check"]["error"] and r["competitor"]["status"] == "offline" and r["competitor"]["consecutive_failures"] == 1
    web.fail(feed, httpx.ReadTimeout("slow"))
    r = run(client, cid)
    assert "timeout" in r["check"]["error"] and r["competitor"]["consecutive_failures"] == 2 and r["competitor"]["last_error"]
    web.set(feed, rss([("Back online", SITE + "b", now_utc() - timedelta(days=1), None, None)]), "application/rss+xml")
    r = run(client, cid)
    assert r["check"]["status"] == "success" and r["competitor"]["status"] == "online" and r["competitor"]["consecutive_failures"] == 0 and r["competitor"]["last_error"] is None
    checks = client.get(f"/api/checks?competitor_id={cid}").json()
    assert [c["status"] for c in checks] == ["success", "failed", "failed"] and client.get("/api/dashboard").json()["checks"]["failed"] >= 2


def test_an_invalid_feed_url_is_reported_clearly(client, web):
    web.set(SITE + "notafeed", "<html><body>Not a feed</body></html>")
    cid = add_live(client, feed_url=SITE + "notafeed")
    r = run(client, cid)
    assert r["check"]["status"] == "failed" and "did not return a valid RSS/Atom feed" in r["check"]["error"]


def test_unreachable_site_fails_without_breaking_check_all(client, web):
    good_feed = "https://good.test/feed.xml"
    web.set(good_feed, rss([("Fine", "https://good.test/a", now_utc() - timedelta(days=1), None, None)]), "application/rss+xml")
    web.fail("https://down.test/", httpx.ConnectError("refused"))
    good = add_live(client, "https://good.test/", feed_url=good_feed)
    down = add_live(client, "https://down.test/")
    disabled = client.post("/api/competitors", json={"name": "Off", "website_url": "https://off.test/", "enabled": False}).json()["id"]
    r = client.post("/api/check-all").json()
    live = {c["competitor_id"]: c for c in r["checks"]}
    assert live[good]["status"] == "success" and live[down]["status"] == "failed" and "network" in live[down]["error"] and disabled not in live
    enabled_sample = [c for c in client.get("/api/competitors").json() if c["kind"] == "sample" and c["enabled"]]
    assert r["checked"] == len(enabled_sample) + 2 and r["failed"] >= 1 and r["skipped"] == 0
    assert client.get(f"/api/competitors/{down}").json()["status"] == "offline" and client.get(f"/api/competitors/{good}").json()["status"] == "online"
    assert not any(c["checking"] for c in client.get("/api/competitors").json())


def test_oversized_responses_are_refused(client, web, monkeypatch):
    monkeypatch.setenv("MAX_RESPONSE_BYTES", "10000")
    from spy.api import get_fetcher
    from spy.main import app
    fetcher = web.fetcher()
    app.dependency_overrides[get_fetcher] = lambda: fetcher
    web.set(SITE, "x" * 20000)
    cid = add_live(client)
    assert "too_large" in run(client, cid)["check"]["error"]


def test_a_check_cannot_run_twice_at_once_and_disabled_competitors_cannot_be_checked(client, web):
    web.set(SITE, "<html></html>")
    cid = add_live(client)
    store.begin_check(cid)
    r = client.post(f"/api/competitors/{cid}/check")
    assert r.status_code == 409 and "already running" in r.json()["detail"]
    store.get_competitor(cid).checking = False
    off = client.post("/api/competitors", json={"name": "Off", "website_url": "https://off2.test/", "enabled": False}).json()["id"]
    assert client.post(f"/api/competitors/{off}/check").status_code == 409
    assert client.post("/api/competitors/99999/check").status_code == 404


# ---------------------------------------------------------------- sample (simulated) competitors
def test_sample_competitors_are_simulated_and_failures_are_shown(client):
    comps = {c["name"]: c for c in client.get("/api/competitors").json()}
    ok = run(client, comps["Acme Analytics"]["id"])
    assert ok["check"]["status"] == "success" and ok["competitor"]["status"] == "online" and ok["competitor"]["kind"] == "sample"
    flaky = comps["Globex Cloud"]["id"]
    first, second = run(client, flaky), run(client, flaky)
    assert {first["check"]["status"], second["check"]["status"]} == {"success", "failed"}                  # alternates, demonstrating failure + recovery
    assert client.post(f"/api/competitors/{comps['Initech Labs']['id']}/check").status_code == 409


# ---------------------------------------------------------------- parsing units
def test_parse_feed_rejects_html_and_empty_feeds():
    assert parse_feed(b"<html><body>hello</body></html>", "https://x.test/") is None
    assert parse_feed(rss([]).encode(), "https://x.test/") is None
    m, items = parse_feed(rss([("T", "/relative/link", None, None, None)]).encode(), "https://x.test/base/")
    assert m == "rss" and items[0].url == "https://x.test/relative/link" and items[0].published is None


def test_extract_page_items_skips_non_article_links():
    items = extract_page_items(PAGE.encode() % b"2020-01-01T10:00:00Z", "https://rival.test/")
    assert len(items) == 2 and all(i.url.startswith("https://rival.test/blog/") for i in items) and items[0].published is not None


# ---------------------------------------------------------------- safety: private addresses are never fetched
@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/admin", "http://192.168.1.1/",
                                 "http://[::1]/", "http://0.0.0.0/", "ftp://example.com/", "http://user:pw@example.com/"])
def test_private_and_unsafe_urls_are_blocked(url):
    with pytest.raises(FetchError) as e:
        assert_public_url(url)
    assert e.value.kind in ("blocked", "invalid")


def test_check_of_a_private_address_fails_safely_with_the_real_guard(client):
    from spy.api import get_fetcher
    from spy.main import app
    app.dependency_overrides.pop(get_fetcher, None)
    app.dependency_overrides[get_fetcher] = lambda: Fetcher()                                     # the real guard, the real httpx client
    cid = add_live(client, "http://127.0.0.1:9/")
    r = run(client, cid)
    assert r["check"]["status"] == "failed" and "blocked" in r["check"]["error"] and "non-public" in r["check"]["error"]


def test_a_redirect_to_a_private_address_is_blocked_hop_by_hop(client, web):
    def guard(url):
        if "169.254" in url:
            raise FetchError("blocked", "resolves to a non-public address")
    from spy.api import get_fetcher
    from spy.main import app
    fetcher = web.fetcher(guard=guard)
    app.dependency_overrides[get_fetcher] = lambda: fetcher
    web.redirect(SITE, "http://169.254.169.254/latest/meta-data/")
    web.set("http://169.254.169.254/latest/meta-data/", "SECRET")
    cid = add_live(client)
    r = run(client, cid)
    assert r["check"]["status"] == "failed" and "blocked" in r["check"]["error"]
    assert "http://169.254.169.254/latest/meta-data/" not in web.requests                       # the request was never sent
