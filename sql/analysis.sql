-- MySQL 8.0. Import Olist CSVs into tables: orders, customers, order_items,
-- order_payments, order_reviews, products, sellers (adapt table names if needed).
-- Order-level aggregation prevents many-to-many multiplication.
WITH item_totals AS (
  SELECT order_id, SUM(price) AS product_revenue,
         SUM(freight_value) AS freight_total, COUNT(*) AS item_count
  FROM order_items GROUP BY order_id
), payment_totals AS (
  SELECT order_id, SUM(payment_value) AS payment_total
  FROM order_payments GROUP BY order_id
), review_totals AS (
  SELECT order_id, AVG(review_score) AS avg_review_score
  FROM order_reviews GROUP BY order_id
)
SELECT o.order_id, o.order_status, o.order_purchase_timestamp,
       c.customer_unique_id, c.customer_state,
       i.product_revenue, i.freight_total, i.item_count,
       p.payment_total, r.avg_review_score,
       TIMESTAMPDIFF(HOUR, o.order_purchase_timestamp,
         o.order_delivered_customer_date) / 24.0 AS delivery_days,
       CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 1 WHEN o.order_delivered_customer_date IS NOT NULL
                     AND o.order_estimated_delivery_date IS NOT NULL THEN 0
            ELSE NULL END AS late_flag
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN item_totals i ON o.order_id = i.order_id
LEFT JOIN payment_totals p ON o.order_id = p.order_id
LEFT JOIN review_totals r ON o.order_id = r.order_id;

-- Monthly realized/fulfilled item value; delivered orders only.
WITH item_totals AS (
 SELECT order_id, SUM(price) AS product_revenue FROM order_items GROUP BY order_id
)
SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS purchase_month,
       COUNT(*) AS delivered_orders,
       ROUND(SUM(i.product_revenue),2) AS product_revenue_brl,
       ROUND(AVG(i.product_revenue),2) AS avg_product_order_value_brl
FROM orders o JOIN item_totals i ON o.order_id = i.order_id
WHERE o.order_status = 'delivered'
GROUP BY purchase_month ORDER BY purchase_month;

-- Repeat purchase: customer_unique_id rather than per-order customer_id.
SELECT COUNT(*) AS delivered_customers,
       SUM(order_count >= 2) AS returning_customers,
       ROUND(AVG(order_count >= 2)*100,2) AS observed_repeat_rate_pct
FROM (
 SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
 FROM orders o JOIN customers c ON o.customer_id = c.customer_id
 WHERE o.order_status = 'delivered'
 GROUP BY c.customer_unique_id
) x;

-- Delivery delay and rating association (not causation).
WITH scores AS (
 SELECT order_id, AVG(review_score) AS avg_review_score
 FROM order_reviews GROUP BY order_id
)
SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 'late' ELSE 'on_time_or_early' END AS delivery_group,
       COUNT(*) AS rated_orders,
       ROUND(AVG(s.avg_review_score),3) AS mean_review_score
FROM orders o JOIN scores s ON o.order_id = s.order_id
WHERE o.order_status='delivered'
 AND o.order_delivered_customer_date IS NOT NULL
 AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY delivery_group;

-- Data quality: ensure join row counts and missingness.
SELECT order_status, COUNT(*) AS n,
 SUM(order_delivered_customer_date IS NULL) AS missing_actual_delivery
FROM orders GROUP BY order_status;
