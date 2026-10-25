"""Worked examples and API/export checks for the construction carbon MVP."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from civil_api_contracts.carbon import CarbonProjectInput
from civil_workflows.carbon import calculate_project
from fastapi.testclient import TestClient

from apps.api.main import app


def _quantity(kind: str, value: float, unit: str) -> dict[str, str | float]:
    return {"kind": kind, "input_value": value, "input_unit": unit}


def _project(asset_type: str, amount: float = 10.0) -> dict[str, object]:
    return {
        "name": f"{asset_type} example",
        "asset_type": asset_type,
        "rows": [
            {
                "row_id": "material-1",
                "item_name": "cited material",
                "category": "materials",
                "stage": "A1-A3",
                "quantity": _quantity("mass", amount, "tonne"),
                "factor": {
                    "numerator": _quantity("ghg_emission", 200, "kilogram"),
                    "denominator": _quantity("mass", 1, "tonne"),
                    "source_name": "worked-example factor",
                    "source_version": "test-v1",
                },
                "evidence_ref": "fixture://material-1",
            },
            {
                "row_id": "transport-1",
                "item_name": "delivery activity",
                "category": "transport",
                "stage": "A4",
                "quantity": _quantity("length", 50, "kilometer"),
                "factor": {
                    "numerator": _quantity("ghg_emission", 2, "kilogram"),
                    "denominator": _quantity("length", 1, "kilometer"),
                    "source_name": "worked-example transport factor",
                    "source_version": "test-v1",
                },
            },
        ],
    }


@pytest.mark.parametrize("asset_type", ["road", "bridge", "building", "interior"])
def test_four_asset_worked_examples(asset_type: str) -> None:
    project = CarbonProjectInput.model_validate(_project(asset_type))
    result = calculate_project(project)
    assert result.total_emission.to("kilogram") == 2100
    assert result.by_stage["A1-A3"].to("kilogram") == 2000
    assert result.by_stage["A4"].to("kilogram") == 100
    assert result.by_stage["A5"].to("kilogram") == 0
    assert result.rows[0].trace.standard_id == "ISO 14040"
    assert all(item.status == "no_direct_material_method" for item in result.credit_readiness)


def test_quantity_factor_dimensions_and_missing_source_rejected() -> None:
    bad = _project("road")
    bad["rows"][0]["factor"]["denominator"] = _quantity("volume", 1, "meter ** 3")  # type: ignore[index]
    with pytest.raises(ValueError, match="same kind"):
        CarbonProjectInput.model_validate(bad)
    bad = _project("road")
    bad["rows"][0]["factor"]["source_name"] = ""  # type: ignore[index]
    with pytest.raises(ValueError):
        CarbonProjectInput.model_validate(bad)


def test_tver_building_screening_keeps_estimate_separate_from_credit() -> None:
    project = _project("building")
    project["tver"] = {
        "methodology_id": "T-VER-S-METH-06-15",
        "monitoring_year": 2026,
        "baseline_emission": _quantity("ghg_emission", 10, "tonne"),
        "project_emission": _quantity("ghg_emission", 7, "tonne"),
        "leakage_emission": _quantity("ghg_emission", 0.2, "tonne"),
        "component_evidence_ref": "fixture://components",
        "additionality_evidence_ref": "fixture://additionality",
        "credit_rights_evidence_ref": "fixture://rights",
        "monitoring_plan_ref": "fixture://monitoring",
        "building_type": "office",
        "building_measures": ["lighting", "hvac"],
        "new_equipment": True,
    }
    result = calculate_project(CarbonProjectInput.model_validate(project))
    assert result.tver is not None
    assert result.tver.estimated_reduction.to("tonne") == pytest.approx(2.8)
    assert result.tver.screening_status == "potentially_applicable"
    assert result.tver.credit_status == "estimate_not_issued"


def test_tver_concrete_precast_is_not_applicable() -> None:
    project = _project("bridge")
    project["tver"] = {
        "methodology_id": "T-VER-P-METH-14-02",
        "monitoring_year": 2026,
        "baseline_emission": _quantity("ghg_emission", 4, "tonne"),
        "project_emission": _quantity("ghg_emission", 3, "tonne"),
        "leakage_emission": _quantity("ghg_emission", 0, "tonne"),
        "component_evidence_ref": "fixture://components",
        "ready_mix": False,
        "captured_co2_used": True,
        "equivalent_strength": True,
        "commercial_use": True,
        "concrete_recycled": False,
        "product_traceable": True,
    }
    result = calculate_project(CarbonProjectInput.model_validate(project))
    assert result.tver is not None
    assert result.tver.screening_status == "not_applicable"
    assert "ready_mix_required" in result.tver.findings


def test_tver_missing_component_evidence_is_reported() -> None:
    project = _project("building")
    project["tver"] = {
        "methodology_id": "T-VER-S-METH-06-15",
        "monitoring_year": 2026,
        "baseline_emission": _quantity("ghg_emission", 10, "tonne"),
        "project_emission": _quantity("ghg_emission", 7, "tonne"),
        "leakage_emission": _quantity("ghg_emission", 0, "tonne"),
        "building_type": "office",
        "building_measures": ["lighting", "hvac"],
        "new_equipment": True,
        "additionality_evidence_ref": "fixture://additionality",
        "credit_rights_evidence_ref": "fixture://rights",
        "monitoring_plan_ref": "fixture://monitoring",
    }
    result = calculate_project(CarbonProjectInput.model_validate(project))
    assert result.tver is not None
    assert result.tver.screening_status == "insufficient_data"
    assert "component_evidence_missing" in result.tver.findings


def test_project_revisions_and_three_exports(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("CIVIL_CARBON_DB_PATH", str(tmp_path / "carbon.sqlite3"))
    client = TestClient(app)
    created = client.post("/api/v1/carbon/projects", json=_project("road"))
    assert created.status_code == 201, created.text
    first = created.json()
    project_id = first["project_id"]
    assert client.get(f"/api/v1/carbon/projects/{project_id}").json()["revision_number"] == 1
    updated = client.post(
        f"/api/v1/carbon/projects/{project_id}/revisions",
        json={"expected_revision_number": 1, "project": _project("road", amount=12)},
    )
    assert updated.status_code == 201, updated.text
    assert updated.json()["result"]["total_emission"]["input_value"] == 2500
    conflict = client.post(
        f"/api/v1/carbon/projects/{project_id}/revisions",
        json={"expected_revision_number": 1, "project": _project("road", amount=13)},
    )
    assert conflict.status_code == 409
    assert (
        client.get(f"/api/v1/carbon/projects/{project_id}/revisions/1").json()["result"][
            "total_emission"
        ]["input_value"]
        == 2100
    )
    assert len(client.get(f"/api/v1/carbon/projects/{project_id}/revisions").json()) == 2
    for file_format, signature in (("pdf", b"%PDF-"), ("docx", b"PK"), ("xlsx", b"PK")):
        response = client.get(
            f"/api/v1/carbon/projects/{project_id}/revisions/2/export/{file_format}?locale=en-US"
        )
        assert response.status_code == 200, response.text
        assert response.content.startswith(signature)
        if file_format != "pdf":
            with ZipFile(BytesIO(response.content)) as archive:
                assert archive.testzip() is None
                xml = b" ".join(
                    archive.read(name) for name in archive.namelist() if name.endswith(".xml")
                )
                assert updated.json()["input_snapshot_hash"].encode() in xml
                assert b"worked-example factor" in xml
        else:
            assert len(response.content) > 1000
        assert "r2" in response.headers["content-disposition"]


def test_csv_import_and_thai_exports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CIVIL_CARBON_DB_PATH", str(tmp_path / "carbon.sqlite3"))
    client = TestClient(app)
    csv_text = (
        "row_id,item_name,category,stage,quantity_kind,quantity_value,quantity_unit,"
        "factor_numerator_value,factor_numerator_unit,factor_denominator_value,"
        "factor_denominator_unit,source_name,source_version,evidence_ref\n"
        "r1,Concrete,structure,A1-A3,volume,5,meter ** 3,250,kilogram,1,"
        "meter ** 3,verified EPD,2026,fixture://epd\n"
    )
    response = client.post(
        "/api/v1/carbon/import-csv",
        files={"file": ("boq.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200, response.text
    rows = response.json()
    assert rows[0]["factor"]["source_name"] == "verified EPD"
    project = {"name": "อาคารตัวอย่าง", "asset_type": "building", "rows": rows}
    saved = client.post("/api/v1/carbon/projects", json=project)
    assert saved.status_code == 201, saved.text
    project_id = saved.json()["project_id"]
    for format_name, signature in (("pdf", b"%PDF-"), ("docx", b"PK"), ("xlsx", b"PK")):
        export = client.get(
            f"/api/v1/carbon/projects/{project_id}/revisions/1/export/{format_name}?locale=th-TH"
        )
        assert export.status_code == 200, export.text
        assert export.content.startswith(signature)


def test_kiakkai_boq_worked_example_exposes_source_and_trace() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/carbon/examples/kiakkai")
    assert response.status_code == 200, response.text
    example = response.json()
    assert example["asset_type"] == "bridge"
    assert len(example["rows"]) == 4
    assert example["rows"][0]["quantity"]["input_value"] == 891
    assert example["rows"][0]["factor"]["numerator"]["input_value"] == 268
    assert "epd17806" in example["rows"][0]["factor"]["source_url"]
    asphalt = example["rows"][1]
    assert asphalt["category"] == "road-asphalt"
    assert asphalt["quantity"]["input_value"] == 2544
    assert asphalt["quantity"]["input_unit"] == "tonne"
    assert asphalt["factor"]["numerator"]["input_value"] == 52.18
    assert "2.4" in asphalt["evidence_ref"]
    assert "mineralproducts.org" in asphalt["factor"]["source_url"]
    steel, hdpe = example["rows"][2:]
    assert steel["category"] == "steel"
    assert steel["quantity"]["input_value"] == 80
    assert steel["factor"] is None
    assert hdpe["category"] == "hdpe-pipe"
    assert hdpe["quantity"]["input_value"] == 3300
    assert hdpe["factor"] is None
    result = client.post("/api/v1/carbon/calculate", json=example)
    assert result.status_code == 200, result.text
    assert result.json()["total_emission"]["input_value"] == pytest.approx(371_533.92)
    assert result.json()["rows"][1]["emission"]["input_value"] == pytest.approx(132_745.92)
    assert len(result.json()["rows"]) == 2
    assert result.json()["pending_row_ids"] == [steel["row_id"], hdpe["row_id"]]
    pathways = result.json()["credit_readiness"]
    assert len(pathways) == 4
    assert pathways[0]["methodology_id"] == "T-VER-P-METH-14-02"
    assert pathways[1]["methodology_id"] is None
    assert pathways[2]["reason_code"] == "steel_purchase_has_no_direct_method"
    assert pathways[3]["methodology_id"] == "T-VER-S-METH-09-06"
    assert pathways[3]["methodology_version"] == "02"
    assert all(item["status"] != "potentially_applicable" for item in pathways)
    assert "partial_total_missing_emission_factors" in result.json()["warnings"]
    asphalt_trace = result.json()["rows"][1]["trace"]
    assert asphalt_trace["operands"]["factor_denominator"]["input_unit"] == "tonne"
    assert result.json()["rows"][0]["trace"]["operands"]["activity_quantity"]["input_value"] == 891
    assert result.json()["tver"] is None


def test_pending_materials_roundtrip_in_revisions_and_exports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CIVIL_CARBON_DB_PATH", str(tmp_path / "carbon.sqlite3"))
    client = TestClient(app)
    example = client.get("/api/v1/carbon/examples/kiakkai").json()
    saved = client.post("/api/v1/carbon/projects", json=example)
    assert saved.status_code == 201, saved.text
    revision = saved.json()
    assert revision["result"]["pending_row_ids"] == [
        example["rows"][2]["row_id"], example["rows"][3]["row_id"]
    ]
    project_id = revision["project_id"]
    for file_format in ("docx", "xlsx", "pdf"):
        response = client.get(
            f"/api/v1/carbon/projects/{project_id}/revisions/1/export/{file_format}?locale=en-US"
        )
        assert response.status_code == 200, response.text
        if file_format != "pdf":
            with ZipFile(BytesIO(response.content)) as archive:
                xml = b" ".join(
                    archive.read(name) for name in archive.namelist() if name.endswith(".xml")
                )
            assert b"Pending data" in xml
            assert b"hdpe-pipe" in xml
            assert b"steel" in xml
            assert b"CreditScreen" in xml or b"credit pathway screening" in xml.lower()


def test_csv_pending_factor_requires_missing_data_explanation() -> None:
    client = TestClient(app)
    header = (
        "row_id,item_name,category,stage,quantity_kind,quantity_value,quantity_unit,"
        "factor_numerator_value,factor_numerator_unit,factor_denominator_value,"
        "factor_denominator_unit,source_name,source_version,evidence_ref\n"
    )
    pending = "hdpe,HDPE pipe,hdpe-pipe,A1-A3,length,3300,meter,,,,,,,Needs SDR and EPD\n"
    response = client.post(
        "/api/v1/carbon/import-csv",
        files={"file": ("boq.csv", (header + pending).encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json()[0]["factor"] is None
    assert response.json()[0]["quantity"]["input_value"] == 3300
    invalid = "hdpe,HDPE pipe,hdpe-pipe,A1-A3,length,3300,meter,5,,,,,,Needs SDR\n"
    response = client.post(
        "/api/v1/carbon/import-csv",
        files={"file": ("boq.csv", (header + invalid).encode(), "text/csv")},
    )
    assert response.status_code == 422
