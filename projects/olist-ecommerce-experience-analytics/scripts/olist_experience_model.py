"""
Brazilian E-Commerce Delivery Experience Analytics

Portfolio script for building an order-level analytical mart and training baseline
models to identify low-review risk in the Olist e-commerce dataset.
"""

from pathlib import Path
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def read_csvs(input_dir: str) -> dict:
    path = Path(input_dir)
    return {
        "orders": pd.read_csv(path / "olist_orders_dataset.csv", parse_dates=[
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ]),
        "items": pd.read_csv(path / "olist_order_items_dataset.csv"),
        "payments": pd.read_csv(path / "olist_order_payments_dataset.csv"),
        "reviews": pd.read_csv(path / "olist_order_reviews_dataset.csv"),
        "products": pd.read_csv(path / "olist_products_dataset.csv"),
        "customers": pd.read_csv(path / "olist_customers_dataset.csv"),
        "sellers": pd.read_csv(path / "olist_sellers_dataset.csv"),
        "translation": pd.read_csv(path / "product_category_name_translation.csv"),
    }


def build_order_mart(dfs: dict) -> pd.DataFrame:
    orders = dfs["orders"]
    items = dfs["items"]
    payments = dfs["payments"]
    reviews = dfs["reviews"]
    customers = dfs["customers"]

    items_agg = items.groupby("order_id").agg(
        items_count=("order_item_id", "count"),
        unique_products=("product_id", "nunique"),
        sellers_count=("seller_id", "nunique"),
        revenue=("price", "sum"),
        freight=("freight_value", "sum"),
    ).reset_index()

    payments_agg = payments.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        payment_installments=("payment_installments", "max"),
        payment_types=("payment_type", lambda x: "|".join(sorted(set(x.astype(str))))),
    ).reset_index()

    reviews_agg = reviews.groupby("order_id").agg(
        review_score=("review_score", "mean"),
        review_count=("review_id", "count"),
        has_review_comment=("review_comment_message", lambda x: x.notna().any()),
    ).reset_index()

    mart = (
        orders
        .merge(customers, on="customer_id", how="left")
        .merge(items_agg, on="order_id", how="left")
        .merge(payments_agg, on="order_id", how="left")
        .merge(reviews_agg, on="order_id", how="left")
    )

    mart["delivery_days"] = (
        mart["order_delivered_customer_date"] - mart["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    mart["delay_days"] = (
        mart["order_delivered_customer_date"] - mart["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400

    mart["is_delayed"] = (mart["delay_days"] > 0).astype(float)
    mart.loc[mart["order_delivered_customer_date"].isna(), "is_delayed"] = np.nan
    mart["low_review"] = (mart["review_score"] <= 2).astype(float)
    mart.loc[mart["review_score"].isna(), "low_review"] = np.nan

    return mart


def train_low_review_model(dfs: dict, mart: pd.DataFrame, output_dir: Path) -> None:
    products = dfs["products"].merge(dfs["translation"], on="product_category_name", how="left")
    items = dfs["items"].merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id",
        how="left",
    )

    first_item = (
        items.sort_values(["order_id", "order_item_id"])
        .groupby("order_id")
        .first()
        .reset_index()[["order_id", "product_category_name_english", "seller_id"]]
        .merge(dfs["sellers"][["seller_id", "seller_state"]], on="seller_id", how="left")
    )

    model_df = mart.merge(first_item, on="order_id", how="left")
    model_df["freight_ratio"] = model_df["freight"] / model_df["revenue"]
    model_df["same_state"] = model_df["customer_state"] == model_df["seller_state"]

    features = [
        "delivery_days", "delay_days", "items_count", "sellers_count", "revenue",
        "freight", "freight_ratio", "payment_installments", "customer_state",
        "seller_state", "same_state", "product_category_name_english"
    ]

    model_df = (
        model_df[(model_df["order_status"] == "delivered") & model_df["review_score"].notna()]
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=features + ["low_review"])
    )

    x = model_df[features]
    y = model_df["low_review"].astype(int)

    numeric_features = [
        "delivery_days", "delay_days", "items_count", "sellers_count",
        "revenue", "freight", "freight_ratio", "payment_installments"
    ]
    categorical_features = ["customer_state", "seller_state", "same_state", "product_category_name_english"]

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ])

    models = {
        "Logistic Regression": Pipeline([
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]),
        "Random Forest": Pipeline([
            ("preprocess", preprocessor),
            ("model", RandomForestClassifier(
                n_estimators=120, max_depth=12, random_state=42,
                class_weight="balanced", n_jobs=-1
            )),
        ]),
    }

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    results = []
    for name, model in models.items():
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        proba = model.predict_proba(x_test)[:, 1]
        results.append({
            "model": name,
            "accuracy": accuracy_score(y_test, pred),
            "roc_auc": roc_auc_score(y_test, proba),
            "precision": precision_score(y_test, pred),
            "recall": recall_score(y_test, pred),
            "f1": f1_score(y_test, pred),
        })

    pd.DataFrame(results).to_csv(output_dir / "model_metrics.csv", index=False)


def main(input_dir: str, output_dir: str = "outputs") -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    dfs = read_csvs(input_dir)
    mart = build_order_mart(dfs)

    summary = pd.DataFrame([{
        "orders": len(dfs["orders"]),
        "delivered_orders": int((dfs["orders"]["order_status"] == "delivered").sum()),
        "items": len(dfs["items"]),
        "unique_customers": dfs["customers"]["customer_unique_id"].nunique(),
        "sellers": dfs["sellers"]["seller_id"].nunique(),
        "products": dfs["products"]["product_id"].nunique(),
        "total_gmv": dfs["items"]["price"].sum() + dfs["items"]["freight_value"].sum(),
        "avg_order_value": mart["payment_value"].mean(),
        "avg_review_score": mart["review_score"].mean(),
        "low_review_rate": (mart["review_score"] <= 2).mean(),
        "delay_rate": mart.loc[mart["order_status"] == "delivered", "is_delayed"].mean(),
        "avg_delivery_days": mart.loc[mart["order_status"] == "delivered", "delivery_days"].mean(),
    }])
    summary.to_csv(output / "executive_summary.csv", index=False)

    train_low_review_model(dfs, mart, output)


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "outputs")
