import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


state_module = load_module("build_telemedicine_state_summary", SCRIPTS_DIR / "build_telemedicine_state_summary.py")


class TelemedicineStateSummaryTests(unittest.TestCase):
    def test_state_summary_aggregates_top100_and_strategy(self):
        source = pd.DataFrame(
            [
                {
                    "uf_sigla": "AA",
                    "regiao_nome_oficial": "Teste",
                    "populacao_residente": 1_000_000,
                    "decision_class": "national_priority_high_readiness",
                    "telemedicine_phase2_balanced": 90,
                    "phase2_rank_balanced": 1,
                    "phase2_need_pillar": 90,
                    "phase2_spatial_mismatch_score": 70,
                    "phase2_feasibility_pillar": 80,
                    "digital_readiness_score": 90,
                },
                {
                    "uf_sigla": "AA",
                    "regiao_nome_oficial": "Teste",
                    "populacao_residente": 500_000,
                    "decision_class": "pharmacy_assisted_pilot",
                    "telemedicine_phase2_balanced": 70,
                    "phase2_rank_balanced": 50,
                    "phase2_need_pillar": 80,
                    "phase2_spatial_mismatch_score": 95,
                    "phase2_feasibility_pillar": 60,
                    "digital_readiness_score": 70,
                },
                {
                    "uf_sigla": "BB",
                    "regiao_nome_oficial": "Teste",
                    "populacao_residente": 800_000,
                    "decision_class": "regional_scale_opportunity",
                    "telemedicine_phase2_balanced": 55,
                    "phase2_rank_balanced": 200,
                    "phase2_need_pillar": 60,
                    "phase2_spatial_mismatch_score": 55,
                    "phase2_feasibility_pillar": 50,
                    "digital_readiness_score": 65,
                },
            ]
        )

        summary = state_module.build_state_summary(source).set_index("uf_sigla")

        self.assertEqual(int(summary.loc["AA", "top100_municipalities"]), 2)
        self.assertEqual(int(summary.loc["AA", "pharmacy_assisted_pilot_count"]), 1)
        self.assertEqual(summary.loc["AA", "state_strategy_tier"], "hybrid_national_and_pharmacy_pilot")
        self.assertEqual(int(summary.loc["BB", "regional_scale_opportunity_count"]), 1)
        self.assertGreater(summary.loc["AA", "population_weighted_phase2_score"], summary.loc["BB", "population_weighted_phase2_score"])

    def test_generated_state_summary_matches_municipal_totals(self):
        path = PROJECT_DIR / "data" / "enriched" / "telemedicine_state_opportunity_summary.csv"
        if not path.exists():
            self.skipTest("State opportunity summary artifact has not been generated yet")
        summary = pd.read_csv(path)

        self.assertEqual(len(summary), 27)
        self.assertEqual(int(summary["top100_municipalities"].sum()), 100)
        self.assertEqual(int(summary["pharmacy_assisted_pilot_count"].sum()), 4)
        self.assertTrue(summary["state_rank"].is_unique)
        self.assertIn(summary.sort_values("state_rank").iloc[0]["uf_sigla"], {"SP", "RJ", "DF", "GO", "RS", "MG", "PR"})


if __name__ == "__main__":
    unittest.main()
