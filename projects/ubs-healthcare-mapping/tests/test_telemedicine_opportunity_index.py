import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_opportunity_index.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_opportunity_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TelemedicineOpportunityIndexTests(unittest.TestCase):
    def setUp(self):
        self.source = pd.DataFrame([
            {
                "ibge_municipio": "100001",
                "municipio_nome_ibge": "Grande descoberta",
                "uf_sigla": "AA",
                "regiao_nome": "Teste",
                "populacao_residente": 1_000_000,
                "aps_coverage_capped_pct": 50,
                "active_ubs": 10,
                "active_ubs_per_100k": 1,
                "pharmacies": 100,
                "pharmacies_per_100k": 10,
            },
            {
                "ibge_municipio": "100002",
                "municipio_nome_ibge": "Pequena descoberta",
                "uf_sigla": "AA",
                "regiao_nome": "Teste",
                "populacao_residente": 50_000,
                "aps_coverage_capped_pct": 50,
                "active_ubs": 1,
                "active_ubs_per_100k": 2,
                "pharmacies": 5,
                "pharmacies_per_100k": 10,
            },
            {
                "ibge_municipio": "100003",
                "municipio_nome_ibge": "Sem farmacia",
                "uf_sigla": "BB",
                "regiao_nome": "Teste",
                "populacao_residente": 200_000,
                "aps_coverage_capped_pct": 40,
                "active_ubs": 2,
                "active_ubs_per_100k": 1,
                "pharmacies": 0,
                "pharmacies_per_100k": 0,
            },
        ])

    def test_estimates_potentially_uncovered_population(self):
        module = load_module()
        result, _ = module.build_index(self.source)

        large = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        self.assertEqual(int(large["potentially_uncovered_population"]), 500_000)
        self.assertAlmostEqual(large["aps_relative_gap"], 0.5)

    def test_absolute_need_distinguishes_equal_relative_coverage(self):
        module = load_module()
        result, _ = module.build_index(self.source)

        large = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        small = result.loc[result["ibge_municipio"].eq("100002")].iloc[0]
        self.assertGreater(large["uncovered_volume_percentile"], small["uncovered_volume_percentile"])
        self.assertGreater(large["need_score"], small["need_score"])

    def test_zero_pharmacy_is_not_a_deployment_candidate(self):
        module = load_module()
        result, _ = module.build_index(self.source)

        empty = result.loc[result["ibge_municipio"].eq("100003")].iloc[0]
        self.assertEqual(empty["pharmacy_launchability_score"], 0)
        self.assertEqual(empty["academic_eligibility"], "no_observed_pfpb_pharmacy")
        self.assertEqual(empty["positioning_segment"], "infrastructure_gap")

    def test_scenarios_and_rank_stability_are_emitted(self):
        module = load_module()
        result, sensitivity = module.build_index(self.source)

        self.assertEqual(set(sensitivity["scenario"]), {"balanced", "equity_led", "deployment_led"})
        self.assertEqual(len(sensitivity), len(result) * 3)
        self.assertTrue({"rank_best", "rank_worst", "rank_range"}.issubset(result.columns))

    def test_missing_core_data_is_not_scored(self):
        module = load_module()
        incomplete = pd.concat([
            self.source,
            pd.DataFrame([{
                "ibge_municipio": "100004",
                "municipio_nome_ibge": "Sem APS",
                "uf_sigla": "CC",
                "regiao_nome": "Teste",
                "populacao_residente": 100_000,
                "aps_coverage_capped_pct": pd.NA,
                "active_ubs": 1,
                "active_ubs_per_100k": 1,
                "pharmacies": 10,
                "pharmacies_per_100k": 10,
            }]),
        ], ignore_index=True)

        result, _ = module.build_index(incomplete)
        missing = result.loc[result["ibge_municipio"].eq("100004")].iloc[0]
        self.assertEqual(missing["academic_eligibility"], "insufficient_core_data")
        self.assertTrue(pd.isna(missing["telemedicine_opportunity_balanced"]))

    def test_reconciles_to_official_universe_and_excludes_invalid_codes(self):
        module = load_module()
        universe = pd.DataFrame([
            {"ibge_municipio": "100001", "municipio_nome_oficial": "Grande descoberta", "uf_sigla_oficial": "AA"},
            {"ibge_municipio": "100002", "municipio_nome_oficial": "Pequena descoberta", "uf_sigla_oficial": "AA"},
            {"ibge_municipio": "100003", "municipio_nome_oficial": "Sem farmacia", "uf_sigla_oficial": "BB"},
            {"ibge_municipio": "100004", "municipio_nome_oficial": "Ausente na fonte", "uf_sigla_oficial": "CC"},
        ])
        source = pd.concat([
            self.source,
            pd.DataFrame([{
                "ibge_municipio": "999999",
                "municipio_nome_ibge": "Codigo invalido",
                "uf_sigla": "ZZ",
            }]),
        ], ignore_index=True)

        reconciled, invalid = module.reconcile_official_universe(source, universe)

        self.assertEqual(set(reconciled["ibge_municipio"]), {"100001", "100002", "100003", "100004"})
        self.assertEqual(invalid["ibge_municipio"].tolist(), ["999999"])
        absent = reconciled.loc[reconciled["ibge_municipio"].eq("100004")].iloc[0]
        self.assertEqual(absent["municipio_nome_ibge"], "Ausente na fonte")
        self.assertEqual(absent["universe_status"], "missing_source_record")

    def test_structural_zero_gap_does_not_receive_midrank_need(self):
        module = load_module()
        full_coverage = self.source.iloc[[0]].copy()
        full_coverage["ibge_municipio"] = "100005"
        full_coverage["aps_coverage_capped_pct"] = 100
        result, _ = module.build_index(pd.concat([self.source, full_coverage], ignore_index=True))

        covered = result.loc[result["ibge_municipio"].eq("100005")].iloc[0]
        self.assertEqual(covered["uncovered_volume_percentile"], 0)
        self.assertEqual(covered["aps_gap_percentile"], 0)
        self.assertEqual(covered["need_score"], 0)

    def test_monte_carlo_sensitivity_is_reproducible(self):
        module = load_module()
        result, _ = module.build_index(self.source)

        first = module.monte_carlo_sensitivity(result, iterations=30, seed=7)
        second = module.monte_carlo_sensitivity(result, iterations=30, seed=7)

        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), len(result))
        eligible = first["academic_eligibility"].eq("eligible_proxy")
        self.assertTrue(first.loc[eligible, "mc_rank_median"].notna().all())
        self.assertTrue(first.loc[eligible, "mc_probability_top_decile"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
