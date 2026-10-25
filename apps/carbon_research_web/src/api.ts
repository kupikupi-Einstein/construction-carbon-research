import type { ActivityRow, CarbonResult, ProjectInput, ProjectRevision } from "./types";
import { createBrowserProjectStore } from "./browserProjects";

const root = "/api/v1/carbon";
export const browserProjectMode = import.meta.env.VITE_PUBLIC_BROWSER_PROJECTS === "1";

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

const prepareRevision = (project: ProjectInput, projectId: string, revisionNumber: number) =>
  request<ProjectRevision>("/prepare-revision", json({ project_id: projectId, revision_number: revisionNumber, project }));
const browserStore = browserProjectMode ? createBrowserProjectStore(localStorage, prepareRevision) : null;

async function downloadExport(revision: ProjectRevision, format: string, locale: string) {
  const response = browserProjectMode
    ? await fetch(`${root}/export-snapshot/${format}?locale=${encodeURIComponent(locale)}`, json({
      project_id: revision.project_id,
      revision_id: revision.revision_id,
      revision_number: revision.revision_number,
      created_at: revision.created_at,
      input_snapshot_hash: revision.input_snapshot_hash,
      project: revision.project,
    }))
    : await fetch(`${root}/projects/${revision.project_id}/revisions/${revision.revision_number}/export/${format}?locale=${encodeURIComponent(locale)}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `carbon-${revision.project_id}-r${revision.revision_number}.${format}`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export const api = {
  list: () => browserStore ? browserStore.list() : request<ProjectRevision[]>("/projects"),
  get: (id: string) => browserStore ? browserStore.get(id) : request<ProjectRevision>(`/projects/${id}`),
  revisions: (id: string) => browserStore ? browserStore.revisions(id) : request<ProjectRevision[]>(`/projects/${id}/revisions`),
  calculate: (project: ProjectInput) => request<CarbonResult>("/calculate", json(project)),
  kiakkaiExample: () => request<ProjectInput>("/examples/kiakkai"),
  create: (project: ProjectInput) => browserStore ? browserStore.create(project) : request<ProjectRevision>("/projects", json(project)),
  revise: (id: string, expected: number, project: ProjectInput) =>
    browserStore ? browserStore.revise(id, expected, project)
      : request<ProjectRevision>(`/projects/${id}/revisions`, json({ expected_revision_number: expected, project })),
  importCsv: async (file: File) => {
    const form = new FormData();
    form.set("file", file);
    return request<ActivityRow[]>("/import-csv", { method: "POST", body: form });
  },
  downloadExport,
};
