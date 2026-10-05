"""HTTP fetching for live checks: timeouts, size cap, and protection against requests to private/internal addresses (SSRF).

The app is public and fetches URLs that visitors type, so every request - including each redirect hop - is checked first.
"""
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from .config import get_settings

USER_AGENT = "CompetitorBlogSpy/1.0 (+demo project; polite content monitor)"


class FetchError(Exception):
    """kind: timeout | network | http_error | too_large | blocked | invalid"""

    def __init__(self, kind: str, message: str, status: int | None = None):
        super().__init__(message)
        self.kind, self.message, self.status = kind, message, status

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}"


def assert_public_url(url: str) -> None:
    """Allow only http(s) URLs whose host resolves to PUBLIC addresses (no localhost, private, link-local or metadata IPs)."""
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise FetchError("invalid", f"not an http(s) URL: {url[:80]}")
    if p.username or p.password:
        raise FetchError("blocked", "URLs with embedded credentials are not allowed")
    if get_settings().allow_private_urls:
        return
    host = p.hostname
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise FetchError("network", f"cannot resolve host {host}: {e}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise FetchError("blocked", f"{host} resolves to a non-public address; only public websites can be monitored")


@dataclass
class FetchResult:
    url: str
    status: int
    content: bytes
    content_type: str


class Fetcher:
    """Thin httpx wrapper. `transport` and `guard` can be replaced in tests."""

    def __init__(self, transport=None, guard=assert_public_url, timeout: float | None = None):
        s = get_settings()
        self.guard, self.max_bytes = guard, s.max_response_bytes
        self.timeout = timeout or s.request_timeout
        self.client = httpx.Client(
            transport=transport, timeout=httpx.Timeout(self.timeout), follow_redirects=True, max_redirects=4,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml,application/atom+xml,*/*;q=0.8"},
            event_hooks={"request": [lambda request: self.guard(str(request.url))]})   # runs for every redirect hop too

    def get(self, url: str) -> FetchResult:
        try:
            with self.client.stream("GET", url) as resp:
                if resp.status_code >= 400:
                    raise FetchError("http_error", f"HTTP {resp.status_code}", resp.status_code)
                chunks, size = [], 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise FetchError("too_large", f"response larger than {self.max_bytes} bytes")
                    chunks.append(chunk)
                return FetchResult(str(resp.url), resp.status_code, b"".join(chunks), resp.headers.get("content-type", ""))
        except FetchError:
            raise
        except httpx.TimeoutException:
            raise FetchError("timeout", f"timed out after {self.timeout:g}s")
        except httpx.TooManyRedirects:
            raise FetchError("invalid", "too many redirects")
        except httpx.InvalidURL as e:
            raise FetchError("invalid", str(e))
        except httpx.HTTPError as e:
            raise FetchError("network", f"{type(e).__name__}: {e}")

    def close(self) -> None:
        self.client.close()
