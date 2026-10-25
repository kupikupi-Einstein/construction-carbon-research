import test from "node:test";
import assert from "node:assert/strict";
import { findMatchingProject, readProjectContext } from "../src/projectWorkspace.ts";

const draft = {
  name: "Bridge BOQ", asset_type: "bridge",
  rows: [{ row_id: "concrete" }, { row_id: "steel" }],
};
const saved = { project_id: "saved-1", revision_number: 2, project: draft };

test("an old local draft is associated with its saved project by stable BOQ row IDs", () => {
  assert.equal(findMatchingProject(draft, [saved])?.project_id, "saved-1");
  assert.equal(findMatchingProject({ ...draft, rows: [...draft.rows, { row_id: "new-row" }] }, [saved])?.project_id, "saved-1");
});

test("a name alone never associates unrelated or ambiguous projects", () => {
  assert.equal(findMatchingProject({ ...draft, rows: [{ row_id: "unrelated" }] }, [saved]), null);
  assert.equal(findMatchingProject(draft, [saved, { ...saved, project_id: "saved-2" }]), null);
});

test("saved context restores project identity without changing the draft", () => {
  const storage = { getItem: () => JSON.stringify({ projectId: "saved-1", latestRevision: 2, selectedRevision: 1 }) };
  assert.deepEqual(readProjectContext(storage), { projectId: "saved-1", latestRevision: 2, selectedRevision: 1 });
  assert.deepEqual(readProjectContext({ getItem: () => "broken json" }),
    { projectId: null, latestRevision: null, selectedRevision: null });
});
