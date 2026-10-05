"""JSON API (all routes live under /api). Interactive docs: /docs"""
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import APIRouter, Depends, Query

from . import __version__
from .config import get_settings
from .models import CompetitorIn, RestoreIn
from .monitor import check_competitor
from .net import Fetcher
from .store import StoreError, store
from .util import iso, now_utc

router = APIRouter(prefix="/api")

_fetcher: Fetcher | None = None


def get_fetcher() -> Fetcher:
    """One shared HTTP client per function instance (created on first use). Tests replace this dependency."""
    global _fetcher
    if _fetcher is None:
        _fetcher = Fetcher()
    return _fetcher


# ------------------------------------------------------------------------------------------------ health / state
@router.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": __version__, "time": iso(now_utc()), "storage": "memory",
            "instance_started_at": iso(store.started_at), "uptime_seconds": int((now_utc() - store.started_at).total_seconds())}


@router.get("/state", tags=["system"])
def state():
    """pristine = this server instance still holds the untouched sample data (used by the browser backup/restore)."""
    store.ensure_seeded()
    return {"pristine": store.pristine, "storage": "memory", "max_competitors": get_settings().max_competitors, "instance_started_at": iso(store.started_at)}


@router.post("/state/restore", tags=["system"])
def restore(body: RestoreIn):
    added = store.restore_live_competitors(body.competitors)
    return {"restored": len(added), "competitors": [store.competitor_dict(c) for c in added]}


@router.post("/demo/reset", tags=["system"])
def reset_demo():
    store.reset()
    return {"status": "reset", "competitors": len(store.list_competitors())}


# ------------------------------------------------------------------------------------------------ competitors
@router.get("/competitors", tags=["competitors"])
def list_competitors():
    return [store.competitor_dict(c) for c in store.list_competitors()]


@router.post("/competitors", status_code=201, tags=["competitors"])
def create_competitor(body: CompetitorIn):
    c = store.add_competitor(body.name, body.website_url, body.feed_url, body.enabled, kind="live")
    return store.competitor_dict(c)


@router.get("/competitors/{cid}", tags=["competitors"])
def get_competitor(cid: int):
    return store.competitor_dict(store.get_competitor(cid))


@router.put("/competitors/{cid}", tags=["competitors"])
def update_competitor(cid: int, body: CompetitorIn):
    return store.competitor_dict(store.update_competitor(cid, body.name, body.website_url, body.feed_url, body.enabled))


@router.delete("/competitors/{cid}", tags=["competitors"])
def delete_competitor(cid: int):
    store.delete_competitor(cid)
    return {"deleted": cid}


# ------------------------------------------------------------------------------------------------ monitoring
def _run_check(cid: int, fetcher: Fetcher):
    try:
        return check_competitor(store, cid, fetcher, random.Random())
    finally:
        store.get_competitor(cid).checking = False          # whatever happened, the competitor can be checked again


@router.post("/competitors/{cid}/check", tags=["monitoring"])
def check_one(cid: int, fetcher: Fetcher = Depends(get_fetcher)):
    """Check one competitor now (live competitors are fetched for real; sample competitors are simulated)."""
    store.begin_check(cid)
    chk = _run_check(cid, fetcher)
    return {"check": store.check_dict(chk), "competitor": store.competitor_dict(store.get_competitor(cid))}


@router.post("/check-all", tags=["monitoring"])
def check_all(fetcher: Fetcher = Depends(get_fetcher)):
    """Check every enabled competitor (a few at a time). A failing competitor never stops the others."""
    started, skipped = [], 0
    for c in store.list_competitors():
        if not c.enabled:
            continue
        try:
            store.begin_check(c.id)
            started.append(c.id)
        except StoreError:
            skipped += 1                                     # already being checked
    with ThreadPoolExecutor(max_workers=get_settings().check_concurrency) as pool:
        results = list(pool.map(lambda cid: _run_check(cid, fetcher), started))
    return {"checked": len(results), "skipped": skipped, "new_articles": sum(r.new_articles for r in results),
            "failed": sum(r.status == "failed" for r in results), "checks": [store.check_dict(r) for r in results]}


@router.get("/checks", tags=["monitoring"])
def list_checks(limit: int = Query(50, ge=1, le=300), competitor_id: int | None = None):
    return [store.check_dict(k) for k in store.list_checks(limit, competitor_id)]


# ------------------------------------------------------------------------------------------------ articles / dashboard
@router.get("/articles", tags=["articles"])
def list_articles(competitor_id: int | None = None, q: str | None = Query(None, max_length=100), status: Literal["new", "baseline"] | None = None,
                  limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0)):
    total, items = store.list_articles(competitor_id, q, status, limit, offset)
    return {"total": total, "limit": limit, "offset": offset, "items": [store.article_dict(a) for a in items]}


@router.get("/articles/{aid}", tags=["articles"])
def get_article(aid: int):
    return store.article_dict(store.get_article(aid))


@router.get("/dashboard", tags=["dashboard"])
def dashboard():
    return store.dashboard()
