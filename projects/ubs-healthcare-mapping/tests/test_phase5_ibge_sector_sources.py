import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd
import shapefile


PROJECT_DIR = Path(__file__).resolve().parents[1]
FETCH_SCRIPT = PROJECT_DIR / "scripts" / "fetch_ibge_2022_sector_sources.py"
PREP_SCRIPT = PROJECT_DIR / "scripts" / "prepare_ibge_2022_sector_origins.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Phase5IBGESectorSourceTests(unittest.TestCase):
    def test_manifest_has_basic_aggregate_dictionary_and_all_uf_geometry(self):
        module = load_module("fetch_ibge_2022_sector_sources", FETCH_SCRIPT)
        manifest = module.build_manifest(check_remote=False)

        self.assertEqual((manifest["source_role"] == "sector_geometry_shapefile_uf").sum(), 27)
        self.assertIn("sector_basic_aggregate_population", set(manifest["source_role"]))
        self.assertIn("GO_setores_CD2022.zip", set(manifest["expected_filename"]))
        self.assertTrue(manifest["url"].str.contains("Censo_Demografico_2022").any())

    def test_prepare_sector_origins_from_synthetic_shapefile_and_aggregate(self):
        module = load_module("prepare_ibge_2022_sector_origins", PREP_SCRIPT)
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            shp_base = temp_dir / "GO_setores_CD2022"
            writer = shapefile.Writer(str(shp_base), shapeType=shapefile.POLYGON)
            writer.field("CD_SETOR", "C")
            writer.field("CD_MUN", "C")
            writer.field("NM_MUN", "C")
            writer.field("SIGLA_UF", "C")
            writer.field("SITUACAO", "C")
            writer.poly([[[-49.30, -16.72], [-49.20, -16.72], [-49.20, -16.62], [-49.30, -16.62], [-49.30, -16.72]]])
            writer.record("520870705000001", "5208707", "Goiânia", "GO", "Urbana")
            writer.close()
            zip_path = temp_dir / "GO_setores_CD2022.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                for suffix in (".shp", ".shx", ".dbf"):
                    archive.write(shp_base.with_suffix(suffix), arcname=shp_base.with_suffix(suffix).name)

            aggregate = temp_dir / "Agregados_por_setores_basico_BR.csv"
            pd.DataFrame([{"CD_SETOR": "520870705000001", "v0001": "123"}]).to_csv(
                aggregate, sep=";", index=False, encoding="latin1",
            )

            origins = module.build_sector_origins(zip_path, aggregate)

        self.assertEqual(len(origins), 1)
        self.assertEqual(origins.iloc[0]["origin_id"], "520870705000001")
        self.assertEqual(origins.iloc[0]["ibge_municipio_7"], "5208707")
        self.assertEqual(origins.iloc[0]["origin_population"], 123)
        self.assertEqual(origins.iloc[0]["origin_granularity"], "census_sector")
        self.assertEqual(origins.iloc[0]["precision_status"], "intramunicipal_population_origins_loaded")
        self.assertEqual(origins.iloc[0]["origin_source"], "IBGE_CD2022_SETOR_V0001")
        self.assertAlmostEqual(origins.iloc[0]["origin_latitude"], -16.67, places=2)
        self.assertAlmostEqual(origins.iloc[0]["origin_longitude"], -49.25, places=2)


if __name__ == "__main__":
    unittest.main()
