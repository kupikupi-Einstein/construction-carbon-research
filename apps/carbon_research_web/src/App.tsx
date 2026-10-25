import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { api } from "./api";
import { calculationPreview, needsFactor, normalizeProject, pauseFactor, resumeFactor } from "./factorStatus";
import { findingText, tr } from "./i18n";
import type {
  ActivityRow,
  AssetType,
  CarbonResult,
  Locale,
  ProjectInput,
  ProjectRevision,
  Quantity,
  Stage,
  TverInput,
} from "./types";

type View = "overview" | "inputs" | "tver" | "results" | "exports";

const views: View[] = ["overview", "inputs", "tver", "results", "exports"];
const legacyExampleIds = ["boq-p2-5.1.2.1-concrete-proxy", "boq-p2-4.2-asphalt-proxy"];
const isLegacyExample = (project: ProjectInput) => project.name.startsWith("ตัวอย่าง BOQ เกียกกาย")
  && project.rows.length > 0 && project.rows.length <= 2
  && project.rows.every((row) => legacyExampleIds.includes(row.row_id));
const upgradeExample = (project: ProjectInput, example: ProjectInput): ProjectInput => ({
  ...project,
  name: example.name,
  description: example.description,
  rows: [...project.rows, ...example.rows.filter((row) => !project.rows.some((old) => old.row_id === row.row_id))],
});
const stages: Stage[] = ["A1-A3", "A4", "A5"];
const kinds = ["mass", "volume", "area", "length", "energy", "transport_work", "time", "dimensionless"];
const kindKeys: Record<string, Parameters<typeof tr>[0]> = {
  mass: "kindMass", volume: "kindVolume", area: "kindArea", length: "kindLength",
  energy: "kindEnergy", transport_work: "kindTransport", time: "kindTime", dimensionless: "kindCount",
};
const operandKeys: Record<string, Parameters<typeof tr>[0]> = {
  activity_quantity: "operandActivity",
  factor_denominator: "operandDenominator",
  factor_numerator: "operandNumerator",
};
const kindUnits: Record<string, string> = {
  mass: "tonne",
  volume: "meter ** 3",
  area: "meter ** 2",
  length: "kilometer",
  energy: "kilowatt_hour",
  transport_work: "tonne * kilometer",
  time: "hour",
  dimensionless: "dimensionless",
};
const ghg = (value = 0): Quantity => ({ kind: "ghg_emission", input_value: value, input_unit: "tonne" });
const emptyRow = (): ActivityRow => ({
  row_id: crypto.randomUUID(),
  item_name: "",
  category: "materials",
  stage: "A1-A3",
  quantity: { kind: "mass", input_value: 0, input_unit: "tonne" },
  factor: {
    numerator: { kind: "ghg_emission", input_value: 0, input_unit: "kilogram" },
    denominator: { kind: "mass", input_value: 1, input_unit: "tonne" },
    source_name: "",
    source_version: "",
  },
});
const emptyProject = (): ProjectInput => ({
  schema_version: "civil.carbon.project.v1",
  name: "",
  asset_type: "building",
  description: "",
  rows: [emptyRow()],
  tver: null,
});
const emptyTver = (method: TverInput["methodology_id"]): TverInput => ({
  methodology_id: method,
  methodology_version: "01",
  monitoring_year: new Date().getFullYear(),
  baseline_emission: ghg(),
  project_emission: ghg(),
  leakage_emission: ghg(),
  component_evidence_ref: "",
  additionality_evidence_ref: "",
  credit_rights_evidence_ref: "",
  monitoring_plan_ref: "",
  building_type: "office",
  building_measures: [],
  new_equipment: false,
  ready_mix: false,
  captured_co2_used: false,
  equivalent_strength: false,
  commercial_use: false,
  concrete_recycled: false,
  product_traceable: false,
});

function Field({ label, children, wide = false, hint }: { label: string; children: ReactNode; wide?: boolean; hint?: string }) {
  return <label className={`field${wide ? " wide" : ""}`}><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}

function Button({ children, onClick, secondary = false, disabled = false }: {
  children: ReactNode; onClick: () => void; secondary?: boolean; disabled?: boolean;
}) {
  return <button className={secondary ? "button secondary" : "button"} onClick={onClick} disabled={disabled}>{children}</button>;
}

const amountKg = (quantity: Quantity | undefined) => quantity?.canonical_value ?? quantity?.input_value ?? 0;
const tonnes = (quantity: Quantity | undefined) => amountKg(quantity) / 1000;
const number = (value: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value);
const quantityText = (quantity: Quantity) => `${number(quantity.input_value)} ${quantity.input_unit}`;
const safeUrl = (value?: string | null) => {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch { return null; }
};

export default function App() {
  const [locale, setLocale] = useState<Locale>("th-TH");
  const t = (key: Parameters<typeof tr>[0]) => tr(key, locale);
  const [view, setView] = useState<View>("overview");
  const [projects, setProjects] = useState<ProjectRevision[]>([]);
  const [draft, setDraft] = useState<ProjectInput>(() => {
    try {
      const saved = localStorage.getItem("carbon-research-draft-v1");
      return saved ? normalizeProject(JSON.parse(saved) as ProjectInput) : emptyProject();
    } catch { return emptyProject(); }
  });
  const [projectId, setProjectId] = useState<string | null>(null);
  const [latestRevision, setLatestRevision] = useState<number | null>(null);
  const [revisions, setRevisions] = useState<ProjectRevision[]>([]);
  const [selectedRevision, setSelectedRevision] = useState<number | null>(null);
  const [result, setResult] = useState<CarbonResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { localStorage.setItem("carbon-research-draft-v1", JSON.stringify(draft)); }, [draft]);
  useEffect(() => { document.title = t("brand"); }, [locale]);
  useEffect(() => { void api.list().then(setProjects).catch(console.error); }, []);
  useEffect(() => {
    if (!isLegacyExample(draft)) return;
    void api.kiakkaiExample().then((example) => {
      setDraft((current) => isLegacyExample(current) ? upgradeExample(current, example) : current);
    }).catch(console.error);
  }, []);
  useEffect(() => {
    if (!draft.name.trim() || draft.rows.some((row) => !row.item_name.trim())) {
      setResult(null);
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      void api.calculate(calculationPreview(draft, t("draftPreviewEvidence"))).then((calculated) => {
        if (active) setResult(calculated);
      }).catch(() => { if (active) setResult(null); });
    }, 400);
    return () => { active = false; window.clearTimeout(timer); };
  }, [draft, locale]);

  const selected = revisions.find((revision) => revision.revision_number === selectedRevision);
  const comparison = revisions.length > 1 ? revisions[0] : null;
  const incompleteFactorRows = draft.rows.filter(needsFactor);
  const resultRows = useMemo(() => new Map(result?.rows.map((row) => [row.row_id, row]) ?? []), [result]);

  async function openProject(id: string) {
    setBusy(true);
    try {
      const [latest, history] = await Promise.all([api.get(id), api.revisions(id)]);
      setProjectId(id);
      setLatestRevision(latest.revision_number);
      setRevisions(history);
      setSelectedRevision(latest.revision_number);
      if (isLegacyExample(latest.project)) {
        const example = await api.kiakkaiExample();
        const upgraded = upgradeExample(latest.project, example);
        setDraft(upgraded);
        setResult(await api.calculate(upgraded));
        setView("inputs");
        setMessage(t("legacyExampleUpdated"));
      } else {
        setDraft(latest.project);
        setResult(latest.result);
        setView("overview");
        setMessage("");
      }
    } catch (error) { console.error(error); setMessage(t("error")); }
    finally { setBusy(false); }
  }

  function newProject() {
    setProjectId(null);
    setLatestRevision(null);
    setRevisions([]);
    setSelectedRevision(null);
    setResult(null);
    setDraft(emptyProject());
    setView("inputs");
    setMessage("");
  }

  function updateRow(id: string, updater: (row: ActivityRow) => void) {
    setDraft((before) => ({
      ...before,
      rows: before.rows.map((row) => {
        if (row.row_id !== id) return row;
        const next = structuredClone(row);
        updater(next);
        return next;
      }),
    }));
    setResult(null);
    setMessage("");
  }

  function updateTver(updater: (value: TverInput) => void) {
    setDraft((before) => {
      if (!before.tver) return before;
      const next = structuredClone(before.tver);
      updater(next);
      return { ...before, tver: next };
    });
    setResult(null);
  }

  async function calculate() {
    setBusy(true);
    try {
      setResult(await api.calculate(calculationPreview(draft, t("draftPreviewEvidence"))));
      setMessage(incompleteFactorRows.length
        ? t("previewIncomplete").replace("{items}", incompleteFactorRows.map((row) => row.item_name).join(", "))
        : "");
      setView("results");
    }
    catch (error) { console.error(error); setMessage(t("error")); }
    finally { setBusy(false); }
  }

  async function save() {
    if (incompleteFactorRows.length) {
      setMessage(t("saveIncomplete").replace("{items}", incompleteFactorRows.map((row) => row.item_name).join(", ")));
      setView("inputs");
      return;
    }
    const missingEvidenceRows = draft.rows.filter((row) => row.factor === null && !row.evidence_ref?.trim());
    if (missingEvidenceRows.length) {
      setMessage(t("saveEvidence").replace("{items}", missingEvidenceRows.map((row) => row.item_name).join(", ")));
      setView("inputs");
      return;
    }
    setBusy(true);
    try {
      const validDraft = normalizeProject(draft);
      const revision = projectId && latestRevision
        ? await api.revise(projectId, latestRevision, validDraft)
        : await api.create(validDraft);
      const history = await api.revisions(revision.project_id);
      setProjectId(revision.project_id);
      setLatestRevision(revision.revision_number);
      setSelectedRevision(revision.revision_number);
      setRevisions(history);
      setResult(revision.result);
      setProjects(await api.list());
      setMessage(t("saved"));
      setView("results");
    } catch (error) { console.error(error); setMessage(t("error")); }
    finally { setBusy(false); }
  }

  async function importCsv(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const rows = await api.importCsv(file);
      setDraft((before) => ({ ...before, rows: [...before.rows.filter((row) => row.item_name), ...rows] }));
      setResult(null);
      setMessage("");
    } catch (error) { console.error(error); setMessage(t("error")); }
    finally { setBusy(false); event.target.value = ""; }
  }

  async function loadExample() {
    setBusy(true);
    try {
      const example = await api.kiakkaiExample();
      const calculated = await api.calculate(example);
      setProjectId(null);
      setLatestRevision(null);
      setRevisions([]);
      setSelectedRevision(null);
      setDraft(example);
      setResult(calculated);
      setView("inputs");
      setMessage(t("exampleLoaded"));
    } catch (error) { console.error(error); setMessage(t("error")); }
    finally { setBusy(false); }
  }

  function chooseRevision(revisionNumber: number) {
    const revision = revisions.find((item) => item.revision_number === revisionNumber);
    if (!revision) return;
    setSelectedRevision(revisionNumber);
    setDraft(revision.project);
    setResult(revision.result);
    setMessage("");
  }

  const checkbox = (key: keyof TverInput, label: string) => (
    <label className="check"><input type="checkbox" checked={draft.tver?.[key] === true}
      onChange={(event) => updateTver((value) => { (value as unknown as Record<string, unknown>)[key] = event.target.checked; })} />{label}</label>
  );

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">◈</div><div><strong>{t("brand")}</strong><span>{t("subtitle")}</span></div></div>
      <div className="sidebar-section"><div className="sidebar-label">{t("projects")} <span>{projects.length}</span></div><Button onClick={newProject} secondary>{t("newProject")}</Button></div>
      <div className="project-list" aria-label={t("projects")}>
        {!projectId && <button className="project-link active" onClick={() => setView("inputs")}>
          <span className="project-dot" /><span><strong>{draft.name || t("untitled")}</strong><small>{t("localDraft")} · {draft.rows.length} {t("rows")}</small></span>
        </button>}
        {projects.length === 0 && <p className="sidebar-empty">{t("noProjects")}</p>}
        {projects.map((revision) =>
        <button key={revision.project_id} className={`project-link${projectId === revision.project_id ? " active" : ""}`}
          onClick={() => void openProject(revision.project_id)}>
          <span className="project-dot" /><span><strong>{revision.project.name}</strong><small>{t("revision")} {revision.revision_number} · {revision.project.rows.length} {t("rows")} · {t(revision.project.asset_type)}</small></span>
        </button>)}</div>
      <div className="sidebar-foot">{t("draft")}</div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumb">{t("workspace")} <span>/</span> {draft.name || t("untitled")}</div>
        <div className="top-actions"><span className="draft-tag">{t("localDraft")}</span><div className="lang-toggle">
          <button className={locale === "th-TH" ? "selected" : ""} onClick={() => setLocale("th-TH")}>TH</button>
          <button className={locale === "en-US" ? "selected" : ""} onClick={() => setLocale("en-US")}>EN</button>
        </div></div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">{t("researchKicker")}</div><h1>{draft.name || t("untitled")}</h1><p>{t("draft")}</p></div>
          <div className="heading-actions"><Button onClick={() => void calculate()} secondary disabled={busy}>{t("preview")}</Button><Button onClick={() => void save()} disabled={busy}>{projectId ? t("save") : t("create")}</Button></div></div>
        {message && <div role="status" className="notice">{message}</div>}
        <nav className="tabs" aria-label={t("workspace")}>{views.map((item) => <button key={item} onClick={() => setView(item)}
          className={view === item ? "active" : ""}>{t(item)}</button>)}</nav>

        {view === "overview" && <div className="overview-grid">
          <section className="card lead-card"><div className="card-kicker">{t("profileKicker")}</div><h2>{t("overview")}</h2>
            <div className="form-grid"><Field label={t("name")} wide><input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></Field>
              <Field label={t("asset")}><select value={draft.asset_type} onChange={(event) => setDraft({ ...draft, asset_type: event.target.value as AssetType })}>
                {(["road", "bridge", "building", "interior"] as AssetType[]).map((asset) => <option key={asset} value={asset}>{t(asset)}</option>)}</select></Field>
              <Field label={t("description")} wide><textarea value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} rows={3} /></Field></div>
          </section>
          <section className="card metric-card"><div className="card-kicker">A1–A5</div><div className="metric-number">{result?.rows.length ? number(tonnes(result.total_emission)) : "—"}</div><div className="metric-unit">tCO₂e</div><p>{result?.pending_row_ids.length ? t("partialTotal") : t("total")}</p></section>
          <section className="card metric-card mint"><div className="card-kicker">BOQ</div><div className="metric-number">{draft.rows.length}</div><div className="metric-unit">{t("rows")}</div><p>{t("inputIntro")}</p></section>
          {revisions.length > 0 && <section className="card history-card"><div className="card-kicker">{t("historyKicker")}</div><h2>{t("history")}</h2>
            <div className="history-list">{revisions.map((revision) => <button key={revision.revision_id} onClick={() => chooseRevision(revision.revision_number)}
              className={selectedRevision === revision.revision_number ? "active" : ""}>
              <strong>{t("revision")} {revision.revision_number}</strong><span>{new Date(revision.created_at).toLocaleString(locale)}</span></button>)}</div>
            {selected && comparison && selected.revision_number !== comparison.revision_number && <p className="compare-line">{t("compare")}: {number(tonnes(selected.result.total_emission) - tonnes(comparison.result.total_emission))} tCO₂e</p>}
          </section>}
        </div>}

        {view === "inputs" && <section className="card editor-card"><div className="section-head"><div><div className="card-kicker">{t("inventoryKicker")}</div><h2>{t("inputs")}</h2><p>{t("inputIntro")}</p></div>
          <div className="import-actions"><Button onClick={() => void loadExample()} secondary disabled={busy}>{t("loadExample")}</Button><label className="button secondary file-button">{t("csv")}<input type="file" accept=".csv,text/csv" onChange={(event) => void importCsv(event)} /></label></div></div>
          <div className="input-guide"><h3>{t("inputGuideTitle")}</h3><ol><li>{t("inputStep1")}</li><li>{t("inputStep2")}</li><li>{t("inputStep3")}</li><li>{t("inputStep4")}</li></ol><p>{t("supportedMaterials")}</p><p className="status-guide">{t("factorStatusGuide")}</p><p>{t("inputCostNote")}</p><p>{t("inputExampleNote")}</p></div>
          <div className="row-list">{draft.rows.map((row, index) => <div className="activity-card" key={row.row_id}>
            <div className="activity-head"><span className="number-badge">{String(index + 1).padStart(2, "0")}</span><strong>{row.item_name || t("item")}</strong><button className="text-button" onClick={() => { setDraft({ ...draft, rows: draft.rows.filter((item) => item.row_id !== row.row_id) }); setResult(null); }} disabled={draft.rows.length === 1}>{t("remove")}</button></div>
            <div className="form-grid rows-grid"><Field label={t("item")} wide><input value={row.item_name} onChange={(event) => updateRow(row.row_id, (next) => { next.item_name = event.target.value; })} /></Field>
              <Field label={t("category")}><input value={row.category} onChange={(event) => updateRow(row.row_id, (next) => { next.category = event.target.value; })} /></Field>
              <Field label={t("stage")}><select value={row.stage} onChange={(event) => updateRow(row.row_id, (next) => { next.stage = event.target.value as Stage; })}>{stages.map((stage) => <option key={stage}>{stage}</option>)}</select></Field>
              <Field label={t("quantity")} hint={t("quantityHint")}><input type="number" min="0" step="any" value={row.quantity.input_value} onChange={(event) => updateRow(row.row_id, (next) => { next.quantity.input_value = Number(event.target.value); })} /></Field>
              <Field label={t("unit")}><div className="compound"><select value={row.quantity.kind} aria-label={t("quantityKind")} onChange={(event) => updateRow(row.row_id, (next) => { const kind = event.target.value; if (next.quantity.kind !== kind) next.inactive_factor = null; next.quantity.kind = kind; next.quantity.input_unit = kindUnits[kind] ?? "dimensionless"; if (next.factor) { next.factor.denominator.kind = kind; next.factor.denominator.input_unit = kindUnits[kind] ?? "dimensionless"; } })}>{kinds.map((kind) => <option key={kind} value={kind}>{t(kindKeys[kind] ?? "kindCount")}</option>)}</select><input value={row.quantity.input_unit} aria-label={t("quantityUnit")} onChange={(event) => updateRow(row.row_id, (next) => { next.quantity.input_unit = event.target.value; })} /></div></Field>
              <label className="field wide"><span>{t("factorStatus")}</span><span><input type="checkbox" checked={row.factor === null} onChange={(event) => updateRow(row.row_id, (next) => { Object.assign(next, event.target.checked ? pauseFactor(next) : resumeFactor(next)); })} /> {t("pendingFactor")}</span><small>{t("pendingHint")}</small></label>
              {row.factor && <>
              <Field label={`${t("factorTop")} (kgCO₂e)`} hint={t("factorTopHint")}><input type="number" min="0" step="any" value={row.factor.numerator.input_value} onChange={(event) => updateRow(row.row_id, (next) => { if (next.factor) next.factor.numerator.input_value = Number(event.target.value); })} /></Field>
              <Field label={t("factorBottom")} hint={t("factorBottomHint")}><div className="compound"><input type="number" min="0.000001" step="any" value={row.factor.denominator.input_value} onChange={(event) => updateRow(row.row_id, (next) => { if (next.factor) next.factor.denominator.input_value = Number(event.target.value); })} /><input value={row.factor.denominator.input_unit} aria-label={t("denominatorUnit")} onChange={(event) => updateRow(row.row_id, (next) => { if (next.factor) next.factor.denominator.input_unit = event.target.value; })} /></div></Field>
              <Field label={t("source")}><input value={row.factor.source_name} onChange={(event) => updateRow(row.row_id, (next) => { if (next.factor) next.factor.source_name = event.target.value; })} /></Field>
              <Field label={t("version")}><input value={row.factor.source_version} onChange={(event) => updateRow(row.row_id, (next) => { if (next.factor) next.factor.source_version = event.target.value; })} /></Field>
              <Field label={t("sourceUrl")} wide><input type="url" value={row.factor.source_url ?? ""} onChange={(event) => updateRow(row.row_id, (next) => { if (next.factor) next.factor.source_url = event.target.value || null; })} /></Field>
              </>}
              {needsFactor(row) && <p className="factor-warning">{t("factorRequired")}</p>}
              {row.factor === null && !row.evidence_ref?.trim() && <p className="factor-warning">{t("pendingEvidenceRequired")}</p>}
              <Field label={t("evidence")} wide><input value={row.evidence_ref ?? ""} onChange={(event) => updateRow(row.row_id, (next) => { next.evidence_ref = event.target.value; })} /></Field></div>
            {resultRows.get(row.row_id) && <div className="row-result">{t("emission")}: {number(tonnes(resultRows.get(row.row_id)?.emission))} tCO₂e</div>}
            {result?.pending_row_ids.includes(row.row_id) && <div className="row-result">{needsFactor(row) ? t("factorRequired") : t("pendingExcluded")}</div>}
          </div>)}</div><Button onClick={() => { setDraft({ ...draft, rows: [...draft.rows, emptyRow()] }); setResult(null); }} secondary>{t("addRow")}</Button>
        </section>}

        {view === "tver" && <section className="card editor-card"><div className="card-kicker">{t("tverKicker")}</div><h2>{t("tver")}</h2>
          <div className="credit-flow"><div><h3>{t("creditInputsTitle")}</h3><p>{t("creditInputsExplainer")}</p></div><div className="credit-flow-numbers"><span>{t("footprintPartial")}</span><strong>{result?.rows.length ? `${number(tonnes(result.total_emission))} tCO₂e` : "—"}</strong><span>{t("creditNotCalculated")}</span></div></div>
          <div className="credit-screen"><h3>{t("autoScreenTitle")}</h3><p>{t("autoScreenIntro")}</p>{result?.credit_readiness.length ? <div className="credit-screen-list">{result.credit_readiness.map((item) => { const input = draft.rows.find((row) => row.row_id === item.row_id); const link = safeUrl(item.source_url); return <div className="credit-screen-row" key={item.row_id}><div><strong>{input?.item_name ?? item.row_id}</strong><small>{item.footprint_status === "pending_factor" ? t("pendingExcluded") : t("emission")}</small></div><div><span className="status-pill">{item.methodology_id ? t("activityRequired") : t("noDirectMethod")}</span><p>{findingText(item.reason_code, locale)}</p>{item.methodology_id && <p><strong>{t("creditPathway")}: {item.methodology_id} v{item.methodology_version}</strong></p>}{link && <a href={link} target="_blank" rel="noreferrer">{t("reference")} ↗</a>}</div></div>; })}</div> : <p>{t("dataGap")}</p>}<p className="credit-notice">{t("noCreditIssued")}</p></div>
          <div className="credit-explainer"><h3>{t("creditExplainerTitle")}</h3><p>{t("creditExplainer")}</p><h4>{t("creditOtherTitle")}</h4><ul>
          <li><a href="https://tver.tgo.or.th/database/public/methodology/98?lang=en" target="_blank" rel="noreferrer">{t("creditCement")} · T-VER-P-METH-08-01 ↗</a></li>
          <li><a href="https://tver.tgo.or.th/database/public/methodologies/1?category_id=9&lang=en" target="_blank" rel="noreferrer">{t("creditPlastic")} · T-VER-S-METH-09-06 ↗</a></li>
          <li><a href="https://tver.tgo.or.th/database/public/methodologies/1?category_id=6&lang=en" target="_blank" rel="noreferrer">{t("creditEnergy")} ↗</a></li>
        </ul><p>{t("creditMethodLimit")}</p></div><h3>{t("manualTverTitle")}</h3><p className="section-copy">{t("manualTverIntro")}</p><p className="section-copy">{t("methodIntro")}</p>
          <Field label={t("method")}><select value={draft.tver?.methodology_id ?? ""} onChange={(event) => { const method = event.target.value; setDraft({ ...draft, tver: method ? emptyTver(method as TverInput["methodology_id"]) : null }); setResult(null); }}>
            <option value="">{t("methodNone")}</option><option value="T-VER-S-METH-06-15">{t("methodBuilding")}</option><option value="T-VER-P-METH-14-02">{t("methodConcrete")}</option></select></Field>
          {draft.tver && <><div className="form-grid tver-grid"><Field label={t("monitoringYear")}><input type="number" value={draft.tver.monitoring_year} onChange={(event) => updateTver((value) => { value.monitoring_year = Number(event.target.value); })} /></Field>
            {(["baseline_emission", "project_emission", "leakage_emission"] as const).map((key, index) => <Field key={key} label={t((["baseline", "projectEmissions", "leakage"] as const)[index]!)}><input type="number" min="0" step="any" value={draft.tver?.[key].input_value ?? 0} onChange={(event) => updateTver((value) => { value[key].input_value = Number(event.target.value); })} /></Field>)}
            {(["component_evidence_ref", "additionality_evidence_ref", "credit_rights_evidence_ref", "monitoring_plan_ref"] as const).map((key, index) => <Field key={key} label={t((["componentEvidence", "additionality", "rights", "monitoring"] as const)[index]!)}><input value={draft.tver?.[key] ?? ""} onChange={(event) => updateTver((value) => { value[key] = event.target.value; })} /></Field>)}</div>
            {draft.tver.methodology_id === "T-VER-S-METH-06-15" ? <div className="method-options"><Field label={t("buildingType")}><select value={draft.tver.building_type ?? "office"} onChange={(event) => updateTver((value) => { value.building_type = event.target.value; })}>{(["office", "hotel", "hospital", "shopping_center", "theatre", "service", "assembly", "condominium", "education"] as const).map((type) => <option key={type} value={type}>{t(type)}</option>)}</select></Field>
              <Field label={t("measures")}><input value={draft.tver.building_measures?.join(", ") ?? ""} onChange={(event) => updateTver((value) => { value.building_measures = event.target.value.split(",").map((item) => item.trim()).filter(Boolean); })} /></Field>{checkbox("new_equipment", t("newEquipment"))}</div>
              : <div className="method-options check-grid">{checkbox("ready_mix", t("readyMix"))}{checkbox("captured_co2_used", t("capturedCo2"))}{checkbox("equivalent_strength", t("strength"))}{checkbox("commercial_use", t("commercial"))}{checkbox("concrete_recycled", t("recycled"))}{checkbox("product_traceable", t("traceable"))}</div>}{result?.tver && <div className="credit-manual-result"><strong>{t("estimate")}: {number(tonnes(result.tver.estimated_reduction))} tCO₂e</strong><p>{result.tver.screening_status === "potentially_applicable" ? t("potential") : result.tver.screening_status === "not_applicable" ? t("notApplicable") : t("insufficient")} · {t("noCreditIssued")}</p></div>}</>}
        </section>}

        {view === "results" && <div className="results-grid">{result ? <><section className="card result-hero"><div className="card-kicker">{t("totalKicker")}</div><div className="result-number">{result.rows.length ? number(tonnes(result.total_emission)) : "—"}<span>tCO₂e</span></div><p>{t("draft")}</p>{result.pending_row_ids.length > 0 && <p>{t("partialTotal")} ({result.pending_row_ids.length})</p>}{incompleteFactorRows.length > 0 && <p className="factor-warning">{t("previewIncomplete").replace("{items}", incompleteFactorRows.map((row) => row.item_name).join(", "))}</p>}</section>
          <section className="card chart-card"><h2>{t("stageChart")}</h2>{stages.map((stage) => { const value = tonnes(result.by_stage[stage]); const total = Math.max(tonnes(result.total_emission), 0.001); const hasRows = draft.rows.some((row) => row.stage === stage); return <div className="bar-row" key={stage}><strong>{stage}</strong><div className="bar-track"><div style={{ width: `${Math.min(100, value / total * 100)}%` }} /></div><span>{hasRows ? number(value) : "—"}</span></div>; })}<small>tCO₂e</small></section>
          <section className="card chart-card"><h2>{t("categories")}</h2>{Object.entries(result.by_category).map(([category, quantity]) => <div className="category-line" key={category}><span>{category}</span><strong>{number(tonnes(quantity))} tCO₂e</strong></div>)}</section>
          <section className="card trace-card"><h2>{t("traceTitle")}</h2><p>{t("traceIntro")}</p>
            {result.rows.map((item) => { const input = draft.rows.find((row) => row.row_id === item.row_id); const trace = item.trace; const factorUrl = safeUrl(input?.factor?.source_url); const ruleUrl = safeUrl(trace.source_url); return <details key={item.row_id}>
              <summary><span>{input?.item_name ?? item.row_id}</span><strong>{number(item.emission.canonical_value ?? item.emission.input_value)} kgCO₂e</strong></summary>
              <div className="trace-detail"><p><strong>{t("traceRule")}:</strong> <code>{trace.formula}</code></p>
                <div className="trace-operands">{Object.entries(trace.operands).map(([key, value]) => <div key={key}><span>{t(operandKeys[key] ?? "traceOperand")}</span><strong>{quantityText(value)}</strong></div>)}</div>
                <p><strong>{t("traceResult")}:</strong> {quantityText(item.emission)}</p>
                <p><strong>{t("traceFactorSource")}:</strong> {input?.factor?.source_name} · {input?.factor?.source_version} {factorUrl && <a href={factorUrl} target="_blank" rel="noreferrer">{t("sourceUrl")} ↗</a>}</p>
                <p><strong>{t("traceBoqEvidence")}:</strong> {input?.evidence_ref || "—"}</p>
                <p><strong>{t("reference")}:</strong> {trace.standard_id} {trace.edition} · {trace.clause} {ruleUrl && <a href={ruleUrl} target="_blank" rel="noreferrer">↗</a>}</p>
              </div>
            </details>; })}
            {result.pending_row_ids.map((id) => { const input = draft.rows.find((row) => row.row_id === id); return <details key={id}><summary><span>{input?.item_name ?? id}</span><strong>{t("pendingExcluded")}</strong></summary><div className="trace-detail"><p>{input ? quantityText(input.quantity) : "—"}</p><p><strong>{t("traceBoqEvidence")}:</strong> {input?.evidence_ref || "—"}</p><p>{input && needsFactor(input) ? t("factorRequired") : t("pendingHint")}</p></div></details>; })}
          </section>
          {result.tver && <section className="card tver-result"><div className="card-kicker">T-VER</div><h2>{t("screening")}</h2><div className="credit-number">{number(tonnes(result.tver.estimated_reduction))} <span>tCO₂e</span></div><p>{t("estimate")}: {result.tver.methodology_id}</p><div className="status-pill">{result.tver.screening_status === "potentially_applicable" ? t("potential") : result.tver.screening_status === "not_applicable" ? t("notApplicable") : t("insufficient")}</div><p className="credit-notice">{t("noCredits")}</p><ul>{result.tver.findings.map((finding) => <li key={finding}>{findingText(finding, locale)}</li>)}</ul></section>}
        </> : <section className="card empty-state"><div className="empty-icon">◇</div><h2>{t("dataGap")}</h2><Button onClick={() => void calculate()} disabled={busy}>{t("preview")}</Button></section>}</div>}

        {view === "exports" && <section className="card export-card"><div className="card-kicker">{t("outputKicker")}</div><h2>{t("exports")}</h2><p>{t("exportIntro")}</p>
          {projectId && selectedRevision ? <><Field label={t("current")}><select value={selectedRevision} onChange={(event) => chooseRevision(Number(event.target.value))}>{revisions.map((revision) => <option key={revision.revision_id} value={revision.revision_number}>{t("revision")} {revision.revision_number} · {new Date(revision.created_at).toLocaleDateString(locale)}</option>)}</select></Field>
            <div className="export-options">{(["pdf", "xlsx", "docx"] as const).map((format) => <a key={format} className="export-option" href={api.exportUrl(projectId, selectedRevision, format, locale)}><span className="file-icon">{format.toUpperCase()}</span><strong>{t(format)}</strong><span>↓</span></a>)}</div>
            <p className="manifest">SHA-256 · {selected?.input_snapshot_hash}</p></> : <p className="empty-copy">{t("noSaved")}</p>}</section>}
        <footer className="footer">{t("disclaimer")}</footer>
      </div>
    </main>
  </div>;
}
