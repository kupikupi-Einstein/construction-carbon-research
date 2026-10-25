"""Small, deterministic rules used by the carbon research workflow.

The T-VER reduction here is an arithmetic cross-check of *user supplied* BE/PE/LE
components. It does not implement the component equations of either methodology,
and must never be presented as an issued or independently verified credit.
"""

from __future__ import annotations

from dataclasses import dataclass

from civil_core.quantity import Quantity


@dataclass(frozen=True)
class RuleReference:
    rule_id: str
    standard_id: str
    edition: str
    clause: str
    source_url: str
    formula: str


CARBON_LCA_RULE = RuleReference(
    rule_id="carbon.activity.factor.v1",
    standard_id="ISO 14040",
    edition="2006",
    clause="Life cycle inventory",
    source_url="https://www.iso.org/standard/37456.html",
    formula="emissions = activity_quantity / factor_denominator × factor_numerator",
)

TVER_METHODS: dict[str, RuleReference] = {
    "T-VER-S-METH-06-15": RuleReference(
        rule_id="tver.building_energy.reduction.v1",
        standard_id="T-VER-S-METH-06-15",
        edition="01",
        clause="7",
        source_url="https://tver.tgo.or.th/database/public/methodology/46?category_id=6&lang=en",
        formula="ER_y = BE_y - PE_y - LE_y",
    ),
    "T-VER-P-METH-14-02": RuleReference(
        rule_id="tver.concrete_ccu.reduction.v1",
        standard_id="T-VER-P-METH-14-02",
        edition="01",
        clause="8, equation 31",
        source_url="https://tver.tgo.or.th/database/public/methodology/99?lang=en",
        formula="ER_y = BE_y - PE_y - LE_y",
    ),
}


@dataclass(frozen=True)
class CreditPathwayReference:
    material_key: str
    methodology_id: str | None
    methodology_version: str | None
    source_url: str
    reason_code: str


CREDIT_PATHWAYS: dict[str, CreditPathwayReference] = {
    "concrete": CreditPathwayReference(
        "concrete", "T-VER-P-METH-14-02", "01",
        "https://tver.tgo.or.th/database/public/methodology/99?lang=en",
        "concrete_ccu_activity_required",
    ),
    "plastic": CreditPathwayReference(
        "plastic", "T-VER-S-METH-09-06", "02",
        "https://tver.tgo.or.th/database/public/methodologies/1?category_id=9&lang=en",
        "plastic_recycling_activity_required",
    ),
    "steel": CreditPathwayReference(
        "steel", None, None,
        "https://tver.tgo.or.th/database/public/methodologies/1?lang=en",
        "steel_purchase_has_no_direct_method",
    ),
    "asphalt": CreditPathwayReference(
        "asphalt", None, None,
        "https://tver.tgo.or.th/database/public/methodologies/1?lang=en",
        "material_purchase_has_no_direct_method",
    ),
    "other": CreditPathwayReference(
        "other", None, None,
        "https://tver.tgo.or.th/database/public/methodologies/1?lang=en",
        "material_purchase_has_no_direct_method",
    ),
}


def credit_material_key(category: str) -> str:
    """Map BOQ categories to research pathways, without inferring project eligibility."""
    normalized = category.casefold()
    if "hdpe" in normalized or "plastic" in normalized:
        return "plastic"
    if "concrete" in normalized:
        return "concrete"
    if "steel" in normalized:
        return "steel"
    if "asphalt" in normalized:
        return "asphalt"
    return "other"


def calculate_activity_emission(
    activity_quantity: Quantity,
    factor_numerator: Quantity,
    factor_denominator: Quantity,
) -> Quantity:
    """Scale a cited factor to activity data, retaining dimensions at the boundary."""
    if activity_quantity.kind != factor_denominator.kind:
        raise ValueError("activity and emission-factor denominator must have the same kind")
    if factor_numerator.kind != "ghg_emission":
        raise ValueError("emission-factor numerator must be ghg_emission")
    if activity_quantity.canonical_value < 0 or factor_numerator.canonical_value < 0:
        raise ValueError("activity and emission factor must be nonnegative")
    if factor_denominator.canonical_value <= 0:
        raise ValueError("emission-factor denominator must be positive")
    result = (
        activity_quantity.canonical_value
        / factor_denominator.canonical_value
        * factor_numerator.canonical_value
    )
    return Quantity.from_canonical("ghg_emission", result)


def calculate_tver_reduction(baseline: Quantity, project: Quantity, leakage: Quantity) -> Quantity:
    """Aggregate user-supplied methodology components; negative values remain visible."""
    values = (baseline, project, leakage)
    if any(value.kind != "ghg_emission" for value in values):
        raise ValueError("BE, PE and LE must be ghg_emission quantities")
    if any(value.canonical_value < 0 for value in values):
        raise ValueError("BE, PE and LE must be nonnegative")
    return Quantity.from_canonical(
        "ghg_emission",
        baseline.canonical_value - project.canonical_value - leakage.canonical_value,
    )
