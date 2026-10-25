import test from "node:test";
import assert from "node:assert/strict";
import { draftStorageKey, shouldLoadStarterExample, starterSeenKey } from "../src/starterWorkspace.ts";

const storage = (entries = {}) => ({ getItem: (key) => entries[key] ?? null });

test("public first visit offers the BOQ starter even after an empty draft was saved", () => {
  assert.equal(shouldLoadStarterExample(storage(), true, false), true);
  assert.equal(shouldLoadStarterExample(storage({ [draftStorageKey]: JSON.stringify({
    name: "", rows: [{ item_name: "" }], tver: null,
  }) }), true, false), true);
});

test("starter never replaces an existing draft, project, or prior starter choice", () => {
  assert.equal(shouldLoadStarterExample(storage({ [draftStorageKey]: JSON.stringify({
    name: "My bridge", rows: [{ item_name: "Steel" }],
  }) }), true, false), false);
  assert.equal(shouldLoadStarterExample(storage(), true, true), false);
  assert.equal(shouldLoadStarterExample(storage({ [starterSeenKey]: "1" }), true, false), false);
  assert.equal(shouldLoadStarterExample(storage(), false, false), false);
});
