"""Build municipal geodesic access proxies for active UBS and OSM pharmacies."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


EARTH_RADIUS_KM = 6371.0088


def _rings(value: object) -> list[list[list[float]]]:
    if not isinstance(value, list) or not value:
        return []
    first = value[0]
    if (
        isinstance(first, list) and len(first) >= 2
        and isinstance(first[0], (int, float)) and isinstance(first[1], (int, float))
    ):
        return [value]
    result = []
    for child in value:
        result.extend(_rings(child))
    return result


def _ring_area_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    points = ring if ring[0] == ring[-1] else [*ring, ring[0]]
    cross_sum = 0.0
    x_sum = 0.0
    y_sum = 0.0
    for first, second in zip(points, points[1:]):
        cross = first[0] * second[1] - second[0] * first[1]
        cross_sum += cross
        x_sum += (first[0] + second[0]) * cross
        y_sum += (first[1] + second[1]) * cross
    area = cross_sum / 2
    if abs(area) < 1e-12:
        return 0.0, float(np.mean([point[0] for point in ring])), float(np.mean([point[1] for point in ring]))
    return area, x_sum / (6 * area), y_sum / (6 * area)


def _point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        crosses = (y1 > latitude) != (y2 > latitude)
        if crosses:
            boundary_x = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < boundary_x:
                inside = not inside
        previous = current
    return inside


def main_ring_centroid(coordinates: object) -> tuple[float, float, bool]:
    candidates = []
    for ring in _rings(coordinates):
        area, longitude, latitude = _ring_area_centroid(ring)
        candidates.append((abs(area), longitude, latitude, ring))
    if not candidates:
        raise ValueError("Municipal geometry has no polygon ring")
    _, longitude, latitude, ring = max(candidates, key=lambda item: item[0])
    return longitude, latitude, _point_in_ring(longitude, latitude, ring)


def build_origins(geometry: dict, universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, item in geometry.items():
        longitude, latitude, inside = main_ring_centroid(item["coordinates"])
        rows.append({
            "ibge_municipio_7": str(code),
            "origin_longitude": longitude,
            "origin_latitude": latitude,
            "origin_inside_main_polygon": inside,
            "origin_method": "centroid_of_largest_simplified_municipal_polygon",
        })
    origins = pd.DataFrame(rows)
    official = universe.copy()
    official["ibge_municipio_7"] = official["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    return official.merge(origins, on="ibge_municipio_7", how="left", validate="one_to_one")


def _sphere_points(latitude: pd.Series, longitude: pd.Series) -> np.ndarray:
    lat = np.radians(pd.to_numeric(latitude).to_numpy(float))
    lon = np.radians(pd.to_numeric(longitude).to_numpy(float))
    return np.column_stack((np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)))


def nearest_facility(origins: pd.DataFrame, facilities: pd.DataFrame, label: str) -> pd.DataFrame:
    valid_origins = origins["origin_latitude"].notna() & origins["origin_longitude"].notna()
    valid_facilities = facilities["latitude"].between(-34, 6) & facilities["longitude"].between(-74, -28)
    facility = facilities.loc[valid_facilities].reset_index(drop=True)
    if facility.empty:
        raise ValueError(f"No valid {label} facility coordinates")
    output = origins[["ibge_municipio_7"]].copy()
    output[f"nearest_{label}_id"] = pd.NA
    output[f"nearest_{label}_geodesic_km"] = np.nan
    tree = cKDTree(_sphere_points(facility["latitude"], facility["longitude"]))
    chord, index = tree.query(_sphere_points(
        origins.loc[valid_origins, "origin_latitude"], origins.loc[valid_origins, "origin_longitude"]
    ), k=1)
    angular = 2 * np.arcsin(np.clip(chord / 2, 0, 1))
    output.loc[valid_origins, f"nearest_{label}_geodesic_km"] = angular * EARTH_RADIUS_KM
    output.loc[valid_origins, f"nearest_{label}_id"] = facility.iloc[index]["facility_id"].astype(str).to_numpy()
    return output


def classify_mismatch(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    complete = result["nearest_ubs_geodesic_km"].notna() & result["nearest_pharmacy_geodesic_km"].notna()
    ubs_threshold = result.loc[complete, "nearest_ubs_geodesic_km"].quantile(0.75)
    pharmacy_threshold = result.loc[complete, "nearest_pharmacy_geodesic_km"].quantile(0.25)
    result["phase2_ubs_far_threshold_km_p75"] = ubs_threshold
    result["phase2_pharmacy_near_threshold_km_p25"] = pharmacy_threshold
    result["hard_ubs_easy_pharmacy_flag"] = (
        complete
        & result["nearest_ubs_geodesic_km"].ge(ubs_threshold)
        & result["nearest_pharmacy_geodesic_km"].le(pharmacy_threshold)
        & pd.to_numeric(result["pharmacies"], errors="coerce").gt(0)
    )
    result["spatial_access_status"] = "geodesic_centroid_proxy_not_travel_time"
    result.loc[~complete, "spatial_access_status"] = "insufficient_spatial_data"
    return result


def load_active_ubs(ubs_path: Path, operations_path: Path, suspects_path: Path) -> pd.DataFrame:
    ubs = pd.read_csv(ubs_path, sep=";", dtype={"CNES": str})
    operations = pd.read_csv(operations_path, dtype={"cnes": str})
    active_ids = set(
        operations.loc[operations["cnes_present_latest_st"].eq(True), "cnes"]
        .astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(7)
    )
    suspects = pd.read_csv(suspects_path, dtype={"cnes": str})
    suspect_ids = set(
        suspects["cnes"].dropna().astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(7)
    )
    ubs["cnes"] = ubs["CNES"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(7)
    ubs["latitude"] = pd.to_numeric(ubs["LATITUDE"].astype("string").str.replace(",", ".", regex=False), errors="coerce")
    ubs["longitude"] = pd.to_numeric(ubs["LONGITUDE"].astype("string").str.replace(",", ".", regex=False), errors="coerce")
    ubs = ubs.loc[ubs["cnes"].isin(active_ids) & ~ubs["cnes"].isin(suspect_ids)].copy()
    ubs["facility_id"] = ubs["cnes"]
    return ubs[["facility_id", "latitude", "longitude"]].drop_duplicates("facility_id")


def main() -> None:
    root = Path("projects/ubs-healthcare-mapping")
    parser = argparse.ArgumentParser(description="Build Phase 2 municipal spatial-access proxies.")
    parser.add_argument("--geometry", type=Path, default=root / "data/geodata/ibge_malhas_municipais_minima.json")
    parser.add_argument("--universe", type=Path, default=root / "data/reference/ibge_municipality_universe.csv")
    parser.add_argument("--ubs", type=Path, default=root / "data/Unidades_Basicas_Saude-UBS.csv")
    parser.add_argument("--operations", type=Path, default=root / "data/ubs_operational_status.csv")
    parser.add_argument("--suspects", type=Path, default=root / "data/spatial_validation_suspect_ubs.csv")
    parser.add_argument("--osm-pharmacies", type=Path, default=root / "data/spatial/osm_pharmacies.csv")
    parser.add_argument("--phase1", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase1.csv")
    parser.add_argument("--output", type=Path, default=root / "data/enriched/municipality_phase2_spatial_access.csv")
    parser.add_argument("--metadata", type=Path, default=root / "data/enriched/municipality_phase2_spatial_access_metadata.json")
    args = parser.parse_args()

    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
    origins = build_origins(geometry, pd.read_csv(args.universe, dtype=str))
    active_ubs = load_active_ubs(args.ubs, args.operations, args.suspects)
    osm = pd.read_csv(args.osm_pharmacies)
    osm = osm.loc[osm["valid_coordinates"].eq(True)].copy()
    osm["facility_id"] = osm["osm_feature_id"]
    ubs_access = nearest_facility(origins, active_ubs, "ubs")
    pharmacy_access = nearest_facility(origins, osm, "pharmacy")
    result = origins.merge(ubs_access, on="ibge_municipio_7", validate="one_to_one")
    result = result.merge(pharmacy_access, on="ibge_municipio_7", validate="one_to_one")
    phase1 = pd.read_csv(args.phase1, dtype={"ibge_municipio_7": str})
    result = result.merge(
        phase1[["ibge_municipio_7", "pharmacies", "populacao_residente"]].drop_duplicates("ibge_municipio_7"),
        on="ibge_municipio_7", how="left", validate="one_to_one",
    )
    result = classify_mismatch(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "origin": "centroid of largest polygon in simplified IBGE municipal geometry",
        "ubs_facilities": len(active_ubs),
        "ubs_rule": "present in latest CNES/ST and not listed by the existing municipal-geometry suspect audit",
        "pharmacy_facilities": len(osm),
        "pharmacy_rule": "OpenStreetMap amenity=pharmacy; independent from official PFPB accreditation",
        "distance": "great-circle/geodesic distance in kilometres",
        "hard_ubs_easy_pharmacy_rule": "UBS distance >= national P75, pharmacy distance <= national P25, and at least one official PFPB record",
        "important_limit": "This is not travel time, a road-network route, or population-weighted access. Municipal geometric centroids may not represent where residents live.",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 2 spatial proxies for {len(result):,} municipalities to {args.output}")


if __name__ == "__main__":
    main()
