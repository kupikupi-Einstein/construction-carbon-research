"""Canonical unit system shared by every civil_* package.

Every package converts input quantities to these canonical SI-based units before computing, and
only converts back to a display unit at the
presentation layer. Nothing downstream of civil_core should carry an un-dimensioned float across a
package boundary — that is how a stray "is this meters or millimeters?" bug becomes a silent 1000x
error in a real design check.

Built entirely on Pint's default unit registry (kip, ksi, psi, kgf, degree, and compound
expressions like "kilogram_force / centimeter ** 2" all parse without any custom unit definitions
here — verified against pint 0.25).
"""

from __future__ import annotations

import pint

ureg: pint.UnitRegistry[float] = pint.UnitRegistry()

# quantity kind -> canonical (internal, SI-based) unit. Add a kind here before using it anywhere
# else in the platform; civil_codes/civil_analysis must never invent their own canonical unit for
# a kind that already exists.
CANONICAL_UNITS: dict[str, str] = {
    "dimensionless": "dimensionless",
    "length": "meter",
    "area": "meter ** 2",
    "volume": "meter ** 3",
    "moment_of_inertia": "meter ** 4",
    "warping_constant": "meter ** 6",
    "section_modulus": "meter ** 3",
    "mass": "kilogram",
    "ghg_emission": "kilogram",
    "mass_per_length": "kilogram / meter",
    "energy": "joule",
    "transport_work": "kilogram * meter",
    "density": "kilogram / meter ** 3",
    "force": "newton",
    "distributed_force": "newton / meter",
    "translational_stiffness": "newton / meter",
    "stress": "pascal",
    "moment": "newton * meter",
    "strain": "dimensionless",
    "curvature": "1 / meter",
    "angle": "radian",
    "temperature": "kelvin",
    "time": "second",
}


class UnknownQuantityKindError(ValueError):
    """Raised when a quantity kind is not registered in CANONICAL_UNITS.

    Subclasses ValueError (not KeyError) so that pydantic consistently wraps it into a
    ValidationError when raised from inside Quantity's model_validator, the same way
    DimensionalMismatchError is — callers should not have to handle two different exception
    families depending on which specific input problem occurred.
    """


class DimensionalMismatchError(ValueError):
    """Raised when a unit string is not dimensionally compatible with a kind's canonical unit."""


def canonical_unit(kind: str) -> str:
    try:
        return CANONICAL_UNITS[kind]
    except KeyError as exc:
        raise UnknownQuantityKindError(
            f"unknown quantity kind {kind!r}; register it in civil_core.units.CANONICAL_UNITS first"
        ) from exc


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert `value` from `from_unit` to `to_unit`. Raises DimensionalMismatchError if the two
    units do not share dimensionality (e.g. converting a length to a force)."""
    try:
        quantity = ureg.Quantity(value, from_unit)
        return float(quantity.to(to_unit).magnitude)
    except pint.errors.DimensionalityError as exc:
        raise DimensionalMismatchError(
            f"cannot convert {from_unit!r} to {to_unit!r}: {exc}"
        ) from exc
    except (pint.errors.UndefinedUnitError, pint.errors.DefinitionSyntaxError) as exc:
        raise DimensionalMismatchError(
            f"invalid unit string {from_unit!r} or {to_unit!r}: {exc}"
        ) from exc


def to_canonical(value: float, unit: str, kind: str) -> float:
    """Convert a user-entered `value`/`unit` into `kind`'s canonical internal value."""
    return convert(value, unit, canonical_unit(kind))


def is_dimensionally_compatible(unit: str, kind: str) -> bool:
    """True if `unit` shares dimensionality with `kind`'s canonical unit (e.g. mm/m, kip/N)."""
    try:
        convert(1.0, unit, canonical_unit(kind))
        return True
    except DimensionalMismatchError:
        return False
