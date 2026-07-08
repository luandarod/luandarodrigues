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

The original UBS CSV may use semicolon separators and comma decimal separators.
This script auto-detects separators and normalizes both comma and dot decimal formats.

Key detail:
    the UBS and APS files in this project use the six-digit municipality code.
    IBGE Localidades and SIDRA use the official seven-digit municipality code.
    The pipeline keeps both and joins on the six-digit key.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import requests

LOCALIDADES_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
SIDRA_4714_URL = "https://apisidra.ibge.gov.br/values/t/4714/n6/all/p/last"


def _safe_get(url: str, timeout: int = 60) -> Any:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def read_ubs_csv(path: Path) -> pd.DataFrame:
    """Read UBS CSV with automatic delimiter and encoding handling."""
    encodings = ["utf-8-sig", "utf-8", "latin1"]
    separators = [None, ";", ",", "\t"]

    last_error: Exception | None = None
    for encoding in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(
                    path,
                    sep=sep,
                    engine="python" if sep is None else "c",
                    encoding=encoding,
                    dtype=str,
                )
                normalized_cols = [str(c).strip().lower() for c in df.columns]
                if "ibge" in normalized_cols:
                    return df
                # If the file was read as a single column, try next separator.
                if len(df.columns) == 1:
                    continue
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

    raise ValueError(
        "Could not read the UBS CSV with an IBGE column. "
        "Check if the file is a valid CSV and contains the header 'IBGE'. "
        f"Last error: {last_error}"
    )


def _normalize_decimal_series(series: pd.Series) -> pd.Series:
    """Convert decimal strings with comma or dot separators to numeric values."""
    return pd.to_numeric(
        series.astype(str)
        .str.strip()
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


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

        ibge_municipio_7 = int(item.get("id"))
        rows.append(
            {
                "ibge_municipio": ibge_municipio_7 // 10,
                "ibge_municipio_7": ibge_municipio_7,
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
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "ibge" not in df.columns:
        raise ValueError(f"Input file must contain an 'ibge' municipality code column. Columns found: {list(df.columns)}")

    ibge_code = pd.to_numeric(df["ibge"], errors="coerce").astype("Int64")
    df["ibge_municipio"] = ibge_code.where(ibge_code < 1000000, ibge_code // 10).astype("Int64")
    df["ibge_municipio_7"] = ibge_code.where(ibge_code >= 1000000, pd.NA).astype("Int64")

    if "latitude" in df.columns:
        df["latitude"] = _normalize_decimal_series(df["latitude"])
    else:
        df["latitude"] = pd.NA

    if "longitude" in df.columns:
        df["longitude"] = _normalize_decimal_series(df["longitude"])
    else:
        df["longitude"] = pd.NA

    df["has_valid_coordinates"] = df["latitude"].between(-34, 6) & df["longitude"].between(-74, -34)
    return df


def aggregate_ubs_by_municipality(df: pd.DataFrame) -> pd.DataFrame:
    group = df.groupby("ibge_municipio", dropna=True)
    result = group.agg(
        ubs_records=("ibge_municipio", "size"),
        valid_coordinate_records=("has_valid_coordinates", "sum"),
        latitude_missing=("latitude", lambda s: s.isna().sum()),
        longitude_missing=("longitude", lambda s: s.isna().sum()),
    ).reset_index()
    result["coordinate_validity_pct"] = result["valid_coordinate_records"] / result["ubs_records"] * 100
    result["missing_coordinate_records"] = result["ubs_records"] - result["valid_coordinate_records"]
    return result


def _clean_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "-", "..", "...", "X"}:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def fetch_sidra_4714() -> pd.DataFrame:
    """Fetch and reshape SIDRA Table 4714."""
    data = _safe_get(SIDRA_4714_URL)
    if not data or len(data) < 2:
        raise ValueError("SIDRA API returned no data.")

    raw = pd.DataFrame(data[1:])
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
    parsed["sidra_ibge_municipio_7"] = pd.to_numeric(parsed["ibge_municipio"], errors="coerce").astype("Int64")
    parsed["ibge_municipio"] = (parsed["sidra_ibge_municipio_7"] // 10).astype("Int64")
    parsed["value"] = parsed["value"].map(_clean_numeric)

    def classify_variable(label: str) -> str:
        label_norm = (
            str(label).lower()
            .replace("á", "a").replace("ã", "a").replace("â", "a")
            .replace("é", "e").replace("ê", "e")
            .replace("í", "i").replace("ó", "o").replace("õ", "o")
            .replace("ú", "u").replace("ç", "c")
        )
        if "populacao" in label_norm:
            return "populacao_residente"
        if "area" in label_norm:
            return "area_km2"
        if "densidade" in label_norm:
            return "densidade_demografica"
        return re.sub(r"[^a-z0-9]+", "_", label_norm).strip("_")

    parsed["metric"] = parsed["variable"].map(classify_variable)
    wide = parsed.pivot_table(
        index=["ibge_municipio", "sidra_ibge_municipio_7", "municipio_nome_sidra"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    return wide


def add_priority_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "populacao_residente" in df.columns:
        df["ubs_per_10k_population"] = df["ubs_records"] / df["populacao_residente"].replace(0, pd.NA) * 10000
    else:
        df["ubs_per_10k_population"] = pd.NA
    if "area_km2" in df.columns:
        df["ubs_per_1000_km2"] = df["ubs_records"] / df["area_km2"].replace(0, pd.NA) * 1000
    else:
        df["ubs_per_1000_km2"] = pd.NA
    df["coordinate_quality_flag"] = pd.cut(
        df["coordinate_validity_pct"], bins=[-1, 80, 95, 100], labels=["high_attention", "monitor", "good"]
    )
    if df["ubs_per_10k_population"].notna().any():
        q25 = df["ubs_per_10k_population"].quantile(0.25)
        df["population_pressure_flag"] = df["ubs_per_10k_population"].apply(lambda x: "possible_pressure" if pd.notna(x) and x <= q25 else "baseline")
    else:
        df["population_pressure_flag"] = "population_not_loaded"
    if df["ubs_per_1000_km2"].notna().any():
        q25_area = df["ubs_per_1000_km2"].quantile(0.25)
        df["territorial_dispersion_flag"] = df["ubs_per_1000_km2"].apply(lambda x: "possible_dispersion" if pd.notna(x) and x <= q25_area else "baseline")
    else:
        df["territorial_dispersion_flag"] = "area_not_loaded"
    return df


def build_outputs(input_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ubs = normalize_ubs(read_ubs_csv(input_path))
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
    unmatched_territory_rows = int(enriched["uf_sigla"].isna().sum()) if "uf_sigla" in enriched.columns else 0
    uf_ready = enriched.dropna(subset=["uf_sigla", "uf_nome", "regiao_nome"]).copy()

    agg_spec = {
        "municipalities": ("ibge_municipio", "nunique"),
        "ubs_records": ("ubs_records", "sum"),
        "valid_coordinate_records": ("valid_coordinate_records", "sum"),
        "missing_coordinate_records": ("missing_coordinate_records", "sum"),
    }
    if "populacao_residente" in enriched.columns:
        agg_spec["population"] = ("populacao_residente", "sum")
    if "area_km2" in enriched.columns:
        agg_spec["area_km2"] = ("area_km2", "sum")

    uf_summary = uf_ready.groupby(["uf_sigla", "uf_nome", "regiao_nome"], dropna=False).agg(**agg_spec).reset_index()
    if "population" in uf_summary.columns:
        uf_summary["ubs_per_10k_population"] = uf_summary["ubs_records"] / uf_summary["population"].replace(0, pd.NA) * 10000
    if "area_km2" in uf_summary.columns:
        uf_summary["ubs_per_1000_km2"] = uf_summary["ubs_records"] / uf_summary["area_km2"].replace(0, pd.NA) * 1000
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
        "municipality_join_key": "ibge_municipio, six-digit code used by the UBS and APS source files",
        "official_ibge_key": "ibge_municipio_7, seven-digit code used by IBGE Localidades and SIDRA",
        "ibge_localidades_url": LOCALIDADES_MUNICIPIOS_URL,
        "sidra_4714_url": SIDRA_4714_URL,
        "sidra_loaded": sidra_loaded,
        "unmatched_territory_rows": unmatched_territory_rows,
        "outputs": ["municipality_ubs_territory.csv", "uf_ubs_territory_summary.csv", "priority_matrix.csv"],
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
