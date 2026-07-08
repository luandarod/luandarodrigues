"""Build versioned CSV files used by the static dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build dashboard CSV files.")
    parser.add_argument("--project-dir", default="projects/ubs-healthcare-mapping")
    parser.add_argument("--dashboard-dir", default="docs/dashboards/ubs-healthcare-mapping")
    args = parser.parse_args()
    build_dashboard_data(Path(args.project_dir), Path(args.dashboard_dir))
    print("Dashboard data refreshed.")


if __name__ == "__main__":
    main()
