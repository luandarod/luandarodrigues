import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit_outputs = load_module("audit_telemedicine_outputs", SCRIPTS_DIR / "audit_telemedicine_outputs.py")


class TelemedicineOutputAuditTests(unittest.TestCase):
    def test_outputs_keep_national_and_pharmacy_pilot_views_separated(self):
        summary = audit_outputs.summarize_outputs()

        self.assertEqual(summary["phase2_top100_municipalities"], 100)
        self.assertGreater(summary["phase2_scored_municipalities"], summary["phase4_primary_routed_targets"])
        self.assertTrue(summary["geojson_has_required_fields"])
        self.assertTrue(summary["dashboard_has_separated_filters"])
        self.assertTrue(summary["views_are_separated"])
        self.assertEqual(summary["decision_matrix_rows"], summary["phase4_rows"])
        self.assertEqual(summary["decision_class_counts"]["pharmacy_assisted_pilot"], 4)
        self.assertGreater(summary["decision_class_counts"]["national_priority_high_readiness"], 0)
        self.assertEqual(summary["goiania"]["phase2_rank_balanced"], 1)
        self.assertIsNone(summary["goiania"]["phase4_routed_target_rank"])


if __name__ == "__main__":
    unittest.main()
