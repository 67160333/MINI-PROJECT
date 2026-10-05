"""
สร้างไฟล์ SQL จากข้อมูลใน data/ → sql/thangruam.sql (ตาราง + ข้อมูล)
ใช้กับ MySQL 8 / MariaDB 10.2 ขึ้นไป (เช่น XAMPP) นำเข้าผ่าน phpMyAdmin ได้
รัน:  python scripts/export_sql.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sql" / "thangruam.sql"
ENGINE = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"

SCHEMA = f"""-- ถังรวม: ข้อมูลร้านแก๊ส LPG ที่ขายหลายแบรนด์
-- วิชา Business Idea Creation
-- ข้อมูลร้านเป็นข้อมูลจำลอง (สร้างด้วย scripts/generate_data.py) ยกเว้นตาราง market_share
-- ช่วงข้อมูล 2026-04-01 ถึง 2026-09-30
-- ใช้กับ MySQL 8 / MariaDB 10.2+

SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS thangruam CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE thangruam;

DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS brands;
DROP TABLE IF EXISTS market_share;

CREATE TABLE brands (
  brand          VARCHAR(5)   NOT NULL PRIMARY KEY,  -- WP, PTT, UNQ, SGP
  brand_th       VARCHAR(50)  NOT NULL,
  share_in_shop  DECIMAL(4,2) NOT NULL               -- สัดส่วนลูกค้าในร้าน (สมมติฐาน)
) {ENGINE};

CREATE TABLE products (
  size_kg         INT NOT NULL PRIMARY KEY,          -- ขนาดถัง 4 / 15 / 48 กก.
  gas_price       INT NOT NULL,                      -- ราคาแก๊สต่อถัง (ค่าประมาณ)
  cylinder_value  INT NOT NULL                       -- มูลค่าถัง / ค่ามัดจำ (ค่าประมาณ)
) {ENGINE};

CREATE TABLE customers (
  customer_id         VARCHAR(5)   NOT NULL PRIMARY KEY,
  name                VARCHAR(150) NOT NULL,         -- ชื่อสมมติ
  segment             VARCHAR(20)  NOT NULL,         -- household / restaurant / vendor
  brand               VARCHAR(5)   NOT NULL,
  size_kg             INT          NOT NULL,
  cylinders_at_start  INT          NOT NULL,         -- ถังที่ถืออยู่ ณ 2026-04-01
  first_seen          DATE         NULL,             -- NULL = ลูกค้าเดิมก่อน 2026-04-01
  credit_customer     CHAR(1)      NOT NULL,         -- Y = ซื้อเชื่อ
  FOREIGN KEY (brand)   REFERENCES brands(brand),
  FOREIGN KEY (size_kg) REFERENCES products(size_kg)
) {ENGINE};

CREATE TABLE transactions (
  txn_id          VARCHAR(8)  NOT NULL PRIMARY KEY,
  txn_date        DATE        NOT NULL,
  txn_time        TIME        NOT NULL,
  customer_id     VARCHAR(5)  NOT NULL,
  brand           VARCHAR(5)  NOT NULL,
  size_kg         INT         NOT NULL,
  txn_type        VARCHAR(20) NOT NULL,              -- exchange / new_cylinder / return_cylinder
  full_out        INT         NOT NULL,              -- ถังเต็มที่ส่งออก
  empty_in        INT         NOT NULL,              -- ถังเปล่าที่ได้คืน
  gas_amount      INT         NOT NULL,              -- ค่าแก๊ส (บาท)
  deposit_amount  INT         NOT NULL,              -- มัดจำ (+ รับ / - คืน)
  payment_method  VARCHAR(10) NOT NULL,              -- cash / transfer / credit
  paid_amount     INT         NOT NULL,
  channel         VARCHAR(10) NOT NULL,              -- phone / line / walk_in
  delivery        VARCHAR(10) NOT NULL,              -- delivery / pickup
  driver          VARCHAR(20) NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  INDEX idx_txn_date (txn_date),
  INDEX idx_txn_customer (customer_id)
) {ENGINE};

CREATE TABLE payments (
  payment_id   VARCHAR(6)  NOT NULL PRIMARY KEY,
  pay_date     DATE        NOT NULL,
  customer_id  VARCHAR(5)  NOT NULL,
  amount       INT         NOT NULL,
  method       VARCHAR(10) NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) {ENGINE};

CREATE TABLE market_share (
  company           VARCHAR(10)  NOT NULL PRIMARY KEY,
  company_th        VARCHAR(50)  NOT NULL,
  market_share_pct  DECIMAL(4,1) NOT NULL,
  source            VARCHAR(255) NOT NULL
) {ENGINE};
"""

SOURCE = ("กรมธุรกิจพลังงาน Q2/2568 อ้างในรายงาน LH Bank ต.ค. 2568; "
          "OTHERS = 100 - ผลรวม 5 รายแรก")


def read(p):
    with open(ROOT / p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def inserts(table, cols, rows, batch=200):
    out = []
    for i in range(0, len(rows), batch):
        vals = ",\n".join("(" + ", ".join(q(r[c]) for c in cols) + ")" for r in rows[i:i + batch])
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n{vals};")
    return "\n\n".join(out)


def main():
    OUT.parent.mkdir(exist_ok=True)
    brands = [dict(r, share_in_shop=float(r["share_in_shop"])) for r in read("data/raw/brands.csv")]
    products = [{k: int(v) for k, v in r.items()} for r in read("data/raw/products.csv")]
    cust = []
    for r in read("data/raw/customers.csv"):
        r["size_kg"], r["cylinders_at_start"] = int(r["size_kg"]), int(r["cylinders_at_start"])
        r["first_seen"] = None if r["first_seen"].startswith("ก่อน") else r["first_seen"]
        cust.append(r)
    tx = []
    for r in read("data/raw/transactions.csv"):
        for k in ("size_kg", "full_out", "empty_in", "gas_amount", "deposit_amount", "paid_amount"):
            r[k] = int(r[k])
        r["txn_date"], r["txn_time"] = r.pop("date"), r.pop("time") + ":00"
        r["driver"] = r["driver"] or None
        tx.append(r)
    pay = [dict(r, amount=int(r["amount"]), pay_date=r["date"]) for r in read("data/raw/payments.csv")]
    mk = [dict(r, market_share_pct=float(r["market_share_pct"]), source=SOURCE)
          for r in read("data/reference/market_share_lpg_q2_2568.csv")]

    parts = [SCHEMA, "-- ---------- ข้อมูล ----------",
             inserts("brands", ["brand", "brand_th", "share_in_shop"], brands),
             inserts("products", ["size_kg", "gas_price", "cylinder_value"], products),
             inserts("customers", ["customer_id", "name", "segment", "brand", "size_kg",
                                   "cylinders_at_start", "first_seen", "credit_customer"], cust),
             inserts("transactions", ["txn_id", "txn_date", "txn_time", "customer_id", "brand", "size_kg",
                                      "txn_type", "full_out", "empty_in", "gas_amount", "deposit_amount",
                                      "payment_method", "paid_amount", "channel", "delivery", "driver"], tx),
             inserts("payments", ["payment_id", "pay_date", "customer_id", "amount", "method"], pay),
             inserts("market_share", ["company", "company_th", "market_share_pct", "source"], mk)]
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(OUT.relative_to(ROOT), f"brands={len(brands)} products={len(products)} customers={len(cust)} "
          f"transactions={len(tx)} payments={len(pay)} market_share={len(mk)}")


if __name__ == "__main__":
    main()
