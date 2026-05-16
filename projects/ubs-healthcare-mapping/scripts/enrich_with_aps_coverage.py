"""
Enrich the UBS mapping project with APS potential coverage data.

This script joins the municipality-level UBS + IBGE enriched dataset with an external
APS coverage spreadsheet exported from e-Gestor/SISAB-style reports.

Important format note for this APS report:
    - "Região de Saúde" contains the municipality name in the exported file.
    - "Município" contains the IBGE municipality code.

Expected APS columns, when available:
    Comp. CNES
    Região
    UF
    Estado
    Região de Saúde
    Município
    População
    Qt. eSF
    Qt. eAP 20hs
    Qt. eAP 30hs
    Qt. eCR
    Qt. Cadastro eCR
    Qt. eAPP 20hs
    Qt. Cadastro eAPP 20hs
    Qt. eAPP 30hs
    Qt. Cadastro eAPP 30hs
    Qt. eSFR
    Qt. Cadastro eSFR
    Qt. cadastros das eCR e eAPP
    Qt. capacidade da equipe
    Cobertura APS

Example:
    python enrich_with_aps_coverage.py \
      --ubs-territory data/enriched/municipality_ubs_territory.csv \
      --aps-file data/cobertura-aps-geral.xlsx \
      --output-dir data/enriched
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


def slugify(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def parse_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text in {"", "-", "..", "..."}:
        return None
    text = text.replace("%", "").replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def load_aps_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError("APS file must be .xlsx, .xls or .csv")


def normalize_aps_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    original = list(df.columns)
    df.columns = [slugify(c) for c in df.columns]

    rename_map = {
        "competencia_cnes": "competencia_cnes",
        "comp_cnes": "competencia_cnes",
        "regiao": "regiao_aps",
        "uf": "uf_sigla",
        "estado": "estado_nome",
        # In this report, Região de Saúde is the municipality name.
        "regiao_de_saude": "municipio_nome_aps",
        # In this report, Município is the IBGE municipality code.
        "municipio": "ibge_municipio",
        "populacao": "aps_populacao",
        "qt_esf": "qt_esf",
        "qt_eap_20hs": "qt_eap_20hs",
        "qt_eap_30hs": "qt_eap_30hs",
        "qt_ecr": "qt_ecr",
        "qt_cadastro_ecr": "qt_cadastro_ecr",
        "qt_eapp_20hs": "qt_eapp_20hs",
        "qt_cadastro_eapp_20hs": "qt_cadastro_eapp_20hs",
        "qt_eapp_30hs": "qt_eapp_30hs",
        "qt_cadastro_eapp_30hs": "qt_cadastro_eapp_30hs",
        "qt_esfr": "qt_esfr",
        "qt_cadastro_esfr": "qt_cadastro_esfr",
        "qt_cadastros_das_ecr_e_eapp": "qt_cadastros_ecr_eapp",
        "qt_capacidade_da_equipe": "aps_capacidade_equipe",
        "cobertura_aps": "cobertura_aps_pct",
    }
    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    numeric_cols = [
        "ibge_municipio",
        "aps_populacao",
        "qt_esf",
        "qt_eap_20hs",
        "qt_eap_30hs",
        "qt_ecr",
        "qt_cadastro_ecr",
        "qt_eapp_20hs",
        "qt_cadastro_eapp_20hs",
        "qt_eapp_30hs",
        "qt_cadastro_eapp_30hs",
        "qt_esfr",
        "qt_cadastro_esfr",
        "qt_cadastros_ecr_eapp",
        "aps_capacidade_equipe",
        "cobertura_aps_pct",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].map(parse_number)

    if "ibge_municipio" in df.columns:
        df["ibge_municipio"] = pd.to_numeric(df["ibge_municipio"], errors="coerce").astype("Int64")
    if "uf_sigla" in df.columns:
        df["uf_sigla"] = df["uf_sigla"].astype(str).str.strip().str.upper()
    if "municipio_nome_aps" in df.columns:
        df["municipio_key"] = df["municipio_nome_aps"].map(slugify)

    df.attrs["original_columns"] = original
    return df


def build_outputs(ubs_territory_path: Path, aps_file_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    aps_raw = load_aps_file(aps_file_path)
    aps = normalize_aps_columns(aps_raw)

    metadata = {
        "aps_file": str(aps_file_path),
        "original_aps_columns": aps.attrs.get("original_columns", []),
        "aps_rows": int(len(aps)),
        "municipality_level_join": False,
        "join_strategy": "ibge_municipio when available; fallback to UF + normalized municipality name",
    }

    aps.to_csv(output_dir / "aps_coverage_normalized.csv", index=False)

    if "ibge_municipio" not in aps.columns and not {"uf_sigla", "municipio_key"}.issubset(set(aps.columns)):
        metadata["note"] = "APS file does not contain municipality code or UF+municipality name. Only macro summary was generated."
        aps.to_csv(output_dir / "aps_coverage_macro_summary.csv", index=False)
        (output_dir / "aps_enrichment_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        print("APS file has no municipality join key. Saved macro summary only.")
        return

    ubs = pd.read_csv(ubs_territory_path)
    if "ibge_municipio" not in ubs.columns:
        raise ValueError("UBS territory file must contain ibge_municipio column.")

    ubs["ibge_municipio"] = pd.to_numeric(ubs["ibge_municipio"], errors="coerce").astype("Int64")
    if "municipio_nome_ibge" in ubs.columns:
        ubs["municipio_key"] = ubs["municipio_nome_ibge"].map(slugify)
    if "uf_sigla" in ubs.columns:
        ubs["uf_sigla"] = ubs["uf_sigla"].astype(str).str.strip().str.upper()

    # Keep the most recent competência if multiple periods exist.
    if "competencia_cnes" in aps.columns:
        aps_sorted = aps.sort_values("competencia_cnes")
        if "ibge_municipio" in aps.columns:
            aps_latest = aps_sorted.groupby(["ibge_municipio"], as_index=False).tail(1)
        else:
            aps_latest = aps_sorted.groupby(["uf_sigla", "municipio_key"], as_index=False).tail(1)
    else:
        if "ibge_municipio" in aps.columns:
            aps_latest = aps.drop_duplicates(subset=["ibge_municipio"], keep="last")
        else:
            aps_latest = aps.drop_duplicates(subset=["uf_sigla", "municipio_key"], keep="last")

    if "ibge_municipio" in aps_latest.columns:
        enriched = ubs.merge(aps_latest, on="ibge_municipio", how="left", suffixes=("", "_aps"))
    else:
        enriched = ubs.merge(aps_latest, on=["uf_sigla", "municipio_key"], how="left", suffixes=("", "_aps"))

    population_base = enriched["populacao_residente"] if "populacao_residente" in enriched.columns else enriched.get("aps_populacao")

    if "aps_capacidade_equipe" in enriched.columns and population_base is not None:
        enriched["aps_capacity_per_10k_population"] = enriched["aps_capacidade_equipe"] / population_base * 10000

    if "cobertura_aps_pct" in enriched.columns:
        enriched["coverage_gap_pct"] = 100 - enriched["cobertura_aps_pct"]

    if {"ubs_per_10k_population", "cobertura_aps_pct", "coordinate_validity_pct"}.issubset(enriched.columns):
        ubs_pressure = 1 - enriched["ubs_per_10k_population"].rank(pct=True)
        coverage_gap = enriched["coverage_gap_pct"].rank(pct=True) if "coverage_gap_pct" in enriched.columns else 0
        coord_gap = 1 - enriched["coordinate_validity_pct"] / 100
        enriched["aps_priority_score"] = (ubs_pressure * 0.45 + coverage_gap * 0.40 + coord_gap * 0.15) * 100

    enriched.to_csv(output_dir / "municipality_ubs_aps_coverage.csv", index=False)

    if "uf_sigla" in enriched.columns:
        agg_cols = {
            "municipalities": ("ibge_municipio", "nunique"),
            "ubs_records": ("ubs_records", "sum"),
            "valid_coordinate_records": ("valid_coordinate_records", "sum"),
        }
        optional_sum = [
            "aps_populacao",
            "qt_esf",
            "qt_eap_20hs",
            "qt_eap_30hs",
            "qt_ecr",
            "qt_cadastro_ecr",
            "qt_eapp_20hs",
            "qt_cadastro_eapp_20hs",
            "qt_eapp_30hs",
            "qt_cadastro_eapp_30hs",
            "qt_esfr",
            "qt_cadastro_esfr",
            "qt_cadastros_ecr_eapp",
            "aps_capacidade_equipe",
        ]
        for col in optional_sum:
            if col in enriched.columns:
                agg_cols[col] = (col, "sum")
        if "cobertura_aps_pct" in enriched.columns:
            agg_cols["cobertura_aps_media_pct"] = ("cobertura_aps_pct", "mean")
        if "aps_priority_score" in enriched.columns:
            agg_cols["aps_priority_score"] = ("aps_priority_score", "mean")

        group_cols = [c for c in ["uf_sigla", "uf_nome", "regiao_nome"] if c in enriched.columns]
        uf_summary = enriched.groupby(group_cols, dropna=False).agg(**agg_cols).reset_index()
        uf_summary.to_csv(output_dir / "uf_ubs_aps_coverage_summary.csv", index=False)

    metadata["municipality_level_join"] = True
    metadata["outputs"] = [
        "aps_coverage_normalized.csv",
        "municipality_ubs_aps_coverage.csv",
        "uf_ubs_aps_coverage_summary.csv",
    ]
    (output_dir / "aps_enrichment_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done. APS coverage outputs saved to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Join APS coverage data with UBS + IBGE territorial dataset.")
    parser.add_argument("--ubs-territory", required=True, help="Path to municipality_ubs_territory.csv")
    parser.add_argument("--aps-file", required=True, help="Path to APS coverage XLSX/CSV file")
    parser.add_argument("--output-dir", default="data/enriched", help="Output directory")
    args = parser.parse_args()

    build_outputs(Path(args.ubs_territory), Path(args.aps_file), Path(args.output_dir))


if __name__ == "__main__":
    main()
