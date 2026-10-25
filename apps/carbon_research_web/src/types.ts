export type Locale = "th-TH" | "en-US";
export type AssetType = "road" | "bridge" | "building" | "interior";
export type Stage = "A1-A3" | "A4" | "A5";
export type Quantity = { kind: string; input_value: number; input_unit: string; canonical_value?: number };
export type Factor = {
  numerator: Quantity;
  denominator: Quantity;
  source_name: string;
  source_version: string;
  source_url?: string | null;
};
export type ActivityRow = {
  row_id: string;
  item_name: string;
  category: string;
  stage: Stage;
  quantity: Quantity;
  factor: Factor | null;
  evidence_ref?: string | null;
};
export type TverInput = {
  methodology_id: "T-VER-S-METH-06-15" | "T-VER-P-METH-14-02";
  methodology_version: "01";
  monitoring_year: number;
  baseline_emission: Quantity;
  project_emission: Quantity;
  leakage_emission: Quantity;
  component_evidence_ref: string;
  additionality_evidence_ref?: string | null;
  credit_rights_evidence_ref?: string | null;
  monitoring_plan_ref?: string | null;
  building_type?: string | null;
  building_measures?: string[];
  new_equipment?: boolean | null;
  ready_mix?: boolean | null;
  captured_co2_used?: boolean | null;
  equivalent_strength?: boolean | null;
  commercial_use?: boolean | null;
  concrete_recycled?: boolean | null;
  product_traceable?: boolean | null;
};
export type ProjectInput = {
  schema_version: "civil.carbon.project.v1";
  name: string;
  asset_type: AssetType;
  description: string;
  rows: ActivityRow[];
  tver?: TverInput | null;
};
export type CarbonResult = {
  total_emission: Quantity;
  by_stage: Record<Stage, Quantity>;
  by_category: Record<string, Quantity>;
  rows: { row_id: string; emission: Quantity; trace: {
    formula: string;
    standard_id: string;
    edition: string;
    clause: string;
    source_url: string;
    operands: Record<string, Quantity>;
  } }[];
  pending_row_ids: string[];
  credit_readiness: {
    row_id: string;
    material_key: string;
    methodology_id: string | null;
    methodology_version: string | null;
    source_url: string;
    status: "separate_activity_required" | "no_direct_material_method";
    reason_code: string;
    footprint_status: "calculated" | "pending_factor";
  }[];
  tver?: {
    methodology_id: string;
    screening_status: string;
    estimated_reduction: Quantity;
    findings: string[];
    credit_status: string;
  } | null;
  warnings: string[];
};
export type ProjectRevision = {
  project_id: string;
  revision_id: string;
  revision_number: number;
  created_at: string;
  input_snapshot_hash: string;
  project: ProjectInput;
  result: CarbonResult;
};
