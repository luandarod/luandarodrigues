"""
Heart Disease Risk Prediction

Portfolio script for data quality checks, exploratory analysis and baseline
classification models on the heart disease dataset.
"""

from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def evaluate_model(name, model, x_train, x_test, y_train, y_test):
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    proba = model.predict_proba(x_test)[:, 1]
    return {
        "model": name,
        "accuracy": accuracy_score(y_test, pred),
        "roc_auc": roc_auc_score(y_test, proba),
        "precision": precision_score(y_test, pred),
        "recall": recall_score(y_test, pred),
        "f1": f1_score(y_test, pred),
    }, model


def main(input_path: str, output_dir: str = "outputs") -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    target = "HeartDisease"
    x = df.drop(columns=[target])
    y = df[target]

    numeric_features = x.select_dtypes(include="number").columns.tolist()
    categorical_features = x.select_dtypes(exclude="number").columns.tolist()

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ])

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    models = {
        "Logistic Regression": Pipeline([
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=1000)),
        ]),
        "Random Forest": Pipeline([
            ("preprocess", preprocessor),
            ("model", RandomForestClassifier(n_estimators=300, random_state=42)),
        ]),
    }

    results = []
    fitted_models = {}
    for name, model in models.items():
        metrics, fitted = evaluate_model(name, model, x_train, x_test, y_train, y_test)
        results.append(metrics)
        fitted_models[name] = fitted

    pd.DataFrame(results).to_csv(output / "model_metrics.csv", index=False)

    best_model = fitted_models["Random Forest"]
    perm = permutation_importance(best_model, x_test, y_test, n_repeats=20, random_state=42)
    importance = pd.DataFrame({
        "feature": x.columns,
        "importance_mean": perm.importances_mean,
        "importance_std": perm.importances_std,
    }).sort_values("importance_mean", ascending=False)
    importance.to_csv(output / "feature_importance_permutation.csv", index=False)

    quality = pd.DataFrame([{
        "rows": len(df),
        "columns": df.shape[1],
        "target_rate": y.mean(),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "zero_RestingBP": int((df["RestingBP"] == 0).sum()),
        "zero_Cholesterol": int((df["Cholesterol"] == 0).sum()),
    }])
    quality.to_csv(output / "data_quality_summary.csv", index=False)


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "outputs")
