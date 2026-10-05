"""Vercel-readiness: the entrypoint, vercel.json, dependencies, and the guarantee that nothing touches the filesystem or a database file."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "index.py", *sorted((ROOT / "spy").glob("*.py"))]
MIN_ENV = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}        # deliberately NO application variables


def run_py(code: str, env=None):
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env or MIN_ENV, capture_output=True, text=True, timeout=120)


def test_entrypoint_imports_with_an_empty_environment():
    out = run_py("from index import app; print(type(app).__name__, app.title)")
    assert out.returncode == 0, out.stderr[-600:]
    assert out.stdout.strip() == "FastAPI Competitor Blog Spy"


def test_vercel_entrypoint_file_is_where_vercel_looks_for_it():
    assert (ROOT / "index.py").is_file()                                                  # Vercel detects a FastAPI `app` in index.py at the root
    assert re.search(r"^from spy\.main import app", (ROOT / "index.py").read_text(), re.M)
    for forbidden in ("frontend", "backend", "api", "public", "static"):                  # these directories change how Vercel detects/serves a project
        assert not (ROOT / forbidden).exists(), forbidden
    assert not (ROOT / "pyproject.toml").exists()                                          # one dependency list only (requirements.txt)


def test_vercel_json_is_valid_simple_and_single_service():
    cfg = json.loads((ROOT / "vercel.json").read_text())
    assert set(cfg) <= {"$schema", "headers", "rewrites", "redirects", "cleanUrls", "trailingSlash"}, set(cfg)
    assert "services" not in cfg and "builds" not in cfg and "functions" not in cfg and "crons" not in cfg
    keys = {h["key"] for rule in cfg["headers"] for h in rule["headers"]}
    assert {"X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"} <= keys


def test_dependencies_are_complete_and_free_of_databases():
    names = {re.split(r"[<>=\[ ;]", ln.strip(), 1)[0].lower() for ln in (ROOT / "requirements.txt").read_text().splitlines() if ln.strip() and not ln.startswith("#")}
    assert {"fastapi", "httpx", "feedparser", "beautifulsoup4"} <= names
    assert not names & {"sqlalchemy", "psycopg", "psycopg2", "aiosqlite", "redis", "uvicorn", "pytest", "pymongo"}, names
    dev = (ROOT / "requirements-dev.txt").read_text()
    assert "-r requirements.txt" in dev and "pytest" in dev and "uvicorn" in dev


def test_source_code_has_no_database_or_filesystem_persistence():
    banned = re.compile(r"\bsqlite3\b|sqlalchemy|\btempfile\b|/tmp\b|[\"']/data\b|os\.makedirs|os\.mkdir|\.write_text\(|\.write_bytes\(|open\([^)]*[\"'][wax]\+?[\"']|\bshelve\b|pickle\.dump|\bpsycopg")
    for f in SOURCES:
        hits = banned.findall(f.read_text())
        assert not hits, (f.name, hits)


def test_the_whole_app_runs_with_every_filesystem_write_forbidden():
    """Fresh process; open-for-write, os.open(write), mkdir/remove/rename, tempfile, pathlib writes and sqlite3 all raise. Then use the app."""
    code = r'''
import builtins, io, os, pathlib, sys, tempfile
def deny(*a, **k): raise RuntimeError("filesystem write attempted")
_open = builtins.open
def guarded_open(file, mode="r", *a, **k):
    if any(c in str(mode) for c in "wax+"): raise RuntimeError("write-open of %r" % (file,))
    return _open(file, mode, *a, **k)
builtins.open = guarded_open; io.open = guarded_open
_osopen = os.open
def guarded_osopen(path, flags, *a, **k):
    if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC): raise RuntimeError("os.open for write: %r" % (path,))
    return _osopen(path, flags, *a, **k)
os.open = guarded_osopen
for n in ("mkdir", "makedirs", "remove", "unlink", "rename", "replace", "rmdir"): setattr(os, n, deny)
for n in ("mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile", "TemporaryDirectory"): setattr(tempfile, n, deny)
for n in ("write_text", "write_bytes", "mkdir", "touch", "unlink"): setattr(pathlib.Path, n, deny)
sys.modules["sqlite3"] = None

from fastapi.testclient import TestClient
from index import app
c = TestClient(app)
assert c.get("/").status_code == 200 and "Competitor Blog Spy" in c.get("/").text
assert c.get("/api/health").json()["status"] == "ok"
assert c.get("/api/dashboard").json()["competitors"]["total"] == 4
assert len(c.get("/api/competitors").json()) == 4 and c.get("/api/articles").json()["total"] > 10
r = c.post("/api/competitors", json={"name": "Z", "website_url": "https://z-example.test/"}); assert r.status_code == 201
sample = [x for x in c.get("/api/competitors").json() if x["kind"] == "sample" and x["enabled"]][0]
assert c.post("/api/competitors/%d/check" % sample["id"]).status_code == 200
assert c.post("/api/check-all").status_code == 200
assert c.put("/api/competitors/%d" % r.json()["id"], json={"name": "Z2", "website_url": "https://z-example.test/", "enabled": False}).status_code == 200
assert c.delete("/api/competitors/%d" % r.json()["id"]).status_code == 200
assert c.post("/api/demo/reset").status_code == 200 and c.get("/docs").status_code == 200
print("NO-WRITES-OK")
'''
    out = run_py(code)
    assert out.returncode == 0 and "NO-WRITES-OK" in out.stdout, (out.stdout + out.stderr)[-900:]


def test_guard_self_check_the_forbidden_write_really_raises():
    """Make sure the previous test is meaningful: the same guard does stop a write."""
    code = "import builtins\n_o=builtins.open\ndef g(f,m='r',*a,**k):\n    if 'w' in m: raise RuntimeError('blocked')\n    return _o(f,m,*a,**k)\nbuiltins.open=g\ntry:\n    open('x.txt','w')\nexcept RuntimeError:\n    print('RAISED')"
    assert "RAISED" in run_py(code).stdout


def test_no_secrets_and_env_example_requires_nothing():
    pattern = re.compile(r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE|(?i:password|secret|token|api_?key)\s*=\s*[\"'][^\"']{6,}")
    for f in [*SOURCES, ROOT / ".env.example", ROOT / "vercel.json", ROOT / "README.md"]:
        assert not pattern.search(f.read_text()), f.name
    env = (ROOT / ".env.example").read_text()
    assert "NO environment variable is required" in env
    for line in env.splitlines():
        if line.strip() and not line.startswith("#"):
            assert re.fullmatch(r"[A-Z_]+=[A-Za-z0-9_.:/-]*", line), line
    ignore = (ROOT / ".gitignore").read_text().split()
    assert ".env" in ignore and ".venv/" in ignore and "!.env.example" in ignore


def test_readme_has_the_required_submission_sections():
    text = (ROOT / "README.md").read_text()
    for heading in ("Tech stack", "Features", "Run locally", "Run the tests", "Deploy to Vercel", "Environment variables", "Demo", "How data is kept", "API", "Limitations"):
        assert re.search(r"^#{1,3} .*%s" % re.escape(heading), text, re.M | re.I), heading
