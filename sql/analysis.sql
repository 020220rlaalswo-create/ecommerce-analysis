-- MySQL 8.0 기준입니다. Olist CSV를 orders, customers, order_items,
-- order_payments, order_reviews, products 등의 테이블로 불러오세요.
-- 실제 테이블 이름이 다르면 SQL을 수정해야 합니다.
-- 일대다 관계를 주문별로 먼저 집계하여 중복 합산을 방지합니다.
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

-- 월별 상품 매출: 배송 완료 주문만 포함하며 배송비는 제외합니다.
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

-- 재구매 분석: 주문별 customer_id 대신 고유 고객 ID를 사용합니다.
SELECT COUNT(*) AS delivered_customers,
       SUM(order_count >= 2) AS returning_customers,
       ROUND(AVG(order_count >= 2)*100,2) AS observed_repeat_rate_pct
FROM (
 SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
 FROM orders o JOIN customers c ON o.customer_id = c.customer_id
 WHERE o.order_status = 'delivered'
 GROUP BY c.customer_unique_id
) x;

-- 배송 지연과 리뷰의 연관성을 비교합니다. 인과관계를 뜻하지는 않습니다.
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

-- 데이터 품질 점검: 주문 상태별 실제 배송일 결측 건수를 확인합니다.
SELECT order_status, COUNT(*) AS n,
 SUM(order_delivered_customer_date IS NULL) AS missing_actual_delivery
FROM orders GROUP BY order_status;
