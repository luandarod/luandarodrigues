"""Build a Phase 2 telemedicine index with explicit geodesic mismatch evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


EPSILON = 1e-6
SCENARIOS = {
    "balanced": {"need": 0.45, "spatial_mismatch": 0.30, "feasibility": 0.25},
    "equity_led": {"need": 0.60, "spatial_mismatch": 0.25, "feasibility": 0.15},
    "deployment_led": {"need": 0.35, "spatial_mismatch": 0.25, "feasibility": 0.40},
}


def _percentile(values: pd.Series, valid: pd.Series, inverse: bool = False) -> pd.Series:
    output = pd.Series(np.nan, index=values.index, dtype=float)
    sample = pd.to_numeric(values.loc[valid], errors="coerce").dropna()
    if sample.empty:
        return output
    lower, upper = sample.quantile([0.01, 0.99])
    sample = sample.clip(lower=lower, upper=upper)
    output.loc[sample.index] = sample.rank(pct=True, ascending=not inverse, method="average")
    return output


def _geometric(components: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    matrix = pd.DataFrame(components)
    complete = matrix.notna().all(axis=1)
    output = pd.Series(np.nan, index=matrix.index, dtype=float)
    clipped = matrix.loc[complete].clip(EPSILON, 1)
    output.loc[complete] = np.exp(sum(np.log(clipped[name]) * weight for name, weight in weights.items()))
    return output


def merge_phase2(phase1: pd.DataFrame, spatial: pd.DataFrame) -> pd.DataFrame:
    left = phase1.copy()
    right = spatial.copy()
    left["ibge_municipio_7"] = left["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    right["ibge_municipio_7"] = right["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    columns = [
        "ibge_municipio_7", "origin_longitude", "origin_latitude", "origin_quality_valid",
        "origin_method", "nearest_ubs_id", "nearest_ubs_geodesic_km", "nearest_pharmacy_id",
        "nearest_pharmacy_geodesic_km", "phase2_ubs_far_threshold_km_p75",
        "phase2_pharmacy_near_threshold_km_p25", "hard_ubs_easy_pharmacy_flag",
        "relative_hard_ubs_easy_pharmacy_flag", "hard_ubs_easy_pharmacy_flag_3km_2km",
        "hard_ubs_easy_pharmacy_flag_10km_5km",
        "spatial_access_status",
    ]
    return left.merge(right[columns], on="ibge_municipio_7", how="left", validate="one_to_one")


def build_phase2_index(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    if "hard_ubs_easy_pharmacy_flag" not in result:
        result["hard_ubs_easy_pharmacy_flag"] = (
            pd.to_numeric(result["nearest_ubs_geodesic_km"], errors="coerce").ge(5)
            & pd.to_numeric(result["nearest_pharmacy_geodesic_km"], errors="coerce").le(2)
            & pd.to_numeric(result["pharmacies"], errors="coerce").gt(0)
        )
    spatial_complete = (
        result.get("origin_quality_valid", result.get("origin_inside_main_polygon")).eq(True)
        & pd.to_numeric(result["nearest_ubs_geodesic_km"], errors="coerce").notna()
        & pd.to_numeric(result["nearest_pharmacy_geodesic_km"], errors="coerce").notna()
    )
    phase1_eligible = result["phase1_eligibility"].eq("eligible_phase1_proxy")
    eligible = spatial_complete & phase1_eligible

    result["phase2_ubs_geographic_barrier_percentile"] = _percentile(
        result["nearest_ubs_geodesic_km"], spatial_complete,
    )
    result["phase2_pharmacy_geographic_ease_percentile"] = _percentile(
        result["nearest_pharmacy_geodesic_km"], spatial_complete, inverse=True,
    )
    result["phase2_spatial_mismatch_score"] = 100 * _geometric({
        "ubs_barrier": result["phase2_ubs_geographic_barrier_percentile"],
        "pharmacy_ease": result["phase2_pharmacy_geographic_ease_percentile"],
    }, {"ubs_barrier": 0.60, "pharmacy_ease": 0.40})
    result["phase2_need_pillar"] = pd.to_numeric(result["phase1_need_score"], errors="coerce")
    result["phase2_feasibility_pillar"] = pd.to_numeric(
        result["phase1_deployment_feasibility_score"], errors="coerce",
    )
    result["phase2_eligibility"] = "eligible_phase2_geodesic_proxy"
    result.loc[~phase1_eligible, "phase2_eligibility"] = "phase1_ineligible"
    result.loc[phase1_eligible & ~spatial_complete, "phase2_eligibility"] = "insufficient_spatial_data"
    quality = result.get("origin_quality_valid", result.get("origin_inside_main_polygon"))
    result.loc[phase1_eligible & quality.eq(False), "phase2_eligibility"] = "invalid_origin_proxy"
    result["phase2_evidence_grade"] = "B_spatial_centroid_proxy"
    result.loc[~eligible, "phase2_evidence_grade"] = "C_incomplete"
    result["travel_time_status"] = "not_measured_geodesic_only"

    rank_columns = []
    for scenario, weights in SCENARIOS.items():
        score_column = f"telemedicine_phase2_{scenario}"
        rank_column = f"phase2_rank_{scenario}"
        result[score_column] = 100 * _geometric({
            "need": result["phase2_need_pillar"] / 100,
            "spatial_mismatch": result["phase2_spatial_mismatch_score"] / 100,
            "feasibility": result["phase2_feasibility_pillar"] / 100,
        }, weights)
        result.loc[eligible & result["phase2_need_pillar"].eq(0), score_column] = 0
        result.loc[~eligible, score_column] = np.nan
        result[rank_column] = result.loc[eligible, score_column].rank(ascending=False, method="min")
        rank_columns.append(rank_column)
    result["phase2_rank_best"] = result[rank_columns].min(axis=1)
    result["phase2_rank_worst"] = result[rank_columns].max(axis=1)
    result["phase2_rank_range"] = result["phase2_rank_worst"] - result["phase2_rank_best"]
    target = eligible & result["hard_ubs_easy_pharmacy_flag"].eq(True) & result["phase2_need_pillar"].gt(0)
    result["phase2_spatial_target_rank"] = result.loc[target, "telemedicine_phase2_balanced"].rank(ascending=False, method="min")
    return result.sort_values("telemedicine_phase2_balanced", ascending=False, na_position="last")


def monte_carlo_phase2(result: pd.DataFrame, iterations: int = 1_000, seed: int = 20260712) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    eligible = result["phase2_eligibility"].eq("eligible_phase2_geodesic_proxy")
    subset = result.loc[eligible]
    components = np.clip(subset[[
        "phase2_need_pillar", "phase2_spatial_mismatch_score", "phase2_feasibility_pillar",
    ]].to_numpy(float) / 100, EPSILON, 1)
    scores = np.empty((iterations, len(subset)), dtype=np.float32)
    ranks = np.empty_like(scores)
    structural_zero_need = subset["phase2_need_pillar"].eq(0).to_numpy()
    for iteration in range(iterations):
        weights = rng.dirichlet([9, 6, 5])
        score = np.exp(np.log(components) @ weights) * 100
        score[structural_zero_need] = 0
        scores[iteration] = score
        ranks[iteration] = pd.Series(score).rank(ascending=False, method="average").to_numpy()
    output = result[["ibge_municipio", "ibge_municipio_7", "municipio_nome_ibge", "uf_sigla", "phase2_eligibility"]].copy()
    for column in [
        "phase2_mc_score_median", "phase2_mc_rank_median", "phase2_mc_rank_p05",
        "phase2_mc_rank_p95", "phase2_mc_probability_top_decile",
    ]:
        output[column] = np.nan
    threshold = max(1, int(np.ceil(len(subset) * 0.10)))
    output.loc[eligible, "phase2_mc_score_median"] = np.median(scores, axis=0)
    output.loc[eligible, "phase2_mc_rank_median"] = np.median(ranks, axis=0)
    output.loc[eligible, "phase2_mc_rank_p05"] = np.quantile(ranks, 0.05, axis=0)
    output.loc[eligible, "phase2_mc_rank_p95"] = np.quantile(ranks, 0.95, axis=0)
    output.loc[eligible, "phase2_mc_probability_top_decile"] = (ranks <= threshold).mean(axis=0)
    return output.sort_values("phase2_mc_rank_median", na_position="last")


def main() -> None:
    root = Path("projects/ubs-healthcare-mapping")
    parser = argparse.ArgumentParser(description="Build Phase 2 telemedicine spatial-opportunity index.")
    parser.add_argument("--phase1", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase1.csv")
    parser.add_argument("--spatial", type=Path, default=root / "data/enriched/municipality_phase2_spatial_access.csv")
    parser.add_argument("--output", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase2.csv")
    parser.add_argument("--monte-carlo-output", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase2_monte_carlo.csv")
    parser.add_argument("--ads-shortlist-output", type=Path, default=root / "data/enriched/telemedicine_phase2_ads_geo_shortlist.csv")
    parser.add_argument("--metadata", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase2_metadata.json")
    args = parser.parse_args()
    result = build_phase2_index(merge_phase2(pd.read_csv(args.phase1), pd.read_csv(args.spatial)))
    monte_carlo = monte_carlo_phase2(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    monte_carlo.to_csv(args.monte_carlo_output, index=False)
    shortlist = result.loc[
        result["phase2_eligibility"].eq("eligible_phase2_geodesic_proxy")
        & result["hard_ubs_easy_pharmacy_flag"].eq(True)
        & result["phase2_need_pillar"].gt(0)
    ].merge(
        monte_carlo[[
            "ibge_municipio", "phase2_mc_rank_median", "phase2_mc_rank_p05",
            "phase2_mc_rank_p95", "phase2_mc_probability_top_decile",
        ]], on="ibge_municipio", how="left",
    ).sort_values(
        ["phase2_mc_probability_top_decile", "telemedicine_phase2_balanced"], ascending=[False, False],
    ).head(100)
    shortlist.to_csv(args.ads_shortlist_output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "index_version": "phase2-geodesic-v1",
        "design": "ecological municipal screening with centroid-based geodesic access proxy",
        "spatial_mismatch_weights": {"ubs_barrier": 0.60, "pharmacy_ease": 0.40},
        "scenarios": SCENARIOS,
        "aggregation": "weighted geometric mean after national winsorized percentile normalization",
        "monte_carlo": {"iterations": 1000, "seed": 20260712, "weights": "Dirichlet(9,6,5) for need, spatial mismatch, feasibility"},
        "travel_time_status": "not measured; geodesic distance is not routing",
        "primary_spatial_target_rule": "nearest active UBS >= 5 km, nearest OSM pharmacy <= 2 km, official PFPB present",
        "important_limits": [
            "Municipal geometric centroids are not population-weighted origins.",
            "OSM pharmacy completeness is heterogeneous.",
            "PFPB coordinates remain unavailable; accreditation is used only as a municipal gate.",
            "The score is exploratory and cannot support individual targeting or causal claims.",
        ],
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 2 scores for {len(result):,} municipalities; {result['phase2_eligibility'].eq('eligible_phase2_geodesic_proxy').sum():,} eligible")


if __name__ == "__main__":
    main()
