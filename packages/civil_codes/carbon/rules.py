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
