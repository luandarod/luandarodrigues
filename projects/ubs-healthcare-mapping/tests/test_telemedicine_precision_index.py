import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_precision_index.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_precision_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TelemedicinePrecisionIndexTests(unittest.TestCase):
    def test_precision_index_ranks_high_need_high_mismatch_municipality_first(self):
        module = load_module()
        phase2 = pd.DataFrame([
            {
                "ibge_municipio_7": "1",
                "ibge_municipio": "1",
                "municipio_nome_ibge": "A",
                "uf_sigla": "GO",
                "populacao_residente": 1000,
                "phase2_need_pillar": 90,
                "phase2_feasibility_pillar": 80,
                "telemedicine_phase2_balanced": 70,
                "phase2_rank_balanced": 2,
                "phase2_eligibility": "eligible_phase2_geodesic_proxy",
            },
            {
                "ibge_municipio_7": "2",
                "ibge_municipio": "2",
                "municipio_nome_ibge": "B",
                "uf_sigla": "GO",
                "populacao_residente": 1000,
                "phase2_need_pillar": 40,
                "phase2_feasibility_pillar": 80,
                "telemedicine_phase2_balanced": 80,
                "phase2_rank_balanced": 1,
                "phase2_eligibility": "eligible_phase2_geodesic_proxy",
            },
        ])
        precision = pd.DataFrame([
            {
                "ibge_municipio_7": "1",
                "phase5_weighted_p90_ubs_km": 20,
                "phase5_population_share_pharmacy_le_2km": 0.90,
                "phase5_population_share_hard_ubs_easy_pharmacy": 0.80,
                "phase5_population_origin_coverage_ratio": 1.0,
                "phase5_access_evidence_grade": "A_intramunicipal_population_weighted",
                "phase5_precision_status": "intramunicipal_population_weighted_ready",
            },
            {
                "ibge_municipio_7": "2",
                "phase5_weighted_p90_ubs_km": 1,
                "phase5_population_share_pharmacy_le_2km": 0.10,
                "phase5_population_share_hard_ubs_easy_pharmacy": 0.00,
                "phase5_population_origin_coverage_ratio": 1.0,
                "phase5_access_evidence_grade": "A_intramunicipal_population_weighted",
                "phase5_precision_status": "intramunicipal_population_weighted_ready",
            },
        ])

        result = module.build_precision_index(phase2, precision)

        self.assertEqual(result.iloc[0]["ibge_municipio_7"], "1")
        self.assertEqual(result.iloc[0]["phase5_precision_rank"], 1)
        self.assertEqual(result.iloc[0]["phase5_index_eligibility"], "eligible_phase5_precision")


if __name__ == "__main__":
    unittest.main()
