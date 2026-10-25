# Carbon Research Studio — MVP

เว็บแอปวิจัยสำหรับประเมินคาร์บอนจาก BOQ/กิจกรรมก่อสร้างของถนน สะพาน อาคาร และงานสถาปัตย์/ตกแต่งภายใน รองรับช่วง A1–A3, A4, A5, บันทึกโครงการเป็น revision ที่แก้ย้อนหลังไม่ได้, เปรียบเทียบผลรวมระหว่าง revision และส่งออก PDF/XLSX/DOCX ตาม revision ที่เลือก

## เริ่มใช้ในเครื่องพัฒนา

ใช้ Python environment ตาม `requirements.lock` จากราก repository:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\packages"
npm --prefix apps/carbon_research_web ci
npm --prefix apps/carbon_research_web run build
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8125
```

เปิด `http://127.0.0.1:8125/carbon/` ใน browser ส่วน API อยู่ที่ `/api/v1/carbon` และ schema ที่ `/docs` ข้อมูลบันทึกใน `instance/carbon_research.sqlite3` ตามค่าเริ่มต้น เปลี่ยนตำแหน่งได้ด้วย `CIVIL_CARBON_DB_PATH` หากเครื่องไม่มีฟอนต์ Tahoma ให้ตั้ง `CIVIL_CARBON_PDF_FONT` เป็น path ของฟอนต์ TTF ที่รองรับภาษาไทยก่อนส่งออก PDF ภาษาไทย

เริ่มทดลองได้จากปุ่ม **โหลดตัวอย่าง BOQ เกียกกาย** ในแท็บ **ข้อมูลนำเข้า** แล้วเปิดแท็บ **ผลประเมิน** เพื่อดูสูตร ตัวตั้ง/ตัวหาร หน่วย และที่มาของรายการคอนกรีตฐานราก FB-2 กับแอสฟัลต์ รวมถึงรายการฝาตะแกรงเหล็กและท่อ HDPE ที่รอข้อมูลตาม [worked example](../../docs/phase-0/KIAKKAI_BOQ_WORKED_EXAMPLE_TH.md) ผลรวมเป็นเพียงบางส่วน ไม่ใช่ผลรวมทั้งโครงการ

## ข้อมูลและสูตร

- [boq_template.csv](boq_template.csv) เป็นหัวตารางสำหรับนำเข้า UTF-8 CSV; แต่ละแถวต้องมี `row_id` ไม่ซ้ำและข้อมูล factor พร้อม `source_name`/`source_version` แนะนำให้ใส่ `source_url` และ `evidence_ref` ด้วย
- ปริมาณทุกค่าระบุ `quantity_kind`, ตัวเลข, หน่วย และ factor ในรูป emission numerator ต่อ denominator ที่มีชนิดปริมาณตรงกัน ตัวอย่าง `5 meter ** 3 × 250 kilogram / 1 meter ** 3 = 1,250 kgCO₂e` ตัวเลขนี้เป็น **ตัวอย่างสูตร** ไม่ใช่ factor ที่แอปให้ใช้จริง
- แอปไม่มีฐาน emission factor สำเร็จรูป ผู้วิจัยต้องเลือก factor ที่เหมาะกับสถานที่ ปี ผลิตภัณฑ์ และขอบเขตการศึกษาพร้อมหลักฐานเอง การเปลี่ยน factor หรือ BOQ ต้องบันทึก revision ใหม่เพื่อรักษาผลเดิม
- ผลตอบกลับ API มี `kgCO₂e` ตามแถว/ช่วง/หมวด/โครงการและ calculation trace ซึ่งบันทึกสูตร ตัวตั้ง ตัวหาร แหล่งที่มา เวอร์ชัน และรหัสข้อมูล SHA-256 ใน revision
- T-VER ใน MVP มีการคัดกรองเงื่อนไขเบื้องต้นสำหรับ `T-VER-S-METH-06-15` v01 และ `T-VER-P-METH-14-02` v01 พร้อมตรวจเลขรวม `BE−PE−LE` เท่านั้น ค่า BE/PE/LE ต้องมาจากสมการย่อยและหลักฐานของระเบียบวิธีที่เกี่ยวข้อง การประเมินคาร์บอนฝังตัว A1–A5 ไม่สร้างคาร์บอนเครดิตโดยตัวมันเอง ผล T-VER ทุกกรณีมีสถานะ `estimate_not_issued`

## ขอบเขตการใช้งาน

MVP นี้ใช้สำหรับวิจัยและทดสอบในเครื่องพัฒนา API ปัจจุบันยังไม่มี authentication/RBAC และใช้ SQLite ในเครื่อง ห้ามเปิด service นี้ให้บุคคลทั่วไปหรือใส่ข้อมูลลูกค้าจริงก่อนเพิ่มระบบสิทธิ์ การสำรองข้อมูล audit และฐานข้อมูล production การยืนยัน factor, system boundary, การคำนวณตามระเบียบวิธี, additionality, สิทธิ์ในเครดิต และผลทางวิศวกรรมต้องผ่านผู้เชี่ยวชาญมนุษย์อิสระก่อนใช้ยื่นรับรองหรือทำธุรกรรม

## ตรวจงาน

```powershell
$env:PYTHONPATH = "$PWD;$PWD\packages"
python -m pytest -q tests/integration/test_carbon_research_api.py
python -m ruff check apps/api/carbon.py apps/api/carbon_store.py packages/civil_api_contracts/carbon.py packages/civil_codes/carbon packages/civil_i18n/carbon.py packages/civil_reporting/carbon.py packages/civil_workflows/carbon tests/integration/test_carbon_research_api.py
npm --prefix apps/carbon_research_web run build
```

Task contract อยู่ที่ `docs/phase-0/CARBON_MVP_TASK_CONTRACT_TH.md`
