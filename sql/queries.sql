-- คำสั่ง SQL ที่ใช้คำนวณตัวเลขใน Dashboard
-- รันหลังนำเข้า thangruam.sql แล้ว (MySQL 8 / MariaDB 10.2+)
-- วันที่อ้างอิงของข้อมูล = 2026-09-30

USE thangruam;

-- ภาพรวม
SELECT
  (SELECT SUM(gas_amount) FROM transactions)                AS gas_revenue,
  (SELECT COUNT(*) FROM transactions WHERE full_out > 0)    AS orders,
  ROUND((SELECT COUNT(*) FROM transactions WHERE full_out > 0)
        * 1.0 / (DATEDIFF('2026-09-30', '2026-04-01') + 1), 1)    AS orders_per_day,
  (SELECT SUM(cylinders_at_start) FROM customers)
    + (SELECT SUM(full_out - empty_in) FROM transactions)   AS cylinders_at_customers,
  (SELECT SUM(gas_amount) FROM transactions WHERE payment_method = 'credit')
    - (SELECT SUM(amount) FROM payments)                    AS receivables;

-- 1. ส่วนแบ่งตลาด และสัดส่วนที่ไม่มีแอปจากแบรนด์
SELECT company_th, market_share_pct FROM market_share ORDER BY market_share_pct DESC;
SELECT 100 - market_share_pct AS pct_without_brand_app FROM market_share WHERE company = 'PTTOR';

-- 2. ยอดขายแยกแบรนด์
SELECT b.brand_th,
       SUM(t.gas_amount) AS revenue,
       ROUND(100.0 * SUM(t.gas_amount) / SUM(SUM(t.gas_amount)) OVER (), 1) AS pct
FROM transactions t JOIN brands b ON b.brand = t.brand
GROUP BY b.brand_th
ORDER BY revenue DESC;

-- 2. ยอดขายรายเดือนแยกแบรนด์
SELECT DATE_FORMAT(txn_date, '%Y-%m') AS month, brand, SUM(gas_amount) AS revenue
FROM transactions
GROUP BY DATE_FORMAT(txn_date, '%Y-%m'), brand
ORDER BY month, brand;

-- 3. ออเดอร์ต่อวัน (เฉลี่ย / สูงสุด)
SELECT ROUND(AVG(n), 1) AS avg_per_active_day, MAX(n) AS max_per_day
FROM (SELECT txn_date, COUNT(*) AS n FROM transactions WHERE full_out > 0 GROUP BY txn_date) d;

-- 3. ออเดอร์ตามช่วงเวลา
SELECT HOUR(txn_time) AS hour, COUNT(*) AS orders
FROM transactions WHERE full_out > 0
GROUP BY HOUR(txn_time) ORDER BY hour;

-- 4. ถังที่อยู่กับลูกค้า แยกแบรนด์และขนาด
SELECT c.brand, c.size_kg,
       SUM(c.cylinders_at_start + COALESCE(t.net, 0)) AS cylinders
FROM customers c
LEFT JOIN (SELECT customer_id, SUM(full_out - empty_in) AS net
           FROM transactions GROUP BY customer_id) t ON t.customer_id = c.customer_id
GROUP BY c.brand, c.size_kg
ORDER BY c.brand, c.size_kg;

-- 4. ลูกค้าที่ยังไม่คืนถังเปล่า (ถือถังเกินจำนวนที่วางมัดจำ)
SELECT * FROM (
  SELECT c.customer_id, c.name, c.brand, c.size_kg,
         c.cylinders_at_start + COALESCE(SUM(t.full_out - t.empty_in), 0) AS held,
         c.cylinders_at_start
           + COALESCE(SUM(CASE WHEN t.txn_type = 'new_cylinder'    THEN t.full_out ELSE 0 END), 0)
           - COALESCE(SUM(CASE WHEN t.txn_type = 'return_cylinder' THEN t.empty_in ELSE 0 END), 0) AS with_deposit,
         p.cylinder_value
  FROM customers c
  JOIN products p ON p.size_kg = c.size_kg
  LEFT JOIN transactions t ON t.customer_id = c.customer_id
  GROUP BY c.customer_id, c.name, c.brand, c.size_kg, c.cylinders_at_start, p.cylinder_value
) x
WHERE held > with_deposit AND held > 0
ORDER BY (held - with_deposit) * cylinder_value DESC;

-- 5. ลูกค้าที่หยุดสั่งเกิน 60 วัน แต่ยังถือถังของร้าน
SELECT * FROM (
  SELECT c.customer_id, c.name, c.brand, c.size_kg,
         c.cylinders_at_start + COALESCE(SUM(t.full_out - t.empty_in), 0) AS held,
         MAX(t.txn_date) AS last_order,
         DATEDIFF('2026-09-30', MAX(t.txn_date)) AS idle_days,
         p.cylinder_value
  FROM customers c
  JOIN products p ON p.size_kg = c.size_kg
  LEFT JOIN transactions t ON t.customer_id = c.customer_id
  GROUP BY c.customer_id, c.name, c.brand, c.size_kg, c.cylinders_at_start, p.cylinder_value
) x
WHERE held > 0 AND (idle_days > 60 OR last_order IS NULL)
ORDER BY held * cylinder_value DESC, idle_days DESC;

-- 6. ลูกหนี้ตามอายุหนี้ (เงินที่จ่ายตัดบิลเก่าสุดก่อน)
WITH inv AS (
  SELECT t.customer_id, t.txn_id, t.txn_date, t.gas_amount,
         SUM(t.gas_amount) OVER (PARTITION BY t.customer_id ORDER BY t.txn_date, t.txn_id) AS cum_billed,
         COALESCE(p.paid, 0) AS paid
  FROM transactions t
  LEFT JOIN (SELECT customer_id, SUM(amount) AS paid FROM payments GROUP BY customer_id) p
         ON p.customer_id = t.customer_id
  WHERE t.payment_method = 'credit'
),
unpaid AS (
  SELECT customer_id, txn_date,
         LEAST(gas_amount, GREATEST(0, cum_billed - paid)) AS remaining,
         DATEDIFF('2026-09-30', txn_date) AS age_days
  FROM inv
)
SELECT CASE WHEN age_days <= 30 THEN '0-30 วัน'
            WHEN age_days <= 60 THEN '31-60 วัน'
            WHEN age_days <= 90 THEN '61-90 วัน'
            ELSE 'เกิน 90 วัน' END AS age_bucket,
       SUM(remaining) AS amount
FROM unpaid
WHERE remaining > 0
GROUP BY CASE WHEN age_days <= 30 THEN '0-30 วัน'
              WHEN age_days <= 60 THEN '31-60 วัน'
              WHEN age_days <= 90 THEN '61-90 วัน'
              ELSE 'เกิน 90 วัน' END
ORDER BY MIN(age_days);

-- 6. ลูกหนี้ที่ค้างมากที่สุด
SELECT c.customer_id, c.name, c.brand,
       SUM(t.gas_amount) - COALESCE(p.paid, 0) AS outstanding
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
LEFT JOIN (SELECT customer_id, SUM(amount) AS paid FROM payments GROUP BY customer_id) p
       ON p.customer_id = t.customer_id
WHERE t.payment_method = 'credit'
GROUP BY c.customer_id, c.name, c.brand, p.paid
HAVING SUM(t.gas_amount) - COALESCE(p.paid, 0) > 0
ORDER BY outstanding DESC
LIMIT 8;
