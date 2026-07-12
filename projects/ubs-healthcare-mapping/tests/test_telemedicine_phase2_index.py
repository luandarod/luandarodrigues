import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_phase2_index.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_phase2_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample() -> pd.DataFrame:
    return pd.DataFrame([
        {"ibge_municipio": "1", "phase1_need_score": 80, "phase1_deployment_feasibility_score": 80,
         "phase1_eligibility": "eligible_phase1_proxy", "origin_inside_main_polygon": True,
         "nearest_ubs_geodesic_km": 30, "nearest_pharmacy_geodesic_km": 1, "pharmacies": 2},
        {"ibge_municipio": "2", "phase1_need_score": 80, "phase1_deployment_feasibility_score": 80,
         "phase1_eligibility": "eligible_phase1_proxy", "origin_inside_main_polygon": True,
         "nearest_ubs_geodesic_km": 1, "nearest_pharmacy_geodesic_km": 30, "pharmacies": 2},
        {"ibge_municipio": "3", "phase1_need_score": 60, "phase1_deployment_feasibility_score": 60,
         "phase1_eligibility": "eligible_phase1_proxy", "origin_inside_main_polygon": True,
         "nearest_ubs_geodesic_km": 10, "nearest_pharmacy_geodesic_km": 10, "pharmacies": 2},
    ])


class TelemedicinePhase2IndexTests(unittest.TestCase):
    def test_far_ubs_near_pharmacy_has_higher_spatial_mismatch(self):
        module = load_module()
        result = module.build_phase2_index(sample())
        target = result.loc[result["ibge_municipio"].eq("1")].iloc[0]
        opposite = result.loc[result["ibge_municipio"].eq("2")].iloc[0]
        self.assertGreater(target["phase2_spatial_mismatch_score"], opposite["phase2_spatial_mismatch_score"])
        self.assertGreater(target["telemedicine_phase2_balanced"], opposite["telemedicine_phase2_balanced"])

    def test_outside_polygon_origin_is_not_scored(self):
        module = load_module()
        data = sample()
        data.loc[0, "origin_inside_main_polygon"] = False
        result = module.build_phase2_index(data)
        row = result.loc[result["ibge_municipio"].eq("1")].iloc[0]
        self.assertEqual(row["phase2_eligibility"], "invalid_origin_proxy")
        self.assertTrue(pd.isna(row["telemedicine_phase2_balanced"]))

    def test_phase1_need_is_preserved_as_separate_pillar(self):
        module = load_module()
        result = module.build_phase2_index(sample())
        self.assertTrue((result["phase2_need_pillar"] == result["phase1_need_score"]).all())


if __name__ == "__main__":
    unittest.main()
