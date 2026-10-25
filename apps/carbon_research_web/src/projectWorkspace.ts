import type { ProjectInput, ProjectRevision } from "./types";

export const projectContextKey = "carbon-research-project-context-v1";

export type ProjectContext = {
  projectId: string | null;
  latestRevision: number | null;
  selectedRevision: number | null;
};

export const readProjectContext = (storage: { getItem: (key: string) => string | null }): ProjectContext => {
  try {
    const value = JSON.parse(storage.getItem(projectContextKey) || "{}") as Partial<ProjectContext>;
    return {
      projectId: typeof value.projectId === "string" && value.projectId ? value.projectId : null,
      latestRevision: typeof value.latestRevision === "number" && value.latestRevision > 0 ? value.latestRevision : null,
      selectedRevision: typeof value.selectedRevision === "number" && value.selectedRevision > 0 ? value.selectedRevision : null,
    };
  } catch {
    return { projectId: null, latestRevision: null, selectedRevision: null };
  }
};

export const findMatchingProject = (draft: ProjectInput, projects: ProjectRevision[]): ProjectRevision | null => {
  if (!draft.name.trim() || !draft.rows.length) return null;
  const draftRowIds = new Set(draft.rows.map((row) => row.row_id));
  const matches = projects.filter((saved) => saved.project.name === draft.name
    && saved.project.asset_type === draft.asset_type
    && saved.project.rows.length > 0
    && saved.project.rows.every((row) => draftRowIds.has(row.row_id)));
  return matches.length === 1 ? matches[0]! : null;
};

export const hasNamedCalculationInputs = (project: ProjectInput): boolean =>
  Boolean(project.name.trim() && project.rows.length && project.rows.every((row) => row.item_name.trim()));
