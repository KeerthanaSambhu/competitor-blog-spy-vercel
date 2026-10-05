"""Request validation (pydantic) and the in-memory record types."""
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, field_validator


def clean_http_url(value: str | None, required: bool = False) -> str | None:
    if value is None or not value.strip():
        if required:
            raise ValueError("URL is required")
        return None
    v = value.strip()
    if len(v) > 2048 or any(c.isspace() for c in v):
        raise ValueError("URL is too long or contains spaces")
    p = urlsplit(v)
    if p.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    if not p.hostname or "." not in p.hostname:
        raise ValueError("URL must contain a valid host name, e.g. https://example.com")
    if p.username or p.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    try:
        p.port
    except ValueError:
        raise ValueError("URL has an invalid port")
    return v


class CompetitorIn(BaseModel):
    name: str
    website_url: str
    feed_url: str | None = None
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Name is required")
        if len(v) > 80:
            raise ValueError("Name must be at most 80 characters")
        return v

    @field_validator("website_url")
    @classmethod
    def _site(cls, v: str) -> str:
        return clean_http_url(v, required=True)

    @field_validator("feed_url")
    @classmethod
    def _feed(cls, v: str | None) -> str | None:
        return clean_http_url(v)


class RestoreIn(BaseModel):
    competitors: list[CompetitorIn]


@dataclass
class Competitor:
    id: int
    name: str
    website_url: str
    feed_url: str | None
    enabled: bool
    kind: str                                  # "sample" (simulated) | "live" (really fetched)
    created_at: datetime
    status: str = "unchecked"                  # unchecked | online | offline | disabled
    strategy: str | None = None                # rss | atom | html | sample
    discovered_feed_url: str | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    baseline_done: bool = False
    checks_run: int = 0
    checking: bool = False
    sim_flaky: bool = False                    # sample competitor that fails every other check (to show failure handling)


@dataclass
class Article:
    id: int
    competitor_id: int
    title: str
    url: str
    url_key: str
    discovered_at: datetime
    status: str                                # "new" (detected after monitoring began) | "baseline" (already existed at the first check)
    method: str                                # rss | atom | html | sample
    summary: str = ""
    author: str | None = None
    published_at: datetime | None = None
    delay_seconds: float | None = None         # discovery - publication, only when the source gave a publication time
    tags: list[str] = field(default_factory=list)


@dataclass
class Check:
    id: int
    competitor_id: int
    competitor_name: str
    started_at: datetime
    duration_ms: int
    status: str                                # success | failed
    method: str | None
    items_found: int
    new_articles: int
    error: str | None = None
