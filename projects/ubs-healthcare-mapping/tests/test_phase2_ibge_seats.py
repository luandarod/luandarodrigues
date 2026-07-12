import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "fetch_ibge_municipal_seats.py"


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_ibge_municipal_seats", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IbgeMunicipalSeatTests(unittest.TestCase):
    def test_selects_only_municipal_seats_and_deduplicates_code(self):
        module = load_module()
        records = [
            {"CD_MUN": "5208707", "NM_MUN": "Goiania", "SIGLA_UF": "GO", "CT_LOCALID": "Cidade", "SCT_LOCALI": "Sede Municipal", "LAT_LOCALI": -16.68, "LONG_LOCAL": -49.25},
            {"CD_MUN": "5208707", "NM_MUN": "Goiania", "SIGLA_UF": "GO", "CT_LOCALID": "Vila", "SCT_LOCALI": "Sede Distrital", "LAT_LOCALI": -16.5, "LONG_LOCAL": -49.1},
            {"CD_MUN": "5300108", "NM_MUN": "Brasilia", "SIGLA_UF": "DF", "CT_LOCALID": "Cidade", "SCT_LOCALI": "Capital Federal", "LAT_LOCALI": -15.78, "LONG_LOCAL": -47.9},
        ]
        result = module.select_municipal_seats(records)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["ibge_municipio_7"], "5208707")
        self.assertAlmostEqual(result.iloc[0]["seat_latitude"], -16.68)


if __name__ == "__main__":
    unittest.main()
