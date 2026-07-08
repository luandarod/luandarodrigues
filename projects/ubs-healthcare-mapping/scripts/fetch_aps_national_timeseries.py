"""Fetch national APS potential coverage time series from the public APS reports API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests


BASE_URL = "https://relatorioaps-prd.saude.gov.br"


def get_json(url: str, params: dict[str, Any]) -> Any:
    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def fetch_timeseries(start: str, end: str) -> pd.DataFrame:
    rows = get_json(
        f"{BASE_URL}/cobertura/aps",
        {
            "unidadeGeografica": "BRASIL",
            "nuCompInicio": start,
            "nuCompFim": end,
        },
    )
    if not rows:
        raise ValueError(f"APS API returned no national time-series rows for {start}-{end}.")
    df = pd.DataFrame(rows)
    df["competence"] = pd.to_datetime(df["nuComp"], format="%m/%Y")
    df["coverage_weighted_pct"] = df["qtCapacidadeEquipe"] / df["qtPopulacao"] * 100
    return df.sort_values("competence")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch national APS potential coverage time series.")
    parser.add_argument("--start", default="202101")
    parser.add_argument("--end", default="202604")
    parser.add_argument("--output", default="projects/ubs-healthcare-mapping/data/aps_national_timeseries.csv")
    parser.add_argument("--metadata", default="projects/ubs-healthcare-mapping/data/aps_timeseries_metadata.json")
    args = parser.parse_args()

    output = Path(args.output)
    metadata = Path(args.metadata)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)

    df = fetch_timeseries(args.start, args.end)
    df.to_csv(output, index=False)
    metadata.write_text(
        json.dumps(
            {
                "source": "Relatorios Publicos APS",
                "base_url": BASE_URL,
                "unit": "BRASIL",
                "start": args.start,
                "end": args.end,
                "rows": int(len(df)),
                "output": str(output),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Saved {len(df)} national APS rows to {output}")


if __name__ == "__main__":
    main()
