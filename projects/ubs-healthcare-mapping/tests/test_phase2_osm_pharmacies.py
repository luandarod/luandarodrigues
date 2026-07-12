import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "fetch_osm_pharmacies.py"


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_osm_pharmacies", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OsmPharmacyTests(unittest.TestCase):
    def test_parses_node_and_way_center_and_rejects_missing_geometry(self):
        module = load_module()
        payload = {
            "osm3s": {"timestamp_osm_base": "2026-07-12T00:00:00Z"},
            "elements": [
                {"type": "node", "id": 1, "lat": -16.68, "lon": -49.25, "tags": {"name": "A"}},
                {"type": "way", "id": 2, "center": {"lat": -16.69, "lon": -49.26}, "tags": {"name": "B"}},
                {"type": "relation", "id": 3, "tags": {"name": "Sem centro"}},
            ],
        }

        result, timestamp = module.parse_overpass(payload)

        self.assertEqual(result["osm_feature_id"].tolist(), ["node/1", "way/2"])
        self.assertEqual(timestamp, "2026-07-12T00:00:00Z")
        self.assertTrue(result["valid_coordinates"].all())

    def test_deduplicates_same_osm_feature(self):
        module = load_module()
        element = {"type": "node", "id": 1, "lat": -16.68, "lon": -49.25, "tags": {}}
        result, _ = module.parse_overpass({"elements": [element, element]})
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
