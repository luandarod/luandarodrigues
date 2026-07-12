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
            "ubs_records": 10, "pharmacies": 20, "ubs_per_100k": 1.2,
            "pharmacies_per_100k": 2.4, "access_mismatch_score": 88,
            "access_mismatch_flag": "doctor_harder_pharmacy_easier",
        }])

        result = module.build_gap_geojson(geometries, gap)

        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(result["features"][0]["properties"]["pharmacies"], 20)
        self.assertEqual(result["features"][0]["geometry"]["type"], "MultiPolygon")


if __name__ == "__main__":
    unittest.main()
