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


matrix_module = load_module("build_telemedicine_decision_matrix", SCRIPTS_DIR / "build_telemedicine_decision_matrix.py")


class TelemedicineDecisionMatrixTests(unittest.TestCase):
    def test_decision_matrix_prioritizes_interpretable_classes(self):
        source = pd.DataFrame(
            [
                {
                    "ibge_municipio": 1,
                    "ibge_municipio_7": "0000001",
                    "municipio_nome_ibge": "Capital Alta",
                    "uf_sigla": "AA",
                    "regiao_nome_oficial": "Teste",
                    "populacao_residente": 1_000_000,
                    "phase2_eligibility": "eligible_phase2_geodesic_proxy",
                    "telemedicine_phase2_balanced": 90,
                    "phase2_rank_balanced": 1,
                    "phase2_need_pillar": 95,
                    "phase2_spatial_mismatch_score": 65,
                    "phase2_feasibility_pillar": 80,
                    "digital_readiness_score": 90,
                    "households_with_internet_pct": 90,
                    "mobile_4g5g_resident_coverage_pct": 99,
                    "phase2_spatial_target_rank": pd.NA,
                    "phase4_routed_target_rank": pd.NA,
                    "phase4_interpretation": "not_routed_in_phase4",
                },
                {
                    "ibge_municipio": 2,
                    "ibge_municipio_7": "0000002",
                    "municipio_nome_ibge": "Piloto",
                    "uf_sigla": "BB",
                    "regiao_nome_oficial": "Teste",
                    "populacao_residente": 20_000,
                    "phase2_eligibility": "eligible_phase2_geodesic_proxy",
                    "telemedicine_phase2_balanced": 70,
                    "phase2_rank_balanced": 200,
                    "phase2_need_pillar": 80,
                    "phase2_spatial_mismatch_score": 95,
                    "phase2_feasibility_pillar": 55,
                    "digital_readiness_score": 40,
                    "households_with_internet_pct": 70,
                    "mobile_4g5g_resident_coverage_pct": 80,
                    "phase2_spatial_target_rank": 1,
                    "phase4_routed_target_rank": 1,
                    "phase4_interpretation": "phase4_primary_routed_target",
                },
                {
                    "ibge_municipio": 3,
                    "ibge_municipio_7": "0000003",
                    "municipio_nome_ibge": "Inclusao",
                    "uf_sigla": "CC",
                    "regiao_nome_oficial": "Teste",
                    "populacao_residente": 50_000,
                    "phase2_eligibility": "eligible_phase2_geodesic_proxy",
                    "telemedicine_phase2_balanced": 75,
                    "phase2_rank_balanced": 50,
                    "phase2_need_pillar": 92,
                    "phase2_spatial_mismatch_score": 40,
                    "phase2_feasibility_pillar": 35,
                    "digital_readiness_score": 10,
                    "households_with_internet_pct": 45,
                    "mobile_4g5g_resident_coverage_pct": 50,
                    "phase2_spatial_target_rank": pd.NA,
                    "phase4_routed_target_rank": pd.NA,
                    "phase4_interpretation": "not_routed_in_phase4",
                },
            ]
        )

        matrix = matrix_module.build_decision_matrix(source)
        by_name = matrix.set_index("municipio_nome_ibge")

        self.assertEqual(by_name.loc["Capital Alta", "decision_class"], "national_priority_high_readiness")
        self.assertEqual(by_name.loc["Piloto", "decision_class"], "pharmacy_assisted_pilot")
        self.assertEqual(by_name.loc["Inclusao", "decision_class"], "national_priority_inclusion_first")
        self.assertIn("rank nacional 1", by_name.loc["Capital Alta", "explanation"])

    def test_generated_decision_matrix_keeps_phase4_as_subset(self):
        path = PROJECT_DIR / "data" / "enriched" / "telemedicine_decision_matrix.csv"
        if not path.exists():
            self.skipTest("Decision matrix artifact has not been generated yet")
        matrix = pd.read_csv(path)

        self.assertGreater(len(matrix), 5500)
        self.assertEqual(int(matrix["phase2_rank_balanced"].le(100).sum()), 100)
        self.assertEqual(int(matrix["decision_class"].eq("pharmacy_assisted_pilot").sum()), 4)
        goiania = matrix.loc[
            matrix["municipio_nome_ibge"].eq("Goiânia") & matrix["uf_sigla"].eq("GO")
        ].iloc[0]
        self.assertEqual(int(goiania["phase2_rank_balanced"]), 1)
        self.assertNotEqual(goiania["decision_class"], "pharmacy_assisted_pilot")


if __name__ == "__main__":
    unittest.main()
