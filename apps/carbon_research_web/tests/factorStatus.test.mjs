import test from "node:test";
import assert from "node:assert/strict";
import { calculationPreview, needsFactor, normalizeProject, pauseFactor, resumeFactor } from "../src/factorStatus.ts";

const factor = {
  numerator: { kind: "ghg_emission", input_value: 268, input_unit: "kilogram" },
  denominator: { kind: "volume", input_value: 1, input_unit: "meter ** 3" },
  source_name: "EPD fixture",
  source_version: "2026",
};
const row = (value = factor) => ({
  row_id: "concrete", item_name: "Concrete", category: "material", stage: "A1-A3",
  quantity: { kind: "volume", input_value: 10, input_unit: "meter ** 3" },
  factor: value, evidence_ref: "fixture://boq",
});
const project = (rows) => ({ schema_version: "civil.carbon.project.v1", name: "Example", asset_type: "building", description: "", rows });

test("a sourced factor survives pause and resume", () => {
  const paused = pauseFactor(row());
  assert.equal(paused.factor, null);
  assert.deepEqual(paused.inactive_factor, factor);
  assert.deepEqual(resumeFactor(paused).factor, factor);
});

test("blank factors are never stored as inactive factors", () => {
  const pending = { ...row(null), inactive_factor: null };
  const activated = resumeFactor(pending);
  assert.equal(needsFactor(activated), true);
  const pausedAgain = pauseFactor(activated);
  assert.equal(pausedAgain.inactive_factor, null);
  assert.equal(calculationPreview(project([activated]), "draft missing evidence").rows[0].factor, null);
  assert.equal(calculationPreview(project([pausedAgain]), "draft missing evidence").rows[0].factor, null);
});

test("an old browser draft with an invalid inactive factor is repaired", () => {
  const oldDraft = project([{ ...row(null), inactive_factor: { ...factor, source_name: "" } }]);
  const repaired = normalizeProject(oldDraft);
  assert.equal(repaired.rows[0].inactive_factor, null);
  assert.equal(repaired.rows[0].factor, null);
});
