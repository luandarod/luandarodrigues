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
        "nearest_ubs_geodesic_km", "nearest_pharmacy_geodesic_km",
        "hard_ubs_easy_pharmacy_flag", "hard_ubs_easy_pharmacy_flag_3km_2km",
        "hard_ubs_easy_pharmacy_flag_10km_5km", "telemedicine_phase2_balanced",
        "telemedicine_phase2_equity_led", "telemedicine_phase2_deployment_led",
        "phase2_rank_balanced", "phase2_rank_equity_led", "phase2_rank_deployment_led",
        "phase2_need_pillar", "phase2_feasibility_pillar", "phase2_eligibility",
        "phase2_spatial_target_rank", "travel_time_status",
        "active_ubs_travel_time_minutes", "osm_pharmacy_travel_time_minutes",
        "telemedicine_phase4_routed_validation", "phase4_routed_target_rank",
        "phase4_need_pillar", "phase4_feasibility_pillar",
        "phase4_interpretation", "phase4_evidence_grade",
        "telemedicine_precision_index", "phase5_precision_rank",
        "phase5_spatial_precision_mismatch_score",
        "phase5_weighted_p90_ubs_km", "phase5_weighted_mean_ubs_km",
        "phase5_population_share_pharmacy_le_2km",
        "phase5_population_share_hard_ubs_easy_pharmacy",
        "phase5_precision_status", "phase5_evidence_grade",
        "decision_class", "decision_label", "ads_positioning_tier",
        "recommended_next_action", "primary_driver", "evidence_grade",
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
    state_summary_file = src / "telemedicine_state_opportunity_summary.csv"
    if state_summary_file.exists():
        shutil.copy2(state_summary_file, dst / state_summary_file.name)

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
            gap = pd.read_csv(gap_file)
            phase2_file = src / "telemedicine_opportunity_phase2.csv"
            if phase2_file.exists():
                phase2 = pd.read_csv(phase2_file, low_memory=False)
                gap["ibge_municipio"] = gap["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
                phase2["ibge_municipio"] = phase2["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
                phase2_fields = [
                    "ibge_municipio", "nearest_ubs_geodesic_km", "nearest_pharmacy_geodesic_km",
                    "hard_ubs_easy_pharmacy_flag", "hard_ubs_easy_pharmacy_flag_3km_2km",
                    "hard_ubs_easy_pharmacy_flag_10km_5km", "telemedicine_phase2_balanced",
                    "telemedicine_phase2_equity_led", "telemedicine_phase2_deployment_led",
                    "phase2_rank_balanced", "phase2_rank_equity_led", "phase2_rank_deployment_led",
                    "phase2_need_pillar", "phase2_feasibility_pillar", "phase2_eligibility",
                    "phase2_spatial_target_rank", "travel_time_status",
                ]
                gap = gap.merge(phase2[phase2_fields], on="ibge_municipio", how="left", validate="one_to_one")
            phase4_file = src / "telemedicine_opportunity_phase4.csv"
            if phase4_file.exists():
                phase4 = pd.read_csv(phase4_file, low_memory=False)
                phase4["ibge_municipio"] = phase4["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
                phase4_fields = [
                    "ibge_municipio", "active_ubs_travel_time_minutes", "osm_pharmacy_travel_time_minutes",
                    "telemedicine_phase4_routed_validation", "phase4_routed_target_rank",
                    "phase4_need_pillar", "phase4_feasibility_pillar",
                    "phase4_interpretation", "phase4_evidence_grade",
                ]
                gap = gap.merge(phase4[phase4_fields], on="ibge_municipio", how="left", validate="one_to_one")
            matrix_file = src / "telemedicine_decision_matrix.csv"
            if matrix_file.exists():
                shutil.copy2(matrix_file, dst / matrix_file.name)
                matrix = pd.read_csv(matrix_file, low_memory=False)
                matrix["ibge_municipio"] = matrix["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
                matrix_fields = [
                    "ibge_municipio", "decision_class", "decision_label", "ads_positioning_tier",
                    "recommended_next_action", "primary_driver", "evidence_grade",
                ]
                gap = gap.merge(matrix[matrix_fields], on="ibge_municipio", how="left", validate="one_to_one")
            precision_file = src / "telemedicine_precision_index.csv"
            if precision_file.exists():
                shutil.copy2(precision_file, dst / precision_file.name)
                for optional_name in (
                    "telemedicine_population_origins.csv",
                    "telemedicine_precision_spatial_access.csv",
                    "telemedicine_precision_shortlist.csv",
                ):
                    optional_file = src / optional_name
                    if optional_file.exists():
                        shutil.copy2(optional_file, dst / optional_name)
                precision = pd.read_csv(precision_file, low_memory=False)
                precision["ibge_municipio"] = precision["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
                precision_fields = [
                    "ibge_municipio", "telemedicine_precision_index", "phase5_precision_rank",
                    "phase5_spatial_precision_mismatch_score",
                    "phase5_weighted_p90_ubs_km", "phase5_weighted_mean_ubs_km",
                    "phase5_population_share_pharmacy_le_2km",
                    "phase5_population_share_hard_ubs_easy_pharmacy",
                    "phase5_precision_status", "phase5_evidence_grade",
                ]
                gap = gap.merge(precision[precision_fields], on="ibge_municipio", how="left", validate="one_to_one")
            gap_geojson = build_gap_geojson(geometries, gap)
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
