"""Build state-level telemedicine opportunity summary.

This aggregates the municipal decision matrix into UF-level signals for
portfolio storytelling, state prioritization, and geo-experiment planning.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("projects/ubs-healthcare-mapping")


DECISION_CLASSES = [
    "national_priority_high_readiness",
    "regional_scale_opportunity",
    "pharmacy_assisted_pilot",
    "pharmacy_assisted_geodesic_candidate",
    "high_need_digital_inclusion_first",
    "national_priority_inclusion_first",
    "monitor_or_low_priority",
    "insufficient_evidence",
]


STATE_ACTIONS = {
    "hybrid_national_and_pharmacy_pilot": "Combinar teste digital estadual com validação local dos pilotos farmácia.",
    "national_ads_priority": "Priorizar geoexperimento digital em municípios Top 100 e medir funil por UF.",
    "selective_city_ads": "Testar mídia apenas nos municípios líderes, sem extrapolar para todo o estado.",
    "digital_inclusion_first": "Desenhar oferta assistida ou de baixo consumo antes de campanha digital ampla.",
    "regional_experiment": "Usar como lista ampliada ou experimento regional controlado.",
    "data_quality_first": "Complementar dados antes de recomendar investimento territorial.",
    "monitor": "Manter em monitoramento até nova evidência ou atualização de dados.",
}


def _num(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df.get(column), errors="coerce")


def _weighted_average(group: pd.DataFrame, column: str) -> float:
    values = _num(group, column)
    weights = _num(group, "populacao_residente")
    valid = values.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return float("nan")
    return float(np.average(values.loc[valid], weights=weights.loc[valid]))


def _strategy(row: pd.Series, digital_median: float) -> str:
    scored_share = row["scored_municipalities"] / row["municipalities"] if row["municipalities"] else 0
    if row["pharmacy_assisted_pilot_count"] > 0 and row["top100_municipalities"] > 0:
        return "hybrid_national_and_pharmacy_pilot"
    if row["top100_municipalities"] >= 5:
        return "national_ads_priority"
    if row["top100_municipalities"] >= 1:
        return "selective_city_ads"
    if (
        row["digital_inclusion_first_count"] > 0
        or (
            pd.notna(row["population_weighted_need"])
            and pd.notna(row["population_weighted_digital_readiness"])
            and row["population_weighted_need"] >= 45
            and row["population_weighted_digital_readiness"] < digital_median
        )
    ):
        return "digital_inclusion_first"
    if row["top500_municipalities"] >= 5 or row["regional_scale_opportunity_count"] >= 5:
        return "regional_experiment"
    if scored_share < 0.60 or row["insufficient_evidence_count"] >= 10:
        return "data_quality_first"
    return "monitor"


def build_state_summary(matrix: pd.DataFrame) -> pd.DataFrame:
    source = matrix.copy()
    for column in [
        "populacao_residente",
        "telemedicine_phase2_balanced",
        "phase2_rank_balanced",
        "phase2_need_pillar",
        "phase2_spatial_mismatch_score",
        "phase2_feasibility_pillar",
        "digital_readiness_score",
    ]:
        source[column] = _num(source, column)

    rows = []
    for uf, group in source.groupby("uf_sigla", dropna=False):
        class_counts = group["decision_class"].value_counts().to_dict()
        row = {
            "uf_sigla": uf,
            "regiao_nome": group["regiao_nome_oficial"].dropna().iloc[0] if group["regiao_nome_oficial"].notna().any() else None,
            "municipalities": int(len(group)),
            "population": int(group["populacao_residente"].fillna(0).sum()),
            "scored_municipalities": int(group["telemedicine_phase2_balanced"].notna().sum()),
            "top100_municipalities": int(group["phase2_rank_balanced"].le(100).sum()),
            "top500_municipalities": int(group["phase2_rank_balanced"].le(500).sum()),
            "population_weighted_phase2_score": _weighted_average(group, "telemedicine_phase2_balanced"),
            "population_weighted_need": _weighted_average(group, "phase2_need_pillar"),
            "population_weighted_spatial_mismatch": _weighted_average(group, "phase2_spatial_mismatch_score"),
            "population_weighted_feasibility": _weighted_average(group, "phase2_feasibility_pillar"),
            "population_weighted_digital_readiness": _weighted_average(group, "digital_readiness_score"),
        }
        for decision_class in DECISION_CLASSES:
            row[f"{decision_class}_count"] = int(class_counts.get(decision_class, 0))
        rows.append(row)

    summary = pd.DataFrame(rows)
    summary["scored_municipality_share_pct"] = 100 * summary["scored_municipalities"] / summary["municipalities"]
    summary["top100_per_million_population"] = np.where(
        summary["population"].gt(0),
        summary["top100_municipalities"] / (summary["population"] / 1_000_000),
        np.nan,
    )
    max_top100 = max(1, int(summary["top100_municipalities"].max()))
    max_population = max(1, int(summary["population"].max()))
    summary["state_opportunity_score"] = (
        0.35 * summary["population_weighted_phase2_score"].fillna(0)
        + 0.20 * summary["population_weighted_need"].fillna(0)
        + 0.10 * summary["population_weighted_digital_readiness"].fillna(0)
        + 0.25 * (100 * summary["top100_municipalities"] / max_top100)
        + 0.10 * (100 * np.sqrt(summary["population"] / max_population))
    )
    digital_median = float(summary["population_weighted_digital_readiness"].median())
    summary["digital_inclusion_first_count"] = (
        summary["high_need_digital_inclusion_first_count"]
        + summary["national_priority_inclusion_first_count"]
    )
    summary["state_strategy_tier"] = summary.apply(_strategy, axis=1, digital_median=digital_median)
    summary["recommended_state_action"] = summary["state_strategy_tier"].map(STATE_ACTIONS)
    summary["state_rank"] = summary["state_opportunity_score"].rank(ascending=False, method="min").astype(int)

    ordered_columns = [
        "state_rank",
        "uf_sigla",
        "regiao_nome",
        "state_strategy_tier",
        "recommended_state_action",
        "state_opportunity_score",
        "population_weighted_phase2_score",
        "population_weighted_need",
        "population_weighted_spatial_mismatch",
        "population_weighted_feasibility",
        "population_weighted_digital_readiness",
        "municipalities",
        "population",
        "scored_municipalities",
        "scored_municipality_share_pct",
        "top100_municipalities",
        "top500_municipalities",
        "top100_per_million_population",
    ]
    ordered_columns.extend(f"{decision_class}_count" for decision_class in DECISION_CLASSES)
    ordered_columns.append("digital_inclusion_first_count")
    return summary[ordered_columns].sort_values(["state_rank", "uf_sigla"])


def summarize_states(summary: pd.DataFrame) -> dict[str, object]:
    return {
        "states": int(len(summary)),
        "top_state": str(summary.sort_values("state_rank").iloc[0]["uf_sigla"]),
        "top100_total": int(summary["top100_municipalities"].sum()),
        "phase4_pilot_total": int(summary["pharmacy_assisted_pilot_count"].sum()),
        "strategy_counts": {str(k): int(v) for k, v in summary["state_strategy_tier"].value_counts().sort_index().items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build state-level telemedicine opportunity summary.")
    parser.add_argument("--matrix", type=Path, default=ROOT / "data/enriched/telemedicine_decision_matrix.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_state_opportunity_summary.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/enriched/telemedicine_state_opportunity_summary_metadata.json")
    args = parser.parse_args()

    summary = build_state_summary(pd.read_csv(args.matrix))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "summary_version": "state-opportunity-v1",
        "source": str(args.matrix),
        "state_opportunity_score": {
            "population_weighted_phase2_score": 0.35,
            "population_weighted_need": 0.20,
            "population_weighted_digital_readiness": 0.10,
            "top100_count_scaled_to_best_state": 0.25,
            "sqrt_population_scaled_to_largest_state": 0.10,
        },
        "strategy_rules": STATE_ACTIONS,
        "important_limits": [
            "UF aggregation hides intrastate heterogeneity.",
            "State recommendations are for geo-experiment planning, not clinical claims.",
            "Municipal evidence remains the source of truth for local validation.",
        ],
        "summary": summarize_states(summary),
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata["summary"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
