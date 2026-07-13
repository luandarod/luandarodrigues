"""Build Phase 3 origin-destination pairs for road-network routing."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


ROOT = Path("projects/ubs-healthcare-mapping")


def normalize_cnes(value: object) -> str:
    text = str(value).strip().replace(".0", "")
    digits = re.sub(r"\D", "", text)
    return digits.zfill(7) if digits else ""


def load_ubs_coordinates(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep=";", dtype=str)
    frame["destination_id"] = frame["CNES"].map(normalize_cnes)
    frame["destination_name"] = frame["NOME"].fillna("")
    frame["destination_latitude"] = pd.to_numeric(
        frame["LATITUDE"].astype("string").str.replace(",", ".", regex=False), errors="coerce"
    )
    frame["destination_longitude"] = pd.to_numeric(
        frame["LONGITUDE"].astype("string").str.replace(",", ".", regex=False), errors="coerce"
    )
    return frame[[
        "destination_id",
        "destination_name",
        "destination_latitude",
        "destination_longitude",
    ]].drop_duplicates("destination_id")


def load_osm_pharmacy_coordinates(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str)
    frame["destination_id"] = frame["osm_feature_id"]
    frame["destination_name"] = frame["name"].fillna("")
    frame["destination_latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["destination_longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    return frame[[
        "destination_id",
        "destination_name",
        "destination_latitude",
        "destination_longitude",
    ]].drop_duplicates("destination_id")


def _candidate_rows(shortlist: pd.DataFrame, facilities: pd.DataFrame, destination_type: str) -> pd.DataFrame:
    id_column = "nearest_ubs_id" if destination_type == "active_ubs" else "nearest_pharmacy_id"
    distance_column = (
        "nearest_ubs_geodesic_km" if destination_type == "active_ubs" else "nearest_pharmacy_geodesic_km"
    )
    rows = shortlist[[
        "ibge_municipio_7",
        "municipio_nome_oficial",
        "uf_sigla_oficial",
        "origin_latitude",
        "origin_longitude",
        "origin_method",
        "phase2_spatial_target_rank",
        id_column,
        distance_column,
    ]].copy()
    rows = rows.rename(columns={
        id_column: "destination_id",
        distance_column: "phase2_geodesic_km",
    })
    if destination_type == "active_ubs":
        rows["destination_id"] = rows["destination_id"].map(normalize_cnes)
    rows = rows.merge(facilities, on="destination_id", how="left", validate="many_to_one")
    rows["destination_type"] = destination_type
    return rows


def build_od_matrix(shortlist: pd.DataFrame, ubs: pd.DataFrame, pharmacies: pd.DataFrame) -> pd.DataFrame:
    frames = [
        _candidate_rows(shortlist, ubs, "active_ubs"),
        _candidate_rows(shortlist, pharmacies, "osm_pharmacy"),
    ]
    result = pd.concat(frames, ignore_index=True)
    result["origin_latitude"] = pd.to_numeric(result["origin_latitude"], errors="coerce")
    result["origin_longitude"] = pd.to_numeric(result["origin_longitude"], errors="coerce")
    result["phase2_geodesic_km"] = pd.to_numeric(result["phase2_geodesic_km"], errors="coerce")
    complete = (
        result["origin_latitude"].notna()
        & result["origin_longitude"].notna()
        & result["destination_latitude"].notna()
        & result["destination_longitude"].notna()
    )
    result["routing_readiness_status"] = "ready_for_network_routing"
    result.loc[~complete, "routing_readiness_status"] = "missing_coordinate_for_routing"
    result["routing_profile"] = "driving"
    result["travel_time_minutes"] = pd.NA
    result["network_distance_km"] = pd.NA
    result["routing_source"] = pd.NA
    result["routing_measured_at_utc"] = pd.NA
    result["academic_interpretation"] = "phase3_od_pair_pending_travel_time"
    safe_destination = result["destination_id"].astype(str).str.replace(r"[^A-Za-z0-9]+", "_", regex=True)
    result["od_pair_id"] = (
        result["ibge_municipio_7"].astype(str) + "_" + result["destination_type"] + "_" + safe_destination
    )
    columns = [
        "od_pair_id",
        "ibge_municipio_7",
        "municipio_nome_oficial",
        "uf_sigla_oficial",
        "phase2_spatial_target_rank",
        "origin_method",
        "origin_latitude",
        "origin_longitude",
        "destination_type",
        "destination_id",
        "destination_name",
        "destination_latitude",
        "destination_longitude",
        "phase2_geodesic_km",
        "routing_profile",
        "routing_readiness_status",
        "travel_time_minutes",
        "network_distance_km",
        "routing_source",
        "routing_measured_at_utc",
        "academic_interpretation",
    ]
    return result[columns].sort_values(["phase2_spatial_target_rank", "destination_type"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 3 routing-ready OD pairs.")
    parser.add_argument("--shortlist", type=Path, default=ROOT / "data/enriched/telemedicine_phase2_ads_geo_shortlist.csv")
    parser.add_argument("--ubs", type=Path, default=ROOT / "data/Unidades_Basicas_Saude-UBS.csv")
    parser.add_argument("--osm-pharmacies", type=Path, default=ROOT / "data/spatial/osm_pharmacies.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_od_matrix.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_od_matrix_metadata.json")
    args = parser.parse_args()

    shortlist = pd.read_csv(args.shortlist, dtype={"ibge_municipio_7": str})
    od_matrix = build_od_matrix(
        shortlist=shortlist,
        ubs=load_ubs_coordinates(args.ubs),
        pharmacies=load_osm_pharmacy_coordinates(args.osm_pharmacies),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    od_matrix.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "phase": "phase3-routing-preparation",
        "source_shortlist": str(args.shortlist),
        "rows": len(od_matrix),
        "municipalities": int(od_matrix["ibge_municipio_7"].nunique()),
        "routing_status": "pending; no travel-time estimate is produced by this script",
        "recommended_next_step": "Route each OD pair with a documented OSRM/ORS profile and timestamp.",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(od_matrix):,} Phase 3 OD pairs to {args.output}")


if __name__ == "__main__":
    main()
