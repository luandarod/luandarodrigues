"""
Run sensitivity analysis for the exploratory APS priority score.

The base score is useful as a screening device, but its weights are subjective.
This script compares alternative weight scenarios and reports how stable UF
rankings are when the analytical emphasis changes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SCENARIOS = {
    "base": {"ubs_pressure": 0.45, "coverage_gap": 0.40, "coord_gap": 0.15, "territory_gap": 0.00},
    "coverage_led": {"ubs_pressure": 0.30, "coverage_gap": 0.55, "coord_gap": 0.15, "territory_gap": 0.00},
    "territory_led": {"ubs_pressure": 0.30, "coverage_gap": 0.30, "coord_gap": 0.10, "territory_gap": 0.30},
    "data_quality_led": {"ubs_pressure": 0.25, "coverage_gap": 0.25, "coord_gap": 0.40, "territory_gap": 0.10},
}


def build_components(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result[
        result["uf_sigla"].notna()
        & (result["uf_sigla"].astype(str).str.upper() != "NAN")
    ].copy()
    result["ubs_pressure"] = 1 - result["ubs_per_10k_population"].rank(pct=True)
    result["coverage_gap"] = result["coverage_gap_pct"].rank(pct=True)
    result["coord_gap"] = 1 - result["coordinate_validity_pct"] / 100
    result["territory_gap"] = 1 - result["ubs_per_1000_km2"].rank(pct=True)
    return result


def score_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    scored = build_components(df)
    for scenario, weights in SCENARIOS.items():
        scored[f"score_{scenario}"] = sum(scored[col] * weight for col, weight in weights.items()) * 100

    score_cols = [f"score_{scenario}" for scenario in SCENARIOS]
    uf_scores = (
        scored.groupby(["uf_sigla", "uf_nome", "regiao_nome"], dropna=False)[score_cols]
        .mean()
        .reset_index()
    )
    for col in score_cols:
        uf_scores[f"rank_{col.removeprefix('score_')}"] = uf_scores[col].rank(ascending=False, method="min")
    rank_cols = [f"rank_{scenario}" for scenario in SCENARIOS]
    uf_scores["rank_min"] = uf_scores[rank_cols].min(axis=1)
    uf_scores["rank_max"] = uf_scores[rank_cols].max(axis=1)
    uf_scores["rank_range"] = uf_scores["rank_max"] - uf_scores["rank_min"]
    uf_scores["rank_std"] = uf_scores[rank_cols].std(axis=1)
    return uf_scores.sort_values("score_base", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build APS priority sensitivity outputs.")
    parser.add_argument("--input", default="projects/ubs-healthcare-mapping/data/enriched/municipality_ubs_aps_coverage.csv")
    parser.add_argument("--output", default="projects/ubs-healthcare-mapping/data/enriched/priority_sensitivity_uf_scores.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    score_scenarios(df).to_csv(output, index=False)
    print(f"Saved priority sensitivity scores to {output}")


if __name__ == "__main__":
    main()
