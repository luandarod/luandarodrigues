"""
Mapping Primary Healthcare Units in Brazil

Portfolio script for exploratory analysis, data quality checks and regional aggregation
of Brazilian UBS records.

Expected input columns:
cnes, uf, ibge, nome, logradouro, bairro, latitude, longitude
"""

from pathlib import Path
import pandas as pd

UF_TO_REGION = {
    "AC": "North", "AP": "North", "AM": "North", "PA": "North", "RO": "North", "RR": "North", "TO": "North",
    "AL": "Northeast", "BA": "Northeast", "CE": "Northeast", "MA": "Northeast", "PB": "Northeast",
    "PE": "Northeast", "PI": "Northeast", "RN": "Northeast", "SE": "Northeast",
    "DF": "Center-West", "GO": "Center-West", "MT": "Center-West", "MS": "Center-West",
    "ES": "Southeast", "MG": "Southeast", "RJ": "Southeast", "SP": "Southeast",
    "PR": "South", "RS": "South", "SC": "South",
}

IBGE_UF_TO_SIGLA = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def add_region(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "uf" in df.columns and pd.api.types.is_numeric_dtype(df["uf"]):
        df["uf_sigla"] = df["uf"].map(IBGE_UF_TO_SIGLA)
    elif "uf" in df.columns:
        df["uf_sigla"] = df["uf"].astype(str).str.upper().str.strip()
    df["region"] = df["uf_sigla"].map(UF_TO_REGION)
    return df


def main(input_path: str, output_dir: str = "outputs") -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    df = normalize_columns(df)
    df = add_region(df)

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["has_valid_coordinates"] = df["latitude"].between(-34, 6) & df["longitude"].between(-74, -34)

    total = len(df)
    summary = pd.DataFrame([
        {"metric": "total_records", "value": total, "percentage": 100},
        {"metric": "unique_cnes", "value": df["cnes"].nunique(), "percentage": df["cnes"].nunique() / total * 100},
        {"metric": "states", "value": df["uf_sigla"].nunique(), "percentage": None},
        {"metric": "municipalities", "value": df["ibge"].nunique(), "percentage": None},
        {"metric": "valid_coordinates", "value": int(df["has_valid_coordinates"].sum()), "percentage": df["has_valid_coordinates"].mean() * 100},
        {"metric": "missing_complete_coordinates", "value": int((~df["has_valid_coordinates"]).sum()), "percentage": (~df["has_valid_coordinates"]).mean() * 100},
        {"metric": "repeated_coordinates", "value": int(df.duplicated(["latitude", "longitude"], keep=False).sum()), "percentage": df.duplicated(["latitude", "longitude"], keep=False).mean() * 100},
    ])

    region_distribution = (
        df.groupby("region", dropna=False)
        .size()
        .reset_index(name="ubs")
        .assign(percentage=lambda x: x["ubs"] / total * 100)
        .sort_values("ubs", ascending=False)
    )

    state_distribution = (
        df.groupby(["uf_sigla", "region"], dropna=False)
        .size()
        .reset_index(name="ubs")
        .assign(percentage=lambda x: x["ubs"] / total * 100)
        .sort_values("ubs", ascending=False)
    )

    summary.to_csv(output / "data_quality_summary.csv", index=False)
    region_distribution.to_csv(output / "region_distribution.csv", index=False)
    state_distribution.to_csv(output / "state_distribution.csv", index=False)


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "outputs")
