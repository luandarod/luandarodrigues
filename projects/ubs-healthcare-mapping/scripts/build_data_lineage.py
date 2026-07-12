"""Create a small data lineage manifest with file size, rows, columns and SHA-256."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


DEFAULT_FILES = [
    "data/Unidades_Basicas_Saude-UBS.csv",
    "data/cobertura-aps-latest.csv",
    "data/aps_national_timeseries.csv",
    "data/geodata/ibge_malhas_municipais_minima.json",
    "data/spatial_validation_by_uf.csv",
    "data/spatial_validation_suspect_ubs.csv",
    "data/spatial_validation_metadata.json",
    "data/ubs_operational_status.csv",
    "data/ubs_operational_status_by_uf.csv",
    "data/ubs_operational_status_metadata.json",
    "data/pharmacies.csv",
    "data/pharmacies_by_uf.csv",
    "data/pharmacies_metadata.json",
    "data/enriched/municipality_ubs_territory.csv",
    "data/enriched/municipality_ubs_aps_coverage.csv",
    "data/enriched/uf_ubs_territory_summary.csv",
    "data/enriched/uf_ubs_aps_coverage_summary.csv",
    "data/enriched/priority_sensitivity_uf_scores.csv",
    "data/enriched/robust_priority_index_uf.csv",
    "data/enriched/robust_priority_sensitivity_uf.csv",
    "data/enriched/municipality_pharmacy_access_gap.csv",
    "data/reference/ibge_municipality_universe.csv",
    "data/quality/telemedicine_index_invalid_codes.csv",
    "data/enriched/telemedicine_opportunity_preliminary.csv",
    "data/enriched/telemedicine_pre_paper_analytic.csv",
    "data/enriched/telemedicine_opportunity_scenarios.csv",
    "data/enriched/telemedicine_opportunity_monte_carlo.csv",
    "data/enriched/telemedicine_opportunity_candidates.csv",
    "data/enriched/telemedicine_ads_geo_shortlist.csv",
    "data/enriched/telemedicine_opportunity_metadata.json",
    "data/enriched/municipality_sia_assisted_production.csv",
    "data/enriched/municipality_sia_assisted_production_metadata.json",
    "data/enriched/municipality_cnes_workforce_teams.csv",
    "data/enriched/municipality_cnes_workforce_teams_metadata.json",
    "data/enriched/municipality_ibge_internet_readiness.csv",
    "data/enriched/municipality_ibge_internet_readiness_metadata.json",
    "data/enriched/municipality_anatel_connectivity.csv",
    "data/enriched/municipality_anatel_connectivity_metadata.json",
    "data/enriched/telemedicine_opportunity_phase1.csv",
    "data/enriched/telemedicine_opportunity_phase1_monte_carlo.csv",
    "data/enriched/telemedicine_phase1_ads_geo_shortlist.csv",
    "data/enriched/telemedicine_opportunity_phase1_metadata.json",
    "data/spatial/osm_pharmacies.csv",
    "data/spatial/osm_pharmacies_metadata.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_shape(path: Path) -> tuple[int | None, int | None]:
    if path.suffix.lower() != ".csv":
        return None, None
    df = pd.read_csv(path, sep=None, engine="python")
    return len(df), len(df.columns)


def build_manifest(project_dir: Path, output: Path) -> None:
    rows = []
    for relative in DEFAULT_FILES:
        path = project_dir / relative
        if not path.exists():
            continue
        n_rows, n_cols = csv_shape(path)
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "rows": n_rows,
                "columns": n_cols,
                "sha256": sha256(path),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build data lineage manifest.")
    parser.add_argument("--project-dir", default="projects/ubs-healthcare-mapping")
    parser.add_argument("--output", default="projects/ubs-healthcare-mapping/data/data_lineage_manifest.csv")
    args = parser.parse_args()
    build_manifest(Path(args.project_dir), Path(args.output))
    print(f"Saved data lineage manifest to {args.output}")


if __name__ == "__main__":
    main()
