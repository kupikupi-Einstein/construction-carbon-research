"""Research-stage construction carbon project API."""

from __future__ import annotations

import csv
import json
import os
from io import StringIO
from pathlib import Path
from typing import Annotated
from uuid import UUID

from civil_api_contracts.carbon import (
    ActivityRow,
    CarbonProjectInput,
    CarbonResult,
    ProjectRevision,
)
from civil_reporting.carbon import render_carbon_docx, render_carbon_pdf, render_carbon_xlsx
from civil_workflows.carbon import calculate_project
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

from apps.api.carbon_store import CarbonStore, ProjectNotFoundError, RevisionConflictError

router = APIRouter(prefix="/api/v1/carbon", tags=["carbon research"])


@router.get("/examples/kiakkai", response_model=CarbonProjectInput)
def kiakkai_worked_example() -> CarbonProjectInput:
    """A disclosed partial takeoff from the user-provided BOQ, not a project total."""
    path = Path(__file__).resolve().parent / "data" / "kiakkai_example.json"
    return CarbonProjectInput.model_validate(json.loads(path.read_text(encoding="utf-8")))


def get_store() -> CarbonStore:
    configured = os.environ.get("CIVIL_CARBON_DB_PATH")
    path = (
        Path(configured)
        if configured
        else Path(__file__).resolve().parents[2] / "instance" / "carbon_research.sqlite3"
    )
    return CarbonStore(path)


StoreDependency = Annotated[CarbonStore, Depends(get_store)]


class ReviseRequest(BaseModel):
    expected_revision_number: int = Field(ge=1)
    project: CarbonProjectInput


@router.post("/import-csv", response_model=list[ActivityRow])
async def import_boq_csv(file: Annotated[UploadFile, File()]) -> list[ActivityRow]:
    content = await file.read(2_000_001)
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail="CSV exceeds 2 MB")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8") from error
    reader = csv.DictReader(StringIO(decoded))
    required = {
        "row_id",
        "item_name",
        "category",
        "stage",
        "quantity_kind",
        "quantity_value",
        "quantity_unit",
        "factor_numerator_value",
        "factor_numerator_unit",
        "factor_denominator_value",
        "factor_denominator_unit",
        "source_name",
        "source_version",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise HTTPException(status_code=422, detail="CSV columns do not match the BOQ template")
    rows: list[ActivityRow] = []
    try:
        for record in reader:
            if len(rows) >= 10_000:
                raise HTTPException(status_code=413, detail="CSV exceeds 10000 rows")
            kind = record["quantity_kind"]
            factor_fields = (
                "factor_numerator_value", "factor_numerator_unit",
                "factor_denominator_value", "factor_denominator_unit",
                "source_name", "source_version",
            )
            supplied = [bool((record[field] or "").strip()) for field in factor_fields]
            if any(supplied) and not all(supplied):
                raise ValueError("emission factor columns must be all filled or all blank")
            factor = None
            if all(supplied):
                factor = {
                    "numerator": {
                        "kind": "ghg_emission",
                        "input_value": float(record["factor_numerator_value"]),
                        "input_unit": record["factor_numerator_unit"],
                    },
                    "denominator": {
                        "kind": kind,
                        "input_value": float(record["factor_denominator_value"]),
                        "input_unit": record["factor_denominator_unit"],
                    },
                    "source_name": record["source_name"],
                    "source_version": record["source_version"],
                    "source_url": record.get("source_url") or None,
                }
            rows.append(
                ActivityRow.model_validate(
                    {
                        "row_id": record["row_id"],
                        "item_name": record["item_name"],
                        "category": record["category"],
                        "stage": record["stage"],
                        "quantity": {
                            "kind": kind,
                            "input_value": float(record["quantity_value"]),
                            "input_unit": record["quantity_unit"],
                        },
                        "factor": factor,
                        "evidence_ref": record.get("evidence_ref") or None,
                    }
                )
            )
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(
            status_code=422, detail=f"invalid CSV row {len(rows) + 2}: {error}"
        ) from error
    return rows


@router.post("/calculate", response_model=CarbonResult)
def preview_calculation(project: CarbonProjectInput) -> CarbonResult:
    return calculate_project(project)


@router.post("/projects", response_model=ProjectRevision, status_code=201)
def create_project(project: CarbonProjectInput, store: StoreDependency) -> ProjectRevision:
    return store.create(project)


@router.get("/projects", response_model=list[ProjectRevision])
def list_projects(store: StoreDependency) -> list[ProjectRevision]:
    return store.list_latest()


@router.get("/projects/{project_id}", response_model=ProjectRevision)
def get_project(project_id: UUID, store: StoreDependency) -> ProjectRevision:
    try:
        return store.get(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="project not found") from error


@router.get("/projects/{project_id}/revisions", response_model=list[ProjectRevision])
def list_revisions(project_id: UUID, store: StoreDependency) -> list[ProjectRevision]:
    try:
        return store.list_revisions(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="project not found") from error


@router.get("/projects/{project_id}/revisions/{revision_number}", response_model=ProjectRevision)
def get_revision(project_id: UUID, revision_number: int, store: StoreDependency) -> ProjectRevision:
    try:
        return store.get(project_id, revision_number)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="revision not found") from error


@router.post("/projects/{project_id}/revisions", response_model=ProjectRevision, status_code=201)
def add_revision(
    project_id: UUID, request: ReviseRequest, store: StoreDependency
) -> ProjectRevision:
    try:
        return store.revise(project_id, request.project, request.expected_revision_number)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="project not found") from error
    except RevisionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/projects/{project_id}/revisions/{revision_number}/export/{file_format}")
def export_revision(
    project_id: UUID,
    revision_number: int,
    file_format: str,
    store: StoreDependency,
    locale: str = "th-TH",
) -> Response:
    if locale not in ("th-TH", "en-US"):
        raise HTTPException(status_code=422, detail="unsupported locale")
    renderers = {
        "pdf": (render_carbon_pdf, "application/pdf"),
        "docx": (
            render_carbon_docx,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        "xlsx": (
            render_carbon_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    if file_format not in renderers:
        raise HTTPException(status_code=404, detail="unsupported export format")
    try:
        revision = store.get(project_id, revision_number)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="revision not found") from error
    renderer, media_type = renderers[file_format]
    try:
        content = renderer(revision, locale)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    filename = f"carbon-{project_id}-r{revision_number}.{file_format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
