"""Validate whether UBS coordinates fall inside their declared IBGE municipality."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from analyze_ubs import IBGE_UF_TO_SIGLA, add_region, normalize_columns, normalize_decimal_series, read_ubs_csv


MALHAS_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf_id}"
    "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
)


def _point_on_segment(x: float, y: float, a: list[float], b: list[float], eps: float = 1e-10) -> bool:
    ax, ay = a
    bx, by = b
    cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
    if abs(cross) > eps:
        return False
    return min(ax, bx) - eps <= x <= max(ax, bx) + eps and min(ay, by) - eps <= y <= max(ay, by) + eps


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 4:
        return False

    previous = ring[-1]
    for current in ring:
        if _point_on_segment(x, y, previous, current):
            return True
        xi, yi = current
        xj, yj = previous
        intersects = (yi > y) != (yj > y)
        if intersects:
            x_intersection = (xj - xi) * (y - yi) / ((yj - yi) or 1e-20) + xi
            if x <= x_intersection:
                inside = not inside
        previous = current

    return inside


def _polygon_bbox(multipolygon: list[Any]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for polygon in multipolygon:
        for ring in polygon:
            for x, y in ring:
                xs.append(float(x))
                ys.append(float(y))
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_multipolygon(lon: float, lat: float, multipolygon: list[Any], bbox: tuple[float, float, float, float]) -> bool:
    min_x, min_y, max_x, max_y = bbox
    if lon < min_x or lon > max_x or lat < min_y or lat > max_y:
        return False

    for polygon in multipolygon:
        outer = polygon[0]
        holes = polygon[1:]
        if _point_in_ring(lon, lat, outer) and not any(_point_in_ring(lon, lat, hole) for hole in holes):
            return True
    return False


def fetch_or_load_malhas(cache_path: Path, timeout: int = 60) -> dict[str, dict[str, Any]]:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    malhas: dict[str, dict[str, Any]] = {}
    for uf_id in sorted(IBGE_UF_TO_SIGLA):
        url = MALHAS_URL.format(uf_id=uf_id)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        for feature in payload.get("features", []):
            code = str(feature.get("properties", {}).get("codarea", "")).strip()
            geometry = feature.get("geometry") or {}
            geometry_type = geometry.get("type")
            if geometry_type == "MultiPolygon":
                coordinates = geometry.get("coordinates", [])
            elif geometry_type == "Polygon":
                coordinates = [geometry.get("coordinates", [])]
            else:
                coordinates = []
            if code and coordinates:
                malhas[code] = {
                    "uf_id": uf_id,
                    "uf_sigla": IBGE_UF_TO_SIGLA[uf_id],
                    "coordinates": coordinates,
                    "bbox": _polygon_bbox(coordinates),
                }

    cache_path.write_text(json.dumps(malhas, ensure_ascii=False), encoding="utf-8")
    return malhas


def build_spatial_validation(
    ubs_path: Path,
    territory_path: Path,
    output_by_uf: Path,
    output_suspects: Path,
    output_metadata: Path,
    cache_path: Path,
) -> None:
    ubs = add_region(normalize_columns(read_ubs_csv(ubs_path)))
    ubs["latitude"] = normalize_decimal_series(ubs["latitude"])
    ubs["longitude"] = normalize_decimal_series(ubs["longitude"])
    ubs["ibge_municipio"] = pd.to_numeric(ubs["ibge"], errors="coerce").astype("Int64")

    territory = pd.read_csv(territory_path)
    code_map = territory[["ibge_municipio", "ibge_municipio_7", "municipio_nome_ibge", "uf_sigla"]].drop_duplicates()
    ubs = ubs.merge(code_map, on="ibge_municipio", how="left", suffixes=("", "_territory"))
    ubs["municipal_polygon_code"] = pd.to_numeric(ubs["ibge_municipio_7"], errors="coerce").astype("Int64").astype(str)
    ubs.loc[ubs["municipal_polygon_code"].eq("<NA>"), "municipal_polygon_code"] = pd.NA

    malhas = fetch_or_load_malhas(cache_path)
    statuses: list[str] = []

    for row in ubs.itertuples(index=False):
        lat = row.latitude
        lon = row.longitude
        code = getattr(row, "municipal_polygon_code")
        if pd.isna(lat) or pd.isna(lon):
            statuses.append("missing_coordinates")
            continue
        if not (-34 <= lat <= 6 and -74 <= lon <= -34):
            statuses.append("outside_brazil_bbox")
            continue
        if pd.isna(code) or str(code) not in malhas:
            statuses.append("missing_municipal_polygon")
            continue

        polygon = malhas[str(code)]
        inside = _point_in_multipolygon(float(lon), float(lat), polygon["coordinates"], tuple(polygon["bbox"]))
        statuses.append("inside_declared_municipality" if inside else "outside_declared_municipality")

    ubs["spatial_validation_status"] = statuses
    status_columns = [
        "inside_declared_municipality",
        "outside_declared_municipality",
        "missing_coordinates",
        "outside_brazil_bbox",
        "missing_municipal_polygon",
    ]
    for status in status_columns:
        ubs[status] = ubs["spatial_validation_status"].eq(status)

    by_uf = (
        ubs.groupby(["uf_sigla", "region"], dropna=False)
        .agg(
            ubs_records=("cnes", "size"),
            inside_declared_municipality=("inside_declared_municipality", "sum"),
            outside_declared_municipality=("outside_declared_municipality", "sum"),
            missing_coordinates=("missing_coordinates", "sum"),
            outside_brazil_bbox=("outside_brazil_bbox", "sum"),
            missing_municipal_polygon=("missing_municipal_polygon", "sum"),
        )
        .reset_index()
    )
    by_uf["inside_declared_municipality_pct"] = (
        by_uf["inside_declared_municipality"] / by_uf["ubs_records"] * 100
    )
    by_uf["spatial_issue_records"] = by_uf["ubs_records"] - by_uf["inside_declared_municipality"]
    by_uf["spatial_issue_pct"] = by_uf["spatial_issue_records"] / by_uf["ubs_records"] * 100

    suspect_columns = [
        "cnes",
        "uf_sigla",
        "ibge_municipio",
        "ibge_municipio_7",
        "municipio_nome_ibge",
        "nome",
        "latitude",
        "longitude",
        "spatial_validation_status",
    ]
    suspects = ubs.loc[~ubs["inside_declared_municipality"], suspect_columns].copy()

    output_by_uf.parent.mkdir(parents=True, exist_ok=True)
    by_uf.sort_values("inside_declared_municipality_pct").to_csv(output_by_uf, index=False)
    suspects.sort_values(["uf_sigla", "spatial_validation_status", "ibge_municipio", "cnes"]).to_csv(
        output_suspects, index=False
    )

    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "IBGE API de malhas geograficas",
        "source_url_template": MALHAS_URL,
        "geometry_quality": "minima",
        "intrarregiao": "municipio",
        "cached_polygons": len(malhas),
        "ubs_records": int(len(ubs)),
        "suspect_records": int(len(suspects)),
        "method": "Point-in-polygon against the declared IBGE municipality polygon; simplified IBGE meshes are used for screening, not cadastral precision.",
    }
    output_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate UBS coordinates against IBGE municipal meshes.")
    parser.add_argument("--ubs", default="projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv")
    parser.add_argument(
        "--territory",
        default="projects/ubs-healthcare-mapping/data/enriched/municipality_ubs_territory.csv",
    )
    parser.add_argument("--output-by-uf", default="projects/ubs-healthcare-mapping/data/spatial_validation_by_uf.csv")
    parser.add_argument("--output-suspects", default="projects/ubs-healthcare-mapping/data/spatial_validation_suspect_ubs.csv")
    parser.add_argument("--metadata", default="projects/ubs-healthcare-mapping/data/spatial_validation_metadata.json")
    parser.add_argument("--cache", default="projects/ubs-healthcare-mapping/data/geodata/ibge_malhas_municipais_minima.json")
    args = parser.parse_args()

    build_spatial_validation(
        Path(args.ubs),
        Path(args.territory),
        Path(args.output_by_uf),
        Path(args.output_suspects),
        Path(args.metadata),
        Path(args.cache),
    )
    print(f"Saved spatial validation to {args.output_by_uf} and {args.output_suspects}")


if __name__ == "__main__":
    main()
