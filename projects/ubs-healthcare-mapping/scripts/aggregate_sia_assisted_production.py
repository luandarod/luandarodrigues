"""Aggregate existing SIA/SUS evidence for UBS at municipality level.

The PA quantity includes all reported outpatient procedures. It must not be
interpreted as medical consultations until procedures are filtered through the
competence-specific SIGTAP table.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


def _key(values: pd.Series) -> pd.Series:
    return values.astype("string").str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True).str[:6]


def aggregate_production(status: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    source = status.copy()
    source["ibge_municipio"] = _key(source["ibge_municipio"])
    for column in ("cnes_present_latest_st", "sia_recent_production"):
        source[column] = source[column].astype("boolean").fillna(False)
    for column in ("sia_records", "sia_quantity", "sia_value", "sia_competence_count"):
        source[column] = pd.to_numeric(source[column], errors="coerce").fillna(0)
    source["active_and_sia"] = source["cnes_present_latest_st"] & source["sia_recent_production"]

    municipal = source.groupby("ibge_municipio", as_index=False).agg(
        ubs_in_operational_source=("cnes", "nunique"),
        active_ubs_cnes_st=("cnes_present_latest_st", "sum"),
        ubs_with_recent_sia_production=("sia_recent_production", "sum"),
        active_ubs_with_recent_sia_production=("active_and_sia", "sum"),
        sia_record_rows=("sia_records", "sum"),
        sia_quantity_all_procedures=("sia_quantity", "sum"),
        sia_approved_value=("sia_value", "sum"),
        sia_competence_observations=("sia_competence_count", "sum"),
    )
    pop = population[["ibge_municipio", "populacao_residente"]].copy()
    pop["ibge_municipio"] = _key(pop["ibge_municipio"])
    pop["populacao_residente"] = pd.to_numeric(pop["populacao_residente"], errors="coerce")
    pop = pop.drop_duplicates("ibge_municipio")
    result = municipal.merge(pop, on="ibge_municipio", how="left", validate="one_to_one")

    active = result["active_ubs_cnes_st"].replace(0, np.nan)
    population_denominator = result["populacao_residente"].replace(0, np.nan)
    result["sia_reporting_coverage_pct"] = result["active_ubs_with_recent_sia_production"] / active * 100
    result["sia_quantity_all_procedures_per_1000"] = (
        result["sia_quantity_all_procedures"] / population_denominator * 1_000
    )
    result["sia_quantity_per_reporting_ubs"] = (
        result["sia_quantity_all_procedures"]
        / result["ubs_with_recent_sia_production"].replace(0, np.nan)
    )
    result["production_interpretation"] = "all_outpatient_procedures_reporting_proxy"
    result.loc[result["active_ubs_cnes_st"].eq(0), "production_interpretation"] = "no_active_ubs_denominator"
    result["consultation_specific_status"] = "not_yet_filtered_by_sigtap"
    return result.sort_values("ibge_municipio")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate municipal SIA evidence already collected for UBS.")
    parser.add_argument("--status", type=Path, default=Path("projects/ubs-healthcare-mapping/data/ubs_operational_status.csv"))
    parser.add_argument(
        "--population",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_pre_paper_analytic.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_sia_assisted_production.csv"),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_sia_assisted_production_metadata.json"),
    )
    args = parser.parse_args()
    result = aggregate_production(pd.read_csv(args.status), pd.read_csv(args.population))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": str(args.status),
        "rows": len(result),
        "scope": "UBS records in project with recent SIA/SUS PA evidence",
        "window": "three latest available PA files per UF in the source snapshot",
        "important_limit": "PA_QTDPRO aggregates all outpatient procedures and is not a consultation count.",
        "score_use": "evidence and reporting coverage only; excluded from opportunity score",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(result):,} municipal production rows to {args.output}")


if __name__ == "__main__":
    main()
