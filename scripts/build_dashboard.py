"""
อ่าน CSV ใน data/ แล้วฝังลงใน dashboard/template.html → dashboard/index.html
ผลลัพธ์เป็นไฟล์ HTML ไฟล์เดียว เปิดด้วยเบราว์เซอร์ได้ทันที ไม่ต้องต่ออินเทอร์เน็ต
รัน:  python scripts/build_dashboard.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
START, ASOF = "2026-04-01", "2026-09-30"


def read(path, ints=(), floats=()):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ints:
            r[k] = int(r[k])
        for k in floats:
            r[k] = float(r[k])
    return rows


def main():
    tx = read(RAW / "transactions.csv",
              ints=("size_kg", "full_out", "empty_in", "gas_amount", "deposit_amount", "paid_amount"))
    cols = ["date", "time", "customer_id", "brand", "size_kg", "txn_type", "full_out", "empty_in",
            "gas_amount", "payment_method", "delivery"]
    data = {
        "start": START, "asof": ASOF,
        "brands": read(RAW / "brands.csv", floats=("share_in_shop",)),
        "products": read(RAW / "products.csv", ints=("size_kg", "gas_price", "cylinder_value")),
        "customers": read(RAW / "customers.csv", ints=("size_kg", "cylinders_at_start")),
        "payments": read(RAW / "payments.csv", ints=("amount",)),
        "market": read(REF / "market_share_lpg_q2_2568.csv", floats=("market_share_pct",)),
        "team": read(ROOT / "team.csv"),
        "txCols": cols,
        "tx": [[t[c] for c in cols] for t in tx],
    }
    tpl = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = tpl.replace("/*__DATA__*/null", payload)
    (ROOT / "dashboard" / "index.html").write_text(out, encoding="utf-8")
    print(f"dashboard/index.html  ({len(out)/1024:.0f} KB, {len(tx)} transactions)")


if __name__ == "__main__":
    main()
