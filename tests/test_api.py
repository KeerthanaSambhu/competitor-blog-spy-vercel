import re


def add(client, name="Acme", site="https://acme.test/", **kw):
    return client.post("/api/competitors", json={"name": name, "website_url": site, **kw})


def test_health_needs_no_configuration(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["storage"] == "memory" and body["version"] and body["uptime_seconds"] >= 0


def test_dashboard_page_and_favicon_are_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Competitor Blog Spy" in r.text and "<script>" in r.text and 'id="view"' in r.text
    assert client.get("/favicon.ico").status_code == 200
    assert client.get("/docs").status_code == 200 and client.get("/openapi.json").status_code == 200


def test_demo_data_is_there_immediately(client):
    d = client.get("/api/dashboard").json()
    assert d["storage"] == "memory" and d["competitors"]["total"] == 4 and d["competitors"]["sample"] == 4
    assert d["articles"]["total"] >= 15 and d["articles"]["new"] > 0 and d["articles"]["baseline"] > 0
    assert len(d["articles"]["per_day"]) == 14 and d["articles"]["by_competitor"]
    t = d["detection_delay"]
    assert t["measured"] > 0 and t["fastest_seconds"] <= t["average_seconds"] <= t["slowest_seconds"]
    assert t["slowest_seconds"] > t["target_seconds"] > t["fastest_seconds"]             # the demo shows an over-target delay, exactly
    assert t["within_target"] < t["measured"]
    assert d["checks"]["total"] > 0 and d["checks"]["failed"] >= 1 and d["latest_articles"] and d["recent_checks"]
    states = d["competitors"]["by_status"]
    assert states.get("online") and states.get("offline") and states.get("disabled")


def test_dashboard_numbers_match_the_lists(client):
    d = client.get("/api/dashboard").json()
    arts = client.get("/api/articles?limit=200").json()
    assert d["articles"]["total"] == arts["total"] == len(arts["items"])
    delays = [a["detection_delay_seconds"] for a in arts["items"] if a["status"] == "new" and a["detection_delay_seconds"] is not None]
    assert d["detection_delay"]["measured"] == len(delays) and d["detection_delay"]["slowest_seconds"] == max(delays)
    assert abs(d["detection_delay"]["average_seconds"] - sum(delays) / len(delays)) < 0.001
    checks = client.get("/api/checks?limit=300").json()
    assert d["checks"]["total"] == len(checks) and d["checks"]["failed"] == sum(c["status"] == "failed" for c in checks)


# ---------------------------------------------------------------- competitors CRUD
def test_competitor_create_read_update_delete(client):
    r = add(client, "  New   Rival ", "https://rival.test/blog", feed_url="https://rival.test/feed.xml")
    assert r.status_code == 201
    c = r.json()
    assert c["name"] == "New Rival" and c["kind"] == "live" and c["status"] == "unchecked" and c["feed_url"] == "https://rival.test/feed.xml"
    assert client.get(f"/api/competitors/{c['id']}").json()["name"] == "New Rival"
    assert any(x["id"] == c["id"] for x in client.get("/api/competitors").json())

    u = client.put(f"/api/competitors/{c['id']}", json={"name": "Renamed", "website_url": "https://rival.test/news", "feed_url": None, "enabled": False})
    assert u.status_code == 200 and u.json()["name"] == "Renamed" and u.json()["status"] == "disabled" and u.json()["feed_url"] is None
    back = client.put(f"/api/competitors/{c['id']}", json={"name": "Renamed", "website_url": "https://rival.test/news", "enabled": True})
    assert back.json()["status"] == "unchecked"

    assert client.delete(f"/api/competitors/{c['id']}").json() == {"deleted": c["id"]}
    assert client.get(f"/api/competitors/{c['id']}").status_code == 404
    assert client.delete(f"/api/competitors/{c['id']}").status_code == 404
    assert client.put("/api/competitors/9999", json={"name": "x", "website_url": "https://x.test"}).status_code == 404


def test_competitor_validation_messages_name_the_field(client):
    bad = [({"name": "", "website_url": "https://a.test"}, "name"), ({"name": "x" * 81, "website_url": "https://a.test"}, "name"),
           ({"name": "A", "website_url": "ftp://a.test"}, "website_url"), ({"name": "A", "website_url": "not a url"}, "website_url"),
           ({"name": "A", "website_url": "https://localhost"}, "website_url"), ({"name": "A", "website_url": "https://user:pw@a.test/"}, "website_url"),
           ({"name": "A", "website_url": "https://a.test", "feed_url": "javascript:alert(1)"}, "feed_url"), ({"website_url": "https://a.test"}, "name")]
    for body, field in bad:
        r = client.post("/api/competitors", json=body)
        assert r.status_code == 422, body
        assert r.json()["field"] == field and r.json()["detail"], body


def test_duplicate_website_is_refused_even_with_url_variations(client):
    assert add(client, "One", "https://same.test/blog/").status_code == 201
    for variant in ("http://www.same.test/blog", "https://SAME.test/blog/?utm_source=x#top"):
        r = add(client, "Two", variant)
        assert r.status_code == 409 and r.json()["field"] == "website_url" and "One" in r.json()["detail"]
    other = add(client, "Three", "https://same.test/other")
    assert other.status_code == 201
    assert client.put(f"/api/competitors/{other.json()['id']}", json={"name": "Three", "website_url": "https://same.test/blog"}).status_code == 409


def test_competitor_limit_protects_the_public_demo(client, monkeypatch):
    monkeypatch.setenv("MAX_COMPETITORS", "6")
    assert add(client, "A", "https://a1.test").status_code == 201 and add(client, "B", "https://b1.test").status_code == 201
    r = add(client, "C", "https://c1.test")
    assert r.status_code == 409 and "limit" in r.json()["detail"].lower()


def test_deleting_a_competitor_removes_its_articles_and_checks(client):
    comps = client.get("/api/competitors").json()
    victim = comps[0]
    n_before = client.get("/api/articles?limit=200").json()["total"]
    n_mine = client.get(f"/api/articles?competitor_id={victim['id']}&limit=200").json()["total"]
    assert n_mine > 0 and client.get(f"/api/checks?competitor_id={victim['id']}").json()
    client.delete(f"/api/competitors/{victim['id']}")
    assert client.get("/api/articles?limit=200").json()["total"] == n_before - n_mine
    assert client.get(f"/api/checks?competitor_id={victim['id']}").json() == []


# ---------------------------------------------------------------- articles
def test_article_list_filters_search_and_paging(client):
    allr = client.get("/api/articles?limit=200").json()
    assert allr["total"] > 10
    first = client.get("/api/articles?limit=5").json()
    second = client.get("/api/articles?limit=5&offset=5").json()
    assert len(first["items"]) == 5 and not {a["id"] for a in first["items"]} & {a["id"] for a in second["items"]} and first["total"] == allr["total"]
    stamps = [a["discovered_at"] for a in allr["items"]]
    assert stamps == sorted(stamps, reverse=True)                                    # newest first
    cid = allr["items"][0]["competitor_id"]
    mine = client.get(f"/api/articles?competitor_id={cid}&limit=200").json()
    assert mine["total"] and all(a["competitor_id"] == cid for a in mine["items"])
    new = client.get("/api/articles?status=new&limit=200").json()
    base = client.get("/api/articles?status=baseline&limit=200").json()
    assert new["total"] + base["total"] == allr["total"] and all(a["detection_delay_seconds"] is None for a in base["items"])
    word = allr["items"][0]["title"].split()[0]
    hits = client.get("/api/articles", params={"q": word.upper(), "limit": 200}).json()
    assert hits["total"] >= 1 and all(word.lower() in (a["title"] + a["summary"] + " ".join(a["tags"])).lower() for a in hits["items"])
    assert client.get("/api/articles?q=zzzz-no-such-text").json()["total"] == 0
    assert client.get("/api/articles?status=bogus").status_code == 422 and client.get("/api/articles?limit=0").status_code == 422


def test_article_details(client):
    a = client.get("/api/articles?status=new&limit=1").json()["items"][0]
    d = client.get(f"/api/articles/{a['id']}").json()
    for key in ("title", "url", "summary", "author", "tags", "published_at", "discovered_at", "detection_delay_seconds", "method", "status", "competitor_name"):
        assert key in d
    assert d["detection_delay_seconds"] is not None and d["competitor_name"]
    assert client.get("/api/articles/999999").status_code == 404


# ---------------------------------------------------------------- state / reset / browser-backup restore
def test_reset_restores_the_sample_data(client):
    add(client)
    assert client.get("/api/state").json()["pristine"] is False
    assert client.post("/api/demo/reset").json()["status"] == "reset"
    assert len(client.get("/api/competitors").json()) == 4 and client.get("/api/state").json()["pristine"] is True


def test_restore_from_browser_backup_only_on_an_untouched_server(client):
    payload = {"competitors": [{"name": "Backed up", "website_url": "https://backup.test/", "feed_url": None, "enabled": True},
                               {"name": "Second", "website_url": "https://second.test/", "enabled": False}]}
    assert client.get("/api/state").json()["pristine"] is True
    r = client.post("/api/state/restore", json=payload)
    assert r.status_code == 200 and r.json()["restored"] == 2
    names = {c["name"]: c for c in client.get("/api/competitors").json()}
    assert names["Backed up"]["kind"] == "live" and names["Second"]["status"] == "disabled" and len(names) == 6
    assert client.get("/api/state").json()["pristine"] is False
    assert client.post("/api/state/restore", json=payload).status_code == 409                # never overwrites a server that has data
    assert client.post("/api/state/restore", json={"competitors": [{"name": "", "website_url": "x"}]}).status_code == 422


def test_ui_only_calls_routes_that_exist(client):
    from spy.ui import INDEX_HTML
    paths = client.get("/openapi.json").json()["paths"]
    used = set(re.findall(r"api\('(?:GET|POST|PUT|DELETE)', '(/[a-z\-/]*)", INDEX_HTML))
    assert {"/dashboard", "/competitors", "/articles", "/checks", "/check-all", "/state", "/state/restore", "/demo/reset"} <= {u.rstrip("/") or u for u in used} | {"/competitors"}
    for u in used:
        assert any(p.startswith("/api" + u.rstrip("/")) for p in paths), u
    assert not re.search(r"""(src|href)=["']https?://(?!www\.w3\.org)""", INDEX_HTML)      # no external assets: works without any CDN
