"""Fetch municipal household internet access from IBGE SIDRA table 9936."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests


TABLE_ID = 9936
YEAR = 2022
API_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/9936/periodos/2022/"
    "variaveis/381%7C1000381?localidades=N6%5Ball%5D&"
    "classificacao=2072%5B77584,77585,77586%5D%7C63%5B95826%5D%7C125%5B2932%5D"
)
COUNT_VARIABLE = "381"
PERCENT_VARIABLE = "1000381"
CATEGORY_COLUMNS = {
    "77584": "total",
    "77585": "with_internet",
    "77586": "without_internet",
}


def _number(value: object) -> float | None:
    text = str(value).strip().replace(",", ".")
    if text in {"", "-", "...", "X"}:
        return None
    return float(text)


def parse_sidra_results(payload: list[dict]) -> pd.DataFrame:
    rows: dict[str, dict[str, object]] = {}
    for variable in payload:
        variable_id = str(variable["id"])
        for result in variable.get("resultados", []):
            internet_classification = next(
                (item for item in result.get("classificacoes", []) if str(item.get("id")) == "2072"),
                None,
            )
            if internet_classification is None:
                continue
            category_id = next(iter(internet_classification["categoria"]))
            category = CATEGORY_COLUMNS.get(str(category_id))
            if category is None:
                continue
            for series in result.get("series", []):
                location = series["localidade"]
                code = str(location["id"])
                row = rows.setdefault(code, {
                    "ibge_municipio_7": code,
                    "municipio_nome_sidra": location["nome"],
                })
                value = _number(series["serie"].get(str(YEAR)))
                if variable_id == COUNT_VARIABLE:
                    row[f"households_{category}"] = value
                elif variable_id == PERCENT_VARIABLE and category != "total":
                    row[f"households_{category}_pct"] = value
    return pd.DataFrame(rows.values())


def reconcile_universe(observed: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    official = universe.copy()
    official["ibge_municipio_7"] = official["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    data = observed.copy()
    data["ibge_municipio_7"] = data["ibge_municipio_7"].astype("string")
    result = official.merge(data, on="ibge_municipio_7", how="left", validate="one_to_one")
    result["internet_data_status"] = "available_census_2022"
    result.loc[result["households_with_internet_pct"].isna(), "internet_data_status"] = "missing_2022_boundary"
    result["household_internet_readiness"] = result["households_with_internet_pct"] / 100
    result["household_count_residual"] = (
        result["households_total"]
        - result["households_with_internet"]
        - result["households_without_internet"]
    )
    result["internet_quality_flag"] = "valid_0_100"
    invalid = result["households_with_internet_pct"].notna() & ~result["households_with_internet_pct"].between(0, 100)
    result.loc[invalid, "internet_quality_flag"] = "invalid_outside_0_100"
    result.loc[result["households_with_internet_pct"].isna(), "internet_quality_flag"] = "missing"
    count_mismatch = result["household_count_residual"].abs().gt(1)
    result.loc[count_mismatch, "internet_quality_flag"] = "count_residual_above_1"
    result["internet_interpretation"] = "household access; does not measure speed, stability, literacy or pharmacy connectivity"
    return result


def fetch() -> list[dict]:
    response = requests.get(API_URL, timeout=120, headers={"User-Agent": "ubs-healthcare-mapping/1.0"})
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch municipal household internet access from SIDRA 9936.")
    parser.add_argument("--universe", type=Path, default=Path("projects/ubs-healthcare-mapping/data/reference/ibge_municipality_universe.csv"))
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_ibge_internet_readiness.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_ibge_internet_readiness_metadata.json"))
    args = parser.parse_args()
    observed = parse_sidra_results(fetch())
    result = reconcile_universe(observed, pd.read_csv(args.universe, dtype=str))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "IBGE SIDRA",
        "table": TABLE_ID,
        "year": YEAR,
        "api_url": API_URL,
        "official_universe_rows": len(result),
        "available_rows": int(result["households_with_internet_pct"].notna().sum()),
        "important_limit": "Household access does not measure connection speed, stability, digital literacy or pharmacy site readiness.",
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved IBGE internet readiness for {len(result):,} official municipalities to {args.output}")


if __name__ == "__main__":
    main()
