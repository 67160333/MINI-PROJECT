"""
แปลงข้อมูลใน data/raw/ เป็นตารางพร้อมใช้ใน BI (Power BI / Excel / Looker Studio) → data/bi/
คำนวณตัวชี้วัดที่ซับซ้อนไว้ล่วงหน้า (ยอดถัง ถังเกินมัดจำ ถังหลับ อายุหนี้ FIFO)
เพื่อให้ใน BI ใช้แค่ Sum/Count ไม่ต้องเขียน DAX
รัน:  python scripts/build_bi_tables.py
"""
import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "bi"
ASOF = dt.date(2026, 9, 30)
DORMANT_DAYS = 60
MONTH_TH = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
SEG_TH = {"household": "บ้าน", "restaurant": "ร้านอาหาร", "vendor": "รถเข็น/แผงลอย"}


def read(name):
    with open(RAW / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(name, rows, fields):
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cust = read("customers.csv")
    tx = read("transactions.csv")
    pay = read("payments.csv")
    brand_th = {b["brand"]: b["brand_th"] for b in read("brands.csv")}
    cval = {int(p["size_kg"]): int(p["cylinder_value"]) for p in read("products.csv")}

    # ---- transactions (enriched)
    tx_rows = []
    for t in tx:
        d = dt.date.fromisoformat(t["date"])
        fo, ei = int(t["full_out"]), int(t["empty_in"])
        tx_rows.append(dict(
            txn_id=t["txn_id"], date=t["date"], month_no=d.month, month_th=MONTH_TH[d.month - 1],
            weekday=d.isoweekday(), hour=int(t["time"][:2]), customer_id=t["customer_id"],
            brand=t["brand"], brand_th=brand_th[t["brand"]], size_kg=int(t["size_kg"]), txn_type=t["txn_type"],
            is_order=1 if fo > 0 else 0, full_out=fo, empty_in=ei,
            net_unreturned=(fo - ei) if t["txn_type"] == "exchange" else 0,
            gas_amount=int(t["gas_amount"]), deposit_amount=int(t["deposit_amount"]),
            payment_method=t["payment_method"], channel=t["channel"], delivery=t["delivery"], driver=t["driver"],
        ))
    write("fact_transactions.csv", tx_rows, list(tx_rows[0].keys()))

    # ---- customer summary
    bal, ent, last = defaultdict(int), defaultdict(int), {}
    for c in cust:
        bal[c["customer_id"]] = ent[c["customer_id"]] = int(c["cylinders_at_start"])
    for t in tx:
        cid = t["customer_id"]
        bal[cid] += int(t["full_out"]) - int(t["empty_in"])
        if t["txn_type"] == "new_cylinder":
            ent[cid] += int(t["full_out"])
        if t["txn_type"] == "return_cylinder":
            ent[cid] -= int(t["empty_in"])
        last[cid] = max(last.get(cid, ""), t["date"])

    # FIFO aging
    paid = defaultdict(int)
    for p in pay:
        paid[p["customer_id"]] += int(p["amount"])
    inv = defaultdict(list)
    for t in sorted(tx, key=lambda x: x["date"]):
        if t["payment_method"] == "credit":
            inv[t["customer_id"]].append(t)
    aging_rows, ar, oldest = [], defaultdict(int), {}
    buckets = [("0–30 วัน", 1), ("31–60 วัน", 2), ("61–90 วัน", 3), ("90+ วัน", 4)]
    for cid, lst in inv.items():
        left = paid[cid]
        bsum = defaultdict(int)
        for t in lst:
            amt = int(t["gas_amount"])
            use = min(left, amt)
            left -= use
            rem = amt - use
            if rem > 0:
                age = (ASOF - dt.date.fromisoformat(t["date"])).days
                oldest.setdefault(cid, age)
                bsum[0 if age <= 30 else 1 if age <= 60 else 2 if age <= 90 else 3] += rem
                ar[cid] += rem
        brand = next(c["brand"] for c in cust if c["customer_id"] == cid)
        for i, amt in bsum.items():
            aging_rows.append(dict(customer_id=cid, brand=brand, brand_th=brand_th[brand],
                                   age_bucket=buckets[i][0], bucket_order=buckets[i][1], amount=amt))
    write("fact_ar_aging.csv", aging_rows,
          ["customer_id", "brand", "brand_th", "age_bucket", "bucket_order", "amount"])

    rows = []
    for c in cust:
        cid, size = c["customer_id"], int(c["size_kg"])
        held, extra = bal[cid], max(0, bal[cid] - ent[cid])
        idle = (ASOF - dt.date.fromisoformat(last[cid])).days if cid in last else None
        dormant = 1 if held > 0 and (idle is None or idle > DORMANT_DAYS) else 0
        rows.append(dict(
            customer_id=cid, name=c["name"], segment=c["segment"], segment_th=SEG_TH[c["segment"]],
            brand=c["brand"], brand_th=brand_th[c["brand"]], size_kg=size, credit_customer=c["credit_customer"],
            cylinders_held=held, cylinders_with_deposit=ent[cid], cylinders_extra=extra,
            cylinder_value=cval[size], held_value=held * cval[size], extra_value=extra * cval[size],
            last_order_date=last.get(cid, ""), idle_days="" if idle is None else idle,
            is_dormant=dormant, dormant_cylinders=held * dormant, dormant_value=held * cval[size] * dormant,
            ar_outstanding=ar[cid], ar_oldest_days=oldest.get(cid, ""),
            ar_over_60=1 if oldest.get(cid, 0) > 60 else 0,
        ))
    write("dim_customers.csv", rows, list(rows[0].keys()))

    # ---- market (copy reference with flag)
    with open(ROOT / "data" / "reference" / "market_share_lpg_q2_2568.csv", encoding="utf-8-sig") as f:
        mk = list(csv.DictReader(f))
    for m in mk:
        m["has_brand_app"] = "มีแอปจากแบรนด์" if m["company"] == "PTTOR" else "ไม่มี"
    write("ref_market_share.csv", mk, ["company", "company_th", "market_share_pct", "has_brand_app"])

    print("data/bi/: fact_transactions, dim_customers, fact_ar_aging, ref_market_share")
    s = lambda k: sum(r[k] for r in rows)
    print("check: held", s("cylinders_held"), "extra", s("cylinders_extra"), s("extra_value"),
          "dormant", s("is_dormant"), s("dormant_cylinders"), s("dormant_value"),
          "AR", s("ar_outstanding"), "AR>60", sum(a["amount"] for a in aging_rows if a["bucket_order"] >= 3))


if __name__ == "__main__":
    main()
