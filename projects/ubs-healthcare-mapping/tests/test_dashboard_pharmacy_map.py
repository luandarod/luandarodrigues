import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_dashboard_data.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_dashboard_data", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DashboardPharmacyMapTests(unittest.TestCase):
    def test_builds_geojson_with_access_gap_properties(self):
        module = load_module()
        geometries = {"3550308": {"uf_id": 35, "uf_sigla": "SP", "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]]}}
        gap = pd.DataFrame([{
            "ibge_municipio": "355030", "municipio_nome_ibge": "São Paulo", "uf_sigla": "SP",
            "populacao_residente": 100000, "ubs_records": 10, "active_ubs": 8, "active_ubs_per_100k": 8,
            "aps_coverage_capped_pct": 70, "pharmacies": 20, "ubs_per_100k": 1.2,
            "pharmacies_per_100k": 2.4, "access_mismatch_score": 88,
            "access_mismatch_flag": "consistent_mismatch", "evidence_level": "complete",
            "threshold_active_ubs_per_100k_q25": 9, "threshold_pharmacies_per_100k_median": 2,
            "nearest_ubs_geodesic_km": 8, "nearest_pharmacy_geodesic_km": 1,
            "hard_ubs_easy_pharmacy_flag": True, "telemedicine_phase2_balanced": 72,
            "phase2_spatial_target_rank": 1,
        }])

        result = module.build_gap_geojson(geometries, gap)

        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(result["features"][0]["properties"]["pharmacies"], 20)
        self.assertTrue(result["features"][0]["properties"]["hard_ubs_easy_pharmacy_flag"])
        self.assertEqual(result["features"][0]["geometry"]["type"], "MultiPolygon")


if __name__ == "__main__":
    unittest.main()
