"""Build a robust UF-level priority index for UBS/APS territorial screening."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SCENARIOS = {
    "balanced": {
        "ubs_population_gap": 0.25,
        "aps_coverage_gap": 0.25,
        "operational_gap": 0.20,
        "spatial_quality_gap": 0.15,
        "territorial_vulnerability_proxy": 0.15,
    },
    "coverage_led": {
        "ubs_population_gap": 0.18,
        "aps_coverage_gap": 0.40,
        "operational_gap": 0.18,
        "spatial_quality_gap": 0.12,
        "territorial_vulnerability_proxy": 0.12,
    },
    "operations_led": {
        "ubs_population_gap": 0.18,
        "aps_coverage_gap": 0.18,
        "operational_gap": 0.40,
        "spatial_quality_gap": 0.12,
        "territorial_vulnerability_proxy": 0.12,
    },
    "data_quality_led": {
        "ubs_population_gap": 0.18,
        "aps_coverage_gap": 0.18,
        "operational_gap": 0.14,
        "spatial_quality_gap": 0.35,
        "territorial_vulnerability_proxy": 0.15,
    },
    "vulnerability_led": {
        "ubs_population_gap": 0.20,
        "aps_coverage_gap": 0.18,
        "operational_gap": 0.17,
        "spatial_quality_gap": 0.10,
        "territorial_vulnerability_proxy": 0.35,
    },
}


def pct_rank(series: pd.Series, ascending: bool = True) -> pd.Series:
    return series.rank(pct=True, ascending=ascending, method="average")


def build_index(project_dir: Path, output_index: Path, output_sensitivity: Path) -> None:
    enriched = project_dir / "data" / "enriched"
    territory = pd.read_csv(enriched / "uf_ubs_territory_summary.csv")
    aps = pd.read_csv(enriched / "uf_ubs_aps_coverage_summary.csv")
    spatial = pd.read_csv(project_dir / "data" / "spatial_validation_by_uf.csv")
    operational = pd.read_csv(project_dir / "data" / "ubs_operational_status_by_uf.csv")

    df = (
        territory.merge(
            aps[
                [
                    "uf_sigla",
                    "cobertura_aps_ponderada_capped_pct",
                    "coverage_gap_media_pct",
                    "aps_populacao",
                    "aps_capacidade_equipe",
                ]
            ],
            on="uf_sigla",
            how="left",
        )
        .merge(spatial[["uf_sigla", "spatial_issue_pct"]], on="uf_sigla", how="left")
        .merge(
            operational[
                [
                    "uf_sigla",
                    "cnes_active_proxy_pct",
                    "active_with_recent_sia_production_pct",
                    "recent_sia_production_pct",
                ]
            ],
            on="uf_sigla",
            how="left",
        )
    )

    df["population_density"] = df["population"] / df["area_km2"]
    df["ubs_population_gap"] = 1 - pct_rank(df["ubs_per_10k_population"], ascending=True)
    df["aps_coverage_gap"] = (100 - df["cobertura_aps_ponderada_capped_pct"]).clip(lower=0) / 100
    df["operational_gap"] = 1 - df["active_with_recent_sia_production_pct"].fillna(0) / 100
    df["spatial_quality_gap"] = df["spatial_issue_pct"].fillna(0) / 100
    df["density_pressure"] = pct_rank(df["population_density"], ascending=True)
    df["territorial_dispersion_pressure"] = 1 - pct_rank(df["ubs_per_1000_km2"], ascending=True)
    df["territorial_vulnerability_proxy"] = (
        0.5 * df["density_pressure"] + 0.5 * df["territorial_dispersion_pressure"]
    )

    component_cols = [
        "ubs_population_gap",
        "aps_coverage_gap",
        "operational_gap",
        "spatial_quality_gap",
        "territorial_vulnerability_proxy",
    ]
    for scenario, weights in SCENARIOS.items():
        df[f"robust_priority_{scenario}"] = sum(df[col] * weight for col, weight in weights.items()) * 100
        df[f"rank_{scenario}"] = df[f"robust_priority_{scenario}"].rank(ascending=False, method="min")

    score_cols = [f"robust_priority_{scenario}" for scenario in SCENARIOS]
    rank_cols = [f"rank_{scenario}" for scenario in SCENARIOS]
    df["robust_priority_min"] = df[score_cols].min(axis=1)
    df["robust_priority_max"] = df[score_cols].max(axis=1)
    df["robust_priority_range"] = df["robust_priority_max"] - df["robust_priority_min"]
    df["rank_min"] = df[rank_cols].min(axis=1)
    df["rank_max"] = df[rank_cols].max(axis=1)
    df["rank_range"] = df["rank_max"] - df["rank_min"]
    df["priority_stability_flag"] = pd.cut(
        df["rank_range"],
        bins=[-1, 2, 6, 27],
        labels=["stable", "moderate", "sensitive"],
    )

    index_columns = [
        "uf_sigla",
        "uf_nome",
        "regiao_nome",
        "ubs_records",
        "population",
        "area_km2",
        "ubs_per_10k_population",
        "ubs_per_1000_km2",
        "cobertura_aps_ponderada_capped_pct",
        "active_with_recent_sia_production_pct",
        "spatial_issue_pct",
        "population_density",
        *component_cols,
        *score_cols,
        "robust_priority_min",
        "robust_priority_max",
        "robust_priority_range",
        "rank_min",
        "rank_max",
        "rank_range",
        "priority_stability_flag",
    ]
    ranked = df[index_columns].sort_values("robust_priority_balanced", ascending=False)

    sensitivity_rows = []
    for scenario in SCENARIOS:
        scenario_df = df[["uf_sigla", "uf_nome", "regiao_nome"]].copy()
        scenario_df["scenario"] = scenario
        scenario_df["robust_priority_score"] = df[f"robust_priority_{scenario}"]
        scenario_df["rank"] = df[f"rank_{scenario}"]
        sensitivity_rows.append(scenario_df)
    sensitivity = pd.concat(sensitivity_rows, ignore_index=True)
    sensitivity = sensitivity[["scenario", "uf_sigla", "uf_nome", "regiao_nome", "robust_priority_score", "rank"]]

    output_index.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output_index, index=False)
    sensitivity.to_csv(output_sensitivity, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build robust UF priority index.")
    parser.add_argument("--project-dir", default="projects/ubs-healthcare-mapping")
    parser.add_argument(
        "--output-index",
        default="projects/ubs-healthcare-mapping/data/enriched/robust_priority_index_uf.csv",
    )
    parser.add_argument(
        "--output-sensitivity",
        default="projects/ubs-healthcare-mapping/data/enriched/robust_priority_sensitivity_uf.csv",
    )
    args = parser.parse_args()

    build_index(Path(args.project_dir), Path(args.output_index), Path(args.output_sensitivity))
    print(f"Saved robust priority index to {args.output_index}")


if __name__ == "__main__":
    main()
