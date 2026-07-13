"""Build Phase 5 population-weighted spatial access metrics."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from build_phase2_spatial_access import load_active_ubs, nearest_facility


PROJECT_ROOT = Path("projects/ubs-healthcare-mapping")


def weighted_quantile(values: pd.Series, weights: pd.Series, quantile: float) -> float:
    valid = pd.to_numeric(values, errors="coerce").notna() & pd.to_numeric(weights, errors="coerce").gt(0)
    if not valid.any():
        return float("nan")
    data = pd.DataFrame({
        "value": pd.to_numeric(values.loc[valid], errors="coerce"),
        "weight": pd.to_numeric(weights.loc[valid], errors="coerce"),
    }).sort_values("value")
    cutoff = quantile * data["weight"].sum()
    cumulative = data["weight"].cumsum()
    return float(data.loc[cumulative.ge(cutoff), "value"].iloc[0])


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = pd.to_numeric(values, errors="coerce").notna() & pd.to_numeric(weights, errors="coerce").gt(0)
    if not valid.any():
        return float("nan")
    return float(np.average(pd.to_numeric(values.loc[valid]), weights=pd.to_numeric(weights.loc[valid])))


def build_origin_access(origins: pd.DataFrame, ubs: pd.DataFrame, pharmacies: pd.DataFrame) -> pd.DataFrame:
    frame = origins.copy()
    frame["origin_latitude"] = pd.to_numeric(frame["origin_latitude"], errors="coerce")
    frame["origin_longitude"] = pd.to_numeric(frame["origin_longitude"], errors="coerce")
    ubs_access = nearest_facility(frame, ubs, "ubs").drop(columns=["ibge_municipio_7"])
    pharmacy_access = nearest_facility(frame, pharmacies, "pharmacy").drop(columns=["ibge_municipio_7"])
    return pd.concat([frame, ubs_access, pharmacy_access], axis=1)


def aggregate_origin_access(origin_access: pd.DataFrame, phase2: pd.DataFrame) -> pd.DataFrame:
    rows = []
    phase2_lookup = phase2.copy()
    phase2_lookup["ibge_municipio_7"] = phase2_lookup["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    phase2_lookup = phase2_lookup.drop_duplicates("ibge_municipio_7").set_index("ibge_municipio_7")

    for code, group in origin_access.groupby("ibge_municipio_7", dropna=False):
        population = pd.to_numeric(group["origin_population"], errors="coerce").fillna(0)
        total_population = float(population.sum())
        ubs_distance = pd.to_numeric(group["nearest_ubs_geodesic_km"], errors="coerce")
        pharmacy_distance = pd.to_numeric(group["nearest_pharmacy_geodesic_km"], errors="coerce")
        valid_both = ubs_distance.notna() & pharmacy_distance.notna() & population.gt(0)
        covered_population = float(population.loc[valid_both].sum())
        municipal_population = float(phase2_lookup.loc[code, "populacao_residente"]) if code in phase2_lookup.index else total_population
        active_ubs = float(phase2_lookup.loc[code, "active_ubs"]) if code in phase2_lookup.index and pd.notna(phase2_lookup.loc[code, "active_ubs"]) else np.nan
        physician_fte = float(phase2_lookup.loc[code, "physician_fte_40h"]) if code in phase2_lookup.index and "physician_fte_40h" in phase2_lookup.columns and pd.notna(phase2_lookup.loc[code, "physician_fte_40h"]) else np.nan
        pharmacies = float(phase2_lookup.loc[code, "pharmacies"]) if code in phase2_lookup.index and pd.notna(phase2_lookup.loc[code, "pharmacies"]) else np.nan
        denominator = covered_population if covered_population > 0 else np.nan
        share_ubs_far = float(population.loc[valid_both & ubs_distance.gt(5)].sum() / denominator) if denominator == denominator else np.nan
        share_pharmacy_near = float(population.loc[valid_both & pharmacy_distance.le(2)].sum() / denominator) if denominator == denominator else np.nan
        share_hard_easy = float(population.loc[valid_both & ubs_distance.gt(5) & pharmacy_distance.le(2)].sum() / denominator) if denominator == denominator else np.nan
        granularity_series = (
            group["origin_granularity"]
            if "origin_granularity" in group
            else pd.Series(["unspecified_intramunicipal_origin"] * len(group), index=group.index)
        )
        granularities = granularity_series.dropna().astype(str).unique().tolist()
        proxy_only = granularities == ["municipality_single_origin"]
        rows.append({
            "ibge_municipio_7": str(code),
            "phase5_population_origins": int(len(group)),
            "phase5_origin_granularity": ";".join(sorted(granularities)),
            "phase5_origin_population": total_population,
            "phase5_population_covered_by_distances": covered_population,
            "phase5_population_origin_coverage_ratio": (
                total_population / municipal_population if municipal_population and municipal_population > 0 else np.nan
            ),
            "phase5_distance_coverage_ratio": (
                covered_population / total_population if total_population > 0 else np.nan
            ),
            "phase5_weighted_mean_ubs_km": _weighted_mean(ubs_distance, population),
            "phase5_weighted_p50_ubs_km": weighted_quantile(ubs_distance, population, 0.50),
            "phase5_weighted_p90_ubs_km": weighted_quantile(ubs_distance, population, 0.90),
            "phase5_weighted_mean_pharmacy_km": _weighted_mean(pharmacy_distance, population),
            "phase5_weighted_p50_pharmacy_km": weighted_quantile(pharmacy_distance, population, 0.50),
            "phase5_weighted_p90_pharmacy_km": weighted_quantile(pharmacy_distance, population, 0.90),
            "phase5_population_share_ubs_gt_5km": share_ubs_far,
            "phase5_population_share_pharmacy_le_2km": share_pharmacy_near,
            "phase5_population_share_hard_ubs_easy_pharmacy": share_hard_easy,
            "phase5_population_per_active_ubs": (
                municipal_population / active_ubs if active_ubs and active_ubs > 0 else np.nan
            ),
            "phase5_population_per_physician_fte": (
                municipal_population / physician_fte if physician_fte and physician_fte > 0 else np.nan
            ),
            "phase5_population_per_pfpb_pharmacy": (
                municipal_population / pharmacies if pharmacies and pharmacies > 0 else np.nan
            ),
            "phase5_precision_status": (
                "municipal_single_origin_proxy_not_intramunicipal"
                if proxy_only
                else "intramunicipal_population_weighted_ready"
            ),
            "phase5_access_evidence_grade": (
                "B2_municipal_population_proxy"
                if proxy_only
                else "A_intramunicipal_population_weighted"
            ),
        })
    return pd.DataFrame(rows)


def build_metadata(origins: pd.DataFrame, output: pd.DataFrame, active_ubs: pd.DataFrame, pharmacies: pd.DataFrame) -> dict:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": "telemedicine_precision_spatial_access",
        "phase": "phase5_spatial_precision",
        "population_origins": int(len(origins)),
        "municipalities": int(output["ibge_municipio_7"].nunique()),
        "ubs_facilities": int(len(active_ubs)),
        "pharmacy_facilities": int(len(pharmacies)),
        "distance": "great-circle/geodesic distance in kilometres; not road-network travel time",
        "weighted_metrics": [
            "population-weighted mean UBS distance",
            "population-weighted p50/p90 UBS distance",
            "population-weighted mean/p50/p90 pharmacy distance",
            "share of population >5 km from nearest active UBS",
            "share of population <=2 km from nearest OSM pharmacy",
            "share of population both >5 km from UBS and <=2 km from pharmacy",
        ],
        "e2sfca_readiness_fields": [
            "phase5_population_per_active_ubs",
            "phase5_population_per_physician_fte",
            "phase5_population_per_pfpb_pharmacy",
        ],
        "precision_status_counts": {
            str(k): int(v) for k, v in output["phase5_precision_status"].value_counts().sort_index().items()
        },
        "academic_use_note": "Academic claims require intramunicipal IBGE 2022 sector/grid origins and, ideally, routed travel-time validation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_population_origins.csv")
    parser.add_argument("--phase2", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_opportunity_phase2.csv")
    parser.add_argument("--ubs", type=Path, default=PROJECT_ROOT / "data/Unidades_Basicas_Saude-UBS.csv")
    parser.add_argument("--operations", type=Path, default=PROJECT_ROOT / "data/ubs_operational_status.csv")
    parser.add_argument("--suspects", type=Path, default=PROJECT_ROOT / "data/spatial_validation_suspect_ubs.csv")
    parser.add_argument("--osm-pharmacies", type=Path, default=PROJECT_ROOT / "data/spatial/osm_pharmacies.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_precision_spatial_access.csv")
    parser.add_argument("--metadata", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_precision_spatial_access_metadata.json")
    args = parser.parse_args()

    origins = pd.read_csv(args.origins, dtype={"ibge_municipio_7": str})
    phase2 = pd.read_csv(args.phase2, dtype={"ibge_municipio_7": str}, low_memory=False)
    active_ubs = load_active_ubs(args.ubs, args.operations, args.suspects)
    pharmacies = pd.read_csv(args.osm_pharmacies)
    pharmacies = pharmacies.loc[pharmacies["valid_coordinates"].eq(True)].copy()
    pharmacies["facility_id"] = pharmacies["osm_feature_id"]
    origin_access = build_origin_access(origins, active_ubs, pharmacies)
    output = aggregate_origin_access(origin_access, phase2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    args.metadata.write_text(json.dumps(build_metadata(origins, output, active_ubs, pharmacies), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 5 population-weighted access for {len(output):,} municipalities")


if __name__ == "__main__":
    main()
