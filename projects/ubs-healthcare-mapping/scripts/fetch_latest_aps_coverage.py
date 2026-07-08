"""
Fetch the latest public APS potential coverage data from the official APS reports API.

The public web report currently calls:
    https://relatorioaps-prd.saude.gov.br/data/competencias-cnes
    https://relatorioaps-prd.saude.gov.br/cobertura/aps

The script saves the municipal table as CSV so the enrichment pipeline can run
without depending on a manual spreadsheet download.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests


BASE_URL = "https://relatorioaps-prd.saude.gov.br"


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def latest_competence() -> str:
    competencies = get_json(f"{BASE_URL}/data/competencias-cnes")
    if not competencies:
        raise ValueError("APS API returned no competencies.")
    return str(competencies[0])


def fetch_municipal_coverage(competence: str) -> pd.DataFrame:
    params = {
        "unidadeGeografica": "MUNICIPIO",
        "nuCompInicio": competence,
        "nuCompFim": competence,
    }
    rows = get_json(f"{BASE_URL}/cobertura/aps", params=params)
    if not rows:
        raise ValueError(f"APS API returned no rows for competence {competence}.")
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch latest municipal APS potential coverage data.")
    parser.add_argument("--competence", help="CNES competence in YYYYMM format. Defaults to latest available.")
    parser.add_argument("--output", default="projects/ubs-healthcare-mapping/data/cobertura-aps-latest.csv")
    parser.add_argument("--metadata", default="projects/ubs-healthcare-mapping/data/aps_api_metadata.json")
    args = parser.parse_args()

    competence = args.competence or latest_competence()
    output = Path(args.output)
    metadata = Path(args.metadata)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)

    df = fetch_municipal_coverage(competence)
    df.to_csv(output, index=False)

    metadata.write_text(
        json.dumps(
            {
                "source": "Relatorios Publicos APS",
                "base_url": BASE_URL,
                "competence": competence,
                "rows": int(len(df)),
                "unit": "MUNICIPIO",
                "output": str(output),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Saved {len(df)} APS rows for {competence} to {output}")


if __name__ == "__main__":
    main()
