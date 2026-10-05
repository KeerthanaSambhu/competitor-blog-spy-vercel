"""Vercel entrypoint: Vercel looks for a FastAPI instance named `app` in index.py at the project root."""
from spy.main import app  # noqa: F401
