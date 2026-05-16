-- 01_create_order_mart.sql
-- Order-level analytical mart for Olist e-commerce analytics.

CREATE VIEW order_mart AS
WITH item_metrics AS (
    SELECT
        order_id,
        COUNT(*) AS items_count,
        COUNT(DISTINCT product_id) AS unique_products,
        COUNT(DISTINCT seller_id) AS sellers_count,
        SUM(price) AS revenue,
        SUM(freight_value) AS freight
    FROM olist_order_items_dataset
    GROUP BY order_id
),
payment_metrics AS (
    SELECT
        order_id,
        SUM(payment_value) AS payment_value,
        MAX(payment_installments) AS payment_installments
    FROM olist_order_payments_dataset
    GROUP BY order_id
),
review_metrics AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score,
        COUNT(*) AS review_count
    FROM olist_order_reviews_dataset
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    i.items_count,
    i.unique_products,
    i.sellers_count,
    i.revenue,
    i.freight,
    p.payment_value,
    p.payment_installments,
    r.review_score,
    r.review_count
FROM olist_orders_dataset o
LEFT JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
LEFT JOIN item_metrics i ON o.order_id = i.order_id
LEFT JOIN payment_metrics p ON o.order_id = p.order_id
LEFT JOIN review_metrics r ON o.order_id = r.order_id;
