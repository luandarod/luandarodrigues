import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "fetch_anatel_connectivity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_anatel_connectivity", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AnatelConnectivityTests(unittest.TestCase):
    def test_mobile_uses_aggregate_operator_and_keeps_4g5g_and_5g_separate(self):
        module = load_module()
        raw = pd.DataFrame([
            [5208707, "Goiania", "GO", "4G5G", "Todas", "03-2026", 0.90, 0.95, 0.94],
            [5208707, "Goiania", "GO", "5G", "Todas", "03-2026", 0.50, 0.70, 0.68],
            [5208707, "Goiania", "GO", "4G5G", "CLARO", "03-2026", 0.80, 0.85, 0.84],
        ], columns=[
            "Código Município", "Município", "UF", "Tecnologia", "Operadora", "Período",
            "% área coberta", "% moradores cobertos", "% domicilios cobertos",
        ])

        result = module.aggregate_mobile_coverage(raw)
        row = result.iloc[0]

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(row["mobile_4g5g_resident_coverage_pct"], 95.0)
        self.assertAlmostEqual(row["mobile_5g_resident_coverage_pct"], 70.0)
        self.assertEqual(row["mobile_reference_period"], "2026-03")

    def test_fixed_broadband_selects_latest_period_and_municipal_level(self):
        module = load_module()
        raw = pd.DataFrame([
            [2026, 4, "GO", "Goiania", 5208707, 27.0, "Municipio"],
            [2026, 5, "GO", "Goiania", 5208707, 28.4, "Municipio"],
            [2026, 5, "Brasil", "Brasil", 0, 26.0, "Brasil"],
        ], columns=["Ano", "Mes", "UF", "Municipio", "Codigo IBGE", "Densidade", "Nivel"])

        result = module.aggregate_fixed_broadband(raw)

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.iloc[0]["fixed_broadband_accesses_per_100_people"], 28.4)
        self.assertEqual(result.iloc[0]["fixed_broadband_reference_period"], "2026-05")

    def test_missing_municipality_is_not_imputed_as_zero(self):
        module = load_module()
        universe = pd.DataFrame([
            {"ibge_municipio_7": "5208707", "municipio_nome_oficial": "Goiania"},
            {"ibge_municipio_7": "5210000", "municipio_nome_oficial": "Sem dado"},
        ])
        mobile = pd.DataFrame([{
            "ibge_municipio_7": "5208707", "mobile_4g5g_resident_coverage_pct": 99.0,
            "mobile_5g_resident_coverage_pct": 90.0, "mobile_reference_period": "2026-03",
        }])
        fixed = pd.DataFrame([{
            "ibge_municipio_7": "5208707", "fixed_broadband_accesses_per_100_people": 28.0,
            "fixed_broadband_reference_period": "2026-05",
        }])

        result = module.reconcile_universe(mobile, fixed, universe)
        missing = result.loc[result["ibge_municipio_7"].eq("5210000")].iloc[0]

        self.assertTrue(pd.isna(missing["mobile_4g5g_resident_coverage_pct"]))
        self.assertTrue(pd.isna(missing["fixed_broadband_accesses_per_100_people"]))
        self.assertEqual(missing["anatel_data_status"], "missing")


if __name__ == "__main__":
    unittest.main()
