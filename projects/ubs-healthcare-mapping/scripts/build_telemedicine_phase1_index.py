"""Build the Phase 1 municipal telemedicine opportunity index.

The index separates unmet-healthcare need from deployment feasibility. SIA
all-procedure production is carried as audit evidence and never scored.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


EPSILON = 1e-6
NEED_WEIGHTS = {
    "uncovered_volume": 0.45,
    "aps_gap": 0.20,
    "ubs_scarcity": 0.15,
    "physician_fte_scarcity": 0.20,
}
DIGITAL_WEIGHTS = {"household_internet": 0.50, "mobile_4g5g": 0.30, "fixed_broadband": 0.20}
FEASIBILITY_WEIGHTS = {"pharmacy": 0.70, "digital": 0.30}
SCENARIOS = {
    "balanced": {"need": 0.50, "feasibility": 0.50},
    "equity_led": {"need": 0.70, "feasibility": 0.30},
    "deployment_led": {"need": 0.40, "feasibility": 0.60},
}


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _percentile(
    values: pd.Series,
    valid: pd.Series,
    *,
    inverse: bool = False,
    log_transform: bool = False,
    structural_zero: bool = False,
) -> pd.Series:
    output = pd.Series(np.nan, index=values.index, dtype=float)
    sample = pd.to_numeric(values.loc[valid], errors="coerce").dropna()
    if structural_zero:
        output.loc[sample.loc[sample.le(0)].index] = 0
        sample = sample.loc[sample.gt(0)]
    if sample.empty:
        return output
    if log_transform:
        sample = np.log1p(sample.clip(lower=0))
    lower, upper = sample.quantile([0.01, 0.99])
    sample = sample.clip(lower=lower, upper=upper)
    output.loc[sample.index] = sample.rank(pct=True, ascending=not inverse, method="average")
    return output


def _geometric(components: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    matrix = pd.DataFrame(components)
    available = matrix.notna().all(axis=1)
    output = pd.Series(np.nan, index=matrix.index, dtype=float)
    clipped = matrix.loc[available].clip(lower=EPSILON, upper=1)
    output.loc[available] = np.exp(sum(np.log(clipped[name]) * weight for name, weight in weights.items()))
    return output


def merge_phase1_sources(
    base: pd.DataFrame,
    workforce: pd.DataFrame,
    internet: pd.DataFrame,
    anatel: pd.DataFrame,
    production: pd.DataFrame,
) -> pd.DataFrame:
    result = base.copy()
    result["ibge_municipio"] = result["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
    sources = [
        (workforce, [
            "physicians_unique", "physician_fte_40h", "physician_fte_per_100k",
            "active_ubs_with_physician_pct", "active_cnes_teams_all_types", "workforce_quality_flag",
        ]),
        (internet, ["households_with_internet_pct", "internet_data_status", "internet_quality_flag"]),
        (anatel, [
            "mobile_4g5g_resident_coverage_pct", "mobile_5g_resident_coverage_pct",
            "mobile_reference_period", "fixed_broadband_accesses_per_100_people",
            "fixed_broadband_reference_period", "anatel_data_status",
        ]),
        (production, [
            "sia_quantity_all_procedures", "sia_reporting_coverage_pct",
            "production_interpretation", "consultation_specific_status",
        ]),
    ]
    for source, columns in sources:
        incoming = source.copy()
        incoming["ibge_municipio"] = incoming["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
        selected = ["ibge_municipio", *[column for column in columns if column in incoming.columns]]
        result = result.merge(incoming[selected].drop_duplicates("ibge_municipio"), on="ibge_municipio", how="left", validate="one_to_one")
    return result


def build_phase1_index(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    population = _numeric(result, "populacao_residente")
    aps_coverage = _numeric(result, "aps_coverage_capped_pct").clip(0, 100)
    uncovered = _numeric(result, "potentially_uncovered_population")
    ubs_rate = _numeric(result, "active_ubs_per_100k")
    physician_rate = _numeric(result, "physician_fte_per_100k")
    pharmacies = _numeric(result, "pharmacies").fillna(0).clip(lower=0)
    pharmacy_rate = _numeric(result, "pharmacies_per_100k").fillna(0).clip(lower=0)
    household_internet = _numeric(result, "households_with_internet_pct")
    mobile = _numeric(result, "mobile_4g5g_resident_coverage_pct")
    fixed = _numeric(result, "fixed_broadband_accesses_per_100_people")

    result["aps_relative_gap"] = (1 - aps_coverage / 100).clip(0, 1)
    need_complete = population.gt(0) & uncovered.notna() & aps_coverage.notna() & ubs_rate.notna() & physician_rate.notna()
    digital_complete = household_internet.notna() & mobile.notna() & fixed.notna()
    pharmacy_observed = pharmacies.gt(0)
    complete = need_complete & digital_complete & pharmacy_observed

    result["phase1_uncovered_volume_percentile"] = _percentile(uncovered, need_complete, log_transform=True, structural_zero=True)
    result["phase1_aps_gap_percentile"] = _percentile(result["aps_relative_gap"], need_complete, structural_zero=True)
    result["phase1_ubs_scarcity_percentile"] = _percentile(ubs_rate, need_complete, inverse=True)
    result["phase1_physician_fte_scarcity_percentile"] = _percentile(physician_rate, need_complete, inverse=True)
    result["phase1_need_score"] = 100 * _geometric({
        "uncovered_volume": result["phase1_uncovered_volume_percentile"],
        "aps_gap": result["phase1_aps_gap_percentile"],
        "ubs_scarcity": result["phase1_ubs_scarcity_percentile"],
        "physician_fte_scarcity": result["phase1_physician_fte_scarcity_percentile"],
    }, NEED_WEIGHTS)
    result.loc[need_complete & result["aps_relative_gap"].eq(0), "phase1_need_score"] = 0

    result["household_internet_percentile"] = _percentile(household_internet, digital_complete)
    result["mobile_4g5g_coverage_percentile"] = _percentile(mobile, digital_complete)
    result["fixed_broadband_density_percentile"] = _percentile(fixed, digital_complete, log_transform=True)
    result["digital_readiness_score"] = 100 * _geometric({
        "household_internet": result["household_internet_percentile"],
        "mobile_4g5g": result["mobile_4g5g_coverage_percentile"],
        "fixed_broadband": result["fixed_broadband_density_percentile"],
    }, DIGITAL_WEIGHTS)

    pharmacy_valid = need_complete & pharmacy_observed
    result["phase1_pharmacy_count_percentile"] = _percentile(pharmacies, pharmacy_valid, log_transform=True).fillna(0)
    result["phase1_pharmacy_density_percentile"] = _percentile(pharmacy_rate, pharmacy_valid).fillna(0)
    result["phase1_pharmacy_launchability_score"] = 100 * _geometric({
        "count": result["phase1_pharmacy_count_percentile"],
        "density": result["phase1_pharmacy_density_percentile"],
    }, {"count": 0.50, "density": 0.50})
    result.loc[~pharmacy_observed, "phase1_pharmacy_launchability_score"] = 0
    result["phase1_deployment_feasibility_score"] = 100 * _geometric({
        "pharmacy": result["phase1_pharmacy_launchability_score"] / 100,
        "digital": result["digital_readiness_score"] / 100,
    }, FEASIBILITY_WEIGHTS)

    result["phase1_eligibility"] = "eligible_phase1_proxy"
    result.loc[need_complete & digital_complete & ~pharmacy_observed, "phase1_eligibility"] = "no_observed_pfpb_pharmacy"
    result.loc[~need_complete | ~digital_complete, "phase1_eligibility"] = "insufficient_phase1_data"
    result["phase1_evidence_grade"] = "B_enhanced_ecological_proxy"
    result.loc[~complete, "phase1_evidence_grade"] = "C_incomplete"
    result["spatial_travel_time_status"] = "not_measured"
    result["sia_score_role"] = "audit_only_not_scored"

    eligible = result["phase1_eligibility"].eq("eligible_phase1_proxy")
    rank_columns = []
    for scenario, weights in SCENARIOS.items():
        score = f"telemedicine_phase1_{scenario}"
        rank = f"phase1_rank_{scenario}"
        result[score] = 100 * _geometric({
            "need": result["phase1_need_score"] / 100,
            "feasibility": result["phase1_deployment_feasibility_score"] / 100,
        }, weights)
        result.loc[need_complete & result["phase1_need_score"].eq(0), score] = 0
        result.loc[~complete, score] = np.nan
        result[rank] = result.loc[eligible, score].rank(ascending=False, method="min")
        rank_columns.append(rank)
    result["phase1_rank_best"] = result[rank_columns].min(axis=1)
    result["phase1_rank_worst"] = result[rank_columns].max(axis=1)
    result["phase1_rank_range"] = result["phase1_rank_worst"] - result["phase1_rank_best"]
    return result.sort_values("telemedicine_phase1_balanced", ascending=False, na_position="last")


def monte_carlo_phase1(result: pd.DataFrame, iterations: int = 1_000, seed: int = 20260712) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    eligible = result["phase1_eligibility"].eq("eligible_phase1_proxy")
    subset = result.loc[eligible]
    n = len(subset)
    ranks = np.empty((iterations, n), dtype=np.float32)
    scores = np.empty((iterations, n), dtype=np.float32)
    need = np.clip(subset[[
        "phase1_uncovered_volume_percentile", "phase1_aps_gap_percentile",
        "phase1_ubs_scarcity_percentile", "phase1_physician_fte_scarcity_percentile",
    ]].to_numpy(float), EPSILON, 1)
    digital = np.clip(subset[[
        "household_internet_percentile", "mobile_4g5g_coverage_percentile",
        "fixed_broadband_density_percentile",
    ]].to_numpy(float), EPSILON, 1)
    pharmacy = np.clip(subset[[
        "phase1_pharmacy_count_percentile", "phase1_pharmacy_density_percentile",
    ]].to_numpy(float), EPSILON, 1)
    structural_zero = subset["aps_relative_gap"].eq(0).to_numpy()
    for iteration in range(iterations):
        need_score = np.exp(np.log(need) @ rng.dirichlet([9, 4, 3, 4]))
        digital_score = np.exp(np.log(digital) @ rng.dirichlet([5, 3, 2]))
        pharmacy_score = np.exp(np.log(pharmacy) @ rng.dirichlet([5, 5]))
        pharmacy_share = rng.uniform(0.60, 0.80)
        feasibility = pharmacy_score ** pharmacy_share * digital_score ** (1 - pharmacy_share)
        need_share = rng.uniform(0.40, 0.70)
        score = need_score ** need_share * feasibility ** (1 - need_share) * 100
        score[structural_zero] = 0
        scores[iteration] = score
        ranks[iteration] = pd.Series(score).rank(ascending=False, method="average").to_numpy()
    output = result[["ibge_municipio", "municipio_nome_ibge", "uf_sigla", "phase1_eligibility"]].copy()
    output["phase1_mc_score_median"] = np.nan
    output["phase1_mc_rank_median"] = np.nan
    output["phase1_mc_rank_p05"] = np.nan
    output["phase1_mc_rank_p95"] = np.nan
    output["phase1_mc_probability_top_decile"] = np.nan
    threshold = max(1, int(np.ceil(n * 0.10)))
    output.loc[eligible, "phase1_mc_score_median"] = np.median(scores, axis=0)
    output.loc[eligible, "phase1_mc_rank_median"] = np.median(ranks, axis=0)
    output.loc[eligible, "phase1_mc_rank_p05"] = np.quantile(ranks, 0.05, axis=0)
    output.loc[eligible, "phase1_mc_rank_p95"] = np.quantile(ranks, 0.95, axis=0)
    output.loc[eligible, "phase1_mc_probability_top_decile"] = (ranks <= threshold).mean(axis=0)
    return output.sort_values("phase1_mc_rank_median", na_position="last")


def main() -> None:
    root = Path("projects/ubs-healthcare-mapping")
    parser = argparse.ArgumentParser(description="Build the Phase 1 municipal telemedicine index.")
    parser.add_argument("--base", type=Path, default=root / "data/enriched/telemedicine_opportunity_preliminary.csv")
    parser.add_argument("--workforce", type=Path, default=root / "data/enriched/municipality_cnes_workforce_teams.csv")
    parser.add_argument("--internet", type=Path, default=root / "data/enriched/municipality_ibge_internet_readiness.csv")
    parser.add_argument("--anatel", type=Path, default=root / "data/enriched/municipality_anatel_connectivity.csv")
    parser.add_argument("--production", type=Path, default=root / "data/enriched/municipality_sia_assisted_production.csv")
    parser.add_argument("--output", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase1.csv")
    parser.add_argument("--monte-carlo-output", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase1_monte_carlo.csv")
    parser.add_argument("--ads-shortlist-output", type=Path, default=root / "data/enriched/telemedicine_phase1_ads_geo_shortlist.csv")
    parser.add_argument("--metadata", type=Path, default=root / "data/enriched/telemedicine_opportunity_phase1_metadata.json")
    args = parser.parse_args()
    merged = merge_phase1_sources(
        pd.read_csv(args.base), pd.read_csv(args.workforce), pd.read_csv(args.internet),
        pd.read_csv(args.anatel), pd.read_csv(args.production),
    )
    result = build_phase1_index(merged)
    monte_carlo = monte_carlo_phase1(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    monte_carlo.to_csv(args.monte_carlo_output, index=False)
    shortlist = result.loc[result["phase1_eligibility"].eq("eligible_phase1_proxy")].merge(
        monte_carlo[[
            "ibge_municipio", "phase1_mc_rank_median", "phase1_mc_rank_p05",
            "phase1_mc_rank_p95", "phase1_mc_probability_top_decile",
        ]],
        on="ibge_municipio",
        how="left",
    ).sort_values(
        ["phase1_mc_probability_top_decile", "telemedicine_phase1_balanced"],
        ascending=[False, False],
    ).head(100)
    shortlist.to_csv(args.ads_shortlist_output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "index_version": "phase1-v1",
        "design": "ecological cross-sectional municipal screening",
        "need_weights": NEED_WEIGHTS,
        "digital_weights": DIGITAL_WEIGHTS,
        "feasibility_weights": FEASIBILITY_WEIGHTS,
        "scenarios": SCENARIOS,
        "aggregation": "weighted geometric mean after winsorized empirical percentile normalization",
        "sia_role": "audit evidence only; all-procedure quantity is not consultation-specific and is not scored",
        "monte_carlo": {
            "iterations": 1000, "seed": 20260712,
            "need_weights": "Dirichlet(9,4,3,4)", "digital_weights": "Dirichlet(5,3,2)",
            "pharmacy_weights": "Dirichlet(5,5)", "pharmacy_feasibility_share": "Uniform(0.60,0.80)",
            "overall_need_share": "Uniform(0.40,0.70)",
            "interpretation": "exploratory robustness assumptions, not empirical priors",
        },
        "unmeasured": ["travel time", "individual clinical demand", "pharmacy site readiness", "causal impact"],
        "allowed_use": "hypothesis generation, municipal screening and aggregate geo-experiment planning",
        "ads_shortlist_rule": "top 100 eligible municipalities by Monte Carlo top-decile probability, then balanced score",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Phase 1 scores for {len(result):,} municipalities; {result['phase1_eligibility'].eq('eligible_phase1_proxy').sum():,} eligible")


if __name__ == "__main__":
    main()
