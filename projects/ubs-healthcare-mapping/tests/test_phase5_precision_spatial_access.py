import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_precision_spatial_access.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_precision_spatial_access", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Phase5PrecisionSpatialAccessTests(unittest.TestCase):
    def test_weighted_quantile_uses_population_weights(self):
        module = load_module()
        values = pd.Series([1.0, 10.0])
        weights = pd.Series([90.0, 10.0])

        self.assertAlmostEqual(module.weighted_quantile(values, weights, 0.50), 1.0)
        self.assertAlmostEqual(module.weighted_quantile(values, weights, 0.95), 10.0)

    def test_aggregate_origin_access_builds_population_weighted_mismatch(self):
        module = load_module()
        origin_access = pd.DataFrame([
            {
                "ibge_municipio_7": "1",
                "origin_population": 80,
                "nearest_ubs_geodesic_km": 6,
                "nearest_pharmacy_geodesic_km": 1,
            },
            {
                "ibge_municipio_7": "1",
                "origin_population": 20,
                "nearest_ubs_geodesic_km": 1,
                "nearest_pharmacy_geodesic_km": 5,
            },
        ])
        phase2 = pd.DataFrame([{
            "ibge_municipio_7": "1",
            "populacao_residente": 100,
            "active_ubs": 1,
            "physician_fte_40h": 0.5,
            "pharmacies": 2,
        }])

        result = module.aggregate_origin_access(origin_access, phase2)
        row = result.iloc[0]

        self.assertAlmostEqual(row["phase5_weighted_mean_ubs_km"], 5.0)
        self.assertAlmostEqual(row["phase5_population_share_ubs_gt_5km"], 0.8)
        self.assertAlmostEqual(row["phase5_population_share_pharmacy_le_2km"], 0.8)
        self.assertAlmostEqual(row["phase5_population_share_hard_ubs_easy_pharmacy"], 0.8)
        self.assertAlmostEqual(row["phase5_population_origin_coverage_ratio"], 1.0)
        self.assertAlmostEqual(row["phase5_population_per_active_ubs"], 100.0)


if __name__ == "__main__":
    unittest.main()
