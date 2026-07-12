"""Fetch official municipal-seat coordinates from IBGE Localidades 2022."""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
import shapefile


SOURCE_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/"
    "localidades/Localidades_do_Brasil/2022/Localidades_Brasil_shp.zip"
)
USER_AGENT = "ubs-healthcare-mapping/1.0 (academic spatial accessibility study)"


def select_municipal_seats(records: list[dict]) -> pd.DataFrame:
    rows = []
    for record in records:
        subcategory = str(record.get("SCT_LOCALI", "")).casefold()
        category = str(record.get("CT_LOCALID", "")).casefold()
        if subcategory not in {"sede municipal", "capital federal"} and category != "distrito estadual de fernando de noronha":
            continue
        rows.append({
            "ibge_municipio_7": str(record.get("CD_MUN", "")),
            "municipio_nome_ibge_seat": record.get("NM_MUN"),
            "uf_sigla_ibge_seat": record.get("SIGLA_UF"),
            "seat_latitude": pd.to_numeric(record.get("LAT_LOCALI"), errors="coerce"),
            "seat_longitude": pd.to_numeric(record.get("LONG_LOCAL"), errors="coerce"),
            "seat_category": record.get("CT_LOCALID"),
            "seat_subcategory": record.get("SCT_LOCALI"),
        })
    frame = pd.DataFrame(rows).drop_duplicates("ibge_municipio_7")
    valid = frame["seat_latitude"].between(-34, 6) & frame["seat_longitude"].between(-74, -28)
    if not valid.all():
        raise ValueError("IBGE municipal-seat coordinate outside Brazilian bounds")
    return frame.sort_values("ibge_municipio_7").reset_index(drop=True)


def parse_shapefile_zip(content: bytes) -> pd.DataFrame:
    archive = zipfile.ZipFile(io.BytesIO(content))
    shp_name = next(name for name in archive.namelist() if name.lower().endswith(".shp"))
    base = shp_name[:-4]
    reader = shapefile.Reader(
        shp=io.BytesIO(archive.read(base + ".shp")),
        shx=io.BytesIO(archive.read(base + ".shx")),
        dbf=io.BytesIO(archive.read(base + ".dbf")),
        encoding="utf-8",
    )
    return select_municipal_seats([record.as_dict() for record in reader.iterRecords()])


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official IBGE municipal-seat coordinates.")
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/reference/ibge_municipal_seats_2022.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("projects/ubs-healthcare-mapping/data/reference/ibge_municipal_seats_2022_metadata.json"))
    args = parser.parse_args()
    response = requests.get(SOURCE_URL, headers={"User-Agent": USER_AGENT}, timeout=180)
    response.raise_for_status()
    result = parse_shapefile_zip(response.content)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "IBGE Censo Demografico 2022 - Localidades do Brasil",
        "source_url": SOURCE_URL,
        "selection": "SCT_LOCALI equals Sede Municipal",
        "records": len(result),
        "coordinate_reference": "SIRGAS 2000 geographic coordinates",
        "important_limit": "A municipal seat is an urban reference point, not a population-weighted origin and not representative of all rural residents.",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(result):,} official municipal-seat coordinates to {args.output}")


if __name__ == "__main__":
    main()
