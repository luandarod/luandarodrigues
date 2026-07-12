import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "fetch_cnes_workforce_teams.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("fetch_cnes_workforce_teams", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CnesWorkforceTests(unittest.TestCase):
    def test_deduplicates_physician_links_and_uses_max_hours_per_link(self):
        module = load_module()
        rows = [
            {"CNES": "0000001", "CBO": "225125", "CNS_PROF": "A", "CPF_PROF": "", "HORA_AMB": "20"},
            {"CNES": "0000001", "CBO": "225125", "CNS_PROF": "A", "CPF_PROF": "", "HORA_AMB": "30"},
            {"CNES": "0000002", "CBO": "225130", "CNS_PROF": "A", "CPF_PROF": "", "HORA_AMB": "10"},
            {"CNES": "0000001", "CBO": "223505", "CNS_PROF": "B", "CPF_PROF": "", "HORA_AMB": "40"},
        ]
        target = {"0000001": "100001", "0000002": "100001"}

        result = module.aggregate_professional_rows(rows, target, {"0000001", "0000002"})
        row = result.iloc[0]

        self.assertEqual(row["physicians_unique"], 1)
        self.assertEqual(row["physician_cnes_links"], 2)
        self.assertEqual(row["physician_ambulatory_hours_weekly"], 40)
        self.assertEqual(row["physician_fte_40h"], 1)
        self.assertEqual(row["active_ubs_with_physician"], 2)

    def test_excludes_non_physician_cbo_and_never_outputs_identifiers(self):
        module = load_module()
        rows = [{
            "CNES": "0000001", "CBO": "223505", "CNS_PROF": "SECRET", "CPF_PROF": "SECRET",
            "NOMEPROF": "NAME", "HORA_AMB": "40",
        }]
        result = module.aggregate_professional_rows(rows, {"0000001": "100001"}, {"0000001"})

        self.assertTrue(result.empty)
        self.assertFalse({"CNS_PROF", "CPF_PROF", "NOMEPROF"} & set(result.columns))

    def test_counts_only_teams_without_deactivation_date(self):
        module = load_module()
        rows = [
            {"CNES": "0000001", "IDEQUIPE": "TEAM1", "TIPO_EQP": "70", "DT_DESAT": "900001"},
            {"CNES": "0000001", "IDEQUIPE": "TEAM2", "TIPO_EQP": "70", "DT_DESAT": "202401"},
            {"CNES": "0000002", "IDEQUIPE": "TEAM3", "TIPO_EQP": "01", "DT_DESAT": ""},
        ]
        target = {"0000001": "100001", "0000002": "100001"}

        result = module.aggregate_team_rows(rows, target, {"0000001", "0000002"})
        row = result.iloc[0]

        self.assertEqual(row["active_cnes_teams_all_types"], 2)
        self.assertEqual(row["active_ubs_with_cnes_team"], 2)
        self.assertEqual(row["active_cnes_team_types"], 2)


if __name__ == "__main__":
    unittest.main()
