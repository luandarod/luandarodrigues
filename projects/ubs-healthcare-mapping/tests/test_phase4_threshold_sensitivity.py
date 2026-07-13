import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_phase4_threshold_sensitivity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_phase4_threshold_sensitivity", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Phase4ThresholdSensitivityTests(unittest.TestCase):
    def test_counts_candidates_for_each_threshold_pair(self):
        module = load_module()
        frame = pd.DataFrame([
            {
                "municipio_nome_oficial": "A",
                "uf_sigla_oficial": "AA",
                "active_ubs_travel_time_minutes": 20,
                "osm_pharmacy_travel_time_minutes": 2,
            },
            {
                "municipio_nome_oficial": "B",
                "uf_sigla_oficial": "BB",
                "active_ubs_travel_time_minutes": 12,
                "osm_pharmacy_travel_time_minutes": 8,
            },
        ])

        result = module.build_sensitivity(frame, ubs_thresholds=(10, 15), pharmacy_thresholds=(3, 10))

        strict = result.loc[
            result["ubs_hard_minutes_threshold"].eq(15)
            & result["pharmacy_easy_minutes_threshold"].eq(3)
        ].iloc[0]
        broad = result.loc[
            result["ubs_hard_minutes_threshold"].eq(10)
            & result["pharmacy_easy_minutes_threshold"].eq(10)
        ].iloc[0]
        self.assertEqual(strict["candidate_count"], 1)
        self.assertEqual(strict["candidate_municipalities"], "A/AA")
        self.assertEqual(broad["candidate_count"], 2)


if __name__ == "__main__":
    unittest.main()
