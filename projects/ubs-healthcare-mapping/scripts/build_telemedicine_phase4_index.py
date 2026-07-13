"""Build Phase 4 routed telemedicine validation index."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("projects/ubs-healthcare-mapping")
EPSILON = 1e-6
PHASE4_WEIGHTS = {"need": 0.45, "routed_access": 0.35, "feasibility": 0.20}


def _percentile(values: pd.Series, valid: pd.Series, inverse: bool = False) -> pd.Series:
    output = pd.Series(np.nan, index=values.index, dtype=float)
    sample = pd.to_numeric(values.loc[valid], errors="coerce").dropna()
    if sample.empty:
        return output
    output.loc[sample.index] = sample.rank(pct=True, ascending=not inverse, method="average")
    return output


def _geometric(components: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    matrix = pd.DataFrame(components)
    complete = matrix.notna().all(axis=1)
    output = pd.Series(np.nan, index=matrix.index, dtype=float)
    clipped = matrix.loc[complete].clip(EPSILON, 1)
    output.loc[complete] = np.exp(sum(np.log(clipped[name]) * weight for name, weight in weights.items()))
    return output


def merge_phase4(phase2: pd.DataFrame, routing: pd.DataFrame) -> pd.DataFrame:
    left = phase2.copy()
    right = routing.copy()
    left["ibge_municipio_7"] = left["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    right["ibge_municipio_7"] = right["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    routing_columns = [
        "ibge_municipio_7",
        "active_ubs_travel_time_minutes",
        "osm_pharmacy_travel_time_minutes",
        "active_ubs_network_distance_km",
        "osm_pharmacy_network_distance_km",
        "phase3_routed_hard_ubs_easy_pharmacy_flag",
        "phase3_access_interpretation",
        "phase3_time_ratio_ubs_to_pharmacy",
    ]
    return left.merge(right[routing_columns], on="ibge_municipio_7", how="left", validate="one_to_one")


def build_phase4_index(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    routed = (
        pd.to_numeric(result["active_ubs_travel_time_minutes"], errors="coerce").notna()
        & pd.to_numeric(result["osm_pharmacy_travel_time_minutes"], errors="coerce").notna()
    )
    result["phase4_eligibility"] = "not_routed_phase4"
    result.loc[routed, "phase4_eligibility"] = "eligible_phase4_routed_validation"
    result["phase4_evidence_grade"] = "C_not_routed"
    result.loc[routed, "phase4_evidence_grade"] = "B_routed_public_osrm_proxy"

    result["phase4_ubs_travel_barrier_percentile_routed_subset"] = _percentile(
        result["active_ubs_travel_time_minutes"], routed,
    )
    result["phase4_pharmacy_travel_ease_percentile_routed_subset"] = _percentile(
        result["osm_pharmacy_travel_time_minutes"], routed, inverse=True,
    )
    result["phase4_routed_access_score"] = 100 * _geometric({
        "ubs_barrier": result["phase4_ubs_travel_barrier_percentile_routed_subset"],
        "pharmacy_ease": result["phase4_pharmacy_travel_ease_percentile_routed_subset"],
    }, {"ubs_barrier": 0.65, "pharmacy_ease": 0.35})
    result["phase4_need_pillar"] = pd.to_numeric(result["phase2_need_pillar"], errors="coerce")
    result["phase4_feasibility_pillar"] = pd.to_numeric(result["phase2_feasibility_pillar"], errors="coerce")
    result["telemedicine_phase4_routed_validation"] = 100 * _geometric({
        "need": result["phase4_need_pillar"] / 100,
        "routed_access": result["phase4_routed_access_score"] / 100,
        "feasibility": result["phase4_feasibility_pillar"] / 100,
    }, PHASE4_WEIGHTS)
    result.loc[~routed, "telemedicine_phase4_routed_validation"] = np.nan
    result["phase4_routed_validation_rank"] = result.loc[
        routed, "telemedicine_phase4_routed_validation"
    ].rank(ascending=False, method="min")
    result["phase4_routed_target_rank"] = result.loc[
        routed & result["phase3_routed_hard_ubs_easy_pharmacy_flag"].eq(True),
        "telemedicine_phase4_routed_validation",
    ].rank(ascending=False, method="min")
    result["phase4_interpretation"] = "not_routed_in_phase4"
    result.loc[routed, "phase4_interpretation"] = "routed_validation_not_primary_target"
    result.loc[
        routed & result["phase3_routed_hard_ubs_easy_pharmacy_flag"].eq(True),
        "phase4_interpretation",
    ] = "phase4_primary_routed_target"
    return result.sort_values("telemedicine_phase4_routed_validation", ascending=False, na_position="last")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 4 routed telemedicine validation index.")
    parser.add_argument("--phase2", type=Path, default=ROOT / "data/enriched/telemedicine_opportunity_phase2.csv")
    parser.add_argument("--routing-summary", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_summary.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_opportunity_phase4.csv")
    parser.add_argument("--ads-shortlist-output", type=Path, default=ROOT / "data/enriched/telemedicine_phase4_ads_routed_shortlist.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/enriched/telemedicine_opportunity_phase4_metadata.json")
    args = parser.parse_args()

    result = build_phase4_index(merge_phase4(pd.read_csv(args.phase2, low_memory=False), pd.read_csv(args.routing_summary)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    shortlist = result.loc[
        result["phase4_interpretation"].eq("phase4_primary_routed_target")
    ].sort_values("telemedicine_phase4_routed_validation", ascending=False)
    shortlist.to_csv(args.ads_shortlist_output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "index_version": "phase4-routed-validation-v1",
        "scope": "validation subset only; not a national ranking because only Phase 2 conservative targets were routed",
        "phase4_weights": PHASE4_WEIGHTS,
        "routed_access_weights": {"ubs_travel_barrier": 0.65, "pharmacy_travel_ease": 0.35},
        "primary_target_rule": "Phase 3 routed screen: UBS travel time >= 15 minutes and OSM pharmacy travel time <= 5 minutes",
        "eligible_routed_municipalities": int(result["phase4_eligibility"].eq("eligible_phase4_routed_validation").sum()),
        "primary_routed_targets": int(shortlist.shape[0]),
        "important_limits": [
            "Public OSRM routing must be rerun on a local, versioned OSM extract before academic submission.",
            "Origins are municipal seats, not population-weighted grids.",
            "The pharmacy layer is OSM geography plus municipal PFPB gate, not confirmed partner readiness.",
        ],
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 4 routed validation index for {len(result):,} municipalities; {len(shortlist)} primary routed targets")


if __name__ == "__main__":
    main()
