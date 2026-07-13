"""Build Phase 5 telemedicine precision index."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path("projects/ubs-healthcare-mapping")
EPSILON = 1e-6


def _normalise_ibge_code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"\.0$", "", regex=True)


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


def build_precision_index(phase2: pd.DataFrame, precision_access: pd.DataFrame) -> pd.DataFrame:
    left = phase2.copy()
    right = precision_access.copy()
    left["ibge_municipio_7"] = _normalise_ibge_code(left["ibge_municipio_7"])
    right["ibge_municipio_7"] = _normalise_ibge_code(right["ibge_municipio_7"])
    columns = [
        "ibge_municipio_7",
        "phase5_population_origins",
        "phase5_origin_granularity",
        "phase5_origin_population",
        "phase5_population_origin_coverage_ratio",
        "phase5_distance_coverage_ratio",
        "phase5_weighted_mean_ubs_km",
        "phase5_weighted_p50_ubs_km",
        "phase5_weighted_p90_ubs_km",
        "phase5_weighted_mean_pharmacy_km",
        "phase5_weighted_p50_pharmacy_km",
        "phase5_weighted_p90_pharmacy_km",
        "phase5_population_share_ubs_gt_5km",
        "phase5_population_share_pharmacy_le_2km",
        "phase5_population_share_hard_ubs_easy_pharmacy",
        "phase5_population_per_active_ubs",
        "phase5_population_per_physician_fte",
        "phase5_population_per_pfpb_pharmacy",
        "phase5_precision_status",
        "phase5_access_evidence_grade",
    ]
    defaults: dict[str, object] = {
        "phase5_population_origins": np.nan,
        "phase5_origin_granularity": pd.NA,
        "phase5_origin_population": np.nan,
        "phase5_distance_coverage_ratio": right.get("phase5_population_origin_coverage_ratio", np.nan),
        "phase5_weighted_mean_ubs_km": np.nan,
        "phase5_weighted_p50_ubs_km": np.nan,
        "phase5_weighted_mean_pharmacy_km": np.nan,
        "phase5_weighted_p50_pharmacy_km": np.nan,
        "phase5_weighted_p90_pharmacy_km": np.nan,
        "phase5_population_share_ubs_gt_5km": np.nan,
        "phase5_population_per_active_ubs": np.nan,
        "phase5_population_per_physician_fte": np.nan,
        "phase5_population_per_pfpb_pharmacy": np.nan,
    }
    for column in columns:
        if column not in right:
            right[column] = defaults.get(column, np.nan)
    result = left.merge(right[columns], on="ibge_municipio_7", how="left", validate="one_to_one")
    valid_access = (
        pd.to_numeric(result["phase5_population_origin_coverage_ratio"], errors="coerce").ge(0.90)
        & pd.to_numeric(result["phase5_distance_coverage_ratio"], errors="coerce").ge(0.95)
        & pd.to_numeric(result["phase5_weighted_p90_ubs_km"], errors="coerce").notna()
        & pd.to_numeric(result["phase5_population_share_pharmacy_le_2km"], errors="coerce").notna()
    )
    phase2_eligible = result["phase2_eligibility"].eq("eligible_phase2_geodesic_proxy")
    eligible = valid_access & phase2_eligible

    result["phase5_ubs_p90_barrier_percentile"] = _percentile(result["phase5_weighted_p90_ubs_km"], valid_access)
    result["phase5_pharmacy_near_share_percentile"] = _percentile(result["phase5_population_share_pharmacy_le_2km"], valid_access)
    result["phase5_hard_easy_share_percentile"] = _percentile(result["phase5_population_share_hard_ubs_easy_pharmacy"], valid_access)
    result["phase5_spatial_precision_mismatch_score"] = 100 * _geometric({
        "ubs_p90_barrier": result["phase5_ubs_p90_barrier_percentile"],
        "pharmacy_near_share": result["phase5_pharmacy_near_share_percentile"],
        "hard_easy_share": result["phase5_hard_easy_share_percentile"],
    }, {"ubs_p90_barrier": 0.45, "pharmacy_near_share": 0.25, "hard_easy_share": 0.30})
    result["telemedicine_precision_index"] = 100 * _geometric({
        "need": pd.to_numeric(result["phase2_need_pillar"], errors="coerce") / 100,
        "spatial_precision": result["phase5_spatial_precision_mismatch_score"] / 100,
        "feasibility": pd.to_numeric(result["phase2_feasibility_pillar"], errors="coerce") / 100,
    }, {"need": 0.45, "spatial_precision": 0.35, "feasibility": 0.20})
    result.loc[~eligible, "telemedicine_precision_index"] = np.nan
    result["phase5_precision_rank"] = result.loc[eligible, "telemedicine_precision_index"].rank(ascending=False, method="min")
    result["phase5_index_eligibility"] = "eligible_phase5_precision"
    result.loc[~phase2_eligible, "phase5_index_eligibility"] = "phase2_ineligible"
    result.loc[phase2_eligible & ~valid_access, "phase5_index_eligibility"] = "insufficient_phase5_spatial_precision_data"
    result["phase5_evidence_grade"] = result["phase5_access_evidence_grade"].fillna("C_incomplete")
    result["phase5_method_note"] = np.where(
        result["phase5_access_evidence_grade"].eq("A_intramunicipal_population_weighted"),
        "Population-weighted geodesic access using intramunicipal origins.",
        "Municipal single-origin proxy; use as process scaffold until IBGE 2022 sector/grid origins are loaded.",
    )
    return result.sort_values("telemedicine_precision_index", ascending=False, na_position="last")


def build_shortlist(result: pd.DataFrame, limit: int = 100) -> pd.DataFrame:
    columns = [
        "ibge_municipio",
        "ibge_municipio_7",
        "municipio_nome_ibge",
        "uf_sigla",
        "populacao_residente",
        "telemedicine_precision_index",
        "phase5_precision_rank",
        "phase2_rank_balanced",
        "phase2_need_pillar",
        "phase2_feasibility_pillar",
        "phase5_spatial_precision_mismatch_score",
        "phase5_weighted_p90_ubs_km",
        "phase5_population_share_pharmacy_le_2km",
        "phase5_population_share_hard_ubs_easy_pharmacy",
        "phase5_precision_status",
        "phase5_evidence_grade",
    ]
    return result.loc[result["phase5_index_eligibility"].eq("eligible_phase5_precision"), columns].head(limit)


def build_metadata(result: pd.DataFrame) -> dict:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": "telemedicine_precision_index",
        "phase": "phase5_spatial_precision",
        "index_version": "phase5-population-weighted-geodesic-v1",
        "eligible_municipalities": int(result["phase5_index_eligibility"].eq("eligible_phase5_precision").sum()),
        "precision_status_counts": {
            str(k): int(v) for k, v in result["phase5_precision_status"].fillna("missing").value_counts().sort_index().items()
        },
        "weights": {"need": 0.45, "spatial_precision": 0.35, "feasibility": 0.20},
        "minimum_population_origin_coverage_ratio": 0.90,
        "spatial_precision_components": {
            "phase5_ubs_p90_barrier_percentile": 0.45,
            "phase5_pharmacy_near_share_percentile": 0.25,
            "phase5_hard_easy_share_percentile": 0.30,
        },
        "distance_status": "geodesic_not_travel_time",
        "academic_use_note": "Treat B2 municipal-proxy results as a reproducible scaffold. Use A-grade intramunicipal origins plus routed travel times for stronger academic claims.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_opportunity_phase2.csv")
    parser.add_argument("--precision-access", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_precision_spatial_access.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_precision_index.csv")
    parser.add_argument("--shortlist-output", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_precision_shortlist.csv")
    parser.add_argument("--metadata", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_precision_metadata.json")
    args = parser.parse_args()

    result = build_precision_index(
        pd.read_csv(args.phase2, dtype={"ibge_municipio_7": str}, low_memory=False),
        pd.read_csv(args.precision_access, dtype={"ibge_municipio_7": str}),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    build_shortlist(result).to_csv(args.shortlist_output, index=False)
    args.metadata.write_text(json.dumps(build_metadata(result), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 5 precision index for {len(result):,} municipalities")


if __name__ == "__main__":
    main()
