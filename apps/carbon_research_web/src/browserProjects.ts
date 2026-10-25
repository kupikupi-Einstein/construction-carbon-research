import type { ProjectInput, ProjectRevision } from "./types";

export const browserProjectsKey = "carbon-research-browser-projects-v1";

type StoragePort = Pick<Storage, "getItem" | "setItem">;
type PrepareRevision = (project: ProjectInput, projectId: string, revisionNumber: number) => Promise<ProjectRevision>;

export function createBrowserProjectStore(storage: StoragePort, prepare: PrepareRevision) {
  function read(): ProjectRevision[] {
    try {
      const value: unknown = JSON.parse(storage.getItem(browserProjectsKey) || "[]");
      return Array.isArray(value) ? value.filter((item): item is ProjectRevision =>
        item !== null && typeof item === "object" && typeof item.project_id === "string"
        && Number.isInteger(item.revision_number) && item.project !== null) : [];
    } catch { return []; }
  }

  function write(revisions: ProjectRevision[]) {
    storage.setItem(browserProjectsKey, JSON.stringify(revisions));
  }

  function history(projectId: string): ProjectRevision[] {
    return read().filter((revision) => revision.project_id === projectId)
      .sort((a, b) => b.revision_number - a.revision_number);
  }

  return {
    list: async () => {
      const latest = new Map<string, ProjectRevision>();
      for (const revision of read()) {
        if ((latest.get(revision.project_id)?.revision_number ?? 0) < revision.revision_number) {
          latest.set(revision.project_id, revision);
        }
      }
      return [...latest.values()].sort((a, b) => b.created_at.localeCompare(a.created_at));
    },
    get: async (projectId: string) => {
      const revision = history(projectId)[0];
      if (!revision) throw new Error("project not found in this browser");
      return revision;
    },
    revisions: async (projectId: string) => {
      const revisions = history(projectId);
      if (!revisions.length) throw new Error("project not found in this browser");
      return revisions;
    },
    create: async (project: ProjectInput) => {
      const revision = await prepare(project, crypto.randomUUID(), 1);
      write([...read(), revision]);
      return revision;
    },
    revise: async (projectId: string, expected: number, project: ProjectInput) => {
      const current = history(projectId)[0];
      if (!current) throw new Error("project not found in this browser");
      if (current.revision_number !== expected) throw new Error("revision conflict");
      const revision = await prepare(project, projectId, expected + 1);
      write([...read(), revision]);
      return revision;
    },
  };
}
