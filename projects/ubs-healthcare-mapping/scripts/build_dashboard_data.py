"""Build versioned CSV files used by the static dashboard."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd


def build_gap_geojson(geometries: dict, gap: pd.DataFrame) -> dict:
    """Attach municipal pharmacy/UBS indicators to simplified IBGE geometry."""
    rows = gap.copy()
    rows["ibge_key"] = rows["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
    lookup = rows.set_index("ibge_key").to_dict("index")
    fields = [
        "municipio_nome_ibge", "uf_sigla", "populacao_residente", "ubs_records", "active_ubs",
        "active_ubs_per_100k", "aps_coverage_capped_pct", "pharmacies", "pharmacies_per_100k",
        "access_mismatch_score", "access_mismatch_flag", "evidence_level",
        "threshold_active_ubs_per_100k_q25", "threshold_pharmacies_per_100k_median",
    ]
    features = []
    for ibge7, item in geometries.items():
        row = lookup.get(str(ibge7)[:6])
        if row is None:
            continue
        properties = {field: (None if pd.isna(row.get(field)) else row.get(field)) for field in fields}
        properties["ibge_municipio_7"] = str(ibge7)
        features.append({
            "type": "Feature",
            "geometry": {"type": "MultiPolygon", "coordinates": item["coordinates"]},
            "properties": properties,
        })
    return {"type": "FeatureCollection", "features": features}


def build_dashboard_data(project_dir: Path, dashboard_dir: Path) -> None:
    src = project_dir / "data" / "enriched"
    dst = dashboard_dir / "data"
    dst.mkdir(parents=True, exist_ok=True)

    uf = pd.read_csv(src / "uf_ubs_territory_summary.csv")
    aps = pd.read_csv(src / "uf_ubs_aps_coverage_summary.csv")
    uf_dash = uf.merge(
        aps[
            [
                "uf_sigla",
                "cobertura_aps_ponderada_pct",
                "cobertura_aps_ponderada_capped_pct",
                "aps_priority_score",
            ]
        ],
        on="uf_sigla",
        how="left",
    )
    uf_dash = pd.DataFrame(
        {
            "uf": uf_dash["uf_sigla"],
            "regiao": uf_dash["regiao_nome"],
            "ubs": uf_dash["ubs_records"],
            "municipios": uf_dash["municipalities"],
            "valid_coords": uf_dash["valid_coordinate_records"],
            "missing_coords": uf_dash["missing_coordinate_records"],
            "population_2022": uf_dash["population"],
            "area_km2": uf_dash["area_km2"],
            "ubs_per_100k_pop": uf_dash["ubs_per_10k_population"] * 10,
            "ubs_per_1000_km2": uf_dash["ubs_per_1000_km2"],
            "coord_validity_pct": uf_dash["coordinate_validity_pct"],
            "aps_weighted_coverage_pct": uf_dash["cobertura_aps_ponderada_pct"],
            "aps_weighted_capped_coverage_pct": uf_dash["cobertura_aps_ponderada_capped_pct"],
            "priority_score": uf_dash["aps_priority_score"],
        }
    )
    uf_dash.sort_values("ubs", ascending=False).to_csv(dst / "uf_territory_enriched.csv", index=False)
    uf.to_csv(dst / "uf_ubs_territory_summary.csv", index=False)
    pd.read_csv(src / "region_ubs_territory_summary.csv").to_csv(dst / "region_ubs_territory_summary.csv", index=False)
    pd.read_csv(src / "aps_coverage_normalized.csv").to_csv(dst / "aps_coverage_normalized.csv", index=False)
    pd.read_csv(src / "uf_ubs_aps_coverage_summary.csv").to_csv(dst / "uf_ubs_aps_coverage_summary.csv", index=False)

    # Pharmacy artifacts are optional until an official Farmacia Popular extract
    # has been supplied. When present, keep the GitHub Pages copy in sync.
    for name in ("pharmacies_by_uf.csv",):
        pharmacy_file = project_dir / "data" / name
        if pharmacy_file.exists():
            shutil.copy2(pharmacy_file, dst / name)
    gap_file = src / "municipality_pharmacy_access_gap.csv"
    if gap_file.exists():
        shutil.copy2(gap_file, dst / gap_file.name)
        geometry_file = project_dir / "data" / "geodata" / "ibge_malhas_municipais_minima.json"
        if geometry_file.exists():
            geometries = json.loads(geometry_file.read_text(encoding="utf-8"))
            gap_geojson = build_gap_geojson(geometries, pd.read_csv(gap_file))
            (dst / "municipality_pharmacy_access_gap.geojson").write_text(
                json.dumps(gap_geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build dashboard CSV files.")
    parser.add_argument("--project-dir", default="projects/ubs-healthcare-mapping")
    parser.add_argument("--dashboard-dir", default="docs/dashboards/ubs-healthcare-mapping")
    args = parser.parse_args()
    build_dashboard_data(Path(args.project_dir), Path(args.dashboard_dir))
    print("Dashboard data refreshed.")


if __name__ == "__main__":
    main()
