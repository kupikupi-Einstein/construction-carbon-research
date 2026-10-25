# Construction Carbon Research

Research-stage web app for construction carbon accounting across roads, bridges, buildings, architecture, and interiors. It imports BOQ CSV or manual activity rows, calculates A1–A5 emissions from user-cited factors, stores immutable project revisions, and exports PDF, Excel, and Word reports. A separate T-VER panel screens two methods; its estimates are not issued credits.

The interface has Thai and English modes. [Research method](docs/phase-0/CONSTRUCTION_CARBON_RESEARCH_TH.md), [Kiakkai BOQ worked example](docs/phase-0/KIAKKAI_BOQ_WORKED_EXAMPLE_TH.md), and [MVP acceptance contract](docs/phase-0/CARBON_MVP_TASK_CONTRACT_TH.md) describe scope and limitations. The source BOQ PDF is deliberately not included; the sample contains only derived item data and assumptions.

## Run locally

Use Python 3.12 or newer and Node.js. The commands below are for PowerShell from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
npm --prefix apps/carbon_research_web ci
npm --prefix apps/carbon_research_web run build
$env:PYTHONPATH = "$PWD;$PWD\packages"
.venv\Scripts\python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8125
```

Open `http://127.0.0.1:8125/carbon/`. The API schema is at `/docs`. Local project data defaults to `instance/carbon_research.sqlite3`; set `CIVIL_CARBON_DB_PATH` to change it. Set `CIVIL_CARBON_PDF_FONT` to a Thai-capable TTF path if PDF export cannot find a Thai font.

In **ข้อมูลนำเข้า / Inputs**, click **โหลดตัวอย่าง BOQ เกียกกาย / Load Kiakkai BOQ example**. The four rows include illustrative calculations for pile-cap concrete and asphalt, plus steel grating and HDPE pipe rows awaiting product data and emission factors. Open **ผลประเมิน / Results** for each row's calculation or missing-data explanation. The displayed sum covers only the calculated rows and is not the whole project. Older two-row sample drafts are expanded to four rows in the working draft; save to create a new revision. The left list shows each saved project once; its local working draft remains associated with that project after a refresh. A separate draft entry appears only for a new project that has not been saved.

The **คาร์บอนเครดิต / Carbon credit** tab automatically screens each valid BOQ row as inputs change. It lists research pathways for concrete CO₂ use and plastic recovery/recycling, and explains why steel or asphalt purchases alone do not identify a credit methodology. This screening produces no credit quantity. The separate T-VER worksheet supports preliminary arithmetic checks for two implemented methods only; it requires independently sourced baseline, project and leakage emissions, rights and monitoring evidence. BOQ embodied emissions must not be copied into those fields as credit reductions.

The **สถานะข้อมูลตัวคูณ / Emission factor status** checkbox in an input row pauses that row's factor and excludes the row from the partial total. Clearing the checkbox restores any previously entered factor, its unit and source; saved revisions keep the paused value too. If a row never had a factor (such as the sample steel and HDPE rows), clearing the checkbox opens blank EF fields; it does not estimate emissions automatically. Enter a suitable EF with a matching unit, source and version to include that row. Until then **Calculate** still shows a partial total from complete rows and identifies the excluded rows. Saving a revision requires complete factor details or an explicit pending state with a missing-data note in the evidence field.

## Verify

```powershell
$env:PYTHONPATH = "$PWD;$PWD\packages"
.venv\Scripts\python -m pytest -q tests/integration/test_carbon_research_api.py
.venv\Scripts\python -m ruff check apps packages tests
.venv\Scripts\python -m mypy -m apps.api.carbon -m civil_workflows.carbon.engine
npm --prefix apps/carbon_research_web run build
npm --prefix apps/carbon_research_web test
```

This is a local development app with SQLite and no authentication or RBAC. Do not expose it publicly or enter real customer data. Carbon factors, system boundaries, credit rights, and engineering assumptions need independent human review before certification or trading.
