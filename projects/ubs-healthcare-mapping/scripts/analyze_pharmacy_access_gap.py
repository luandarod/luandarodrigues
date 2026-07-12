"""Identify municipalities where pharmacy supply exceeds relative UBS supply."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _municipality_key(values: pd.Series) -> pd.Series:
    return values.astype("string").str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True).str[:6]


def extend_with_aps_universe(territory: pd.DataFrame, aps: pd.DataFrame) -> pd.DataFrame:
    """Add municipalities present in APS but absent from the UBS register."""
    base = territory.copy()
    base["ibge_municipio"] = _municipality_key(base["ibge_municipio"])
    coverage = aps.copy()
    coverage["ibge_municipio"] = _municipality_key(coverage["ibge_municipio"])
    missing = coverage.loc[~coverage["ibge_municipio"].isin(set(base["ibge_municipio"]))].copy()
    if missing.empty:
        return base
    additions = pd.DataFrame({
        "ibge_municipio": missing["ibge_municipio"],
        "uf_sigla": missing["uf_sigla"],
        "municipio_nome_ibge": missing["municipio_nome_aps"],
        "populacao_residente": missing["aps_populacao"],
        "ubs_records": 0,
        "area_km2": pd.NA,
    })
    return pd.concat([base, additions], ignore_index=True, sort=False)


def analyze_gap(territory: pd.DataFrame, pharmacies: pd.DataFrame) -> pd.DataFrame:
    """Build a municipal, population-adjusted accessibility mismatch proxy.

    The result measures registered supply, not route time, opening status, stock,
    medical staffing or actual access to care.
    """
    municipal = territory.copy()
    municipal["ibge_municipio"] = _municipality_key(municipal["ibge_municipio"])

    pharmacy = pharmacies.copy()
    pharmacy["ibge_municipio"] = _municipality_key(pharmacy["ibge_municipality"])
    pharmacy["is_popular"] = pharmacy["facility_type"].eq("farmacia_popular")
    counts = pharmacy.groupby("ibge_municipio").agg(
        pharmacies=("facility_id", "size"),
        popular_pharmacies=("is_popular", "sum"),
    ).reset_index()

    result = municipal.merge(counts, on="ibge_municipio", how="left")
    for column in ("pharmacies", "popular_pharmacies"):
        result[column] = result[column].fillna(0).astype(int)
    result["other_pharmacies"] = result["pharmacies"] - result["popular_pharmacies"]

    population = pd.to_numeric(result["populacao_residente"], errors="coerce").replace(0, pd.NA)
    result["ubs_per_100k"] = result["ubs_records"] / population * 100_000
    result["pharmacies_per_100k"] = result["pharmacies"] / population * 100_000
    result["popular_pharmacies_per_100k"] = result["popular_pharmacies"] / population * 100_000
    result["pharmacies_per_ubs"] = result["pharmacies"] / result["ubs_records"].replace(0, pd.NA)

    ubs_rank = result["ubs_per_100k"].rank(pct=True, method="average")
    pharmacy_rank = result["pharmacies_per_100k"].rank(pct=True, method="average")
    result["access_mismatch_score"] = ((1 - ubs_rank) * 50 + pharmacy_rank * 50).round(2)
    low_ubs = result["ubs_per_100k"] <= result["ubs_per_100k"].quantile(1 / 3)
    high_pharmacy = result["pharmacies_per_100k"] >= result["pharmacies_per_100k"].quantile(2 / 3)
    result["access_mismatch_flag"] = "no_strong_mismatch"
    result.loc[low_ubs & high_pharmacy & result["pharmacies"].gt(0), "access_mismatch_flag"] = "doctor_harder_pharmacy_easier"
    return result.sort_values("access_mismatch_score", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare municipal UBS and pharmacy availability.")
    parser.add_argument("--territory", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_ubs_territory.csv"))
    parser.add_argument("--pharmacies", type=Path, default=Path("projects/ubs-healthcare-mapping/data/pharmacies.csv"))
    parser.add_argument("--aps", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/aps_coverage_normalized.csv"))
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_pharmacy_access_gap.csv"))
    args = parser.parse_args()
    territory = extend_with_aps_universe(pd.read_csv(args.territory), pd.read_csv(args.aps))
    output = analyze_gap(territory, pd.read_csv(args.pharmacies))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(f"Saved {len(output):,} municipalities to {args.output}")


if __name__ == "__main__":
    main()
