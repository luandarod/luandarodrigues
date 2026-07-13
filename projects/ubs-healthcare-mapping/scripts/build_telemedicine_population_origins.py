"""Build population-origin points for Phase 5 spatial precision.

The preferred academic input is an IBGE 2022 census-sector or statistical-grid
CSV already converted to representative points. Until that file is supplied,
the script emits a clearly labelled one-origin-per-municipality proxy so the
rest of the pipeline is reproducible without pretending intramunicipal
precision.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path("projects/ubs-healthcare-mapping")
BRAZIL_LATITUDE_RANGE = (-34.0, 6.0)
BRAZIL_LONGITUDE_RANGE = (-74.0, -28.0)
REQUIRED_COLUMNS = {
    "origin_id",
    "ibge_municipio_7",
    "origin_latitude",
    "origin_longitude",
    "origin_population",
    "origin_source",
    "origin_granularity",
}


def _normalise_ibge_code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(7)


def build_proxy_origins(spatial: pd.DataFrame) -> pd.DataFrame:
    """Build a documented municipal fallback from the existing Phase 2 origin."""
    result = spatial.copy()
    result["ibge_municipio_7"] = _normalise_ibge_code(result["ibge_municipio_7"])
    population = pd.to_numeric(result["populacao_residente"], errors="coerce")
    output = pd.DataFrame({
        "origin_id": result["ibge_municipio_7"] + "_municipal_proxy",
        "ibge_municipio_7": result["ibge_municipio_7"],
        "municipio_nome": result.get("municipio_nome_oficial", result.get("municipio_nome_ibge")),
        "uf_sigla": result.get("uf_sigla_oficial", result.get("uf_sigla")),
        "origin_latitude": pd.to_numeric(result["origin_latitude"], errors="coerce"),
        "origin_longitude": pd.to_numeric(result["origin_longitude"], errors="coerce"),
        "origin_population": population.fillna(0),
        "origin_population_status": "available",
        "origin_source": "existing_phase2_municipal_origin_proxy",
        "origin_granularity": "municipality_single_origin",
        "source_year": 2022,
        "representative_point_method": result.get("origin_method", "phase2_origin"),
        "precision_status": "needs_intramunicipal_population_origins",
    })
    output.loc[population.isna(), "origin_population_status"] = "missing_population_not_scored"
    output.loc[population.isna(), "precision_status"] = "missing_population_not_scored"
    return validate_origins(output)


def normalize_manual_origins(origins: pd.DataFrame, allow_non_2022: bool = False) -> pd.DataFrame:
    """Normalize user-supplied official 2022 origin CSV columns.

    The CSV must already include representative coordinates. This avoids a
    hidden dependency on shapefile/geopackage engines and keeps the import step
    explicit for pre-paper reproducibility.
    """
    result = origins.copy()
    missing = REQUIRED_COLUMNS.difference(result.columns)
    if missing:
        raise ValueError(f"Manual origin CSV is missing required columns: {sorted(missing)}")
    result["ibge_municipio_7"] = _normalise_ibge_code(result["ibge_municipio_7"])
    result["origin_id"] = result["origin_id"].astype("string")
    result["origin_latitude"] = pd.to_numeric(result["origin_latitude"], errors="coerce")
    result["origin_longitude"] = pd.to_numeric(result["origin_longitude"], errors="coerce")
    result["origin_population"] = pd.to_numeric(result["origin_population"], errors="coerce")
    if "source_year" not in result:
        result["source_year"] = 2022
    result["source_year"] = pd.to_numeric(result["source_year"], errors="coerce").astype("Int64")
    if not allow_non_2022 and not result["source_year"].eq(2022).all():
        bad_years = sorted(result.loc[~result["source_year"].eq(2022), "source_year"].dropna().astype(int).unique().tolist())
        raise ValueError(f"Phase 5 requires IBGE 2022 origins by default; found non-2022 source years: {bad_years}")
    if "precision_status" not in result:
        result["precision_status"] = "intramunicipal_population_origins_loaded"
    if "representative_point_method" not in result:
        result["representative_point_method"] = "supplied_representative_point"
    return validate_origins(result)


def blend_manual_with_proxy(manual_origins: pd.DataFrame, proxy_origins: pd.DataFrame) -> pd.DataFrame:
    """Use manual intramunicipal origins where available and proxy elsewhere."""
    manual = manual_origins.copy()
    proxy = proxy_origins.copy()
    manual["ibge_municipio_7"] = _normalise_ibge_code(manual["ibge_municipio_7"])
    proxy["ibge_municipio_7"] = _normalise_ibge_code(proxy["ibge_municipio_7"])
    manual_municipalities = set(manual["ibge_municipio_7"].dropna().astype(str))
    kept_proxy = proxy.loc[~proxy["ibge_municipio_7"].astype(str).isin(manual_municipalities)].copy()
    blended = pd.concat([manual, kept_proxy], ignore_index=True, sort=False)
    return validate_origins(blended)


def validate_origins(origins: pd.DataFrame) -> pd.DataFrame:
    result = origins.copy()
    missing = REQUIRED_COLUMNS.difference(result.columns)
    if missing:
        raise ValueError(f"Origin table is missing required columns: {sorted(missing)}")
    if result["origin_id"].duplicated().any():
        duplicated = result.loc[result["origin_id"].duplicated(), "origin_id"].head(5).tolist()
        raise ValueError(f"Origin IDs must be unique; duplicated examples: {duplicated}")
    if result["ibge_municipio_7"].isna().any():
        raise ValueError("Every origin must have an IBGE 7-digit municipality code")
    valid_coordinates = (
        pd.to_numeric(result["origin_latitude"], errors="coerce").between(*BRAZIL_LATITUDE_RANGE)
        & pd.to_numeric(result["origin_longitude"], errors="coerce").between(*BRAZIL_LONGITUDE_RANGE)
    )
    if not valid_coordinates.all():
        invalid = result.loc[~valid_coordinates, ["origin_id", "origin_latitude", "origin_longitude"]].head(5).to_dict("records")
        raise ValueError(f"Origins outside plausible Brazil coordinate bounds: {invalid}")
    valid_population = pd.to_numeric(result["origin_population"], errors="coerce").ge(0)
    if not valid_population.all():
        invalid = result.loc[~valid_population, ["origin_id", "origin_population"]].head(5).to_dict("records")
        raise ValueError(f"Origins must have non-negative population: {invalid}")
    return result


def build_metadata(origins: pd.DataFrame, source_kind: str, source_path: Path | None) -> dict:
    by_granularity = origins["origin_granularity"].value_counts().sort_index()
    proxy_only = origins["origin_granularity"].eq("municipality_single_origin").all()
    has_intramunicipal = origins["origin_granularity"].ne("municipality_single_origin").any()
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": "telemedicine_population_origins",
        "phase": "phase5_spatial_precision",
        "source_kind": source_kind,
        "source_path": None if source_path is None else str(source_path),
        "source_year_rule": "IBGE 2022 required unless --allow-non-2022 is explicitly used",
        "origin_rows": int(len(origins)),
        "municipalities": int(origins["ibge_municipio_7"].nunique()),
        "total_origin_population": float(origins["origin_population"].sum()),
        "missing_population_origins": int(origins.get("origin_population_status", pd.Series(dtype=str)).eq("missing_population_not_scored").sum()),
        "origin_granularity_counts": {str(k): int(v) for k, v in by_granularity.items()},
        "precision_status": (
            "intramunicipal_origins_loaded_with_proxy_backfill"
            if has_intramunicipal and not proxy_only and origins["origin_granularity"].eq("municipality_single_origin").any()
            else "manual_intramunicipal_origins_loaded"
            if has_intramunicipal
            else "municipal_single_origin_proxy_pending_ibge_2022_sector_or_grid_origins"
        ),
        "academic_use_note": (
            "Use the proxy output only as a reproducible process scaffold. "
            "For academic spatial inference, supply IBGE 2022 census-sector or statistical-grid "
            "representative points with population."
        ),
        "official_source_references": [
            "https://www.ibge.gov.br/estatisticas/downloads-estatisticas.html",
            "https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/26565-malhas-de-setores-censitarios-divisoes-intramunicipais.html",
            "https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2-spatial", type=Path, default=PROJECT_ROOT / "data/enriched/municipality_phase2_spatial_access.csv")
    parser.add_argument("--manual-origins", type=Path, help="CSV with official 2022 origin_id, ibge_municipio_7, lat/lon and population.")
    parser.add_argument("--blend-with-proxy", action="store_true", help="When manual origins cover only part of Brazil, keep Phase 2 proxy origins for other municipalities.")
    parser.add_argument("--allow-non-2022", action="store_true", help="Allow non-2022 source_year values and record that choice in metadata.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_population_origins.csv.gz")
    parser.add_argument("--metadata", type=Path, default=PROJECT_ROOT / "data/enriched/telemedicine_population_origins_metadata.json")
    args = parser.parse_args()

    if args.manual_origins:
        manual = normalize_manual_origins(pd.read_csv(args.manual_origins), allow_non_2022=args.allow_non_2022)
        if args.blend_with_proxy:
            proxy = build_proxy_origins(pd.read_csv(args.phase2_spatial))
            origins = blend_manual_with_proxy(manual, proxy)
            source_kind = "manual_official_population_origins_with_municipal_proxy_backfill"
        else:
            origins = manual
            source_kind = "manual_official_population_origins_csv"
        source_path = args.manual_origins
    else:
        origins = build_proxy_origins(pd.read_csv(args.phase2_spatial))
        source_kind = "municipal_single_origin_proxy"
        source_path = args.phase2_spatial

    args.output.parent.mkdir(parents=True, exist_ok=True)
    origins.to_csv(args.output, index=False)
    args.metadata.write_text(json.dumps(build_metadata(origins, source_kind, source_path), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(origins):,} population origins for {origins['ibge_municipio_7'].nunique():,} municipalities")


if __name__ == "__main__":
    main()
