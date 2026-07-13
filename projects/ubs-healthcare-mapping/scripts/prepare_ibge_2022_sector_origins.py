"""Prepare IBGE 2022 census-sector population origins for Phase 5.

Inputs:
- a UF sector shapefile ZIP from IBGE Malha de Setores Censitários 2022;
- the IBGE basic sector aggregate CSV or ZIP, where V0001 is total people.

Output is compatible with build_telemedicine_population_origins.py
--manual-origins.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import shapefile

sys.path.append(str(Path(__file__).resolve().parent))
from build_telemedicine_population_origins import normalize_manual_origins


PROJECT_ROOT = Path("projects/ubs-healthcare-mapping")


def _read_csv_from_path_or_zip(path: Path, **kwargs) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No CSV file found inside {path}")
            with archive.open(csv_names[0]) as handle:
                return pd.read_csv(handle, **kwargs)
    return pd.read_csv(path, **kwargs)


def load_basic_population(aggregate_path: Path) -> pd.DataFrame:
    frame = _read_csv_from_path_or_zip(
        aggregate_path,
        sep=";",
        dtype={"CD_SETOR": str, "CD_MUN": str, "v0001": str, "V0001": str},
        encoding="latin1",
        low_memory=False,
    )
    population_column = "V0001" if "V0001" in frame.columns else "v0001"
    if "CD_SETOR" not in frame or population_column not in frame:
        raise ValueError("Aggregate file must include CD_SETOR and V0001/v0001 total-people columns")
    output = frame[["CD_SETOR", population_column]].copy()
    output["CD_SETOR"] = output["CD_SETOR"].astype("string")
    output["origin_population"] = pd.to_numeric(
        output[population_column].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0)
    return output[["CD_SETOR", "origin_population"]]


def _extract_zip_to_temp(zip_path: Path, temp_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(temp_dir)
    shp_files = list(temp_dir.rglob("*.shp"))
    if not shp_files:
        raise ValueError(f"No .shp file found inside {zip_path}")
    return shp_files[0]


def _ring_area_centroid(ring: list[tuple[float, float]]) -> tuple[float, float, float]:
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
        return 0.0, float(sum(point[0] for point in ring) / len(ring)), float(sum(point[1] for point in ring) / len(ring))
    return area, x_sum / (6 * area), y_sum / (6 * area)


def representative_point(shape: shapefile.Shape) -> tuple[float, float]:
    points = [(float(x), float(y)) for x, y in shape.points]
    if not points:
        raise ValueError("Shape has no points")
    part_starts = list(shape.parts) + [len(points)]
    rings = [points[start:end] for start, end in zip(part_starts, part_starts[1:]) if end > start]
    centroids = [_ring_area_centroid(ring) for ring in rings if len(ring) >= 3]
    if not centroids:
        return float(sum(x for x, _ in points) / len(points)), float(sum(y for _, y in points) / len(points))
    _, longitude, latitude = max(centroids, key=lambda item: abs(item[0]))
    return longitude, latitude


def load_sector_geometry(shapefile_zip: Path) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as temp:
        shp_path = _extract_zip_to_temp(shapefile_zip, Path(temp))
        reader = shapefile.Reader(str(shp_path), encoding="utf-8")
        fields = [field[0] for field in reader.fields[1:]]
        rows = []
        try:
            for record in reader.iterShapeRecords():
                attrs = dict(zip(fields, record.record))
                if "CD_SETOR" not in attrs or "CD_MUN" not in attrs:
                    raise ValueError("Sector shapefile must include CD_SETOR and CD_MUN attributes")
                longitude, latitude = representative_point(record.shape)
                rows.append({
                    "CD_SETOR": str(attrs["CD_SETOR"]),
                    "ibge_municipio_7": str(attrs["CD_MUN"]),
                    "municipio_nome": attrs.get("NM_MUN"),
                    "uf_sigla": attrs.get("SIGLA_UF") or attrs.get("CD_UF"),
                    "sector_situation": attrs.get("SITUACAO"),
                    "origin_longitude": longitude,
                    "origin_latitude": latitude,
                })
        finally:
            reader.close()
    return pd.DataFrame(rows)


def build_sector_origins(shapefile_zip: Path, aggregate_path: Path) -> pd.DataFrame:
    geometry = load_sector_geometry(shapefile_zip)
    population = load_basic_population(aggregate_path)
    result = geometry.merge(population, on="CD_SETOR", how="left", validate="one_to_one")
    missing_population = result["origin_population"].isna()
    result["origin_population"] = result["origin_population"].fillna(0)
    result["origin_id"] = result["CD_SETOR"]
    result["origin_source"] = "IBGE Censo 2022 setores: malha setorial + agregado básico V0001"
    result["origin_granularity"] = "census_sector"
    result["source_year"] = 2022
    result["representative_point_method"] = "largest_polygon_ring_centroid_from_sector_shapefile"
    result["origin_population_status"] = "available"
    result.loc[missing_population, "origin_population_status"] = "missing_sector_population_not_scored"
    result["precision_status"] = "intramunicipal_population_origins_loaded"
    result.loc[missing_population, "precision_status"] = "intramunicipal_geometry_loaded_population_missing"
    columns = [
        "origin_id", "ibge_municipio_7", "municipio_nome", "uf_sigla",
        "origin_latitude", "origin_longitude", "origin_population",
        "origin_population_status", "origin_source", "origin_granularity",
        "source_year", "representative_point_method", "precision_status",
        "sector_situation",
    ]
    return normalize_manual_origins(result[columns], allow_non_2022=False)


def build_metadata(origins: pd.DataFrame, shapefile_zip: Path, aggregate_path: Path) -> dict:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": "ibge_2022_sector_population_origins",
        "phase": "phase5a_ibge_intramunicipal_origins",
        "shapefile_zip": str(shapefile_zip),
        "aggregate_path": str(aggregate_path),
        "origin_rows": int(len(origins)),
        "municipalities": int(origins["ibge_municipio_7"].nunique()),
        "total_origin_population": float(origins["origin_population"].sum()),
        "missing_population_origins": int(origins["origin_population_status"].eq("missing_sector_population_not_scored").sum()),
        "source_year": 2022,
        "population_variable": "V0001/v0001: Total de pessoas",
        "evidence_grade_when_used": "A_intramunicipal_population_weighted_geodesic_ready",
        "important_limit": "Representative points are centroids of sector polygons, not address-level resident coordinates.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector-shapefile-zip", type=Path, required=True)
    parser.add_argument("--basic-aggregate", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_population_origins_ibge2022_sectors.csv")
    parser.add_argument("--metadata", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_population_origins_ibge2022_sectors_metadata.json")
    args = parser.parse_args()

    origins = build_sector_origins(args.sector_shapefile_zip, args.basic_aggregate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    origins.to_csv(args.output, index=False)
    args.metadata.write_text(
        json.dumps(build_metadata(origins, args.sector_shapefile_zip, args.basic_aggregate), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(origins):,} IBGE 2022 sector origins for {origins['ibge_municipio_7'].nunique():,} municipalities")


if __name__ == "__main__":
    main()
