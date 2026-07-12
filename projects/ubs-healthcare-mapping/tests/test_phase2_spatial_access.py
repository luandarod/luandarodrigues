import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_phase2_spatial_access.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_phase2_spatial_access", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Phase2SpatialAccessTests(unittest.TestCase):
    def test_polygon_centroid_for_square_is_center_and_inside(self):
        module = load_module()
        coordinates = [[[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]]
        longitude, latitude, inside = module.main_ring_centroid(coordinates)
        self.assertAlmostEqual(longitude, 1.0)
        self.assertAlmostEqual(latitude, 1.0)
        self.assertTrue(inside)

    def test_nearest_distance_is_zero_for_same_coordinate(self):
        module = load_module()
        origins = pd.DataFrame([{"ibge_municipio_7": "1", "origin_latitude": -16.68, "origin_longitude": -49.25}])
        facilities = pd.DataFrame([{"facility_id": "x", "latitude": -16.68, "longitude": -49.25}])
        result = module.nearest_facility(origins, facilities, "ubs")
        self.assertAlmostEqual(result.iloc[0]["nearest_ubs_geodesic_km"], 0.0, places=5)
        self.assertEqual(result.iloc[0]["nearest_ubs_id"], "x")

    def test_classification_requires_far_ubs_near_pharmacy_and_pfpb_presence(self):
        module = load_module()
        frame = pd.DataFrame([
            {"nearest_ubs_geodesic_km": 40, "nearest_pharmacy_geodesic_km": 0.5, "pharmacies": 2},
            {"nearest_ubs_geodesic_km": 1, "nearest_pharmacy_geodesic_km": 20, "pharmacies": 2},
            {"nearest_ubs_geodesic_km": 30, "nearest_pharmacy_geodesic_km": 0.5, "pharmacies": 0},
            {"nearest_ubs_geodesic_km": 10, "nearest_pharmacy_geodesic_km": 10, "pharmacies": 1},
        ])
        result = module.classify_mismatch(frame)
        self.assertTrue(result.iloc[0]["hard_ubs_easy_pharmacy_flag"])
        self.assertFalse(result.iloc[1]["hard_ubs_easy_pharmacy_flag"])
        self.assertFalse(result.iloc[2]["hard_ubs_easy_pharmacy_flag"])


if __name__ == "__main__":
    unittest.main()
