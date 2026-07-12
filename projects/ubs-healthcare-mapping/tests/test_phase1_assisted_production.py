import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "aggregate_sia_assisted_production.py"


def load_module():
    spec = importlib.util.spec_from_file_location("aggregate_sia_assisted_production", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AssistedProductionTests(unittest.TestCase):
    def test_aggregates_recent_production_without_calling_it_consultations(self):
        module = load_module()
        status = pd.DataFrame([
            {
                "cnes": "1", "ibge_municipio": "100001", "cnes_present_latest_st": True,
                "sia_recent_production": True, "sia_records": 10, "sia_quantity": 100,
                "sia_value": 50, "sia_competence_count": 3,
            },
            {
                "cnes": "2", "ibge_municipio": "100001", "cnes_present_latest_st": True,
                "sia_recent_production": False, "sia_records": 0, "sia_quantity": 0,
                "sia_value": 0, "sia_competence_count": 0,
            },
        ])
        population = pd.DataFrame([{"ibge_municipio": "100001", "populacao_residente": 10_000}])

        result = module.aggregate_production(status, population)
        row = result.iloc[0]

        self.assertEqual(row["ubs_with_recent_sia_production"], 1)
        self.assertEqual(row["active_ubs_with_recent_sia_production"], 1)
        self.assertEqual(row["sia_reporting_coverage_pct"], 50)
        self.assertEqual(row["sia_quantity_all_procedures"], 100)
        self.assertEqual(row["sia_quantity_all_procedures_per_1000"], 10)

    def test_zero_active_ubs_does_not_create_infinite_coverage(self):
        module = load_module()
        status = pd.DataFrame([{
            "cnes": "1", "ibge_municipio": "100002", "cnes_present_latest_st": False,
            "sia_recent_production": False, "sia_records": 0, "sia_quantity": 0,
            "sia_value": 0, "sia_competence_count": 0,
        }])
        population = pd.DataFrame([{"ibge_municipio": "100002", "populacao_residente": 5_000}])

        result = module.aggregate_production(status, population)

        self.assertTrue(pd.isna(result.iloc[0]["sia_reporting_coverage_pct"]))
        self.assertEqual(result.iloc[0]["production_interpretation"], "no_active_ubs_denominator")

    def test_reporting_coverage_uses_active_and_sia_intersection(self):
        module = load_module()
        status = pd.DataFrame([
            {
                "cnes": "1", "ibge_municipio": "100003", "cnes_present_latest_st": True,
                "sia_recent_production": True, "sia_records": 1, "sia_quantity": 1,
                "sia_value": 0, "sia_competence_count": 1,
            },
            {
                "cnes": "2", "ibge_municipio": "100003", "cnes_present_latest_st": False,
                "sia_recent_production": True, "sia_records": 1, "sia_quantity": 1,
                "sia_value": 0, "sia_competence_count": 1,
            },
        ])
        population = pd.DataFrame([{"ibge_municipio": "100003", "populacao_residente": 1_000}])

        result = module.aggregate_production(status, population)

        self.assertEqual(result.iloc[0]["ubs_with_recent_sia_production"], 2)
        self.assertEqual(result.iloc[0]["active_ubs_with_recent_sia_production"], 1)
        self.assertEqual(result.iloc[0]["sia_reporting_coverage_pct"], 100)


if __name__ == "__main__":
    unittest.main()
