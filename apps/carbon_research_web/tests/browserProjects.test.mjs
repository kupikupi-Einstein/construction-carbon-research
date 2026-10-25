import test from "node:test";
import assert from "node:assert/strict";
import { createBrowserProjectStore } from "../src/browserProjects.ts";

function fixture() {
  const values = new Map();
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
  let counter = 0;
  const prepare = async (project, projectId, revisionNumber) => ({
    project_id: projectId,
    revision_id: `revision-${++counter}`,
    revision_number: revisionNumber,
    created_at: new Date(2026, 0, counter).toISOString(),
    input_snapshot_hash: "sha256:fixture",
    project,
    result: { total_emission: { input_value: project.rows.length } },
  });
  return { values, storage, prepare, store: createBrowserProjectStore(storage, prepare) };
}

test("browser project revisions persist and stay separate by project", async () => {
  const { storage, prepare, store } = fixture();
  const project = { name: "Bridge", rows: [{ row_id: "steel" }] };
  const first = await store.create(project);
  const another = await store.create({ name: "Road", rows: [] });
  const second = await store.revise(first.project_id, 1, { ...project, rows: [...project.rows, { row_id: "hdpe" }] });
  assert.equal(second.revision_number, 2);
  assert.equal((await store.list()).length, 2);
  assert.equal((await store.get(first.project_id)).revision_number, 2);
  assert.deepEqual((await store.revisions(first.project_id)).map((item) => item.revision_number), [2, 1]);
  assert.equal((await store.get(another.project_id)).project.name, "Road");
  assert.equal((await createBrowserProjectStore(storage, prepare).get(first.project_id)).revision_number, 2);
  await assert.rejects(store.revise(first.project_id, 1, project), /revision conflict/);
});
