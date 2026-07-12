import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_pharmacy_layer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_pharmacy_layer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PharmacyMappingTests(unittest.TestCase):
    def test_normalizes_official_portuguese_columns_and_coordinates(self):
        module = load_module()
        raw = pd.DataFrame(
            [{
                "CNPJ": "12.345.678/0001-90",
                "Razão Social": "Farmácia Exemplo",
                "Município": "São Paulo",
                "UF": "SP",
                "Código IBGE": "3550308",
                "Latitude": "-23,5505",
                "Longitude": "-46,6333",
            }]
        )

        result = module.normalize_pharmacies(raw, source="Farmácia Popular")

        self.assertEqual(result.loc[0, "facility_type"], "farmacia_popular")
        self.assertEqual(result.loc[0, "cnpj"], "12345678000190")
        self.assertAlmostEqual(result.loc[0, "latitude"], -23.5505)
        self.assertTrue(bool(result.loc[0, "valid_coordinates"]))

    def test_rejects_coordinates_outside_brazil(self):
        module = load_module()
        raw = pd.DataFrame([{"nome": "Fora", "uf": "SP", "latitude": 40, "longitude": 10}])

        result = module.normalize_pharmacies(raw)

        self.assertFalse(bool(result.loc[0, "valid_coordinates"]))

    def test_builds_uf_summary_and_geojson_with_only_valid_points(self):
        module = load_module()
        normalized = module.normalize_pharmacies(pd.DataFrame([
            {"nome": "A", "uf": "SP", "municipio": "São Paulo", "latitude": -23.5, "longitude": -46.6},
            {"nome": "B", "uf": "SP", "municipio": "Campinas", "latitude": "", "longitude": ""},
        ]))

        summary = module.summarize_by_uf(normalized)
        geojson = module.to_geojson(normalized)

        self.assertEqual(int(summary.loc[0, "pharmacies"]), 2)
        self.assertEqual(int(summary.loc[0, "valid_coordinates"]), 1)
        self.assertEqual(len(geojson["features"]), 1)
        self.assertEqual(geojson["features"][0]["geometry"]["coordinates"], [-46.6, -23.5])

    def test_writes_versioned_dashboard_artifacts(self):
        module = load_module()
        raw = pd.DataFrame([{"nome": "A", "uf": "RJ", "latitude": -22.9, "longitude": -43.2}])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            module.build_layer(raw, output, source="fixture")

            self.assertTrue((output / "pharmacies.csv").exists())
            self.assertTrue((output / "pharmacies_by_uf.csv").exists())
            self.assertEqual(json.loads((output / "pharmacies.geojson").read_text(encoding="utf-8"))["type"], "FeatureCollection")

    def test_reads_official_workbook_with_institutional_header(self):
        module = load_module()
        rows = [[None] * 8 for _ in range(12)]
        rows.append(["UF", "CÓD. \nMUNICÍPIO", "MUNICÍPIO", "CNPJ", "FARMÁCIA", "ENDEREÇO", "BAIRRO", "Data do Credenciamento"])
        rows.append(["SP", "355030", "SAO PAULO", "12345678000190", "FARMACIA TESTE", "RUA A, 1", "CENTRO", "2026-01-01"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "official.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            raw = module.read_table(path)
            result = module.normalize_pharmacies(raw)

        self.assertEqual(result.loc[0, "ibge_municipality"], "355030")
        self.assertEqual(result.loc[0, "name"], "FARMACIA TESTE")
        self.assertEqual(result.loc[0, "neighborhood"], "CENTRO")


if __name__ == "__main__":
    unittest.main()
