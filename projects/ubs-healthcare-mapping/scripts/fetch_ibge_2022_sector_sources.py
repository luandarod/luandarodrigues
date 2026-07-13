"""Create a manifest and optionally download IBGE 2022 sector inputs for Phase 5A.

The script intentionally does not download every UF by default. Sector geometry
is large enough that a reproducible per-UF cache is safer for local research and
keeps the repository clean.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests


PROJECT_ROOT = Path("projects/ubs-healthcare-mapping")
RAW_DIR = PROJECT_ROOT / "data/raw/ibge_censo_2022_phase5"
MANIFEST = PROJECT_ROOT / "data/reference/ibge_2022_sector_source_manifest.csv"
METADATA = PROJECT_ROOT / "data/reference/ibge_2022_sector_source_manifest_metadata.json"

UF_CODES = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
    "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

SECTOR_SHP_UF_BASE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/UF"
)
BASIC_AGGREGATE_URL = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"
    "Agregados_por_Setor_csv/Agregados_por_setores_basico_BR_20260520.zip"
)
DICTIONARY_URL = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"
    "dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx"
)


def sector_shp_url(uf: str) -> str:
    uf = uf.upper()
    return f"{SECTOR_SHP_UF_BASE}/{uf}_setores_CD2022.zip"


def build_manifest(check_remote: bool = False) -> pd.DataFrame:
    rows = [
        {
            "source_role": "sector_basic_aggregate_population",
            "uf_sigla": "BR",
            "source_year": 2022,
            "url": BASIC_AGGREGATE_URL,
            "expected_filename": Path(urlparse(BASIC_AGGREGATE_URL).path).name,
            "required_for": "origin_population",
            "commit_raw_file": False,
        },
        {
            "source_role": "sector_aggregate_dictionary",
            "uf_sigla": "BR",
            "source_year": 2022,
            "url": DICTIONARY_URL,
            "expected_filename": Path(urlparse(DICTIONARY_URL).path).name,
            "required_for": "variable_definition_v0001_total_people",
            "commit_raw_file": False,
        },
    ]
    rows.extend({
        "source_role": "sector_geometry_shapefile_uf",
        "uf_sigla": uf,
        "source_year": 2022,
        "url": sector_shp_url(uf),
        "expected_filename": f"{uf}_setores_CD2022.zip",
        "required_for": "origin_representative_point",
        "commit_raw_file": False,
    } for uf in UF_CODES)
    manifest = pd.DataFrame(rows)
    if check_remote:
        manifest["http_status"] = manifest["url"].map(lambda url: _head(url)[0])
        manifest["content_length_bytes"] = manifest["url"].map(lambda url: _head(url)[1])
    else:
        manifest["http_status"] = pd.NA
        manifest["content_length_bytes"] = pd.NA
    return manifest


def _head(url: str) -> tuple[int | None, int | None]:
    try:
        response = requests.head(url, timeout=20, allow_redirects=True)
        length = response.headers.get("content-length")
        return response.status_code, int(length) if length and length.isdigit() else None
    except requests.RequestException:
        return None, None


def download_url(url: str, output_dir: Path = RAW_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(urlparse(url).path).name
    target = output_dir / filename
    if target.exists() and target.stat().st_size > 0:
        return target
    with requests.get(url, timeout=120, stream=True) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return target


def write_manifest(manifest: pd.DataFrame, output: Path = MANIFEST, metadata: Path = METADATA) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output, index=False)
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact": "ibge_2022_sector_source_manifest",
        "phase": "phase5a_ibge_intramunicipal_origins",
        "source_count": int(len(manifest)),
        "uf_geometry_sources": int((manifest["source_role"] == "sector_geometry_shapefile_uf").sum()),
        "raw_cache_policy": "downloaded raw files live under data/raw/ibge_censo_2022_phase5 and are git-ignored",
        "official_references": [
            "https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/26565-malhas-de-setores-censitarios-divisoes-intramunicipais.html",
            "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/",
        ],
    }
    metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-remote", action="store_true", help="HEAD-check remote URLs before writing the manifest.")
    parser.add_argument("--download", action="store_true", help="Download selected sources into the git-ignored raw cache.")
    parser.add_argument("--uf", action="append", choices=UF_CODES, help="UF geometry to download; repeatable. If omitted with --download, only BR aggregate and dictionary are downloaded.")
    parser.add_argument("--all-ufs", action="store_true", help="Download geometry for all 27 UFs.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--metadata", type=Path, default=METADATA)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args()

    manifest = build_manifest(check_remote=args.check_remote)
    write_manifest(manifest, args.manifest, args.metadata)

    downloaded: list[Path] = []
    if args.download:
        roles = {"sector_basic_aggregate_population", "sector_aggregate_dictionary"}
        selected = manifest[manifest["source_role"].isin(roles)].copy()
        selected_ufs = UF_CODES if args.all_ufs else [uf.upper() for uf in args.uf or []]
        if selected_ufs:
            selected = pd.concat([
                selected,
                manifest[
                    manifest["source_role"].eq("sector_geometry_shapefile_uf")
                    & manifest["uf_sigla"].isin(selected_ufs)
                ],
            ], ignore_index=True)
        for url in selected["url"]:
            downloaded.append(download_url(str(url), args.raw_dir))

    print(f"Saved IBGE 2022 source manifest with {len(manifest)} rows to {args.manifest}")
    if downloaded:
        print("Downloaded:")
        for path in downloaded:
            print(f"- {path}")


if __name__ == "__main__":
    main()
