-- 02_delivery_performance.sql
-- Delivery performance by customer state.

SELECT
    customer_state,
    COUNT(*) AS orders,
    AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)) AS avg_delivery_days,
    AVG(CASE
        WHEN julianday(order_delivered_customer_date) > julianday(order_estimated_delivery_date) THEN 1.0
        ELSE 0.0
    END) AS delay_rate,
    AVG(freight) AS avg_freight
FROM order_mart
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
GROUP BY customer_state
ORDER BY orders DESC;
