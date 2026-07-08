"""Build coordinate quality diagnostics by UF from the raw UBS registry."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analyze_ubs import add_region, normalize_columns, normalize_decimal_series, read_ubs_csv


def build_coordinate_audit(input_path: Path, output_path: Path) -> None:
    df = add_region(normalize_columns(read_ubs_csv(input_path)))
    df["latitude"] = normalize_decimal_series(df["latitude"])
    df["longitude"] = normalize_decimal_series(df["longitude"])
    df["missing_latitude"] = df["latitude"].isna()
    df["missing_longitude"] = df["longitude"].isna()
    df["complete_coordinates"] = ~(df["missing_latitude"] | df["missing_longitude"])
    df["inside_brazil_bbox"] = df["latitude"].between(-34, 6) & df["longitude"].between(-74, -34)
    df["out_of_brazil_bbox"] = df["complete_coordinates"] & ~df["inside_brazil_bbox"]
    df["valid_coordinates"] = df["complete_coordinates"] & df["inside_brazil_bbox"]
    df["duplicated_valid_coordinates"] = df["valid_coordinates"] & df.duplicated(["latitude", "longitude"], keep=False)

    audit = (
        df.groupby(["uf_sigla", "region"], dropna=False)
        .agg(
            ubs_records=("cnes", "size"),
            missing_latitude=("missing_latitude", "sum"),
            missing_longitude=("missing_longitude", "sum"),
            complete_coordinates=("complete_coordinates", "sum"),
            valid_coordinates=("valid_coordinates", "sum"),
            out_of_brazil_bbox=("out_of_brazil_bbox", "sum"),
            duplicated_valid_coordinates=("duplicated_valid_coordinates", "sum"),
        )
        .reset_index()
    )
    audit["valid_coordinate_pct"] = audit["valid_coordinates"] / audit["ubs_records"] * 100
    audit["missing_any_coordinate_pct"] = (
        (audit["ubs_records"] - audit["complete_coordinates"]) / audit["ubs_records"] * 100
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit.sort_values("valid_coordinate_pct").to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build coordinate quality diagnostics by UF.")
    parser.add_argument("--input", default="projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv")
    parser.add_argument("--output", default="projects/ubs-healthcare-mapping/data/coordinate_quality_by_uf.csv")
    args = parser.parse_args()
    build_coordinate_audit(Path(args.input), Path(args.output))
    print(f"Saved coordinate quality audit to {args.output}")


if __name__ == "__main__":
    main()
