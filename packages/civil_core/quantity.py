"""Quantity: a dimensioned value that remembers what the user actually typed.

Every value that crosses a
package boundary must carry its dimension, keep the original input value/unit for audit and
report display, and expose a canonical (internal, SI-based) value that calculations use. Changing
a project's unit profile must only change *display*, never this canonical value and never a
pass/fail result — that invariant is what canonical_value being derived (not stored/cached) from
input_value/input_unit guarantees: there is only one source of truth per Quantity instance.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from civil_core.units import canonical_unit as _canonical_unit_for_kind
from civil_core.units import convert as _convert
from civil_core.units import to_canonical as _to_canonical


class Quantity(BaseModel):
    """A single dimensioned value. Immutable: build a new Quantity rather than mutating one."""

    model_config = ConfigDict(frozen=True)

    kind: str
    input_value: float
    input_unit: str

    @model_validator(mode="after")
    def _validate_dimension(self) -> Quantity:
        # Raises UnknownQuantityKindError / DimensionalMismatchError eagerly, at construction time,
        # rather than deferring the failure to whichever calculation first reads canonical_value.
        _to_canonical(self.input_value, self.input_unit, self.kind)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def canonical_unit(self) -> str:
        return _canonical_unit_for_kind(self.kind)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def canonical_value(self) -> float:
        return _to_canonical(self.input_value, self.input_unit, self.kind)

    def to(self, unit: str) -> float:
        """Convert this quantity's canonical value to any dimensionally compatible display unit."""
        return _convert(self.canonical_value, self.canonical_unit, unit)

    @classmethod
    def from_canonical(cls, kind: str, canonical_value: float) -> Quantity:
        """Build a Quantity directly from an already-canonical value, e.g. a calculation result
        that has no single "user-entered" unit of its own."""
        return cls(
            kind=kind, input_value=canonical_value, input_unit=_canonical_unit_for_kind(kind)
        )
