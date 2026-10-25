import type { ActivityRow, Factor, ProjectInput } from "./types";

const factorIsComplete = (factor: Factor | null | undefined, row: ActivityRow): factor is Factor =>
  Boolean(factor?.source_name?.trim() && factor.source_version?.trim()
    && factor.numerator?.kind === "ghg_emission"
    && Number.isFinite(factor.numerator.input_value) && factor.numerator.input_value >= 0
    && factor.denominator?.kind === row.quantity.kind
    && Number.isFinite(factor.denominator.input_value) && factor.denominator.input_value > 0
    && factor.numerator.input_unit?.trim() && factor.denominator.input_unit?.trim());

export const needsFactor = (row: ActivityRow): boolean => row.factor !== null && !factorIsComplete(row.factor, row);

export const pauseFactor = (row: ActivityRow): ActivityRow => ({
  ...row,
  inactive_factor: factorIsComplete(row.factor, row) ? row.factor : null,
  factor: null,
});

export const resumeFactor = (row: ActivityRow): ActivityRow => ({
  ...row,
  factor: factorIsComplete(row.inactive_factor, row) ? row.inactive_factor : {
    numerator: { kind: "ghg_emission", input_value: 0, input_unit: "kilogram" },
    denominator: { kind: row.quantity.kind, input_value: 1, input_unit: row.quantity.input_unit },
    source_name: "",
    source_version: "",
  },
  inactive_factor: null,
});

export const normalizeProject = (project: ProjectInput): ProjectInput => ({
  ...project,
  rows: project.rows.map((row) => ({
    ...row,
    inactive_factor: row.factor === null && factorIsComplete(row.inactive_factor, row)
      ? row.inactive_factor : null,
  })),
});

export const calculationPreview = (project: ProjectInput, missingEvidence: string): ProjectInput => ({
  ...project,
  rows: normalizeProject(project).rows.map((row) => {
    if (needsFactor(row)) {
      return { ...row, factor: null, inactive_factor: null, evidence_ref: row.evidence_ref?.trim() || missingEvidence };
    }
    if (row.factor === null && !row.evidence_ref?.trim()) return { ...row, evidence_ref: missingEvidence };
    return row;
  }),
});
