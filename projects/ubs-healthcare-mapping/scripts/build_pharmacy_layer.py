"""Normalize pharmacy records and build dashboard-ready spatial artifacts."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ALIASES = {
    "cnpj": {"cnpj", "nr_cnpj", "numero_cnpj"},
    "cnes": {"cnes", "codigo_cnes", "co_cnes"},
    "name": {"nome", "razao_social", "nome_fantasia", "estabelecimento", "farmacia"},
    "municipality": {"municipio", "nome_municipio", "no_municipio"},
    "ibge_municipality": {"codigo_ibge", "cod_ibge", "ibge", "co_municipio_ibge", "cod_municipio"},
    "uf": {"uf", "sigla_uf", "sg_uf"},
    "address": {"endereco", "logradouro", "ds_endereco"},
    "neighborhood": {"bairro"},
    "accreditation_date": {"data_do_credenciamento", "data_credenciamento"},
    "latitude": {"latitude", "lat"},
    "longitude": {"longitude", "lon", "lng"},
}


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _decimal(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype("string").str.strip().str.replace(",", ".", regex=False), errors="coerce")


def _column_map(df: pd.DataFrame) -> dict[str, str]:
    available = {_key(column): column for column in df.columns}
    return {
        target: available[alias]
        for target, aliases in ALIASES.items()
        for alias in aliases
        if alias in available
    }


def normalize_pharmacies(df: pd.DataFrame, source: str = "official input") -> pd.DataFrame:
    """Convert common official column variants into the project's canonical schema."""
    columns = _column_map(df)
    result = pd.DataFrame(index=df.index)
    for target in ALIASES:
        result[target] = df[columns[target]] if target in columns else pd.NA

    result["cnpj"] = result["cnpj"].astype("string").str.replace(r"\D", "", regex=True).replace("", pd.NA)
    result["cnes"] = result["cnes"].astype("string").str.replace(r"\D", "", regex=True).replace("", pd.NA)
    result["uf"] = result["uf"].astype("string").str.strip().str.upper()
    result["ibge_municipality"] = result["ibge_municipality"].astype("string").str.replace(r"\D", "", regex=True)
    result["latitude"] = _decimal(result["latitude"])
    result["longitude"] = _decimal(result["longitude"])
    result["valid_coordinates"] = result["latitude"].between(-34, 6) & result["longitude"].between(-74, -28)
    result["facility_type"] = "farmacia_popular"
    result["source"] = source
    result["facility_id"] = result["cnpj"].fillna(result["cnes"])
    missing_id = result["facility_id"].isna()
    result.loc[missing_id, "facility_id"] = "pharmacy-" + result.index[missing_id].astype(str)
    return result[
        ["facility_id", "facility_type", "cnes", "cnpj", "name", "ibge_municipality", "municipality",
         "uf", "address", "neighborhood", "accreditation_date", "latitude", "longitude", "valid_coordinates", "source"]
    ]


def summarize_by_uf(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("uf", dropna=False)
        .agg(pharmacies=("facility_id", "size"), valid_coordinates=("valid_coordinates", "sum"), municipalities=("municipality", "nunique"))
        .reset_index()
        .sort_values("pharmacies", ascending=False)
    )


def to_geojson(df: pd.DataFrame) -> dict:
    features = []
    for row in df[df["valid_coordinates"]].itertuples(index=False):
        properties = {
            key: (None if pd.isna(value) else value)
            for key, value in row._asdict().items()
            if key not in {"latitude", "longitude", "valid_coordinates"}
        }
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row.longitude, row.latitude]},
            "properties": properties,
        })
    return {"type": "FeatureCollection", "features": features}


def build_layer(raw: pd.DataFrame, output_dir: Path, source: str = "official input") -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized = normalize_pharmacies(raw, source=source)
    normalized.to_csv(output_dir / "pharmacies.csv", index=False)
    summarize_by_uf(normalized).to_csv(output_dir / "pharmacies_by_uf.csv", index=False)
    (output_dir / "pharmacies.geojson").write_text(
        json.dumps(to_geojson(normalized), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return normalized


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        preview = pd.read_excel(path, header=None, nrows=40)
        header_rows = preview.apply(
            lambda row: row.astype("string").map(_key).eq("uf").any()
            and row.astype("string").map(_key).isin({"cnpj", "farmacia"}).any(),
            axis=1,
        )
        if not header_rows.any():
            raise ValueError("Could not find the pharmacy table header in the workbook")
        return pd.read_excel(path, header=int(header_rows.idxmax())).dropna(how="all")
    return pd.read_csv(path, sep=None, engine="python", encoding_errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Farmacia Popular spatial layer from an official CSV/XLSX file.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/dashboards/ubs-healthcare-mapping/data"))
    parser.add_argument("--source", default="Programa Farmacia Popular - Ministerio da Saude")
    args = parser.parse_args()
    records = build_layer(read_table(args.input), args.output_dir, args.source)
    print(f"Saved {len(records):,} pharmacy records to {args.output_dir}")


if __name__ == "__main__":
    main()
