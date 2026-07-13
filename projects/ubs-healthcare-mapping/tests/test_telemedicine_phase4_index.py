import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_phase4_index.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_phase4_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TelemedicinePhase4IndexTests(unittest.TestCase):
    def test_phase4_scores_only_routed_validation_subset(self):
        module = load_module()
        frame = pd.DataFrame([
            {
                "ibge_municipio_7": "1",
                "phase2_need_pillar": 80,
                "phase2_feasibility_pillar": 80,
                "active_ubs_travel_time_minutes": 25,
                "osm_pharmacy_travel_time_minutes": 2,
                "phase3_routed_hard_ubs_easy_pharmacy_flag": True,
            },
            {
                "ibge_municipio_7": "2",
                "phase2_need_pillar": 80,
                "phase2_feasibility_pillar": 80,
                "active_ubs_travel_time_minutes": 8,
                "osm_pharmacy_travel_time_minutes": 1,
                "phase3_routed_hard_ubs_easy_pharmacy_flag": False,
            },
            {
                "ibge_municipio_7": "3",
                "phase2_need_pillar": 80,
                "phase2_feasibility_pillar": 80,
                "active_ubs_travel_time_minutes": pd.NA,
                "osm_pharmacy_travel_time_minutes": pd.NA,
                "phase3_routed_hard_ubs_easy_pharmacy_flag": pd.NA,
            },
        ])

        result = module.build_phase4_index(frame)

        target = result.loc[result["ibge_municipio_7"].eq("1")].iloc[0]
        routed_non_target = result.loc[result["ibge_municipio_7"].eq("2")].iloc[0]
        unrouted = result.loc[result["ibge_municipio_7"].eq("3")].iloc[0]
        self.assertEqual(target["phase4_interpretation"], "phase4_primary_routed_target")
        self.assertEqual(target["phase4_routed_target_rank"], 1)
        self.assertEqual(routed_non_target["phase4_eligibility"], "eligible_phase4_routed_validation")
        self.assertTrue(pd.isna(routed_non_target["phase4_routed_target_rank"]))
        self.assertEqual(unrouted["phase4_eligibility"], "not_routed_phase4")
        self.assertTrue(pd.isna(unrouted["telemedicine_phase4_routed_validation"]))


if __name__ == "__main__":
    unittest.main()
