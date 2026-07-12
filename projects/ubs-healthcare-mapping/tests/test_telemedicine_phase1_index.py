import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "build_telemedicine_phase1_index.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_telemedicine_phase1_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "ibge_municipio": "100001", "municipio_nome_ibge": "A", "uf_sigla": "AA",
            "populacao_residente": 1_000_000, "aps_coverage_capped_pct": 50,
            "potentially_uncovered_population": 500_000, "active_ubs_per_100k": 1,
            "pharmacies": 100, "pharmacies_per_100k": 10,
            "physician_fte_per_100k": 5, "households_with_internet_pct": 90,
            "mobile_4g5g_resident_coverage_pct": 95,
            "fixed_broadband_accesses_per_100_people": 30,
            "sia_quantity_all_procedures": 10,
        },
        {
            "ibge_municipio": "100002", "municipio_nome_ibge": "B", "uf_sigla": "AA",
            "populacao_residente": 1_000_000, "aps_coverage_capped_pct": 50,
            "potentially_uncovered_population": 500_000, "active_ubs_per_100k": 1,
            "pharmacies": 100, "pharmacies_per_100k": 10,
            "physician_fte_per_100k": 30, "households_with_internet_pct": 40,
            "mobile_4g5g_resident_coverage_pct": 50,
            "fixed_broadband_accesses_per_100_people": 5,
            "sia_quantity_all_procedures": 1_000_000,
        },
    ])


class TelemedicinePhase1IndexTests(unittest.TestCase):
    def test_lower_physician_fte_increases_need_when_other_need_inputs_are_equal(self):
        module = load_module()
        result = module.build_phase1_index(sample())
        low_fte = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        high_fte = result.loc[result["ibge_municipio"].eq("100002")].iloc[0]
        self.assertGreater(low_fte["phase1_need_score"], high_fte["phase1_need_score"])

    def test_digital_readiness_changes_feasibility_but_not_need(self):
        module = load_module()
        result = module.build_phase1_index(sample())
        high_digital = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        low_digital = result.loc[result["ibge_municipio"].eq("100002")].iloc[0]
        self.assertGreater(high_digital["digital_readiness_score"], low_digital["digital_readiness_score"])
        self.assertGreater(high_digital["phase1_deployment_feasibility_score"], low_digital["phase1_deployment_feasibility_score"])

    def test_sia_total_procedure_quantity_does_not_enter_score(self):
        module = load_module()
        original = sample()
        first = module.build_phase1_index(original)
        changed = original.copy()
        changed["sia_quantity_all_procedures"] = changed["sia_quantity_all_procedures"].iloc[::-1].to_numpy()
        second = module.build_phase1_index(changed)
        pd.testing.assert_series_equal(
            first.sort_values("ibge_municipio")["telemedicine_phase1_balanced"].reset_index(drop=True),
            second.sort_values("ibge_municipio")["telemedicine_phase1_balanced"].reset_index(drop=True),
        )

    def test_missing_core_input_is_not_scored_or_zero_imputed(self):
        module = load_module()
        data = sample()
        data.loc[0, "physician_fte_per_100k"] = pd.NA
        result = module.build_phase1_index(data)
        missing = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        self.assertEqual(missing["phase1_eligibility"], "insufficient_phase1_data")
        self.assertTrue(pd.isna(missing["telemedicine_phase1_balanced"]))


if __name__ == "__main__":
    unittest.main()
