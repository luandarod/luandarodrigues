"""Fetch latest CNES professionals and teams for project UBS and aggregate safely.

No personal professional identifiers are persisted. Physician links are
identified in memory, deduplicated and reduced to municipality-level counts and
weekly ambulatory workload.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import defaultdict
from datetime import UTC, datetime
from ftplib import FTP
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_ubs_operational_status import (
    CNES_ST_DIR,
    UFS,
    convert_to_dbf,
    discover_latest_files,
    download_file,
    normalize_cnes,
    numeric,
    scan_dbf_for_cnes,
)


CNES_PF_DIR = CNES_ST_DIR.rsplit("/", 1)[0] + "/PF"
CNES_EP_DIR = CNES_ST_DIR.rsplit("/", 1)[0] + "/EP"


def download_with_retry(remote_dir: str, name: str, output_dir: Path, attempts: int = 3) -> Path:
    last_error = None
    for attempt in range(1, attempts + 1):
        ftp = FTP("ftp.datasus.gov.br", timeout=180)
        try:
            ftp.login()
            return download_file(ftp, remote_dir, name, output_dir)
        except Exception as error:
            last_error = error
            if attempt < attempts:
                time.sleep(attempt * 2)
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()
    raise RuntimeError(f"Failed to download {name} after {attempts} attempts") from last_error


def _municipality_key(values: pd.Series) -> pd.Series:
    return values.astype("string").str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True).str[:6]


def _professional_identity(row: dict[str, object]) -> str:
    return str(row.get("CNS_PROF") or row.get("CPF_PROF") or "").strip()


def aggregate_professional_rows(
    rows,
    target_cnes_to_municipality: dict[str, str],
    active_cnes: set[str],
) -> pd.DataFrame:
    link_hours: dict[tuple[str, str, str, str], float] = {}
    for row in rows:
        cnes = normalize_cnes(row.get("CNES"))
        cbo = str(row.get("CBO") or "").strip()
        identity = _professional_identity(row)
        municipality = target_cnes_to_municipality.get(cnes)
        if municipality is None or not cbo.startswith("225") or not identity:
            continue
        key = (municipality, cnes, identity, cbo)
        link_hours[key] = max(link_hours.get(key, 0), numeric(row.get("HORA_AMB")))

    if not link_hours:
        return pd.DataFrame(columns=[
            "ibge_municipio", "physicians_unique", "physician_cnes_links",
            "physician_ambulatory_hours_weekly", "physician_fte_40h",
            "ubs_with_physician", "active_ubs_with_physician",
        ])
    records = pd.DataFrame([
        {
            "ibge_municipio": municipality,
            "cnes": cnes,
            "professional_identity": identity,
            "cbo": cbo,
            "hours": hours,
            "active_cnes": cnes in active_cnes,
        }
        for (municipality, cnes, identity, cbo), hours in link_hours.items()
    ])
    output = records.groupby("ibge_municipio", as_index=False).agg(
        physicians_unique=("professional_identity", "nunique"),
        physician_cnes_links=("cnes", lambda values: records.loc[values.index, ["cnes", "professional_identity"]].drop_duplicates().shape[0]),
        physician_ambulatory_hours_weekly=("hours", "sum"),
        ubs_with_physician=("cnes", "nunique"),
        active_ubs_with_physician=("cnes", lambda values: records.loc[values.index].loc[records.loc[values.index, "active_cnes"], "cnes"].nunique()),
    )
    output["physician_fte_40h"] = output["physician_ambulatory_hours_weekly"] / 40
    return output


def aggregate_team_rows(
    rows,
    target_cnes_to_municipality: dict[str, str],
    active_cnes: set[str],
) -> pd.DataFrame:
    records = []
    seen = set()
    for row in rows:
        cnes = normalize_cnes(row.get("CNES"))
        municipality = target_cnes_to_municipality.get(cnes)
        team = str(row.get("IDEQUIPE") or "").strip()
        team_type = str(row.get("TIPO_EQP") or "").strip()
        deactivated = str(row.get("DT_DESAT") or "").strip()
        key = (municipality, cnes, team)
        active_date_codes = {"", "900001"}
        if municipality is None or not team or deactivated not in active_date_codes or key in seen:
            continue
        seen.add(key)
        records.append({
            "ibge_municipio": municipality,
            "cnes": cnes,
            "team": team,
            "team_type": team_type,
            "active_cnes": cnes in active_cnes,
        })
    if not records:
        return pd.DataFrame(columns=[
            "ibge_municipio", "active_cnes_teams_all_types", "active_cnes_team_types",
            "ubs_with_cnes_team", "active_ubs_with_cnes_team",
        ])
    frame = pd.DataFrame(records)
    return frame.groupby("ibge_municipio", as_index=False).agg(
        active_cnes_teams_all_types=("team", "nunique"),
        active_cnes_team_types=("team_type", "nunique"),
        ubs_with_cnes_team=("cnes", "nunique"),
        active_ubs_with_cnes_team=("cnes", lambda values: frame.loc[values.index].loc[frame.loc[values.index, "active_cnes"], "cnes"].nunique()),
    )


def build_workforce(
    operational_path: Path,
    population_path: Path,
    output_path: Path,
    metadata_path: Path,
    work_dir: Path | None = None,
    keep_raw: bool = False,
) -> None:
    operational = pd.read_csv(operational_path, dtype={"cnes": str, "ibge_municipio": str})
    operational["cnes"] = operational["cnes"].map(normalize_cnes)
    operational["ibge_municipio"] = _municipality_key(operational["ibge_municipio"])
    target_map = dict(operational[["cnes", "ibge_municipio"]].drop_duplicates("cnes").itertuples(index=False, name=None))
    active_cnes = set(operational.loc[operational["cnes_present_latest_st"].astype("boolean").fillna(False), "cnes"])
    target_by_uf = {uf: set(operational.loc[operational["uf_sigla"].eq(uf), "cnes"]) for uf in UFS}

    temp_context = tempfile.TemporaryDirectory() if work_dir is None else None
    raw_dir = Path(temp_context.name if temp_context else work_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    professional_outputs = []
    team_outputs = []
    processed_files = []

    ftp = FTP("ftp.datasus.gov.br", timeout=180)
    ftp.login()
    pf_files = discover_latest_files(ftp, CNES_PF_DIR, "PF")
    ep_files = discover_latest_files(ftp, CNES_EP_DIR, "EP")
    ftp.quit()
    try:
        for uf in UFS:
            targets = target_by_uf.get(uf, set())
            if not targets:
                continue
            for source, remote_dir, name, fields in [
                ("CNES_PF", CNES_PF_DIR, pf_files.get(uf), ["CNES", "CBO", "CNS_PROF", "CPF_PROF", "HORA_AMB"]),
                ("CNES_EP", CNES_EP_DIR, ep_files.get(uf), ["CNES", "IDEQUIPE", "TIPO_EQP", "DT_DESAT"]),
            ]:
                if not name:
                    continue
                source_dir = raw_dir / source.lower()
                dbc = download_with_retry(remote_dir, name, source_dir)
                dbf = convert_to_dbf(dbc)
                rows = scan_dbf_for_cnes(dbf, "CNES", targets, fields)
                if source == "CNES_PF":
                    professional_outputs.append(aggregate_professional_rows(rows, target_map, active_cnes))
                else:
                    team_outputs.append(aggregate_team_rows(rows, target_map, active_cnes))
                processed_files.append({
                    "source": source,
                    "uf": uf,
                    "file": name,
                    "compressed_bytes": dbc.stat().st_size,
                    "dbf_bytes": dbf.stat().st_size,
                })
                if not keep_raw:
                    dbc.unlink(missing_ok=True)
                    dbf.unlink(missing_ok=True)
    finally:
        if temp_context is not None:
            temp_context.cleanup()

    workforce = pd.concat(professional_outputs, ignore_index=True)
    teams = pd.concat(team_outputs, ignore_index=True)
    population = pd.read_csv(population_path, dtype={"ibge_municipio": str})
    population["ibge_municipio"] = _municipality_key(population["ibge_municipio"])
    population = population[[
        "ibge_municipio", "municipio_nome_ibge", "uf_sigla", "populacao_residente",
        "potentially_uncovered_population", "active_ubs",
    ]].drop_duplicates("ibge_municipio")
    output = population.merge(workforce, on="ibge_municipio", how="left").merge(teams, on="ibge_municipio", how="left")
    count_columns = [
        "physicians_unique", "physician_cnes_links", "physician_ambulatory_hours_weekly",
        "physician_fte_40h", "ubs_with_physician", "active_ubs_with_physician",
        "active_cnes_teams_all_types", "active_cnes_team_types", "ubs_with_cnes_team",
        "active_ubs_with_cnes_team",
    ]
    output[count_columns] = output[count_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    population_denominator = pd.to_numeric(output["populacao_residente"], errors="coerce").replace(0, np.nan)
    fte_denominator = output["physician_fte_40h"].replace(0, np.nan)
    output["physicians_unique_per_100k"] = output["physicians_unique"] / population_denominator * 100_000
    output["physician_fte_per_100k"] = output["physician_fte_40h"] / population_denominator * 100_000
    output["potentially_uncovered_population_per_physician_fte"] = (
        output["potentially_uncovered_population"] / fte_denominator
    )
    output["active_ubs_with_physician_pct"] = (
        output["active_ubs_with_physician"] / output["active_ubs"].replace(0, np.nan) * 100
    ).clip(upper=100)
    outlier_threshold = output["physician_fte_per_100k"].quantile(0.99)
    output["workforce_quality_flag"] = "within_national_p99"
    output.loc[output["physician_fte_per_100k"].gt(outlier_threshold), "workforce_quality_flag"] = "review_above_national_p99"
    output["physician_definition"] = "CBO family 225; weekly ambulatory hours from latest CNES PF snapshot"
    output["team_definition"] = "All non-deactivated CNES EP team types; not restricted to eSF/eAP"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "professional_source_dir": CNES_PF_DIR,
        "team_source_dir": CNES_EP_DIR,
        "pf_files": pf_files,
        "ep_files": ep_files,
        "processed_files": processed_files,
        "physician_rule": "CBO starts with 225",
        "fte_rule": "sum of deduplicated weekly ambulatory hours divided by 40",
        "active_team_rule": "DT_DESAT is blank or uses the CNES active sentinel 900001",
        "physician_fte_per_100k_review_threshold_p99": float(outlier_threshold),
        "privacy": "Professional identifiers were used only in memory for deduplication and are not persisted.",
        "important_limits": [
            "CNES describes registered workload and does not prove attendance or availability.",
            "Latest snapshot does not measure turnover or longitudinal persistence.",
            "All active EP team types are counted; eSF/eAP financed teams come from e-Gestor APS separately.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved workforce and team metrics for {len(output):,} municipalities to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and aggregate latest CNES professionals and teams for UBS.")
    parser.add_argument("--operational", type=Path, default=Path("projects/ubs-healthcare-mapping/data/ubs_operational_status.csv"))
    parser.add_argument("--population", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/telemedicine_pre_paper_analytic.csv"))
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_cnes_workforce_teams.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_cnes_workforce_teams_metadata.json"))
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    build_workforce(args.operational, args.population, args.output, args.metadata, args.work_dir, args.keep_raw)


if __name__ == "__main__":
    main()
