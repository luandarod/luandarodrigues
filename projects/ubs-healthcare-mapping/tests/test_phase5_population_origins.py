import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_population_origins.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_population_origins", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Phase5PopulationOriginTests(unittest.TestCase):
    def test_proxy_origins_preserve_municipal_population_and_status(self):
        module = load_module()
        spatial = pd.DataFrame([
            {
                "ibge_municipio_7": "5208707",
                "municipio_nome_oficial": "Goiânia",
                "uf_sigla_oficial": "GO",
                "origin_latitude": -16.6802,
                "origin_longitude": -49.2565,
                "populacao_residente": 1437366,
                "origin_quality_valid": True,
            }
        ])

        result = module.build_proxy_origins(spatial)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["origin_population"], 1437366)
        self.assertEqual(result.iloc[0]["origin_granularity"], "municipality_single_origin")
        self.assertEqual(result.iloc[0]["precision_status"], "needs_intramunicipal_population_origins")

    def test_validate_origins_rejects_invalid_brazil_coordinates(self):
        module = load_module()
        origins = pd.DataFrame([
            {
                "origin_id": "bad",
                "ibge_municipio_7": "5208707",
                "origin_latitude": 40.0,
                "origin_longitude": -49.0,
                "origin_population": 100,
                "origin_source": "manual",
                "origin_granularity": "sector",
            }
        ])

        with self.assertRaises(ValueError):
            module.validate_origins(origins)

    def test_manual_origins_require_2022_source_year_by_default(self):
        module = load_module()
        origins = pd.DataFrame([
            {
                "origin_id": "sector-1",
                "ibge_municipio_7": "5208707",
                "origin_latitude": -16.7,
                "origin_longitude": -49.2,
                "origin_population": 100,
                "origin_source": "IBGE sector test",
                "origin_granularity": "census_sector",
                "source_year": 2010,
            }
        ])

        with self.assertRaises(ValueError):
            module.normalize_manual_origins(origins, allow_non_2022=False)

    def test_blend_manual_with_proxy_replaces_matching_municipality_only(self):
        module = load_module()
        manual = pd.DataFrame([
            {
                "origin_id": "sector-1",
                "ibge_municipio_7": "5208707",
                "origin_latitude": -16.7,
                "origin_longitude": -49.2,
                "origin_population": 100,
                "origin_source": "IBGE 2022 setores",
                "origin_granularity": "census_sector",
                "source_year": 2022,
            }
        ])
        proxy = pd.DataFrame([
            {
                "origin_id": "5208707_municipal_proxy",
                "ibge_municipio_7": "5208707",
                "origin_latitude": -16.68,
                "origin_longitude": -49.25,
                "origin_population": 1437366,
                "origin_source": "proxy",
                "origin_granularity": "municipality_single_origin",
            },
            {
                "origin_id": "4106902_municipal_proxy",
                "ibge_municipio_7": "4106902",
                "origin_latitude": -25.42,
                "origin_longitude": -49.27,
                "origin_population": 1773718,
                "origin_source": "proxy",
                "origin_granularity": "municipality_single_origin",
            },
        ])

        result = module.blend_manual_with_proxy(module.normalize_manual_origins(manual), proxy)

        self.assertEqual(len(result), 2)
        self.assertIn("sector-1", set(result["origin_id"]))
        self.assertNotIn("5208707_municipal_proxy", set(result["origin_id"]))
        self.assertIn("4106902_municipal_proxy", set(result["origin_id"]))


if __name__ == "__main__":
    unittest.main()
