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

In **ข้อมูลนำเข้า / Inputs**, click **โหลดตัวอย่าง BOQ เกียกกาย / Load Kiakkai BOQ example**. Then calculate and open each row under **ผลประเมิน / Results** for the formula, units, source EPD and BOQ assumptions. The sample has one pile-cap concrete row and one asphalt row using disclosed proxy assumptions; it is not the whole project.

## Verify

```powershell
$env:PYTHONPATH = "$PWD;$PWD\packages"
.venv\Scripts\python -m pytest -q tests/integration/test_carbon_research_api.py
.venv\Scripts\python -m ruff check apps packages tests
.venv\Scripts\python -m mypy -m apps.api.carbon -m civil_workflows.carbon.engine
npm --prefix apps/carbon_research_web run build
```

This is a local development app with SQLite and no authentication or RBAC. Do not expose it publicly or enter real customer data. Carbon factors, system boundaries, credit rights, and engineering assumptions need independent human review before certification or trading.
