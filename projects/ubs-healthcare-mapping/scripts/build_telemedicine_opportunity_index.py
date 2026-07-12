"""Build a transparent preliminary municipal telemedicine opportunity index.

This is an ecological screening instrument. It estimates need and observed
Farmacia Popular launchability; it does not measure individual demand,
travel time, digital readiness, clinical eligibility, or causal impact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCENARIOS = {
    "balanced": {"need": 0.50, "launchability": 0.50},
    "equity_led": {"need": 0.70, "launchability": 0.30},
    "deployment_led": {"need": 0.40, "launchability": 0.60},
}

EPSILON = 1e-6


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def reconcile_official_universe(
    source: pd.DataFrame,
    universe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Align analysis rows to official IBGE codes and isolate invalid source codes."""
    observed = source.copy()
    observed["ibge_municipio"] = (
        observed["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
    )
    official = universe.copy()
    official["ibge_municipio"] = (
        official["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
    )
    official = official.drop_duplicates("ibge_municipio")
    official_codes = set(official["ibge_municipio"])
    invalid = observed.loc[~observed["ibge_municipio"].isin(official_codes)].copy()
    valid = observed.loc[observed["ibge_municipio"].isin(official_codes)].copy()
    overlapping_official_columns = (set(official.columns) & set(valid.columns)) - {"ibge_municipio"}
    valid = valid.drop(columns=sorted(overlapping_official_columns))
    valid["source_row_present"] = True
    reconciled = official.merge(valid, on="ibge_municipio", how="left", validate="one_to_one")
    reconciled["source_row_present"] = reconciled["source_row_present"].eq(True)
    if "municipio_nome_ibge" not in reconciled:
        reconciled["municipio_nome_ibge"] = reconciled["municipio_nome_oficial"]
    else:
        reconciled["municipio_nome_ibge"] = reconciled["municipio_nome_ibge"].fillna(
            reconciled["municipio_nome_oficial"]
        )
    if "uf_sigla" not in reconciled:
        reconciled["uf_sigla"] = reconciled["uf_sigla_oficial"]
    else:
        reconciled["uf_sigla"] = reconciled["uf_sigla"].fillna(reconciled["uf_sigla_oficial"])
    reconciled["universe_status"] = "matched_source"
    reconciled.loc[~reconciled["source_row_present"], "universe_status"] = "missing_source_record"
    return reconciled, invalid


def _percentile(
    values: pd.Series,
    valid: pd.Series,
    *,
    inverse: bool = False,
    log_transform: bool = False,
    structural_zero: bool = False,
) -> pd.Series:
    """Return winsorized empirical percentiles for an explicitly valid universe."""
    output = pd.Series(np.nan, index=values.index, dtype=float)
    sample = pd.to_numeric(values.loc[valid], errors="coerce")
    sample = sample.loc[sample.notna()]
    if structural_zero:
        output.loc[sample.loc[sample.le(0)].index] = 0
        sample = sample.loc[sample.gt(0)]
    if sample.empty:
        return output
    if log_transform:
        sample = np.log1p(sample.clip(lower=0))
    lower, upper = sample.quantile([0.01, 0.99])
    sample = sample.clip(lower=lower, upper=upper)
    output.loc[sample.index] = sample.rank(
        pct=True,
        ascending=not inverse,
        method="average",
    )
    return output


def _weighted_geometric(components: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    matrix = pd.DataFrame(components).clip(lower=EPSILON, upper=1)
    available = matrix.notna().all(axis=1)
    result = pd.Series(np.nan, index=matrix.index, dtype=float)
    result.loc[available] = np.exp(
        sum(np.log(matrix.loc[available, column]) * weights[column] for column in weights)
    )
    return result


def build_index(source: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate need, pharmacy launchability and three declared scenarios."""
    result = source.copy()
    result["ibge_municipio"] = (
        result["ibge_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str[:6]
    )

    population = _numeric(result, "populacao_residente")
    aps_coverage = _numeric(result, "aps_coverage_capped_pct").clip(lower=0, upper=100)
    active_ubs_rate = _numeric(result, "active_ubs_per_100k")
    pharmacies = _numeric(result, "pharmacies").fillna(0).clip(lower=0)
    pharmacy_rate = _numeric(result, "pharmacies_per_100k").fillna(0).clip(lower=0)

    core_complete = population.gt(0) & aps_coverage.notna() & active_ubs_rate.notna()
    pharmacy_observed = pharmacies.gt(0)
    result["aps_relative_gap"] = (1 - aps_coverage / 100).clip(lower=0, upper=1)
    result["potentially_uncovered_population"] = population * result["aps_relative_gap"]

    result["uncovered_volume_percentile"] = _percentile(
        result["potentially_uncovered_population"],
        core_complete,
        log_transform=True,
        structural_zero=True,
    )
    result["aps_gap_percentile"] = _percentile(
        result["aps_relative_gap"],
        core_complete,
        structural_zero=True,
    )
    result["active_ubs_scarcity_percentile"] = _percentile(
        active_ubs_rate,
        core_complete,
        inverse=True,
    )
    result["need_score"] = 100 * _weighted_geometric(
        {
            "uncovered_volume": result["uncovered_volume_percentile"],
            "aps_gap": result["aps_gap_percentile"],
            "ubs_scarcity": result["active_ubs_scarcity_percentile"],
        },
        {"uncovered_volume": 0.50, "aps_gap": 0.25, "ubs_scarcity": 0.25},
    )
    result.loc[core_complete & result["aps_relative_gap"].eq(0), "need_score"] = 0

    positive_universe = core_complete & pharmacy_observed
    result["pharmacy_count_percentile"] = _percentile(
        pharmacies,
        positive_universe,
        log_transform=True,
    ).fillna(0)
    result["pharmacy_density_percentile"] = _percentile(
        pharmacy_rate,
        positive_universe,
    ).fillna(0)
    result["pharmacy_launchability_score"] = 100 * _weighted_geometric(
        {
            "count": result["pharmacy_count_percentile"],
            "density": result["pharmacy_density_percentile"],
        },
        {"count": 0.50, "density": 0.50},
    )
    result.loc[~pharmacy_observed, "pharmacy_launchability_score"] = 0

    result["academic_eligibility"] = "eligible_proxy"
    result.loc[core_complete & ~pharmacy_observed, "academic_eligibility"] = "no_observed_pfpb_pharmacy"
    result.loc[~core_complete, "academic_eligibility"] = "insufficient_core_data"
    result["evidence_grade"] = "B_proxy_only"
    result.loc[~core_complete, "evidence_grade"] = "C_incomplete"
    result["spatial_access_status"] = "not_measured"
    result["digital_readiness_status"] = "not_measured"
    result["clinical_demand_status"] = "not_measured"

    eligible = result["academic_eligibility"].eq("eligible_proxy")
    sensitivity_rows = []
    rank_columns = []
    for scenario, weights in SCENARIOS.items():
        score_column = f"telemedicine_opportunity_{scenario}"
        rank_column = f"rank_{scenario}"
        result[score_column] = 100 * _weighted_geometric(
            {
                "need": result["need_score"] / 100,
                "launchability": result["pharmacy_launchability_score"] / 100,
            },
            weights,
        )
        result.loc[core_complete & result["need_score"].eq(0), score_column] = 0
        result.loc[~core_complete, score_column] = np.nan
        result[rank_column] = result.loc[eligible, score_column].rank(ascending=False, method="min")
        rank_columns.append(rank_column)
        scenario_frame = result[[
            "ibge_municipio", "municipio_nome_ibge", "uf_sigla", score_column, rank_column,
        ]].copy()
        scenario_frame = scenario_frame.rename(columns={score_column: "opportunity_score", rank_column: "rank"})
        scenario_frame.insert(3, "scenario", scenario)
        sensitivity_rows.append(scenario_frame)

    result["rank_best"] = result[rank_columns].min(axis=1)
    result["rank_worst"] = result[rank_columns].max(axis=1)
    result["rank_range"] = result["rank_worst"] - result["rank_best"]

    need_percentile = result.loc[eligible, "need_score"].rank(pct=True, method="average")
    launch_percentile = result.loc[eligible, "pharmacy_launchability_score"].rank(pct=True, method="average")
    result["need_priority_percentile"] = need_percentile
    result["launchability_priority_percentile"] = launch_percentile
    result["positioning_segment"] = "monitor"
    result.loc[eligible & result["need_priority_percentile"].ge(0.80), "positioning_segment"] = "high_need_build_supply"
    result.loc[eligible & result["launchability_priority_percentile"].ge(0.80), "positioning_segment"] = "launchable_secondary"
    result.loc[
        eligible
        & result["need_priority_percentile"].ge(0.80)
        & result["launchability_priority_percentile"].ge(0.80),
        "positioning_segment",
    ] = "pilot_candidate"
    result.loc[core_complete & ~pharmacy_observed, "positioning_segment"] = "infrastructure_gap"
    result.loc[~core_complete, "positioning_segment"] = "insufficient_data"

    result["stable_top_decile"] = (
        eligible
        & result[rank_columns].le(max(1, int(eligible.sum() * 0.10))).all(axis=1)
    )

    sensitivity = pd.concat(sensitivity_rows, ignore_index=True)
    result = result.sort_values("telemedicine_opportunity_balanced", ascending=False, na_position="last")
    return result, sensitivity


def monte_carlo_sensitivity(
    result: pd.DataFrame,
    *,
    iterations: int = 1_000,
    seed: int = 20260712,
) -> pd.DataFrame:
    """Estimate ranking uncertainty under declared exploratory weight ranges.

    Dirichlet draws vary component weights around the nominal structures. The
    need-pillar share is sampled uniformly from 40% to 70%. These distributions
    are analytical assumptions for robustness testing, not empirical priors.
    """
    rng = np.random.default_rng(seed)
    eligible = result["academic_eligibility"].eq("eligible_proxy")
    subset = result.loc[eligible]
    n = len(subset)
    rank_matrix = np.empty((iterations, n), dtype=np.float32)
    score_matrix = np.empty((iterations, n), dtype=np.float32)

    need_components = np.clip(subset[[
        "uncovered_volume_percentile", "aps_gap_percentile", "active_ubs_scarcity_percentile",
    ]].to_numpy(dtype=float), EPSILON, 1)
    launch_components = np.clip(subset[[
        "pharmacy_count_percentile", "pharmacy_density_percentile",
    ]].to_numpy(dtype=float), EPSILON, 1)
    structural_zero_need = subset["aps_relative_gap"].eq(0).to_numpy()

    for iteration in range(iterations):
        need_weights = rng.dirichlet([10, 5, 5])
        launch_weights = rng.dirichlet([5, 5])
        overall_need_weight = rng.uniform(0.40, 0.70)
        need = np.exp(np.log(need_components) @ need_weights)
        need[structural_zero_need] = 0
        launchability = np.exp(np.log(launch_components) @ launch_weights)
        score = np.exp(
            np.log(np.clip(need, EPSILON, 1)) * overall_need_weight
            + np.log(launchability) * (1 - overall_need_weight)
        ) * 100
        score[structural_zero_need] = 0
        score_matrix[iteration] = score
        rank_matrix[iteration] = pd.Series(score).rank(ascending=False, method="average").to_numpy()

    output = result[["ibge_municipio", "municipio_nome_ibge", "uf_sigla", "academic_eligibility"]].copy()
    for column in (
        "mc_score_median", "mc_score_p05", "mc_score_p95",
        "mc_rank_median", "mc_rank_p05", "mc_rank_p95", "mc_probability_top_decile",
    ):
        output[column] = np.nan
    threshold = max(1, int(np.ceil(n * 0.10)))
    output.loc[eligible, "mc_score_median"] = np.median(score_matrix, axis=0)
    output.loc[eligible, "mc_score_p05"] = np.quantile(score_matrix, 0.05, axis=0)
    output.loc[eligible, "mc_score_p95"] = np.quantile(score_matrix, 0.95, axis=0)
    output.loc[eligible, "mc_rank_median"] = np.median(rank_matrix, axis=0)
    output.loc[eligible, "mc_rank_p05"] = np.quantile(rank_matrix, 0.05, axis=0)
    output.loc[eligible, "mc_rank_p95"] = np.quantile(rank_matrix, 0.95, axis=0)
    output.loc[eligible, "mc_probability_top_decile"] = (rank_matrix <= threshold).mean(axis=0)
    return output.sort_values("mc_rank_median", na_position="last")


def write_metadata(path: Path, row_count: int, invalid_code_count: int) -> None:
    metadata = {
        "index_name": "Preliminary Municipal Telemedicine Opportunity Index",
        "unit_of_analysis": "Brazilian municipality",
        "design": "ecological cross-sectional screening",
        "row_count": row_count,
        "invalid_source_code_count": invalid_code_count,
        "need_components": {
            "potentially_uncovered_population_percentile": 0.50,
            "aps_relative_gap_percentile": 0.25,
            "active_ubs_per_100k_inverse_percentile": 0.25,
        },
        "launchability_components": {
            "pfpb_absolute_count_percentile": 0.50,
            "pfpb_per_100k_percentile": 0.50,
        },
        "aggregation": "weighted geometric mean",
        "normalization": "1st/99th percentile winsorization plus empirical percentile rank; log1p for counts",
        "scenarios": SCENARIOS,
        "monte_carlo": {
            "iterations": 1000,
            "seed": 20260712,
            "need_component_weights": "Dirichlet(10,5,5)",
            "launchability_component_weights": "Dirichlet(5,5)",
            "overall_need_weight": "Uniform(0.40,0.70)",
            "interpretation": "exploratory robustness assumptions, not empirical priors",
        },
        "not_measured": [
            "travel time to UBS or pharmacy",
            "physician FTE and consultation production",
            "digital and site readiness",
            "individual clinical demand",
            "causal impact of telemedicine",
        ],
        "allowed_use": "hypothesis generation, municipal screening, aggregate media planning",
        "prohibited_interpretation": "individual targeting, diagnosis, observed demand, real geographic proximity, causal effect",
    }
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build preliminary municipal telemedicine opportunity data.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_pharmacy_access_gap.csv"),
    )
    parser.add_argument(
        "--universe",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/reference/ibge_municipality_universe.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_opportunity_preliminary.csv"),
    )
    parser.add_argument(
        "--sensitivity-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_opportunity_scenarios.csv"),
    )
    parser.add_argument(
        "--candidates-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_opportunity_candidates.csv"),
    )
    parser.add_argument(
        "--invalid-codes-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/quality/telemedicine_index_invalid_codes.csv"),
    )
    parser.add_argument(
        "--analytic-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_pre_paper_analytic.csv"),
    )
    parser.add_argument(
        "--monte-carlo-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_opportunity_monte_carlo.csv"),
    )
    parser.add_argument(
        "--ads-shortlist-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_ads_geo_shortlist.csv"),
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_opportunity_metadata.json"),
    )
    args = parser.parse_args()

    source = pd.read_csv(args.input)
    reconciled, invalid = reconcile_official_universe(source, pd.read_csv(args.universe))
    result, sensitivity = build_index(reconciled)
    for path in (
        args.output,
        args.sensitivity_output,
        args.candidates_output,
        args.invalid_codes_output,
        args.analytic_output,
        args.monte_carlo_output,
        args.ads_shortlist_output,
        args.metadata_output,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    sensitivity.to_csv(args.sensitivity_output, index=False)
    candidates = result.loc[
        result["positioning_segment"].isin(["pilot_candidate", "high_need_build_supply", "launchable_secondary"])
    ].copy()
    candidates.to_csv(args.candidates_output, index=False)
    invalid.to_csv(args.invalid_codes_output, index=False)
    monte_carlo = monte_carlo_sensitivity(result)
    monte_carlo.to_csv(args.monte_carlo_output, index=False)
    analytic = result.merge(
        monte_carlo[[
            "ibge_municipio", "mc_score_median", "mc_score_p05", "mc_score_p95",
            "mc_rank_median", "mc_rank_p05", "mc_rank_p95", "mc_probability_top_decile",
        ]],
        on="ibge_municipio",
        how="left",
    )
    analytic_columns = [
        "ibge_municipio", "ibge_municipio_7", "municipio_nome_ibge", "uf_sigla",
        "uf_nome_oficial", "regiao_nome_oficial", "universe_status",
        "populacao_residente", "aps_coverage_capped_pct", "aps_relative_gap",
        "potentially_uncovered_population", "ubs_records", "active_ubs",
        "active_ubs_per_100k", "pharmacies", "pharmacies_per_100k",
        "uncovered_volume_percentile", "aps_gap_percentile", "active_ubs_scarcity_percentile",
        "pharmacy_count_percentile", "pharmacy_density_percentile", "need_score",
        "pharmacy_launchability_score", "telemedicine_opportunity_balanced",
        "telemedicine_opportunity_equity_led", "telemedicine_opportunity_deployment_led",
        "rank_balanced", "rank_equity_led", "rank_deployment_led", "rank_best", "rank_worst",
        "rank_range", "mc_score_median", "mc_score_p05", "mc_score_p95", "mc_rank_median",
        "mc_rank_p05", "mc_rank_p95", "mc_probability_top_decile", "positioning_segment",
        "stable_top_decile", "academic_eligibility", "evidence_grade", "spatial_access_status",
        "digital_readiness_status", "clinical_demand_status",
    ]
    analytic[analytic_columns].to_csv(args.analytic_output, index=False)
    ads_shortlist = result.loc[result["stable_top_decile"]].merge(
        monte_carlo[["ibge_municipio", "mc_rank_median", "mc_rank_p05", "mc_rank_p95", "mc_probability_top_decile"]],
        on="ibge_municipio",
        how="left",
    ).sort_values(
        ["mc_probability_top_decile", "telemedicine_opportunity_balanced"],
        ascending=[False, False],
    ).head(100)
    ads_shortlist.to_csv(args.ads_shortlist_output, index=False)
    write_metadata(args.metadata_output, len(result), len(invalid))
    print(
        f"Saved {len(result):,} official municipalities, {len(candidates):,} candidate rows "
        f"and {len(invalid):,} invalid source codes"
    )


if __name__ == "__main__":
    main()
