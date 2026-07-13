"""Build Phase 4 threshold sensitivity table for routed targets."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


ROOT = Path("projects/ubs-healthcare-mapping")
DEFAULT_UBS_THRESHOLDS = (10, 15, 20)
DEFAULT_PHARMACY_THRESHOLDS = (3, 5, 10)


def build_sensitivity(
    routed_summary: pd.DataFrame,
    ubs_thresholds: tuple[int, ...] = DEFAULT_UBS_THRESHOLDS,
    pharmacy_thresholds: tuple[int, ...] = DEFAULT_PHARMACY_THRESHOLDS,
) -> pd.DataFrame:
    rows = []
    frame = routed_summary.copy()
    frame["active_ubs_travel_time_minutes"] = pd.to_numeric(frame["active_ubs_travel_time_minutes"], errors="coerce")
    frame["osm_pharmacy_travel_time_minutes"] = pd.to_numeric(frame["osm_pharmacy_travel_time_minutes"], errors="coerce")
    for ubs_minutes in ubs_thresholds:
        for pharmacy_minutes in pharmacy_thresholds:
            flag = (
                frame["active_ubs_travel_time_minutes"].ge(ubs_minutes)
                & frame["osm_pharmacy_travel_time_minutes"].le(pharmacy_minutes)
            )
            selected = frame.loc[flag].sort_values(
                ["active_ubs_travel_time_minutes", "osm_pharmacy_travel_time_minutes"],
                ascending=[False, True],
            )
            rows.append({
                "ubs_hard_minutes_threshold": ubs_minutes,
                "pharmacy_easy_minutes_threshold": pharmacy_minutes,
                "candidate_count": int(flag.sum()),
                "candidate_municipalities": "; ".join(
                    f"{row.municipio_nome_oficial}/{row.uf_sigla_oficial}" for row in selected.itertuples()
                ),
            })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 4 threshold sensitivity table.")
    parser.add_argument("--input", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_summary.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_phase4_threshold_sensitivity.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/enriched/telemedicine_phase4_threshold_sensitivity_metadata.json")
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    sensitivity = build_sensitivity(frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sensitivity.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": str(args.input),
        "ubs_thresholds_minutes": list(DEFAULT_UBS_THRESHOLDS),
        "pharmacy_thresholds_minutes": list(DEFAULT_PHARMACY_THRESHOLDS),
        "purpose": "Operational sensitivity analysis for the Phase 4 routed target rule.",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 4 threshold sensitivity to {args.output}")


if __name__ == "__main__":
    main()
