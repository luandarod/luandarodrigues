-- 03_review_risk_features.sql
-- Features associated with low customer review scores.

SELECT
    CASE WHEN review_score <= 2 THEN 1 ELSE 0 END AS low_review,
    COUNT(*) AS orders,
    AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)) AS avg_delivery_days,
    AVG(julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)) AS avg_delay_days,
    AVG(items_count) AS avg_items_count,
    AVG(sellers_count) AS avg_sellers_count,
    AVG(revenue) AS avg_revenue,
    AVG(freight) AS avg_freight,
    AVG(payment_installments) AS avg_installments
FROM order_mart
WHERE order_status = 'delivered'
  AND review_score IS NOT NULL
GROUP BY low_review;
