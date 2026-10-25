"""Standalone FastAPI entrypoint for construction carbon research."""

import os
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from apps.api.carbon import router as carbon_router

app = FastAPI(title="Construction Carbon Research API", version="0.1.0")
app.include_router(carbon_router)
_request_times: dict[str, deque[float]] = {}


@app.middleware("http")
async def guard_public_api(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Bound anonymous public API traffic; project records remain browser-local."""
    if os.environ.get("CIVIL_CARBON_PUBLIC_MODE") != "1" or not request.url.path.startswith(
        "/api/v1/carbon/"
    ):
        return await call_next(request)
    if request.method in {"POST", "PUT", "PATCH"}:
        length = request.headers.get("content-length")
        if length is None:
            return JSONResponse({"detail": "Content-Length required"}, status_code=411)
        if not length.isdecimal() or int(length) > 5_000_000:
            return JSONResponse({"detail": "request exceeds 5 MB"}, status_code=413)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if len(_request_times) > 5000:
            _request_times.clear()
        hits = _request_times.setdefault(client, deque())
        while hits and hits[0] < now - 60:
            hits.popleft()
        if len(hits) >= 120:
            return JSONResponse({"detail": "too many requests"}, status_code=429)
        hits.append(now)
    return await call_next(request)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Simple liveness probe for the hosting platform."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def homepage() -> RedirectResponse:
    return RedirectResponse(url="/carbon/", status_code=307)

web_dist = Path(__file__).resolve().parents[1] / "carbon_research_web" / "dist"
if web_dist.exists():
    app.mount("/carbon", StaticFiles(directory=web_dist, html=True), name="carbon")
