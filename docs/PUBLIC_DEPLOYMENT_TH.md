# แผนเผยแพร่ Construction Carbon Research

## สถานะปัจจุบัน

- Repository เป็น Public และมี CI บน Pull Request แต่ตัวเว็บยังเป็นแอปพัฒนาในเครื่องที่ใช้ React, FastAPI และ SQLite
- GitHub Pages ให้บริการไฟล์ static และไม่รัน Python/FastAPI หรือฐานข้อมูล จึงนำไฟล์ `dist/` ปัจจุบันขึ้น Pages ตรง ๆ ไม่ได้: หน้าเว็บเรียก `/api/v1/carbon/*` สำหรับคำนวณ เปิดโครงการ นำเข้า และส่งออก
- API ปัจจุบันไม่มีการยืนยันตัวตน: `GET /projects` เปิดรายการและข้อมูลโครงการทั้งหมด ส่วน `POST /projects` และ `/revisions` เขียนข้อมูลได้ ไม่ควรเปิด API นี้สู่สาธารณะ

## ทางเลือกการเผยแพร่

### A. ตัวอย่างวิจัยบน GitHub Pages

สร้างหน้า static ที่อ่านผลตัวอย่าง BOQ และหลักการคำนวณที่สร้างจาก engine ใน CI โดยไม่เรียก API หรือเปิดให้ส่งข้อมูลโครงการขึ้น server ระบุชัดว่าเป็นผลบางส่วนเพื่อการวิจัย และมีลิงก์ source/revision การเผยแพร่นี้ไม่ใช่แอปเต็ม: กรอก BOQ, บันทึก project/revision และ export แบบปัจจุบันไม่ได้

### B. แอปเต็มสำหรับผู้ใช้ภายนอก

ใช้ GitHub สำหรับ source, PR และ CI; โฮสต์ frontend/API บนบริการที่รัน Python ได้ และใช้ฐานข้อมูลที่มี persistence, backup และการแยกข้อมูลผู้ใช้ ก่อนเผยแพร่ต้องทำอย่างน้อย:

1. ยืนยันตัวตน, RBAC และ tenant isolation สำหรับ list/get/create/revise/export
2. ย้าย SQLite ไป PostgreSQL พร้อม migration, backup และ restore test
3. จำกัดขนาด request, rate limit, CORS/HTTPS และจัดการ secrets ในระบบโฮสต์
4. ทดสอบ security, accessibility, error handling และ export ที่ URL จริง
5. ให้ผู้ตรวจอิสระด้าน LCA/วิศวกรรมตรวจ methodology mapping, EF และ worked example ก่อนใช้ผลภายนอก

## เกณฑ์ตรวจหลัง deploy

- URL สาธารณะเปิดได้ผ่าน HTTPS และ asset path ถูกต้อง
- ไม่มีการเรียก API ที่ยังไม่ได้ deploy หรือเปิดข้อมูลโครงการข้ามผู้ใช้
- ผลตัวอย่างยังเป็นผลบางส่วน 371.53392 tCO₂e จากคอนกรีตและแอสฟัลต์เท่านั้น; เหล็ก/HDPE แสดงรอข้อมูล
- คำอธิบายว่า embodied carbon ต่างจากคาร์บอนเครดิตและสถานะการทวนสอบยังปรากฏ
- ถ้าใช้งานแอปเต็ม: สร้าง/เปิด/แก้ revision, นำเข้า, คำนวณ trace และ export PDF/XLSX/DOCX ผ่านการตรวจที่ production URL
- มีวิธี rollback ไปยัง commit ก่อนหน้าและตรวจว่าข้อมูลไม่สูญหาย

อ้างอิง: [GitHub Pages — Creating a site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
