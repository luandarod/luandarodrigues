"""Fetch and freeze the official IBGE municipality universe used by the index."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import requests


IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def fetch_universe() -> pd.DataFrame:
    response = requests.get(IBGE_URL, timeout=60)
    response.raise_for_status()
    rows = []
    for item in response.json():
        if item["microrregiao"] is not None:
            uf = item["microrregiao"]["mesorregiao"]["UF"]
        else:
            uf = item["regiao-imediata"]["regiao-intermediaria"]["UF"]
        region = uf["regiao"]
        rows.append({
            "ibge_municipio": str(item["id"])[:6],
            "ibge_municipio_7": str(item["id"]),
            "municipio_nome_oficial": item["nome"],
            "uf_sigla_oficial": uf["sigla"],
            "uf_nome_oficial": uf["nome"],
            "regiao_nome_oficial": region["nome"],
            "source_url": IBGE_URL,
            "retrieved_at": date.today().isoformat(),
        })
    return pd.DataFrame(rows).sort_values("ibge_municipio")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official IBGE municipality codes.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("projects/ubs-healthcare-mapping/data/reference/ibge_municipality_universe.csv"),
    )
    args = parser.parse_args()
    universe = fetch_universe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(args.output, index=False)
    print(f"Saved {len(universe):,} official municipalities to {args.output}")


if __name__ == "__main__":
    main()
