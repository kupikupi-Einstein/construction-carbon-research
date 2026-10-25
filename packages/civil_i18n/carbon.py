"""Thai and English labels for the carbon research UI and exports."""

from __future__ import annotations

CARBON_CATALOG: dict[str, dict[str, str]] = {
    "title": {
        "th-TH": "รายงานการประเมินคาร์บอนงานก่อสร้าง",
        "en-US": "Construction Carbon Research Report",
    },
    "draft": {
        "th-TH": "ผลประเมินเบื้องต้น ยังไม่ผ่านการทวนสอบ",
        "en-US": "Research estimate — not independently verified",
    },
    "partial_total": {
        "th-TH": "ผลรวมบางส่วน: มีรายการรอข้อมูลตัวคูณการปล่อย",
        "en-US": "Partial total: some rows await emission factors",
    },
    "pending_factor": {
        "th-TH": "รอข้อมูล — ไม่รวมในผลรวม",
        "en-US": "Pending data — excluded from total",
    },
    "credit_readiness": {
        "th-TH": "คัดกรองแนวทางคาร์บอนเครดิตจาก BOQ (ยังไม่ใช่เครดิต)",
        "en-US": "Credit pathway screening from BOQ (not issued credits)",
    },
    "separate_activity_required": {
        "th-TH": "ต้องมีกิจกรรมลดการปล่อยแยกจากการซื้อวัสดุ",
        "en-US": "A reduction activity separate from material purchase is required",
    },
    "no_direct_material_method": {
        "th-TH": "ไม่พบระเบียบวิธีให้เครดิตโดยตรงจากการซื้อวัสดุ",
        "en-US": "No direct credit method identified for material purchase",
    },
    "credit_concrete_ccu_activity_required": {
        "th-TH": "ต้องพิสูจน์การดักจับและใช้ CO2 ในการผลิตคอนกรีต",
        "en-US": "Evidence of captured CO2 use in concrete production is required",
    },
    "credit_plastic_recycling_activity_required": {
        "th-TH": "ต้องพิสูจน์กิจกรรมคัดแยกและรีไซเคิลพลาสติกจากขยะ",
        "en-US": "Plastic recovery and recycling from waste must be demonstrated",
    },
    "credit_steel_purchase_has_no_direct_method": {
        "th-TH": "ซื้อเหล็กไม่เกิดเครดิตโดยตรง ต้องระบุกิจกรรมลดการปล่อยที่ทำจริง",
        "en-US": "Steel purchase gives no direct credit; identify a reduction activity",
    },
    "credit_material_purchase_has_no_direct_method": {
        "th-TH": "ซื้อวัสดุไม่เกิดเครดิตโดยตรง ต้องระบุกิจกรรมลดการปล่อยที่ทำจริง",
        "en-US": "Material purchase gives no direct credit; identify a reduction activity",
    },
    "project": {"th-TH": "โครงการ", "en-US": "Project"},
    "asset_type": {"th-TH": "ประเภทงาน", "en-US": "Asset type"},
    "revision": {"th-TH": "ฉบับแก้ไข", "en-US": "Revision"},
    "created_at": {"th-TH": "วันที่คำนวณ", "en-US": "Calculated at"},
    "hash": {"th-TH": "รหัสข้อมูลนำเข้า", "en-US": "Input snapshot hash"},
    "total": {"th-TH": "ผลรวม A1–A5", "en-US": "Total A1–A5"},
    "by_stage": {"th-TH": "ผลตามช่วงวงจรชีวิต", "en-US": "Life cycle stages"},
    "activities": {"th-TH": "รายการกิจกรรมและวัสดุ", "en-US": "Activities and materials"},
    "trace": {"th-TH": "ลำดับการคำนวณ", "en-US": "Calculation trace"},
    "method": {"th-TH": "ระเบียบวิธี", "en-US": "Methodology"},
    "screening": {"th-TH": "ผลคัดกรอง T-VER", "en-US": "T-VER screening"},
    "credit_notice": {
        "th-TH": "ยังไม่มีการออกคาร์บอนเครดิต",
        "en-US": "No carbon credits have been issued",
    },
    "item": {"th-TH": "รายการ", "en-US": "Item"},
    "category": {"th-TH": "หมวด", "en-US": "Category"},
    "stage": {"th-TH": "ช่วง", "en-US": "Stage"},
    "quantity": {"th-TH": "ปริมาณ", "en-US": "Quantity"},
    "factor": {"th-TH": "ตัวคูณการปล่อย", "en-US": "Emission factor"},
    "source": {"th-TH": "แหล่งข้อมูล", "en-US": "Source"},
    "source_url": {"th-TH": "ลิงก์แหล่งข้อมูล", "en-US": "Source URL"},
    "quantity_kind": {"th-TH": "ชนิดปริมาณ", "en-US": "Quantity kind"},
    "unit": {"th-TH": "หน่วย", "en-US": "Unit"},
    "factor_denominator": {"th-TH": "ปริมาณฐานตัวคูณ", "en-US": "Factor denominator"},
    "operands": {"th-TH": "ค่าที่ใช้คำนวณ", "en-US": "Operands"},
    "component_evidence": {"th-TH": "หลักฐานสมการย่อย", "en-US": "Component evidence"},
    "additionality_evidence": {"th-TH": "หลักฐาน additionality", "en-US": "Additionality evidence"},
    "credit_rights_evidence": {"th-TH": "หลักฐานสิทธิ์เครดิต", "en-US": "Credit rights evidence"},
    "monitoring_plan": {"th-TH": "แผนติดตามผล", "en-US": "Monitoring plan"},
    "findings": {"th-TH": "ประเด็นที่ต้องตรวจต่อ", "en-US": "Items for further review"},
    "emission": {"th-TH": "ผลปล่อย", "en-US": "Emissions"},
    "evidence": {"th-TH": "หลักฐาน", "en-US": "Evidence"},
    "formula": {"th-TH": "สมการ", "en-US": "Formula"},
    "reference": {"th-TH": "อ้างอิง", "en-US": "Reference"},
    "estimated_reduction": {"th-TH": "ผลลดประมาณการ", "en-US": "Estimated reduction"},
    "reviewer": {"th-TH": "ผู้ตรวจทาน", "en-US": "Reviewer"},
    "not_assigned": {"th-TH": "ยังไม่กำหนด", "en-US": "Not assigned"},
}


def carbon_text(key: str, locale: str) -> str:
    if locale not in ("th-TH", "en-US"):
        raise ValueError("unsupported report locale")
    try:
        return CARBON_CATALOG[key][locale]
    except KeyError as error:
        raise KeyError(f"missing carbon translation: {key}/{locale}") from error
