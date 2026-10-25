# Carbon research web app — MVP task contract

Status: implementation draft, 2026-10-25. This document records the user-approved scope for the first delivery; it is not a carbon-credit certification.

## Scope

- New carbon workflow, API contracts, API router, project storage, reporting integration, and a dedicated web UI.
- Asset categories: road, bridge, building, architecture/interior fit-out.
- A1–A5 embodied carbon from user-supplied BOQ/activity data and cited emission factors; scenario comparison.
- T-VER screening and calculation support for the versioned building-energy and concrete-CCU methodologies. Results remain estimates until independent validation, verification, and registry issuance.
- Project creation, immutable revisions, reopening, and PDF/XLSX/DOCX export of one selected revision.
- Do not modify existing engineering apps or unrelated design-code calculations.

## Input/output contract

Each activity row has asset category, item, measured quantity with unit, factor numerator in kgCO2e, factor denominator with unit, factor source/version, A1–A5 stage, and optional evidence reference. The output has kgCO2e per row, stage, category, and project, a structured calculation trace, method/version and factor provenance, warnings, and a separate T-VER eligibility/estimate status.

## Acceptance and definition of done

- Create, list, reopen, revise, and compare projects without changing historical revisions.
- Worked examples for all four asset categories and boundary/unit/error cases.
- T-VER methodology-specific eligibility and calculation tests; no issued-credit claim without registry evidence.
- PDF/XLSX/DOCX exports agree with the selected revision and include a manifest and sources.
- Thai and English UI/report keys; pastel research UI usable with keyboard and on narrow screens.
- Relevant Ruff, mypy, pytest, UI checks, and independent human engineering/LCA review before merge or external certification.
- Security, backup/rollback, documentation, and release checks follow the repository release gate and AGENTS.md.
