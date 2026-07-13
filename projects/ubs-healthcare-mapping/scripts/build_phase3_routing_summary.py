"""Summarize Phase 3 routed access signals by municipality."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


ROOT = Path("projects/ubs-healthcare-mapping")


def build_summary(routed: pd.DataFrame) -> pd.DataFrame:
    base_columns = [
        "ibge_municipio_7",
        "municipio_nome_oficial",
        "uf_sigla_oficial",
        "phase2_spatial_target_rank",
        "origin_method",
    ]
    base = routed[base_columns].drop_duplicates("ibge_municipio_7").copy()
    wide = routed.pivot_table(
        index="ibge_municipio_7",
        columns="destination_type",
        values=["phase2_geodesic_km", "network_distance_km", "travel_time_minutes"],
        aggfunc="first",
    )
    wide.columns = [f"{destination}_{metric}" for metric, destination in wide.columns]
    wide = wide.reset_index()
    result = base.merge(wide, on="ibge_municipio_7", how="left", validate="one_to_one")
    result["phase3_ubs_hard_minutes_threshold"] = 15
    result["phase3_pharmacy_easy_minutes_threshold"] = 5
    result["phase3_routed_hard_ubs_easy_pharmacy_flag"] = (
        result["active_ubs_travel_time_minutes"].ge(result["phase3_ubs_hard_minutes_threshold"])
        & result["osm_pharmacy_travel_time_minutes"].le(result["phase3_pharmacy_easy_minutes_threshold"])
    )
    result["phase3_access_interpretation"] = "routed_not_conservative_target"
    result.loc[result["phase3_routed_hard_ubs_easy_pharmacy_flag"], "phase3_access_interpretation"] = (
        "routed_hard_ubs_easy_pharmacy_candidate"
    )
    result.loc[
        result["active_ubs_travel_time_minutes"].ge(result["phase3_ubs_hard_minutes_threshold"])
        & result["osm_pharmacy_travel_time_minutes"].gt(result["phase3_pharmacy_easy_minutes_threshold"]),
        "phase3_access_interpretation",
    ] = "routed_hard_ubs_but_not_easy_pharmacy"
    result["phase3_time_ratio_ubs_to_pharmacy"] = (
        result["active_ubs_travel_time_minutes"] / result["osm_pharmacy_travel_time_minutes"]
    )
    return result.sort_values(
        ["phase3_routed_hard_ubs_easy_pharmacy_flag", "phase3_time_ratio_ubs_to_pharmacy"],
        ascending=[False, False],
    ).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 3 municipal routing summary.")
    parser.add_argument("--input", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_od_matrix_routed.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_summary.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_summary_metadata.json")
    args = parser.parse_args()

    routed = pd.read_csv(args.input, dtype={"ibge_municipio_7": str})
    summary = build_summary(routed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": str(args.input),
        "municipalities": len(summary),
        "routed_hard_ubs_easy_pharmacy_candidates": int(summary["phase3_routed_hard_ubs_easy_pharmacy_flag"].sum()),
        "rule": "UBS travel time >= 15 minutes and OSM pharmacy travel time <= 5 minutes, using the routed matrix source.",
        "important_limit": "Thresholds are operational screens for validation, not clinical access standards.",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 3 routing summary for {len(summary):,} municipalities to {args.output}")


if __name__ == "__main__":
    main()
