"""In-memory data store (no database, no files). Thread-safe. Seeded with sample data on first use.

Serverless note: this lives in the memory of one function instance. It survives between requests while the instance is warm and
is rebuilt (from the sample data) when a new instance starts - see README "How data is kept".
"""
import threading
from datetime import datetime, timedelta

from .config import get_settings
from .models import Article, Check, Competitor
from .util import iso, now_utc, url_key


class StoreError(Exception):
    def __init__(self, status_code: int, message: str, field: str | None = None):
        super().__init__(message)
        self.status_code, self.message, self.field = status_code, message, field


class Store:
    def __init__(self):
        self._lock = threading.RLock()
        self._seeded = False
        self._seeding_by: int | None = None
        self._clear()

    # ------------------------------------------------------------------ state
    def _clear(self):
        self.competitors: dict[int, Competitor] = {}
        self.articles: dict[int, Article] = {}
        self.checks: list[Check] = []
        self._ids = {"competitor": 0, "article": 0, "check": 0}
        self.user_version = 0                           # incremented by user changes to competitors; 0 = untouched sample state
        self.started_at = now_utc()

    def _next(self, kind: str) -> int:
        self._ids[kind] += 1
        return self._ids[kind]

    def ensure_seeded(self):
        if self._seeded:
            return
        with self._lock:                                  # other threads wait here until seeding is complete
            if self._seeded or self._seeding_by == threading.get_ident():
                return                                    # (the seeding thread itself calls back into the store)
            self._seeding_by = threading.get_ident()
            try:
                from .seed import load_sample_data
                load_sample_data(self)
                self._seeded = True
            finally:
                self._seeding_by = None

    def reset(self):
        """Back to the sample data (also used by the 'Reset demo data' button and by tests)."""
        with self._lock:
            self._clear()
            self._seeded = False
        self.ensure_seeded()

    @property
    def pristine(self) -> bool:
        return self.user_version == 0

    # ------------------------------------------------------------------ competitors
    def list_competitors(self) -> list[Competitor]:
        self.ensure_seeded()
        with self._lock:
            return sorted(self.competitors.values(), key=lambda c: c.id)

    def get_competitor(self, cid: int) -> Competitor:
        self.ensure_seeded()
        c = self.competitors.get(cid)
        if c is None:
            raise StoreError(404, f"Competitor {cid} not found")
        return c

    def _check_duplicate(self, website_url: str, exclude_id: int | None = None):
        key = url_key(website_url)
        for c in self.competitors.values():
            if c.id != exclude_id and url_key(c.website_url) == key:
                raise StoreError(409, f'This website is already added as "{c.name}"', "website_url")

    def add_competitor(self, name, website_url, feed_url=None, enabled=True, kind="live", user=True, **extra) -> Competitor:
        self.ensure_seeded()
        with self._lock:
            if user and len(self.competitors) >= get_settings().max_competitors:
                raise StoreError(409, f"Demo limit reached: at most {get_settings().max_competitors} competitors")
            self._check_duplicate(website_url)
            c = Competitor(id=self._next("competitor"), name=name, website_url=website_url, feed_url=feed_url, enabled=enabled,
                           kind=kind, created_at=now_utc(), status="unchecked" if enabled else "disabled", **extra)
            self.competitors[c.id] = c
            if user:
                self.user_version += 1
            return c

    def update_competitor(self, cid: int, name, website_url, feed_url, enabled) -> Competitor:
        with self._lock:
            c = self.get_competitor(cid)
            self._check_duplicate(website_url, exclude_id=cid)
            if (c.website_url, c.feed_url) != (website_url, feed_url):
                c.discovered_feed_url, c.baseline_done = None, False if c.kind == "live" else c.baseline_done
            c.name, c.website_url, c.feed_url, c.enabled = name, website_url, feed_url, enabled
            c.status = "disabled" if not enabled else ("unchecked" if c.status == "disabled" else c.status)
            self.user_version += 1
            return c

    def delete_competitor(self, cid: int) -> None:
        with self._lock:
            c = self.get_competitor(cid)
            del self.competitors[c.id]
            for aid in [a.id for a in self.articles.values() if a.competitor_id == cid]:
                del self.articles[aid]
            self.checks = [k for k in self.checks if k.competitor_id != cid]
            self.user_version += 1

    def begin_check(self, cid: int) -> Competitor:
        """Mark a competitor as being checked (a second check of the same competitor is refused while one runs)."""
        with self._lock:
            c = self.get_competitor(cid)
            if not c.enabled:
                raise StoreError(409, "Monitoring is disabled for this competitor - enable it first")
            if c.checking:
                raise StoreError(409, "A check of this competitor is already running")
            c.checking = True
            return c

    # ------------------------------------------------------------------ articles
    def add_article(self, comp: Competitor, **fields) -> Article | None:
        """Add an article unless this competitor already has that URL. Returns None for a duplicate."""
        with self._lock:
            key = url_key(fields["url"])
            if any(a.competitor_id == comp.id and a.url_key == key for a in self.articles.values()):
                return None
            art = Article(id=self._next("article"), competitor_id=comp.id, url_key=key, **fields)
            self.articles[art.id] = art
            mine = sorted((a for a in self.articles.values() if a.competitor_id == comp.id), key=lambda a: a.discovered_at)
            for old in mine[:max(0, len(mine) - get_settings().max_articles_per_competitor)]:    # memory stays bounded
                del self.articles[old.id]
            return art

    def get_article(self, aid: int) -> Article:
        self.ensure_seeded()
        a = self.articles.get(aid)
        if a is None:
            raise StoreError(404, f"Article {aid} not found")
        return a

    def list_articles(self, competitor_id=None, q=None, status=None, limit=50, offset=0):
        self.ensure_seeded()
        with self._lock:
            items = list(self.articles.values())
        if competitor_id is not None:
            items = [a for a in items if a.competitor_id == competitor_id]
        if status:
            items = [a for a in items if a.status == status]
        if q:
            needle = q.strip().lower()
            items = [a for a in items if needle in a.title.lower() or needle in a.summary.lower() or any(needle in t.lower() for t in a.tags)]
        items.sort(key=lambda a: (a.discovered_at, a.id), reverse=True)
        return len(items), items[offset:offset + limit]

    # ------------------------------------------------------------------ checks
    def record_check(self, comp: Competitor, started_at: datetime, duration_ms: int, status: str, method, items_found, new_articles, error=None) -> Check:
        with self._lock:
            chk = Check(self._next("check"), comp.id, comp.name, started_at, duration_ms, status, method, items_found, new_articles, error)
            self.checks.append(chk)
            del self.checks[:-300]
            return chk

    def list_checks(self, limit=50, competitor_id=None) -> list[Check]:
        self.ensure_seeded()
        with self._lock:
            items = [c for c in self.checks if competitor_id is None or c.competitor_id == competitor_id]
        return sorted(items, key=lambda c: (c.started_at, c.id), reverse=True)[:limit]

    # ------------------------------------------------------------------ restore (browser backup)
    def restore_live_competitors(self, items) -> list[Competitor]:
        """Re-add competitors a browser had backed up. Only allowed while the server still holds the untouched sample state."""
        self.ensure_seeded()
        with self._lock:
            if not self.pristine:
                raise StoreError(409, "The server already holds changes; nothing restored")
            added = []
            for it in items[:get_settings().max_competitors]:
                try:
                    added.append(self.add_competitor(it.name, it.website_url, it.feed_url, it.enabled, kind="live", user=False))
                except StoreError:
                    continue
            self.user_version += 1
            return added

    # ------------------------------------------------------------------ serialisation
    def competitor_dict(self, c: Competitor) -> dict:
        mine = [a for a in self.articles.values() if a.competitor_id == c.id]
        return {"id": c.id, "name": c.name, "website_url": c.website_url, "feed_url": c.feed_url, "enabled": c.enabled, "kind": c.kind,
                "status": c.status, "strategy": c.strategy, "discovered_feed_url": c.discovered_feed_url,
                "last_checked_at": iso(c.last_checked_at), "last_success_at": iso(c.last_success_at), "last_error": c.last_error,
                "consecutive_failures": c.consecutive_failures, "checking": c.checking, "created_at": iso(c.created_at),
                "article_count": len(mine), "new_article_count": sum(1 for a in mine if a.status == "new")}

    def article_dict(self, a: Article) -> dict:
        c = self.competitors.get(a.competitor_id)
        return {"id": a.id, "competitor_id": a.competitor_id, "competitor_name": c.name if c else None, "competitor_kind": c.kind if c else None,
                "title": a.title, "url": a.url, "summary": a.summary, "author": a.author, "tags": a.tags, "status": a.status, "method": a.method,
                "published_at": iso(a.published_at), "discovered_at": iso(a.discovered_at), "detection_delay_seconds": a.delay_seconds}

    @staticmethod
    def check_dict(k: Check) -> dict:
        return {"id": k.id, "competitor_id": k.competitor_id, "competitor_name": k.competitor_name, "started_at": iso(k.started_at),
                "duration_ms": k.duration_ms, "status": k.status, "method": k.method, "items_found": k.items_found,
                "new_articles": k.new_articles, "error": k.error}

    # ------------------------------------------------------------------ dashboard
    def dashboard(self, target_seconds: int = 300) -> dict:
        self.ensure_seeded()
        now = now_utc()
        with self._lock:
            comps = list(self.competitors.values())
            arts = list(self.articles.values())
            checks = list(self.checks)
        by_status: dict[str, int] = {}
        for c in comps:
            by_status[c.status] = by_status.get(c.status, 0) + 1
        new = [a for a in arts if a.status == "new"]
        delays = [a.delay_seconds for a in new if a.delay_seconds is not None]
        today = now.date()
        per_day = {(today - timedelta(days=i)): 0 for i in range(13, -1, -1)}
        for a in arts:
            d = a.discovered_at.astimezone(now.tzinfo).date()
            if d in per_day:
                per_day[d] += 1
        names = {c.id: c.name for c in comps}
        counts: dict[int, int] = {}
        for a in arts:
            counts[a.competitor_id] = counts.get(a.competitor_id, 0) + 1
        failed = sum(1 for k in checks if k.status == "failed")
        return {
            "storage": "memory",
            "competitors": {"total": len(comps), "enabled": sum(c.enabled for c in comps), "by_status": by_status,
                            "sample": sum(c.kind == "sample" for c in comps), "live": sum(c.kind == "live" for c in comps)},
            "articles": {"total": len(arts), "new": len(new), "baseline": len(arts) - len(new),
                         "last_24h": sum(1 for a in arts if now - a.discovered_at <= timedelta(hours=24)),
                         "per_day": [{"date": d.isoformat(), "count": n} for d, n in per_day.items()],
                         "by_competitor": sorted(({"name": names.get(cid, "?"), "count": n} for cid, n in counts.items()), key=lambda x: -x["count"])[:8]},
            "detection_delay": {"average_seconds": round(sum(delays) / len(delays), 3) if delays else None,
                                "fastest_seconds": min(delays) if delays else None, "slowest_seconds": max(delays) if delays else None,
                                "measured": len(delays), "target_seconds": target_seconds, "within_target": sum(d <= target_seconds for d in delays)},
            "checks": {"total": len(checks), "failed": failed, "success_rate": round(100 * (len(checks) - failed) / len(checks), 1) if checks else None},
            "latest_articles": [self.article_dict(a) for a in sorted(arts, key=lambda a: (a.discovered_at, a.id), reverse=True)[:8]],
            "recent_checks": [self.check_dict(k) for k in sorted(checks, key=lambda k: (k.started_at, k.id), reverse=True)[:8]],
        }


store = Store()
