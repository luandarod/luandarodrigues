"""
Enrich UBS mapping project with IBGE territorial context.

This script extends the UBS portfolio project from a registry distribution analysis into a
territorial intelligence layer. It can join the UBS dataset by municipality IBGE code with:

1. IBGE Localidades API
   - official municipality name
   - UF
   - macroregion
   - immediate and intermediate geographic regions, when available

2. SIDRA / IBGE Table 4714
   - population
   - territorial area
   - demographic density

Expected UBS input columns:
    cnes, uf, ibge, nome, logradouro, bairro, latitude, longitude

Example:
    python enrich_with_ibge.py \
      --input data/raw/ubs.csv \
      --output-dir data/enriched

Outputs:
    municipality_ubs_territory.csv
    uf_ubs_territory_summary.csv
    priority_matrix.csv

Notes:
    - This script requires internet access to call IBGE APIs.
    - If the SIDRA API format changes, the Localidades enrichment still runs and the
      SIDRA step is skipped with a warning.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests

LOCALIDADES_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
SIDRA_4714_URL = "https://apisidra.ibge.gov.br/values/t/4714/n6/all/p/last"


def _safe_get(url: str, timeout: int = 60) -> Any:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _dig(data: Dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def fetch_ibge_municipalities() -> pd.DataFrame:
    """Fetch municipality hierarchy from the official IBGE Localidades API."""
    data = _safe_get(LOCALIDADES_MUNICIPIOS_URL)
    rows = []

    for item in data:
        microrregiao = item.get("microrregiao") or {}
        mesorregiao = microrregiao.get("mesorregiao") or {}
        uf = mesorregiao.get("UF") or {}
        regiao = uf.get("regiao") or {}

        regiao_imediata = item.get("regiao-imediata") or item.get("regiaoImediata") or {}
        regiao_intermediaria = (
            regiao_imediata.get("regiao-intermediaria")
            or regiao_imediata.get("regiaoIntermediaria")
            or {}
        )

        rows.append(
            {
                "ibge_municipio": int(item.get("id")),
                "municipio_nome_ibge": item.get("nome"),
                "microrregiao_id": microrregiao.get("id"),
                "microrregiao_nome": microrregiao.get("nome"),
                "mesorregiao_id": mesorregiao.get("id"),
                "mesorregiao_nome": mesorregiao.get("nome"),
                "uf_id": uf.get("id"),
                "uf_sigla": uf.get("sigla"),
                "uf_nome": uf.get("nome"),
                "regiao_id": regiao.get("id"),
                "regiao_sigla": regiao.get("sigla"),
                "regiao_nome": regiao.get("nome"),
                "regiao_imediata_id": regiao_imediata.get("id"),
                "regiao_imediata_nome": regiao_imediata.get("nome"),
                "regiao_intermediaria_id": regiao_intermediaria.get("id"),
                "regiao_intermediaria_nome": regiao_intermediaria.get("nome"),
            }
        )

    return pd.DataFrame(rows).drop_duplicates(subset=["ibge_municipio"])


def normalize_ubs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    if "ibge" not in df.columns:
        raise ValueError("Input file must contain an 'ibge' municipality code column.")

    df["ibge_municipio"] = pd.to_numeric(df["ibge"], errors="coerce").astype("Int64")

    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    else:
        df["latitude"] = pd.NA

    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    else:
        df["longitude"] = pd.NA

    df["has_valid_coordinates"] = (
        df["latitude"].between(-34, 6) & df["longitude"].between(-74, -34)
    )

    return df


def aggregate_ubs_by_municipality(df: pd.DataFrame) -> pd.DataFrame:
    group = df.groupby("ibge_municipio", dropna=True)

    result = group.agg(
        ubs_records=("ibge_municipio", "size"),
        valid_coordinate_records=("has_valid_coordinates", "sum"),
        latitude_missing=("latitude", lambda s: s.isna().sum()),
        longitude_missing=("longitude", lambda s: s.isna().sum()),
    ).reset_index()

    result["coordinate_validity_pct"] = (
        result["valid_coordinate_records"] / result["ubs_records"] * 100
    )
    result["missing_coordinate_records"] = (
        result["ubs_records"] - result["valid_coordinate_records"]
    )

    return result


def _clean_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "-", "..", "...", "X"}:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def fetch_sidra_4714() -> pd.DataFrame:
    """Fetch and reshape SIDRA Table 4714.

    The SIDRA API returns a first metadata row followed by data rows. This parser is
    intentionally defensive because column labels can vary depending on the selected
    dimensions and API output options.
    """
    data = _safe_get(SIDRA_4714_URL)
    if not data or len(data) < 2:
        raise ValueError("SIDRA API returned no data.")

    header = data[0]
    rows = data[1:]
    raw = pd.DataFrame(rows)

    # Common SIDRA columns:
    # D1C = territorial code, D1N = territorial name, D2N or D3N can hold variable labels,
    # V = value. The exact variable dimension may vary, so detect it by label content.
    code_col = "D1C" if "D1C" in raw.columns else None
    name_col = "D1N" if "D1N" in raw.columns else None
    value_col = "V" if "V" in raw.columns else None

    if not code_col or not value_col:
        raise ValueError("Could not identify SIDRA territorial code/value columns.")

    label_candidates = [c for c in raw.columns if c.endswith("N") and c not in {name_col}]
    variable_col = None
    for col in label_candidates:
        labels = raw[col].astype(str).str.lower().str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii")
        if labels.str.contains("populacao|area|densidade", regex=True).any():
            variable_col = col
            break

    if variable_col is None:
        raise ValueError("Could not identify SIDRA variable label column.")

    parsed = raw[[code_col, name_col, variable_col, value_col]].copy()
    parsed.columns = ["ibge_municipio", "municipio_nome_sidra", "variable", "value"]
    parsed["ibge_municipio"] = pd.to_numeric(parsed["ibge_municipio"], errors="coerce").astype("Int64")
    parsed["value"] = parsed["value"].map(_clean_numeric)

    def classify_variable(label: str) -> str:
        label_norm = (
            str(label)
            .lower()
            .replace("á", "a")
            .replace("ã", "a")
            .replace("â", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )
        if "populacao" in label_norm:
            return "populacao_residente"
        if "area" in label_norm:
            return "area_km2"
        if "densidade" in label_norm:
            return "densidade_demografica"
        return re.sub(r"[^a-z0-9]+", "_", label_norm).strip("_")

    parsed["metric"] = parsed["variable"].map(classify_variable)
    wide = (
        parsed.pivot_table(index=["ibge_municipio", "municipio_nome_sidra"], columns="metric", values="value", aggfunc="first")
        .reset_index()
    )
    wide.columns.name = None
    return wide


def add_priority_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "populacao_residente" in df.columns:
        df["ubs_per_10k_population"] = df["ubs_records"] / df["populacao_residente"] * 10000
    else:
        df["ubs_per_10k_population"] = pd.NA

    if "area_km2" in df.columns:
        df["ubs_per_1000_km2"] = df["ubs_records"] / df["area_km2"] * 1000
    else:
        df["ubs_per_1000_km2"] = pd.NA

    # Risk-oriented flags. These are not clinical judgements; they are portfolio/business
    # rules to help prioritize data review and territorial investigation.
    df["coordinate_quality_flag"] = pd.cut(
        df["coordinate_validity_pct"],
        bins=[-1, 80, 95, 100],
        labels=["high_attention", "monitor", "good"],
    )

    if "ubs_per_10k_population" in df.columns and df["ubs_per_10k_population"].notna().any():
        q25 = df["ubs_per_10k_population"].quantile(0.25)
        df["population_pressure_flag"] = df["ubs_per_10k_population"].apply(
            lambda x: "possible_pressure" if pd.notna(x) and x <= q25 else "baseline"
        )
    else:
        df["population_pressure_flag"] = "population_not_loaded"

    if "ubs_per_1000_km2" in df.columns and df["ubs_per_1000_km2"].notna().any():
        q25_area = df["ubs_per_1000_km2"].quantile(0.25)
        df["territorial_dispersion_flag"] = df["ubs_per_1000_km2"].apply(
            lambda x: "possible_dispersion" if pd.notna(x) and x <= q25_area else "baseline"
        )
    else:
        df["territorial_dispersion_flag"] = "area_not_loaded"

    return df


def build_outputs(input_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ubs = normalize_ubs(pd.read_csv(input_path))
    ubs_municipality = aggregate_ubs_by_municipality(ubs)

    print("Fetching IBGE Localidades...")
    municipalities = fetch_ibge_municipalities()

    enriched = ubs_municipality.merge(municipalities, on="ibge_municipio", how="left")

    sidra_loaded = False
    try:
        print("Fetching SIDRA Table 4714...")
        sidra = fetch_sidra_4714()
        enriched = enriched.merge(sidra, on="ibge_municipio", how="left")
        sidra_loaded = True
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: SIDRA Table 4714 could not be loaded: {exc}")

    enriched = add_priority_metrics(enriched)

    uf_summary = (
        enriched.groupby(["uf_sigla", "uf_nome", "regiao_nome"], dropna=False)
        .agg(
            municipalities=("ibge_municipio", "nunique"),
            ubs_records=("ubs_records", "sum"),
            valid_coordinate_records=("valid_coordinate_records", "sum"),
            missing_coordinate_records=("missing_coordinate_records", "sum"),
            population=("populacao_residente", "sum") if "populacao_residente" in enriched.columns else ("ubs_records", "sum"),
            area_km2=("area_km2", "sum") if "area_km2" in enriched.columns else ("ubs_records", "sum"),
        )
        .reset_index()
    )

    if "populacao_residente" in enriched.columns:
        uf_summary["ubs_per_10k_population"] = uf_summary["ubs_records"] / uf_summary["population"] * 10000
    if "area_km2" in enriched.columns:
        uf_summary["ubs_per_1000_km2"] = uf_summary["ubs_records"] / uf_summary["area_km2"] * 1000
    uf_summary["coordinate_validity_pct"] = uf_summary["valid_coordinate_records"] / uf_summary["ubs_records"] * 100

    priority_matrix = enriched.sort_values(
        by=["population_pressure_flag", "territorial_dispersion_flag", "coordinate_validity_pct", "ubs_records"],
        ascending=[False, False, True, False],
    )

    enriched.to_csv(output_dir / "municipality_ubs_territory.csv", index=False)
    uf_summary.to_csv(output_dir / "uf_ubs_territory_summary.csv", index=False)
    priority_matrix.to_csv(output_dir / "priority_matrix.csv", index=False)

    metadata = {
        "source_ubs_file": str(input_path),
        "ibge_localidades_url": LOCALIDADES_MUNICIPIOS_URL,
        "sidra_4714_url": SIDRA_4714_URL,
        "sidra_loaded": sidra_loaded,
        "outputs": [
            "municipality_ubs_territory.csv",
            "uf_ubs_territory_summary.csv",
            "priority_matrix.csv",
        ],
    }
    (output_dir / "enrichment_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Done. Files saved to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich UBS dataset with IBGE territorial indicators.")
    parser.add_argument("--input", required=True, help="Path to raw UBS CSV file.")
    parser.add_argument("--output-dir", default="data/enriched", help="Output directory.")
    args = parser.parse_args()

    build_outputs(Path(args.input), Path(args.output_dir))


if __name__ == "__main__":
    main()
