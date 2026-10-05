"""A fake internet for the tests: URL -> response, served through httpx.MockTransport (no real network)."""
from datetime import datetime, timezone
from email.utils import format_datetime

import httpx

from spy.net import Fetcher


class FakeWeb:
    def __init__(self):
        self.routes: dict[str, object] = {}
        self.requests: list[str] = []

    def set(self, url: str, body: str | bytes, ctype: str = "text/html; charset=utf-8", status: int = 200):
        self.routes[url] = (status, body.encode() if isinstance(body, str) else body, ctype, {})

    def redirect(self, url: str, to: str):
        self.routes[url] = (302, b"", "text/html", {"location": to})

    def fail(self, url: str, exc: Exception):
        self.routes[url] = exc

    def _handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        r = self.routes.get(url)
        if r is None:
            return httpx.Response(404, content=b"not found")
        if isinstance(r, Exception):
            raise r
        status, body, ctype, extra = r
        return httpx.Response(status, content=body, headers={"content-type": ctype, **extra})

    def fetcher(self, guard=lambda url: None) -> Fetcher:
        return Fetcher(transport=httpx.MockTransport(self._handle), guard=guard)


def rss(items, title="Blog") -> str:
    """items: (title, link, published datetime|None, author|None, description|None)"""
    out = ['<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>%s</title><link>https://x.test/</link><description>d</description>' % title]
    for t, link, pub, author, desc in items:
        out.append("<item><title>%s</title><link>%s</link>" % (t, link))
        if pub:
            out.append("<pubDate>%s</pubDate>" % format_datetime(pub.astimezone(timezone.utc), usegmt=True))
        if author:
            out.append("<author>%s</author>" % author)
        out.append("<description>%s</description></item>" % (desc or ""))
    out.append("</channel></rss>")
    return "".join(out)


def atom(items, title="Blog") -> str:
    out = ['<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>%s</title><id>urn:x</id><updated>2026-01-01T00:00:00Z</updated>' % title]
    for t, link, pub, author, desc in items:
        out.append('<entry><title>%s</title><link href="%s"/><id>%s</id>' % (t, link, link))
        if pub:
            out.append("<updated>%s</updated><published>%s</published>" % ((pub.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),) * 2))
        if author:
            out.append("<author><name>%s</name></author>" % author)
        out.append("<summary>%s</summary></entry>" % (desc or ""))
    out.append("</feed>")
    return "".join(out)


def now_utc():
    return datetime.now(timezone.utc)
