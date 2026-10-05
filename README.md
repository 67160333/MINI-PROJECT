# ถังรวม: Dashboard ร้านแก๊ส LPG ที่ขายหลายแบรนด์

รายวิชา Business Idea Creation

| ชื่อ-นามสกุล | รหัสนักศึกษา |
|---|---|
| ดุลยุตม์ เลื่องสุนทร | 67160333 |

รายงานสรุป: [REPORT.md](REPORT.md)

Dashboard ของบริษัท ถังรวม (ชื่อชั่วคราว) ระบบหลังร้านสำหรับร้านแก๊ส LPG ที่ขายหลายแบรนด์
ใช้ข้อมูล 6 เดือนของร้านแก๊ส 1 ร้านที่ขาย 4 แบรนด์ เพื่อแสดงว่าร้านแบบนี้ต้องการระบบอะไร

**เปิดดู Dashboard:** ดับเบิลคลิก `dashboard/index.html` (ไฟล์เดียว ไม่ต้องติดตั้งอะไร ไม่ต้องต่ออินเทอร์เน็ต)
หรือดูออนไลน์ที่ https://67160333.github.io/MINI-PROJECT/dashboard/

## หัวข้อใน Dashboard

1. ภาพรวมตลาด LPG (ข้อมูลจริง)
2. ยอดขายแยกแบรนด์
3. ออเดอร์รายวันและช่วงเวลา
4. ถังที่อยู่กับลูกค้า และลูกค้าที่ยังไม่คืนถังเปล่า
5. ลูกค้าที่หยุดสั่งแต่ยังถือถังของร้าน
6. ลูกหนี้แยกตามอายุหนี้
7. สรุป

เลือกแบรนด์ได้จากเมนูด้านบน (ยกเว้นข้อ 1)

## ข้อมูลที่ใช้

ค้นใน Kaggle และแหล่งข้อมูลเปิดแล้ว ไม่พบข้อมูลรายการขายของร้านแก๊ส
(พบเพียงราคาแก๊สและทะเบียนผู้ค้าของต่างประเทศ) จึงสร้างข้อมูลจำลองขึ้นจากพฤติกรรมของธุรกิจ

| ไฟล์ | ประเภท | คำอธิบาย |
|---|---|---|
| `data/ข้อมูลที่ใช้_ถังรวม.xlsx` | รวม | ทุกตารางในไฟล์เดียว พร้อมชีตอธิบายและชีตสรุปตัวเลข |
| `sql/thangruam.sql` | รวม | สร้างฐานข้อมูล `thangruam` พร้อมข้อมูลทั้งหมด (MySQL 8 / MariaDB 10.2+) |
| `sql/queries.sql` | | คำสั่ง SQL ที่ใช้คำนวณตัวเลขแต่ละข้อใน Dashboard |
| `data/reference/market_share_lpg_q2_2568.csv` | จริง | ส่วนแบ่งตลาด LPG ของกรมธุรกิจพลังงาน Q2/2568 อ้างใน [รายงาน LH Bank ต.ค. 2568](https://www.lhbank.co.th/getattachment/031004c9-34dc-4c54-b374-4928bb44246c/economic-analysis-Industry-Outlook-2025-Natural-Gas_Oct_2025) แถว "อื่น ๆ" = 100 ลบผลรวม 5 รายแรก |
| `data/raw/customers.csv` | จำลอง | ลูกค้า 220 ราย ชื่อสมมติทั้งหมด |
| `data/raw/transactions.csv` | จำลอง | รายการแลกถัง ซื้อถังใหม่ คืนถัง 2,344 รายการ |
| `data/raw/payments.csv` | จำลอง | การชำระเงินของลูกค้าเครดิต 100 รายการ |
| `data/raw/products.csv` | สมมติฐาน | ราคาแก๊สและมูลค่าถังโดยประมาณ ไม่ใช่ราคาประกาศ |
| `data/raw/brands.csv` | สมมติฐาน | สัดส่วนแบรนด์ในร้านตัวอย่าง |
| `data/bi/` | | ตารางที่คำนวณไว้แล้ว สำหรับนำเข้า Power BI หรือ Excel |

ความหมายของทุกคอลัมน์อยู่ใน [data/DATA_DICTIONARY.md](data/DATA_DICTIONARY.md)

**นำเข้า SQL ด้วย XAMPP:** Start MySQL แล้วเปิด http://localhost/phpmyadmin ไปที่ Import เลือก `sql/thangruam.sql`

**ข้อจำกัด:** ตัวเลขข้อ 2 ถึง 6 มาจากข้อมูลจำลอง แสดงรูปแบบของปัญหา ไม่ใช่ขนาดของปัญหาในร้านจริง
และยังไม่ได้สอบถามว่าร้านแก๊สยินดีจ่ายค่าระบบเดือนละเท่าไร

## สร้างข้อมูลและ Dashboard ใหม่

ใช้ Python 3.8 ขึ้นไป

```bash
python scripts/generate_data.py      # สร้าง data/raw/*.csv (ผลเหมือนเดิมทุกครั้ง)
python scripts/build_dashboard.py    # สร้าง dashboard/index.html
python scripts/build_bi_tables.py    # สร้าง data/bi/
python scripts/export_excel.py       # สร้างไฟล์ Excel (ต้องมี openpyxl)
python scripts/export_sql.py         # สร้างไฟล์ SQL
```

ปรับสมมติฐาน (จำนวนลูกค้า สัดส่วนแบรนด์ ราคา) ได้ที่ส่วนบนของ `scripts/generate_data.py`
แก้รายชื่อสมาชิกที่ `team.csv` แล้วรัน `build_dashboard.py` ใหม่

## โครงสร้าง

```
├── README.md
├── REPORT.md                 รายงานสรุป
├── team.csv                  รายชื่อสมาชิก
├── dashboard/
│   ├── index.html            Dashboard
│   └── template.html         ต้นแบบก่อนใส่ข้อมูล
├── data/
│   ├── ข้อมูลที่ใช้_ถังรวม.xlsx
│   ├── DATA_DICTIONARY.md
│   ├── raw/                  ข้อมูลจำลอง
│   ├── reference/            ข้อมูลจริง
│   └── bi/                   ตารางสำหรับ BI
├── sql/
│   ├── thangruam.sql
│   └── queries.sql
└── scripts/
```
