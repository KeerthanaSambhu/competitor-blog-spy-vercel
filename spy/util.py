from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    """UTC ISO-8601 with a trailing Z (parsed identically by every browser)."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def url_key(url: str) -> str:
    """Comparison form of an article URL: http/https, www., #fragment, trailing slash and utm_* parameters do not matter."""
    p = urlsplit(url.strip())
    host = (p.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    q = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid"))
    return host + (f":{p.port}" if p.port and p.port not in (80, 443) else "") + p.path.rstrip("/") + (("?" + urlencode(q)) if q else "")
