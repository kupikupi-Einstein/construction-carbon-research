"""Versioned contracts for research-stage construction carbon projects."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from civil_core.quantity import Quantity
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CarbonModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssetType(StrEnum):
    ROAD = "road"
    BRIDGE = "bridge"
    BUILDING = "building"
    INTERIOR = "interior"


class LifeCycleStage(StrEnum):
    A1_A3 = "A1-A3"
    A4 = "A4"
    A5 = "A5"


class EmissionFactor(CarbonModel):
    numerator: Quantity
    denominator: Quantity
    source_name: str = Field(min_length=1, max_length=250)
    source_version: str = Field(min_length=1, max_length=100)
    source_url: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_factor(self) -> EmissionFactor:
        if self.numerator.kind != "ghg_emission":
            raise ValueError("factor numerator must have kind ghg_emission")
        if self.numerator.canonical_value < 0 or self.denominator.canonical_value <= 0:
            raise ValueError("factor numerator must be nonnegative and denominator positive")
        return self


class ActivityRow(CarbonModel):
    row_id: str = Field(min_length=1, max_length=100)
    item_name: str = Field(min_length=1, max_length=250)
    category: str = Field(min_length=1, max_length=100)
    stage: LifeCycleStage
    quantity: Quantity
    factor: EmissionFactor | None = None
    evidence_ref: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_row(self) -> ActivityRow:
        if self.quantity.canonical_value < 0:
            raise ValueError("activity quantity must be nonnegative")
        if self.factor is None:
            if not self.evidence_ref:
                raise ValueError("pending activity requires evidence_ref explaining missing data")
            return self
        if self.quantity.kind != self.factor.denominator.kind:
            raise ValueError("activity quantity and factor denominator must have the same kind")
        return self


class TverInput(CarbonModel):
    methodology_id: Literal["T-VER-S-METH-06-15", "T-VER-P-METH-14-02"]
    methodology_version: Literal["01"] = "01"
    monitoring_year: int = Field(ge=2000, le=2200)
    baseline_emission: Quantity
    project_emission: Quantity
    leakage_emission: Quantity
    component_evidence_ref: str = Field(default="", max_length=1000)
    additionality_evidence_ref: str | None = Field(default=None, max_length=1000)
    credit_rights_evidence_ref: str | None = Field(default=None, max_length=1000)
    monitoring_plan_ref: str | None = Field(default=None, max_length=1000)
    building_type: str | None = None
    building_measures: tuple[str, ...] = ()
    new_equipment: bool | None = None
    ready_mix: bool | None = None
    captured_co2_used: bool | None = None
    equivalent_strength: bool | None = None
    commercial_use: bool | None = None
    concrete_recycled: bool | None = None
    product_traceable: bool | None = None

    @model_validator(mode="after")
    def validate_emissions(self) -> TverInput:
        for value in (self.baseline_emission, self.project_emission, self.leakage_emission):
            if value.kind != "ghg_emission" or value.canonical_value < 0:
                raise ValueError("T-VER components must be nonnegative ghg_emission quantities")
        return self


class CarbonProjectInput(CarbonModel):
    schema_version: Literal["civil.carbon.project.v1"] = "civil.carbon.project.v1"
    name: str = Field(min_length=1, max_length=250)
    asset_type: AssetType
    description: str = Field(default="", max_length=2000)
    rows: tuple[ActivityRow, ...] = Field(min_length=1, max_length=10000)
    tver: TverInput | None = None

    @model_validator(mode="after")
    def unique_row_ids(self) -> CarbonProjectInput:
        ids = [row.row_id for row in self.rows]
        if len(ids) != len(set(ids)):
            raise ValueError("row_id must be unique within a project revision")
        return self


class CarbonTraceStep(CarbonModel):
    row_id: str
    rule_id: str
    standard_id: str
    edition: str
    clause: str
    source_url: str
    formula: str
    operands: dict[str, Quantity]
    result: Quantity


class CarbonRowResult(CarbonModel):
    row_id: str
    emission: Quantity
    trace: CarbonTraceStep


class TverScreeningResult(CarbonModel):
    methodology_id: str
    methodology_version: str
    screening_status: Literal["potentially_applicable", "insufficient_data", "not_applicable"]
    estimated_reduction: Quantity
    trace: CarbonTraceStep
    findings: tuple[str, ...]
    credit_status: Literal["estimate_not_issued"] = "estimate_not_issued"


class CreditReadiness(CarbonModel):
    row_id: str
    material_key: str
    methodology_id: str | None
    methodology_version: str | None
    source_url: str
    status: Literal["separate_activity_required", "no_direct_material_method"]
    reason_code: str
    footprint_status: Literal["calculated", "pending_factor"]


class CarbonResult(CarbonModel):
    schema_version: Literal["civil.carbon.result.v1"] = "civil.carbon.result.v1"
    total_emission: Quantity
    by_stage: dict[LifeCycleStage, Quantity]
    by_category: dict[str, Quantity]
    rows: tuple[CarbonRowResult, ...]
    pending_row_ids: tuple[str, ...] = ()
    credit_readiness: tuple[CreditReadiness, ...] = ()
    tver: TverScreeningResult | None = None
    warnings: tuple[str, ...] = ()


class ProjectRevision(CarbonModel):
    project_id: UUID
    revision_id: UUID
    revision_number: int = Field(ge=1)
    created_at: datetime
    input_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    project: CarbonProjectInput
    result: CarbonResult
