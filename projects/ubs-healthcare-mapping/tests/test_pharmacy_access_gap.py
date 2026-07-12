import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "scripts" / "analyze_pharmacy_access_gap.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_pharmacy_access_gap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PharmacyAccessGapTests(unittest.TestCase):
    def setUp(self):
        self.territory = pd.DataFrame([
            {"ibge_municipio": 100001, "uf_sigla": "AA", "municipio_nome_ibge": "Pouca UBS", "populacao_residente": 100000, "ubs_records": 1, "area_km2": 1000},
            {"ibge_municipio": 100002, "uf_sigla": "AA", "municipio_nome_ibge": "Equilibrado", "populacao_residente": 100000, "ubs_records": 10, "area_km2": 100},
            {"ibge_municipio": 100003, "uf_sigla": "BB", "municipio_nome_ibge": "Sem farmácia", "populacao_residente": 50000, "ubs_records": 5, "area_km2": 50},
        ])
        self.pharmacies = pd.DataFrame([
            {"facility_id": "1", "ibge_municipality": "100001", "facility_type": "farmacia_popular"},
            {"facility_id": "2", "ibge_municipality": "100001", "facility_type": "farmacia_popular"},
            {"facility_id": "3", "ibge_municipality": "100001", "facility_type": "farmacia_privada"},
            {"facility_id": "4", "ibge_municipality": "100002", "facility_type": "farmacia_popular"},
        ])

    def _aps(self):
        return pd.DataFrame([
            {"ibge_municipio": 100001, "cobertura_aps_pct": 50, "aps_populacao": 100000},
            {"ibge_municipio": 100002, "cobertura_aps_pct": 95, "aps_populacao": 100000},
            {"ibge_municipio": 100003, "cobertura_aps_pct": 90, "aps_populacao": 50000},
        ])

    def _operational(self):
        return pd.DataFrame([
            {"ibge_municipio": 100001, "cnes": "1", "cnes_present_latest_st": True},
            *[{"ibge_municipio": 100002, "cnes": str(i), "cnes_present_latest_st": True} for i in range(10)],
            *[{"ibge_municipio": 100003, "cnes": str(i), "cnes_present_latest_st": True} for i in range(5)],
        ])

    def test_calculates_supply_rates_and_keeps_zero_pharmacy_municipalities(self):
        module = load_module()
        result = module.analyze_gap(self.territory, self.pharmacies, self._aps(), self._operational())

        sparse = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        empty = result.loc[result["ibge_municipio"].eq("100003")].iloc[0]
        self.assertAlmostEqual(sparse["ubs_per_100k"], 1)
        self.assertAlmostEqual(sparse["pharmacies_per_100k"], 3)
        self.assertEqual(int(empty["pharmacies"]), 0)

    def test_flags_low_ubs_high_pharmacy_access_mismatch(self):
        module = load_module()
        result = module.analyze_gap(self.territory, self.pharmacies, self._aps(), self._operational())

        sparse = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        balanced = result.loc[result["ibge_municipio"].eq("100002")].iloc[0]
        self.assertEqual(sparse["access_mismatch_flag"], "consistent_mismatch")
        self.assertNotEqual(balanced["access_mismatch_flag"], "consistent_mismatch")
        self.assertGreater(sparse["access_mismatch_score"], balanced["access_mismatch_score"])
        self.assertEqual(sparse["evidence_level"], "complete")

    def test_separates_popular_and_other_pharmacies(self):
        module = load_module()
        result = module.analyze_gap(self.territory, self.pharmacies, self._aps(), self._operational())
        sparse = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]

        self.assertEqual(int(sparse["popular_pharmacies"]), 2)
        self.assertEqual(int(sparse["other_pharmacies"]), 1)

    def test_deduplicates_pharmacies_by_cnpj(self):
        module = load_module()
        duplicated = pd.concat([self.pharmacies, self.pharmacies.iloc[[0]]], ignore_index=True)
        duplicated["cnpj"] = ["1", "2", "3", "4", "1"]
        result = module.analyze_gap(self.territory, duplicated, self._aps(), self._operational())
        sparse = result.loc[result["ibge_municipio"].eq("100001")].iloc[0]
        self.assertEqual(int(sparse["pharmacies"]), 3)

    def test_real_goiania_source_counts_are_stable(self):
        pharmacies = pd.read_csv(PROJECT_DIR / "data" / "pharmacies.csv", dtype=str)
        goiania = pharmacies.loc[pharmacies["ibge_municipality"].str[:6].eq("520870")]
        self.assertEqual(len(goiania), 345)
        self.assertEqual(goiania["cnpj"].nunique(), 345)

    def test_extends_territory_with_aps_municipalities_without_ubs(self):
        module = load_module()
        aps = pd.DataFrame([{"ibge_municipio": 100004, "uf_sigla": "CC", "municipio_nome_aps": "Sem UBS", "aps_populacao": 12000}])

        result = module.extend_with_aps_universe(self.territory, aps)

        added = result.loc[result["ibge_municipio"].astype(str).eq("100004")].iloc[0]
        self.assertEqual(int(added["ubs_records"]), 0)
        self.assertEqual(int(added["populacao_residente"]), 12000)


if __name__ == "__main__":
    unittest.main()
