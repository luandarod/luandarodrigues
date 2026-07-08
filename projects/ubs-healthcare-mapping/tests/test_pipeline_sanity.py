import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"
DATA_DIR = PROJECT_DIR / "data"
ENRICHED_DIR = DATA_DIR / "enriched"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


analyze_ubs = load_module("analyze_ubs", SCRIPTS_DIR / "analyze_ubs.py")
enrich_with_ibge = load_module("enrich_with_ibge", SCRIPTS_DIR / "enrich_with_ibge.py")
enrich_with_aps = load_module("enrich_with_aps", SCRIPTS_DIR / "enrich_with_aps_coverage.py")


class PipelineSanityTests(unittest.TestCase):
    def test_decimal_parsing_accepts_comma_and_dot(self):
        values = pd.Series(["-23,5505", "-23.5505", " -46,6333 ", ""])
        parsed = analyze_ubs.normalize_decimal_series(values)

        self.assertAlmostEqual(parsed.iloc[0], -23.5505)
        self.assertAlmostEqual(parsed.iloc[1], -23.5505)
        self.assertAlmostEqual(parsed.iloc[2], -46.6333)
        self.assertTrue(pd.isna(parsed.iloc[3]))

    def test_sidra_number_parser_preserves_decimal_points(self):
        self.assertAlmostEqual(enrich_with_ibge._clean_numeric("164173.431"), 164173.431)
        self.assertAlmostEqual(enrich_with_ibge._clean_numeric("164.173,431"), 164173.431)

    def test_aps_number_parser_preserves_decimal_points(self):
        self.assertAlmostEqual(enrich_with_aps.parse_number("142.74"), 142.74)
        self.assertAlmostEqual(enrich_with_aps.parse_number("142,74"), 142.74)

    def test_generated_territory_outputs_are_sane(self):
        uf = pd.read_csv(ENRICHED_DIR / "uf_ubs_territory_summary.csv")

        self.assertEqual(len(uf), 27)
        self.assertEqual(int(uf["uf_sigla"].isna().sum()), 0)
        self.assertGreaterEqual(int(uf["ubs_records"].sum()), 47710)
        self.assertLess(uf.loc[uf["uf_sigla"].eq("AC"), "area_km2"].iloc[0], 200000)
        self.assertFalse(uf[["ubs_per_10k_population", "ubs_per_1000_km2"]].isna().any().any())

    def test_aps_outputs_keep_weighted_and_capped_coverage(self):
        aps = pd.read_csv(ENRICHED_DIR / "uf_ubs_aps_coverage_summary.csv")

        expected_columns = {
            "cobertura_aps_ponderada_pct",
            "cobertura_aps_ponderada_capped_pct",
            "coverage_gap_media_pct",
            "nominal_capacity_excess_media_pct",
        }
        self.assertTrue(expected_columns.issubset(aps.columns))
        self.assertEqual(len(aps), 27)
        self.assertLessEqual(aps["cobertura_aps_ponderada_capped_pct"].max(), 100)

    def test_official_aps_api_columns_normalize(self):
        raw = pd.DataFrame(
            [
                {
                    "nuComp": "04/2026",
                    "noRegiao": "NORTE",
                    "sgUf": "AC",
                    "noUf": "ACRE",
                    "coMunicipioIbge": "120001",
                    "noMunicipioAcentuado": "ACRELANDIA",
                    "qtPopulacao": 14712,
                    "qtEsf": 6,
                    "qtCapacidadeEquipe": 21000,
                    "qtCobertura": 142.74,
                }
            ]
        )
        normalized = enrich_with_aps.normalize_aps_columns(raw)

        self.assertEqual(normalized.loc[0, "competencia_cnes"], "04/2026")
        self.assertEqual(int(normalized.loc[0, "ibge_municipio"]), 120001)
        self.assertEqual(normalized.loc[0, "uf_sigla"], "AC")
        self.assertAlmostEqual(normalized.loc[0, "cobertura_aps_pct"], 142.74)

    def test_new_limit_mitigation_outputs_exist(self):
        timeseries = pd.read_csv(DATA_DIR / "aps_national_timeseries.csv")
        coordinate_audit = pd.read_csv(DATA_DIR / "coordinate_quality_by_uf.csv")
        lineage = pd.read_csv(DATA_DIR / "data_lineage_manifest.csv")

        self.assertGreaterEqual(len(timeseries), 60)
        self.assertIn("coverage_weighted_pct", timeseries.columns)
        self.assertEqual(len(coordinate_audit), 27)
        self.assertTrue({"missing_latitude", "out_of_brazil_bbox", "duplicated_valid_coordinates"}.issubset(coordinate_audit.columns))
        self.assertTrue({"path", "rows", "columns", "sha256"}.issubset(lineage.columns))


if __name__ == "__main__":
    unittest.main()
