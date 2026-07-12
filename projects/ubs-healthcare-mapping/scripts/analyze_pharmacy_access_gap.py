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


def analyze_gap(
    territory: pd.DataFrame,
    pharmacies: pd.DataFrame,
    aps: pd.DataFrame | None = None,
    operational: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build a municipal, population-adjusted accessibility mismatch proxy.

    The result measures registered supply, not route time, opening status, stock,
    medical staffing or actual access to care.
    """
    municipal = territory.copy()
    municipal["ibge_municipio"] = _municipality_key(municipal["ibge_municipio"])

    pharmacy = pharmacies.copy()
    pharmacy["ibge_municipio"] = _municipality_key(pharmacy["ibge_municipality"])
    identity = "cnpj" if "cnpj" in pharmacy.columns else "facility_id"
    pharmacy = pharmacy.drop_duplicates(identity)
    pharmacy["is_popular"] = pharmacy["facility_type"].eq("farmacia_popular")
    counts = pharmacy.groupby("ibge_municipio").agg(
        pharmacies=("facility_id", "size"),
        popular_pharmacies=("is_popular", "sum"),
    ).reset_index()

    result = municipal.merge(counts, on="ibge_municipio", how="left")
    for column in ("pharmacies", "popular_pharmacies"):
        result[column] = result[column].fillna(0).astype(int)
    result["other_pharmacies"] = result["pharmacies"] - result["popular_pharmacies"]

    if aps is not None:
        coverage = aps.copy()
        coverage["ibge_municipio"] = _municipality_key(coverage["ibge_municipio"])
        coverage = coverage.drop_duplicates("ibge_municipio", keep="last")
        result = result.merge(
            coverage[["ibge_municipio", "cobertura_aps_pct", "aps_populacao"]],
            on="ibge_municipio", how="left",
        )
    else:
        result["cobertura_aps_pct"] = pd.NA
        result["aps_populacao"] = pd.NA

    if operational is not None:
        active = operational.copy()
        active["ibge_municipio"] = _municipality_key(active["ibge_municipio"])
        active["cnes_present_latest_st"] = active["cnes_present_latest_st"].astype("boolean").fillna(False)
        active = active.groupby("ibge_municipio").agg(
            active_ubs=("cnes_present_latest_st", "sum"),
            operational_ubs_observed=("cnes", "nunique"),
        ).reset_index()
        result = result.merge(active, on="ibge_municipio", how="left")
    else:
        result["active_ubs"] = result["ubs_records"]
        result["operational_ubs_observed"] = result["ubs_records"]
    result["active_ubs"] = result["active_ubs"].fillna(0).astype(int)
    result["operational_ubs_observed"] = result["operational_ubs_observed"].fillna(0).astype(int)

    population = pd.to_numeric(result["populacao_residente"], errors="coerce").replace(0, pd.NA)
    result["ubs_per_100k"] = result["ubs_records"] / population * 100_000
    result["active_ubs_per_100k"] = result["active_ubs"] / population * 100_000
    result["pharmacies_per_100k"] = result["pharmacies"] / population * 100_000
    result["popular_pharmacies_per_100k"] = result["popular_pharmacies"] / population * 100_000
    result["pharmacies_per_ubs"] = result["pharmacies"] / result["ubs_records"].replace(0, pd.NA)

    result["aps_coverage_capped_pct"] = pd.to_numeric(result["cobertura_aps_pct"], errors="coerce").clip(upper=100)
    active_median = result.loc[result["active_ubs_per_100k"].notna(), "active_ubs_per_100k"].median()
    active_q25 = result.loc[result["active_ubs_per_100k"].notna(), "active_ubs_per_100k"].quantile(.25)
    pharmacy_median = result.loc[result["pharmacies_per_100k"].notna(), "pharmacies_per_100k"].median()
    result["ubs_supply_pressure"] = (1 - result["active_ubs_per_100k"] / active_median).clip(0, 1)
    result["aps_coverage_gap"] = ((80 - result["aps_coverage_capped_pct"]) / 80).clip(0, 1)
    result["pharmacy_access_signal"] = (result["pharmacies_per_100k"] / (pharmacy_median * 2)).clip(0, 1)
    result["access_mismatch_score"] = (
        result["ubs_supply_pressure"] * 40
        + result["aps_coverage_gap"] * 40
        + result["pharmacy_access_signal"] * 20
    ).round(2)
    complete = result["aps_coverage_capped_pct"].notna() & result["active_ubs_per_100k"].notna()
    result["evidence_level"] = "partial"
    result.loc[complete, "evidence_level"] = "complete"
    consistent = (
        complete
        & result["active_ubs_per_100k"].le(active_q25)
        & result["aps_coverage_capped_pct"].lt(80)
        & result["pharmacies_per_100k"].ge(pharmacy_median)
        & result["pharmacies"].gt(0)
    )
    result["access_mismatch_flag"] = "no_consistent_mismatch"
    result.loc[consistent, "access_mismatch_flag"] = "consistent_mismatch"
    result["threshold_active_ubs_per_100k_q25"] = active_q25
    result["threshold_pharmacies_per_100k_median"] = pharmacy_median
    return result.sort_values("access_mismatch_score", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare municipal UBS and pharmacy availability.")
    parser.add_argument("--territory", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_ubs_territory.csv"))
    parser.add_argument("--pharmacies", type=Path, default=Path("projects/ubs-healthcare-mapping/data/pharmacies.csv"))
    parser.add_argument("--aps", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/aps_coverage_normalized.csv"))
    parser.add_argument("--operational", type=Path, default=Path("projects/ubs-healthcare-mapping/data/ubs_operational_status.csv"))
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_pharmacy_access_gap.csv"))
    args = parser.parse_args()
    territory = extend_with_aps_universe(pd.read_csv(args.territory), pd.read_csv(args.aps))
    output = analyze_gap(territory, pd.read_csv(args.pharmacies), pd.read_csv(args.aps), pd.read_csv(args.operational))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(f"Saved {len(output):,} municipalities to {args.output}")


if __name__ == "__main__":
    main()
