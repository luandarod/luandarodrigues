"""
Olist E-commerce Customer Experience & Logistics Analytics

Builds an order-level analytical table by joining the Olist relational datasets.

Expected files:
- olist_orders_dataset.csv
- olist_order_items_dataset.csv
- olist_order_payments_dataset.csv
- olist_order_reviews_dataset.csv
- olist_customers_dataset.csv
- olist_sellers_dataset.csv
- olist_products_dataset.csv
- olist_geolocation_dataset.csv
- product_category_name_translation.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(a))


def read_data(input_dir):
    input_dir = Path(input_dir)
    return {
        "orders": pd.read_csv(input_dir / "olist_orders_dataset.csv", parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]),
        "items": pd.read_csv(input_dir / "olist_order_items_dataset.csv", parse_dates=["shipping_limit_date"]),
        "payments": pd.read_csv(input_dir / "olist_order_payments_dataset.csv"),
        "reviews": pd.read_csv(input_dir / "olist_order_reviews_dataset.csv", parse_dates=[
            "review_creation_date",
            "review_answer_timestamp",
        ]),
        "customers": pd.read_csv(input_dir / "olist_customers_dataset.csv"),
        "sellers": pd.read_csv(input_dir / "olist_sellers_dataset.csv"),
        "products": pd.read_csv(input_dir / "olist_products_dataset.csv"),
        "geolocation": pd.read_csv(input_dir / "olist_geolocation_dataset.csv"),
        "translation": pd.read_csv(input_dir / "product_category_name_translation.csv"),
    }


def build_order_level(data):
    orders = data["orders"]
    items = data["items"]
    payments = data["payments"]
    reviews = data["reviews"]
    customers = data["customers"]
    sellers = data["sellers"]
    products = data["products"]
    geolocation = data["geolocation"]
    translation = data["translation"]

    item_agg = items.groupby("order_id").agg(
        item_count=("order_item_id", "count"),
        product_count=("product_id", "nunique"),
        seller_count=("seller_id", "nunique"),
        total_price=("price", "sum"),
        total_freight=("freight_value", "sum"),
        avg_price=("price", "mean"),
        max_shipping_limit=("shipping_limit_date", "max"),
    ).reset_index()

    payment_agg = payments.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        payment_installments=("payment_installments", "max"),
        payment_methods=("payment_type", "nunique"),
    ).reset_index()

    dominant_payment = (
        payments.sort_values(["order_id", "payment_value"], ascending=[True, False])
        .drop_duplicates("order_id")[["order_id", "payment_type"]]
    )

    review_agg = reviews.groupby("order_id").agg(
        review_score=("review_score", "mean"),
        has_comment=("review_comment_message", lambda values: values.notna().any()),
    ).reset_index()

    products_translated = products.merge(translation, on="product_category_name", how="left")
    first_item = (
        items.sort_values(["order_id", "order_item_id"])
        .drop_duplicates("order_id")[["order_id", "product_id", "seller_id"]]
        .merge(products_translated[["product_id", "product_category_name_english", "product_weight_g"]], on="product_id", how="left")
        .merge(sellers, on="seller_id", how="left")
    )

    order_level = (
        orders.merge(customers, on="customer_id", how="left")
        .merge(item_agg, on="order_id", how="left")
        .merge(payment_agg, on="order_id", how="left")
        .merge(dominant_payment, on="order_id", how="left")
        .merge(review_agg, on="order_id", how="left")
        .merge(first_item, on="order_id", how="left")
    )

    geo_agg = geolocation.groupby("geolocation_zip_code_prefix").agg(
        lat=("geolocation_lat", "mean"),
        lng=("geolocation_lng", "mean"),
    ).reset_index()

    order_level = order_level.merge(
        geo_agg.rename(columns={
            "geolocation_zip_code_prefix": "customer_zip_code_prefix",
            "lat": "customer_lat",
            "lng": "customer_lng",
        }),
        on="customer_zip_code_prefix",
        how="left",
    )

    order_level = order_level.merge(
        geo_agg.rename(columns={
            "geolocation_zip_code_prefix": "seller_zip_code_prefix",
            "lat": "seller_lat",
            "lng": "seller_lng",
        }),
        on="seller_zip_code_prefix",
        how="left",
    )

    order_level["delivery_days"] = (
        order_level["order_delivered_customer_date"] - order_level["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    order_level["estimated_days"] = (
        order_level["order_estimated_delivery_date"] - order_level["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    order_level["delay_days"] = (
        order_level["order_delivered_customer_date"] - order_level["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    order_level["late_delivery"] = order_level["delay_days"] > 0
    order_level["approval_hours"] = (
        order_level["order_approved_at"] - order_level["order_purchase_timestamp"]
    ).dt.total_seconds() / 3600
    order_level["carrier_handoff_days"] = (
        order_level["order_delivered_carrier_date"] - order_level["order_approved_at"]
    ).dt.total_seconds() / 86400
    order_level["freight_ratio"] = order_level["total_freight"] / order_level["total_price"]
    order_level["seller_customer_km"] = haversine_km(
        order_level["customer_lat"],
        order_level["customer_lng"],
        order_level["seller_lat"],
        order_level["seller_lng"],
    )
    order_level["low_review"] = (order_level["review_score"] <= 2).astype("Int64")

    return order_level


def main(input_dir, output_dir="outputs"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = read_data(input_dir)
    order_level = build_order_level(data)
    order_level.to_csv(output_dir / "olist_order_level_dataset.csv", index=False)

    delivered = order_level[order_level["order_status"] == "delivered"].copy()
    summary = pd.DataFrame([{
        "total_orders": len(order_level),
        "delivered_orders": len(delivered),
        "average_review_score": order_level["review_score"].mean(),
        "late_delivery_rate_delivered": delivered["late_delivery"].mean(),
        "average_delivery_days_delivered": delivered["delivery_days"].mean(),
        "median_delivery_days_delivered": delivered["delivery_days"].median(),
        "average_freight_ratio_delivered": delivered["freight_ratio"].mean(),
    }])
    summary.to_csv(output_dir / "summary_metrics.csv", index=False)


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "outputs")
