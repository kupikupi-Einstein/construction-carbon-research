"""Standalone FastAPI entrypoint for construction carbon research."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apps.api.carbon import router as carbon_router

app = FastAPI(title="Construction Carbon Research API", version="0.1.0")
app.include_router(carbon_router)

web_dist = Path(__file__).resolve().parents[1] / "carbon_research_web" / "dist"
if web_dist.exists():
    app.mount("/carbon", StaticFiles(directory=web_dist, html=True), name="carbon")
