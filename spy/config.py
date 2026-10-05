"""Optional settings read from environment variables. Every variable has a default: nothing is required to start."""
import os
from dataclasses import dataclass


def _num(name: str, default, cast):
    try:
        return cast(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    max_competitors: int
    request_timeout: float
    max_response_bytes: int
    check_concurrency: int
    max_articles_per_competitor: int
    allow_private_urls: bool


def get_settings() -> Settings:
    """Read at call time (not import time) so tests and deployments can change the environment."""
    return Settings(
        max_competitors=max(1, _num("MAX_COMPETITORS", 25, int)),
        request_timeout=max(1.0, _num("REQUEST_TIMEOUT_SECONDS", 8.0, float)),
        max_response_bytes=max(10_000, _num("MAX_RESPONSE_BYTES", 2_000_000, int)),
        check_concurrency=max(1, min(8, _num("CHECK_CONCURRENCY", 4, int))),
        max_articles_per_competitor=max(10, _num("MAX_ARTICLES_PER_COMPETITOR", 100, int)),
        allow_private_urls=os.environ.get("ALLOW_PRIVATE_URLS", "false").strip().lower() in ("1", "true", "yes"),
    )
