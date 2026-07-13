import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
OD_SCRIPT = PROJECT_DIR / "scripts" / "build_phase3_routing_od_matrix.py"
OSRM_SCRIPT = PROJECT_DIR / "scripts" / "fetch_phase3_osrm_travel_times.py"
SUMMARY_SCRIPT = PROJECT_DIR / "scripts" / "build_phase3_routing_summary.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Phase3RoutingPreparationTests(unittest.TestCase):
    def test_build_od_matrix_creates_ubs_and_pharmacy_pairs(self):
        module = load_module(OD_SCRIPT, "build_phase3_routing_od_matrix")
        shortlist = pd.DataFrame([{
            "ibge_municipio_7": "3301850",
            "municipio_nome_oficial": "Guapimirim",
            "uf_sigla_oficial": "RJ",
            "origin_latitude": -22.5301,
            "origin_longitude": -42.9857,
            "origin_method": "official_ibge_2022_municipal_seat",
            "phase2_spatial_target_rank": 1,
            "nearest_ubs_id": "2278448",
            "nearest_ubs_geodesic_km": 6.35,
            "nearest_pharmacy_id": "node/3719376432",
            "nearest_pharmacy_geodesic_km": 0.06,
        }])
        ubs = pd.DataFrame([{
            "destination_id": "2278448",
            "destination_name": "UBS TESTE",
            "destination_latitude": -22.50,
            "destination_longitude": -42.90,
        }])
        pharmacies = pd.DataFrame([{
            "destination_id": "node/3719376432",
            "destination_name": "FARMACIA TESTE",
            "destination_latitude": -22.531,
            "destination_longitude": -42.986,
        }])

        result = module.build_od_matrix(shortlist, ubs, pharmacies)

        self.assertEqual(len(result), 2)
        self.assertEqual(set(result["destination_type"]), {"active_ubs", "osm_pharmacy"})
        self.assertTrue(result["routing_readiness_status"].eq("ready_for_network_routing").all())
        self.assertTrue(result["travel_time_minutes"].isna().all())

    def test_osrm_enrichment_records_minutes_distance_and_source(self):
        module = load_module(OSRM_SCRIPT, "fetch_phase3_osrm_travel_times")
        frame = pd.DataFrame([{
            "origin_latitude": -22.53,
            "origin_longitude": -42.98,
            "destination_latitude": -22.50,
            "destination_longitude": -42.90,
            "routing_profile": "driving",
            "routing_readiness_status": "ready_for_network_routing",
            "travel_time_minutes": pd.NA,
            "network_distance_km": pd.NA,
            "routing_source": pd.NA,
            "routing_measured_at_utc": pd.NA,
            "academic_interpretation": "phase3_od_pair_pending_travel_time",
        }])
        response = Mock()
        response.json.return_value = {"code": "Ok", "routes": [{"duration": 900, "distance": 12000}]}
        response.raise_for_status.return_value = None

        with patch.object(module.requests, "get", return_value=response) as mocked_get:
            result = module.route_matrix(frame, "http://localhost:5000", timeout=5)

        self.assertAlmostEqual(result.loc[0, "travel_time_minutes"], 15.0)
        self.assertAlmostEqual(result.loc[0, "network_distance_km"], 12.0)
        self.assertEqual(result.loc[0, "routing_readiness_status"], "routed")
        self.assertEqual(result.loc[0, "routing_source"], "http://localhost:5000")
        mocked_get.assert_called_once()

    def test_routing_summary_flags_hard_ubs_easy_pharmacy(self):
        module = load_module(SUMMARY_SCRIPT, "build_phase3_routing_summary")
        routed = pd.DataFrame([
            {
                "ibge_municipio_7": "1",
                "municipio_nome_oficial": "Cidade A",
                "uf_sigla_oficial": "AA",
                "phase2_spatial_target_rank": 1,
                "origin_method": "official_ibge_2022_municipal_seat",
                "destination_type": "active_ubs",
                "phase2_geodesic_km": 6,
                "network_distance_km": 20,
                "travel_time_minutes": 22,
            },
            {
                "ibge_municipio_7": "1",
                "municipio_nome_oficial": "Cidade A",
                "uf_sigla_oficial": "AA",
                "phase2_spatial_target_rank": 1,
                "origin_method": "official_ibge_2022_municipal_seat",
                "destination_type": "osm_pharmacy",
                "phase2_geodesic_km": 0.2,
                "network_distance_km": 0.5,
                "travel_time_minutes": 2,
            },
            {
                "ibge_municipio_7": "2",
                "municipio_nome_oficial": "Cidade B",
                "uf_sigla_oficial": "BB",
                "phase2_spatial_target_rank": 2,
                "origin_method": "official_ibge_2022_municipal_seat",
                "destination_type": "active_ubs",
                "phase2_geodesic_km": 8,
                "network_distance_km": 28,
                "travel_time_minutes": 25,
            },
            {
                "ibge_municipio_7": "2",
                "municipio_nome_oficial": "Cidade B",
                "uf_sigla_oficial": "BB",
                "phase2_spatial_target_rank": 2,
                "origin_method": "official_ibge_2022_municipal_seat",
                "destination_type": "osm_pharmacy",
                "phase2_geodesic_km": 1,
                "network_distance_km": 12,
                "travel_time_minutes": 18,
            },
        ])

        result = module.build_summary(routed)

        flagged = result.loc[result["ibge_municipio_7"].eq("1")].iloc[0]
        not_flagged = result.loc[result["ibge_municipio_7"].eq("2")].iloc[0]
        self.assertTrue(flagged["phase3_routed_hard_ubs_easy_pharmacy_flag"])
        self.assertEqual(flagged["phase3_access_interpretation"], "routed_hard_ubs_easy_pharmacy_candidate")
        self.assertFalse(not_flagged["phase3_routed_hard_ubs_easy_pharmacy_flag"])
        self.assertEqual(not_flagged["phase3_access_interpretation"], "routed_hard_ubs_but_not_easy_pharmacy")


if __name__ == "__main__":
    unittest.main()
