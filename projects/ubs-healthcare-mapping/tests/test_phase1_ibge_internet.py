import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "fetch_ibge_internet_readiness.py"


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_ibge_internet_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def result(variable, category, value, location="1000001"):
    return {
        "id": str(variable),
        "resultados": [{
            "classificacoes": [{"id": "2072", "categoria": {str(category): "category"}}],
            "series": [{
                "localidade": {"id": location, "nome": "Municipio (AA)"},
                "serie": {"2022": str(value)},
            }],
        }],
    }


class IbgeInternetReadinessTests(unittest.TestCase):
    def test_parses_counts_and_percentages_by_internet_category(self):
        module = load_module()
        payload = [
            result(381, 77584, 1000),
            result(381, 77585, 800),
            result(381, 77586, 200),
            result(1000381, 77585, 80),
            result(1000381, 77586, 20),
        ]

        parsed = module.parse_sidra_results(payload)
        row = parsed.iloc[0]

        self.assertEqual(row["households_total"], 1000)
        self.assertEqual(row["households_with_internet"], 800)
        self.assertEqual(row["households_without_internet"], 200)
        self.assertEqual(row["households_with_internet_pct"], 80)

    def test_reconciles_new_municipality_as_missing_not_zero(self):
        module = load_module()
        observed = pd.DataFrame([{
            "ibge_municipio_7": "1000001", "households_total": 100,
            "households_with_internet": 80, "households_without_internet": 20,
            "households_with_internet_pct": 80, "households_without_internet_pct": 20,
        }])
        universe = pd.DataFrame([
            {"ibge_municipio": "100000", "ibge_municipio_7": "1000001", "municipio_nome_oficial": "Antigo"},
            {"ibge_municipio": "100001", "ibge_municipio_7": "1000019", "municipio_nome_oficial": "Novo"},
        ])

        result_frame = module.reconcile_universe(observed, universe)
        missing = result_frame.loc[result_frame["ibge_municipio_7"].eq("1000019")].iloc[0]

        self.assertEqual(missing["internet_data_status"], "missing_2022_boundary")
        self.assertTrue(pd.isna(missing["households_with_internet_pct"]))


if __name__ == "__main__":
    unittest.main()
