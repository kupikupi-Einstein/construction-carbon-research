import type { ActivityRow, CarbonResult, ProjectInput, ProjectRevision } from "./types";

const root = "/api/v1/carbon";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(root + path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

const json = (value: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(value),
});

export const api = {
  list: () => request<ProjectRevision[]>("/projects"),
  get: (id: string) => request<ProjectRevision>(`/projects/${id}`),
  revisions: (id: string) => request<ProjectRevision[]>(`/projects/${id}/revisions`),
  calculate: (project: ProjectInput) => request<CarbonResult>("/calculate", json(project)),
  kiakkaiExample: () => request<ProjectInput>("/examples/kiakkai"),
  create: (project: ProjectInput) => request<ProjectRevision>("/projects", json(project)),
  revise: (id: string, expected: number, project: ProjectInput) =>
    request<ProjectRevision>(`/projects/${id}/revisions`, json({ expected_revision_number: expected, project })),
  importCsv: async (file: File) => {
    const form = new FormData();
    form.set("file", file);
    return request<ActivityRow[]>("/import-csv", { method: "POST", body: form });
  },
  exportUrl: (id: string, revision: number, format: string, locale: string) =>
    `${root}/projects/${id}/revisions/${revision}/export/${format}?locale=${encodeURIComponent(locale)}`,
};
