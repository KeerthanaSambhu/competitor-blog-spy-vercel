import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helpers import FakeWeb  # noqa: E402
from index import app  # noqa: E402  (imported exactly the way Vercel imports it)
from spy.api import get_fetcher  # noqa: E402
from spy.store import store  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    for var in ("MAX_COMPETITORS", "REQUEST_TIMEOUT_SECONDS", "MAX_RESPONSE_BYTES", "CHECK_CONCURRENCY", "MAX_ARTICLES_PER_COMPETITOR", "ALLOW_PRIVATE_URLS"):
        monkeypatch.delenv(var, raising=False)
    store.reset()
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def web(client):
    """A fake internet wired into the API (live checks use it instead of the real network)."""
    w = FakeWeb()
    fetcher = w.fetcher()
    app.dependency_overrides[get_fetcher] = lambda: fetcher
    w.fetcher_instance = fetcher
    return w
