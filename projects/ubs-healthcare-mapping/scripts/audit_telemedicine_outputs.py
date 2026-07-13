"""Audit generated telemedicine dashboard outputs.

This script checks the core invariants that separate the national
telemedicine opportunity view from the pharmacy-assisted pilot view.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("projects/ubs-healthcare-mapping")
DASHBOARD_ROOT = Path("docs/dashboards/ubs-healthcare-mapping")


def _read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_outputs(project_dir: Path = PROJECT_ROOT, dashboard_dir: Path = DASHBOARD_ROOT) -> dict[str, Any]:
    enriched = project_dir / "data" / "enriched"
    phase2_path = enriched / "telemedicine_opportunity_phase2.csv"
    phase4_path = enriched / "telemedicine_opportunity_phase4.csv"
    matrix_path = enriched / "telemedicine_decision_matrix.csv"
    state_summary_path = enriched / "telemedicine_state_opportunity_summary.csv"
    geojson_path = dashboard_dir / "data" / "municipality_pharmacy_access_gap.geojson"
    dashboard_path = dashboard_dir / "index.html"

    phase2 = pd.read_csv(phase2_path)
    phase4 = pd.read_csv(phase4_path, low_memory=False)
    matrix = pd.read_csv(matrix_path) if matrix_path.exists() else pd.DataFrame()
    state_summary = pd.read_csv(state_summary_path) if state_summary_path.exists() else pd.DataFrame()
    geojson = _read_geojson(geojson_path)
    dashboard_html = dashboard_path.read_text(encoding="utf-8")

    goiania = phase4[
        phase4["municipio_nome_ibge"].astype("string").str.casefold().eq("goiânia")
        & phase4["uf_sigla"].astype("string").eq("GO")
    ]
    if goiania.empty:
        goiania_summary: dict[str, Any] = {"found": False}
    else:
        row = goiania.iloc[0]
        goiania_summary = {
            "found": True,
            "phase2_rank_balanced": None if pd.isna(row.get("phase2_rank_balanced")) else int(row["phase2_rank_balanced"]),
            "phase2_spatial_target_rank": None if pd.isna(row.get("phase2_spatial_target_rank")) else int(row["phase2_spatial_target_rank"]),
            "phase4_routed_target_rank": None if pd.isna(row.get("phase4_routed_target_rank")) else int(row["phase4_routed_target_rank"]),
        }

    first_properties = geojson["features"][0]["properties"] if geojson.get("features") else {}
    required_geojson_fields = {
        "telemedicine_phase2_balanced",
        "phase2_rank_balanced",
        "phase2_need_pillar",
        "phase2_feasibility_pillar",
        "phase4_interpretation",
        "decision_class",
        "decision_label",
        "primary_driver",
    }
    required_dashboard_filters = {
        'value="national"',
        'value="top100"',
        'value="phase4"',
    }

    summary = {
        "phase2_rows": int(len(phase2)),
        "phase2_scored_municipalities": int(phase2["telemedicine_phase2_balanced"].notna().sum()),
        "phase2_top100_municipalities": int((phase2["phase2_rank_balanced"] <= 100).sum()),
        "phase4_rows": int(len(phase4)),
        "phase4_primary_routed_targets": int((phase4["phase4_interpretation"] == "phase4_primary_routed_target").sum()),
        "decision_matrix_rows": int(len(matrix)),
        "decision_class_counts": (
            {str(k): int(v) for k, v in matrix["decision_class"].value_counts().sort_index().items()}
            if not matrix.empty and "decision_class" in matrix
            else {}
        ),
        "state_summary_rows": int(len(state_summary)),
        "state_top100_total": int(state_summary["top100_municipalities"].sum()) if not state_summary.empty else 0,
        "state_phase4_pilot_total": int(state_summary["pharmacy_assisted_pilot_count"].sum()) if not state_summary.empty else 0,
        "top_state": str(state_summary.sort_values("state_rank").iloc[0]["uf_sigla"]) if not state_summary.empty else None,
        "dashboard_geojson_features": int(len(geojson.get("features", []))),
        "geojson_has_required_fields": required_geojson_fields.issubset(first_properties.keys()),
        "dashboard_has_separated_filters": all(token in dashboard_html for token in required_dashboard_filters),
        "goiania": goiania_summary,
    }
    summary["views_are_separated"] = (
        summary["phase2_scored_municipalities"] > summary["phase4_primary_routed_targets"]
        and summary["phase2_top100_municipalities"] == 100
        and summary["goiania"].get("phase2_rank_balanced") == 1
        and summary["goiania"].get("phase4_routed_target_rank") is None
        and summary["decision_class_counts"].get("pharmacy_assisted_pilot") == summary["phase4_primary_routed_targets"]
        and summary["state_summary_rows"] == 27
        and summary["state_top100_total"] == summary["phase2_top100_municipalities"]
        and summary["state_phase4_pilot_total"] == summary["phase4_primary_routed_targets"]
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--dashboard-dir", type=Path, default=DASHBOARD_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = summarize_outputs(args.project_dir, args.dashboard_dir)
    payload = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
