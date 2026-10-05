"""
สร้างชุดข้อมูลจำลอง (synthetic) ของร้านแก๊ส LPG ที่ขายหลายแบรนด์ 1 ร้าน
ช่วง 1 เม.ย. 2569 – 30 ก.ย. 2569 (6 เดือน)

ทำไมต้องสร้างเอง:
    ค้น Kaggle และแหล่งข้อมูลเปิดแล้ว ไม่พบข้อมูลระดับ "รายการขายของร้านแก๊ส"
    (มีแค่ราคาแก๊ส/ทะเบียนผู้ค้าในต่างประเทศ) จึงจำลองขึ้นจากพฤติกรรมของธุรกิจจริง
    ตัวเลขที่มาจากแหล่งจริงแยกไว้ใน data/reference/ เท่านั้น

ข้อมูลนี้ไม่ใช่ข้อมูลของร้านใดร้านหนึ่ง ชื่อลูกค้าทั้งหมดเป็นชื่อสมมติ
รันซ้ำได้ผลเหมือนเดิมทุกครั้ง (SEED คงที่)

รัน:  python scripts/generate_data.py
"""
import csv
import datetime as dt
import random
from pathlib import Path

SEED = 2569
START = dt.date(2026, 4, 1)
END = dt.date(2026, 9, 30)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw"

# ---------- สมมติฐานของร้าน (ปรับได้) ----------
# สัดส่วนแบรนด์ในร้านนี้ — ร้านเป็นตัวแทนหลักของ WP แต่ขายแบรนด์อื่นด้วย
# เพราะลูกค้าต้องแลกถังยี่ห้อเดิม ร้านจึงต้องรับทุกยี่ห้อที่ลูกค้าในพื้นที่ใช้
BRANDS = {
    "WP":  ("เวิลด์แก๊ส", 0.38),
    "PTT": ("ปตท.",      0.27),
    "UNQ": ("ยูนิคแก๊ส",  0.20),
    "SGP": ("สยามแก๊ส",   0.15),
}
# ราคาขายแก๊สต่อถัง และมูลค่าถัง (ใช้เป็นค่ามัดจำ) — เป็นค่าประมาณ ไม่ใช่ราคาประกาศ
PRODUCTS = {
    4:  dict(gas_price=160,  cylinder_value=700),
    15: dict(gas_price=423,  cylinder_value=1300),
    48: dict(gas_price=1350, cylinder_value=3800),
}

SEGMENTS = {
    # n ลูกค้า, ขนาดถัง (ขนาด, น้ำหนักสุ่ม), จำนวนถังที่ถือ, รอบสั่ง (วัน), โอกาสเป็นลูกค้าเครดิต
    "household":  dict(n=150, sizes=[(15, .9), (4, .1)],  held=(1, 1), interval=(25, 55), credit_p=0.0),
    "restaurant": dict(n=45,  sizes=[(15, .6), (48, .4)], held=(2, 6), interval=(3, 9),   credit_p=0.45),
    "vendor":     dict(n=25,  sizes=[(15, .7), (4, .3)],  held=(1, 2), interval=(5, 14),  credit_p=0.15),
}
NEW_CUSTOMER_P = 0.12   # สัดส่วนลูกค้าใหม่ที่เริ่มซื้อในช่วงนี้
CHURN_P = 0.13          # สัดส่วนลูกค้าที่หยุดสั่งกลางทาง (ร้านไม่รู้ล่วงหน้า)
CHURN_RETURN_P = 0.30   # ลูกค้าที่หยุดแล้วเอาถังมาคืน
STUCK_EMPTY_P = 0.05    # ส่งถังเต็มแล้วยังไม่ได้ถังเปล่าคืน 1 ใบ
SLOW_PAYER_P = 0.25     # ลูกค้าเครดิตที่จ่ายช้า/จ่ายไม่ครบ

AREAS = ["ซอย 1", "ซอย 3", "ซอย 5", "ซอย 7", "หมู่บ้านสุขใจ", "หมู่บ้านร่มเย็น",
         "ตลาดเช้า", "ตลาดนัดเย็น", "ถนนใหญ่", "ชุมชนริมคลอง"]
FIRST = ["สมชาย", "สมศรี", "วิชัย", "มาลี", "ประยูร", "สุนีย์", "บุญมี", "อรุณ", "จันทร์เพ็ญ",
         "ทองดี", "สายใจ", "ณรงค์", "พรทิพย์", "ชัยวัฒน์", "กาญจนา", "สมพร", "อำนวย", "รัตนา",
         "ไพโรจน์", "วันเพ็ญ", "เกษม", "นงลักษณ์", "สุรชัย", "ปราณี", "ธวัชชัย", "ลำดวน"]
SHOP = ["ข้าวมันไก่", "ก๋วยเตี๋ยว", "ข้าวแกง", "ตามสั่ง", "หมูกระทะ", "ส้มตำไก่ย่าง",
        "โจ๊ก", "ข้าวขาหมู", "ติ่มซำ", "สุกี้", "ผัดไทย", "ราดหน้า"]
VENDOR = ["ลูกชิ้นทอด", "ไข่นกกระทา", "กล้วยทอด", "ปาท่องโก๋", "ไก่ทอด", "หมูปิ้ง", "ขนมครก", "โรตี"]
TITLE = ["เจ๊", "ป้า", "ลุง", "พี่", "น้า"]


def tri(rng, lo, hi):
    return max(1, round(rng.triangular(lo, hi, (lo + hi) / 2)))


def pick_weighted(rng, pairs):
    r, acc = rng.random(), 0.0
    for v, w in pairs:
        acc += w
        if r <= acc:
            return v
    return pairs[-1][0]


def order_time(rng):
    hour = pick_weighted(rng, [(7, .05), (8, .08), (9, .10), (10, .14), (11, .12), (12, .06),
                               (13, .06), (14, .07), (15, .09), (16, .12), (17, .08), (18, .03)])
    return f"{hour:02d}:{rng.randint(0, 59):02d}"


def main():
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    brand_pairs = [(b, w) for b, (_, w) in BRANDS.items()]
    days = (END - START).days

    customers, txns, payments = [], [], []
    cid = 0
    used_names = set()

    for seg, cfg in SEGMENTS.items():
        for _ in range(cfg["n"]):
            cid += 1
            c_id = f"C{cid:03d}"
            while True:
                if seg == "household":
                    name = f"บ้านคุณ{rng.choice(FIRST)}"
                elif seg == "restaurant":
                    name = f"ร้าน{rng.choice(SHOP)}{rng.choice(TITLE)}{rng.choice(FIRST)}"
                else:
                    name = f"รถเข็น{rng.choice(VENDOR)}{rng.choice(TITLE)}{rng.choice(FIRST)}"
                name_full = f"{name} ({rng.choice(AREAS)})"
                if name_full not in used_names:
                    used_names.add(name_full)
                    break
            brand = pick_weighted(rng, brand_pairs)
            size = pick_weighted(rng, cfg["sizes"])
            held = rng.randint(*cfg["held"])
            is_new = rng.random() < NEW_CUSTOMER_P
            join = START + dt.timedelta(days=rng.randint(5, days - 20)) if is_new else None
            credit = rng.random() < cfg["credit_p"]
            churn = None
            if rng.random() < CHURN_P:
                churn = START + dt.timedelta(days=rng.randint(20, days - 30))
                if join and churn <= join + dt.timedelta(days=15):
                    churn = None
            customers.append(dict(
                customer_id=c_id, name=name_full, segment=seg, brand=brand, size_kg=size,
                cylinders_at_start=0 if is_new else held,
                first_seen=(join or START).isoformat() if is_new else "ก่อน 2026-04-01",
                credit_customer="Y" if credit else "N",
                _held=held, _join=join, _churn=churn, _slow=credit and rng.random() < SLOW_PAYER_P,
            ))

    tid = 0

    def add_txn(d, c, ttype, full_out, empty_in, deposit, channel=None, credit_ok=True):
        nonlocal tid
        tid += 1
        p = PRODUCTS[c["size_kg"]]
        gas_amount = full_out * p["gas_price"] if ttype in ("exchange", "new_cylinder") else 0
        if channel is None:
            channel = pick_weighted(rng, [("phone", .50), ("line", .25), ("walk_in", .25)])
        delivery = "pickup" if channel == "walk_in" else "delivery"
        if c["credit_customer"] == "Y" and credit_ok and gas_amount > 0:
            method, paid = "credit", 0
        else:
            # สัดส่วนโอนเพิ่มขึ้นตามเวลา (แนวโน้มจริงของไทย)
            t = (d - START).days / days
            method = "transfer" if rng.random() < 0.35 + 0.20 * t else "cash"
            paid = gas_amount + deposit
        txns.append(dict(
            txn_id=f"T{tid:05d}", date=d.isoformat(), time=order_time(rng),
            customer_id=c["customer_id"], brand=c["brand"], size_kg=c["size_kg"], txn_type=ttype,
            full_out=full_out, empty_in=empty_in, gas_amount=gas_amount, deposit_amount=deposit,
            payment_method=method, paid_amount=paid, channel=channel, delivery=delivery,
            driver=(rng.choice(["คนส่ง A", "คนส่ง B"]) if delivery == "delivery" else ""),
        ))

    for c in customers:
        seg = SEGMENTS[c["segment"]]
        held = c["_held"]
        p = PRODUCTS[c["size_kg"]]
        pending = 0
        if c["_join"]:
            d = c["_join"]
            add_txn(d, c, "new_cylinder", held, 0, held * p["cylinder_value"])
            d += dt.timedelta(days=tri(rng, *seg["interval"]))
        else:
            d = START + dt.timedelta(days=rng.randint(0, seg["interval"][1] - 1))
        while d <= END and (c["_churn"] is None or d < c["_churn"]):
            if d.weekday() == 6 and rng.random() < 0.6:   # วันอาทิตย์ร้านเปิดครึ่งวัน ออเดอร์เลื่อน
                d += dt.timedelta(days=1)
                continue
            if c["segment"] == "restaurant":
                q = max(1, min(held, round(rng.triangular(1, held, held * 0.6))))
            else:
                q = 1
            ret = q
            if pending and rng.random() < 0.5:
                ret += pending
                pending = 0
            if rng.random() < STUCK_EMPTY_P and ret > 0:
                ret -= 1
                pending += 1
            add_txn(d, c, "exchange", q, ret, 0)
            # ร้านอาหารขยายกิจการ ซื้อถังเพิ่ม
            if c["segment"] == "restaurant" and rng.random() < 0.02:
                add_txn(d, c, "new_cylinder", 1, 0, p["cylinder_value"])
                held += 1
            d += dt.timedelta(days=tri(rng, *seg["interval"]))
        # ลูกค้าเลิกแล้วบางรายเอาถังมาคืน
        if c["_churn"] and rng.random() < CHURN_RETURN_P:
            rd = c["_churn"] + dt.timedelta(days=rng.randint(3, 40))
            if rd <= END:
                bal = held + pending
                add_txn(rd, c, "return_cylinder", 0, bal, -bal * p["cylinder_value"],
                        channel="walk_in", credit_ok=False)

    # ---------- ลูกค้าเครดิตชำระเงิน ----------
    txns.sort(key=lambda t: (t["date"], t["time"]))
    for i, t in enumerate(txns, 1):
        t["txn_id"] = f"T{i:05d}"
    pid = 0
    by_c = {}
    for t in txns:
        if t["payment_method"] == "credit":
            by_c.setdefault(t["customer_id"], []).append(t)
    cmap = {c["customer_id"]: c for c in customers}
    for c_id, ts in by_c.items():
        c = cmap[c_id]
        slow = c["_slow"]
        d = dt.date.fromisoformat(ts[0]["date"]) + dt.timedelta(days=rng.randint(25, 35))
        stop = c["_churn"] + dt.timedelta(days=rng.randint(0, 20)) if c["_churn"] else END
        if c["_churn"] and slow:
            stop = c["_churn"]   # หยุดสั่งแล้วหายไปพร้อมหนี้
        paid_total = 0
        while d <= min(END, stop):
            billed = sum(t["gas_amount"] for t in ts if dt.date.fromisoformat(t["date"]) <= d)
            due = billed - paid_total
            if due > 0:
                amt = round(due * (rng.uniform(0.5, 0.8) if slow else 1.0))
                pid += 1
                payments.append(dict(payment_id=f"P{pid:04d}", date=d.isoformat(), customer_id=c_id,
                                     amount=amt, method=rng.choice(["transfer", "transfer", "cash"])))
                paid_total += amt
            d += dt.timedelta(days=rng.randint(45, 75) if slow else rng.randint(25, 35))

    # ---------- เขียนไฟล์ ----------
    def write(name, rows, fields):
        with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r[k] for k in fields})

    write("customers.csv", customers,
          ["customer_id", "name", "segment", "brand", "size_kg", "cylinders_at_start", "first_seen", "credit_customer"])
    write("transactions.csv", txns,
          ["txn_id", "date", "time", "customer_id", "brand", "size_kg", "txn_type", "full_out", "empty_in",
           "gas_amount", "deposit_amount", "payment_method", "paid_amount", "channel", "delivery", "driver"])
    payments.sort(key=lambda p: (p["date"], p["customer_id"]))
    for i, pm in enumerate(payments, 1):
        pm["payment_id"] = f"P{i:04d}"
    write("payments.csv", payments, ["payment_id", "date", "customer_id", "amount", "method"])
    prods = [dict(size_kg=s, gas_price=v["gas_price"], cylinder_value=v["cylinder_value"]) for s, v in PRODUCTS.items()]
    write("products.csv", prods, ["size_kg", "gas_price", "cylinder_value"])
    brands = [dict(brand=b, brand_th=n, share_in_shop=w) for b, (n, w) in BRANDS.items()]
    write("brands.csv", brands, ["brand", "brand_th", "share_in_shop"])

    print(f"customers={len(customers)} transactions={len(txns)} payments={len(payments)}")


if __name__ == "__main__":
    main()
