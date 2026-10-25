"""Aggregate construction carbon and screen selected T-VER methods."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from civil_api_contracts.carbon import (
    AssetType,
    CarbonProjectInput,
    CarbonResult,
    CarbonRowResult,
    CarbonTraceStep,
    LifeCycleStage,
    TverInput,
    TverScreeningResult,
)
from civil_codes.carbon import (
    CARBON_LCA_RULE,
    TVER_METHODS,
    calculate_activity_emission,
    calculate_tver_reduction,
)
from civil_core.quantity import Quantity

_ELIGIBLE_BUILDINGS = frozenset(
    {
        "office",
        "hotel",
        "hospital",
        "shopping_center",
        "theatre",
        "service",
        "assembly",
        "condominium",
        "education",
    }
)


def _emission(value: float) -> Quantity:
    return Quantity.from_canonical("ghg_emission", value)


def _screen_tver(data: TverInput, asset_type: AssetType) -> TverScreeningResult:
    rule = TVER_METHODS[data.methodology_id]
    reduction = calculate_tver_reduction(
        data.baseline_emission, data.project_emission, data.leakage_emission
    )
    findings: list[str] = []
    inapplicable = False
    if reduction.canonical_value <= 0:
        findings.append("non_positive_reduction")
        inapplicable = True
    if data.methodology_id == "T-VER-S-METH-06-15":
        if asset_type is not AssetType.BUILDING:
            findings.append("asset_is_not_building")
            inapplicable = True
        if data.building_type not in _ELIGIBLE_BUILDINGS:
            findings.append("building_type_not_eligible_or_missing")
            inapplicable = True
        if len(set(data.building_measures)) < 2:
            findings.append("two_distinct_measures_required")
            inapplicable = True
        if data.new_equipment is not True:
            findings.append("new_equipment_required")
            inapplicable = True
    else:
        if data.ready_mix is not True:
            findings.append("ready_mix_required")
            inapplicable = True
        for field, code in (
            (data.captured_co2_used, "co2_capture_and_use_required"),
            (data.equivalent_strength, "equivalent_strength_required"),
            (data.commercial_use, "commercial_use_required"),
            (data.product_traceable, "product_traceability_required"),
        ):
            if field is not True:
                findings.append(code)
                inapplicable = True
        if data.concrete_recycled is not False:
            findings.append("recycled_concrete_not_in_scope")
            inapplicable = True
    missing = (
        ("component_evidence_missing", data.component_evidence_ref),
        ("additionality_evidence_missing", data.additionality_evidence_ref),
        ("credit_rights_evidence_missing", data.credit_rights_evidence_ref),
        ("monitoring_plan_missing", data.monitoring_plan_ref),
    )
    findings.extend(code for code, ref in missing if not ref)
    findings.append("component_equations_and_evidence_require_independent_review")
    status: Literal["not_applicable", "insufficient_data", "potentially_applicable"] = (
        "not_applicable"
        if inapplicable
        else "insufficient_data"
        if any(not ref for _, ref in missing)
        else "potentially_applicable"
    )
    return TverScreeningResult(
        methodology_id=data.methodology_id,
        methodology_version=data.methodology_version,
        screening_status=status,
        estimated_reduction=reduction,
        trace=CarbonTraceStep(
            row_id="tver-aggregate",
            rule_id=rule.rule_id,
            standard_id=rule.standard_id,
            edition=rule.edition,
            clause=rule.clause,
            source_url=rule.source_url,
            formula=rule.formula,
            operands={
                "BE_y": data.baseline_emission,
                "PE_y": data.project_emission,
                "LE_y": data.leakage_emission,
            },
            result=reduction,
        ),
        findings=tuple(findings),
    )


def calculate_project(project: CarbonProjectInput) -> CarbonResult:
    """Calculate one immutable revision without external state or default factors."""
    row_results: list[CarbonRowResult] = []
    stage_totals: defaultdict[LifeCycleStage, float] = defaultdict(float)
    category_totals: defaultdict[str, float] = defaultdict(float)
    for row in project.rows:
        value = calculate_activity_emission(
            row.quantity, row.factor.numerator, row.factor.denominator
        )
        stage_totals[row.stage] += value.canonical_value
        category_totals[row.category] += value.canonical_value
        row_results.append(
            CarbonRowResult(
                row_id=row.row_id,
                emission=value,
                trace=CarbonTraceStep(
                    row_id=row.row_id,
                    rule_id=CARBON_LCA_RULE.rule_id,
                    standard_id=CARBON_LCA_RULE.standard_id,
                    edition=CARBON_LCA_RULE.edition,
                    clause=CARBON_LCA_RULE.clause,
                    source_url=CARBON_LCA_RULE.source_url,
                    formula=CARBON_LCA_RULE.formula,
                    operands={
                        "activity_quantity": row.quantity,
                        "factor_denominator": row.factor.denominator,
                        "factor_numerator": row.factor.numerator,
                    },
                    result=value,
                ),
            )
        )
    tver = _screen_tver(project.tver, project.asset_type) if project.tver else None
    warnings = ("research_estimate_not_verified",)
    return CarbonResult(
        total_emission=_emission(sum(stage_totals.values())),
        by_stage={stage: _emission(stage_totals[stage]) for stage in LifeCycleStage},
        by_category={key: _emission(value) for key, value in category_totals.items()},
        rows=tuple(row_results),
        tver=tver,
        warnings=warnings,
    )
