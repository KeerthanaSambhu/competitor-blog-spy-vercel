"""FastAPI application. No lifespan hooks, no startup I/O: importing this module only builds the app object."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response

from . import __version__
from .api import router
from .store import StoreError
from .ui import FAVICON_SVG, INDEX_HTML

app = FastAPI(title="Competitor Blog Spy", version=__version__, docs_url="/docs", redoc_url=None,
              description="Monitor competitor blogs and measure how fast new articles are detected. Data is held in server memory (demo mode).")
app.include_router(router)


@app.exception_handler(StoreError)
async def store_error(_: Request, exc: StoreError):
    return JSONResponse({"detail": exc.message, "field": exc.field}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    errors = []
    for e in exc.errors():
        field = str(e["loc"][-1]) if e.get("loc") else None
        msg = str(e.get("msg", "Invalid value")).removeprefix("Value error, ")
        errors.append({"field": field, "message": msg})
    first = errors[0] if errors else {"message": "Invalid request"}
    return JSONResponse({"detail": first["message"], "field": first.get("field"), "errors": errors}, status_code=422)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return HTMLResponse(INDEX_HTML, headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(FAVICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
