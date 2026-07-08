"""Build a CNES + SIA/SUS operational signal for UBS records.

The status is an evidence proxy:
- present in the latest CNES ST file means "active cadastral proxy";
- present in the latest SIA/SUS PA file means "recent production signal".
It is not a direct audit of opening hours, team availability or care quality.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from ftplib import FTP
from pathlib import Path

import pandas as pd
from pyreaddbc import dbc2dbf
from pysus.data.dbf_reader import read_dbf_schema

from analyze_ubs import add_region, normalize_columns, read_ubs_csv


CNES_ST_DIR = "/dissemin/publicos/CNES/200508_/Dados/ST"
SIA_PA_DIR = "/dissemin/publicos/SIASUS/200801_/Dados"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()


def normalize_cnes(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text.split(".")[0].zfill(7)


def numeric(value: object) -> float:
    text = str(value).strip().replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def discover_latest_files(ftp: FTP, remote_dir: str, prefix: str) -> dict[str, str]:
    ftp.cwd(remote_dir)
    names = ftp.nlst()
    latest: dict[str, tuple[str, str]] = {}
    pattern = re.compile(rf"^{prefix}([A-Z]{{2}})(\d{{4}})[a-z]?\.dbc$", re.IGNORECASE)
    for name in names:
        match = pattern.match(name)
        if not match:
            continue
        uf, yymm = match.groups()
        current = latest.get(uf)
        if current is None or yymm > current[0] or (yymm == current[0] and name > current[1]):
            latest[uf] = (yymm, name)
    return {uf: name for uf, (_yymm, name) in latest.items()}


def download_file(ftp: FTP, remote_dir: str, name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / name
    if target.exists() and target.stat().st_size > 0:
        return target
    ftp.cwd(remote_dir)
    with target.open("wb") as handle:
        ftp.retrbinary(f"RETR {name}", handle.write)
    return target


def convert_to_dbf(dbc_path: Path) -> Path:
    dbf_path = dbc_path.with_suffix(".dbf")
    dbc2dbf(str(dbc_path), str(dbf_path))
    return dbf_path


def decode_field(record: bytes, offset: int, length: int) -> str:
    return record[offset : offset + length].rstrip(b"\x00 ").decode("latin-1", errors="ignore").strip()


def scan_dbf_for_cnes(path: Path, cnes_column: str, target_cnes: set[str], columns: list[str]):
    schema = read_dbf_schema(path)
    field_map = {field.name: field for field in schema.fields}
    cnes_field = field_map[cnes_column]
    selected = {name: field_map[name] for name in columns if name in field_map}
    target_bytes = {cnes.encode("latin-1") for cnes in target_cnes}

    with path.open("rb") as handle:
        handle.seek(schema.header_len)
        for _row_idx in range(schema.num_records):
            record = handle.read(schema.record_len)
            if len(record) < schema.record_len:
                break
            if record[:1] in (b"\x00", b"*"):
                continue
            cnes_raw = record[cnes_field.offset : cnes_field.offset + cnes_field.length].rstrip(b"\x00 ")
            if cnes_raw not in target_bytes:
                continue
            row = {name: decode_field(record, field.offset, field.length) for name, field in selected.items()}
            row[cnes_column] = cnes_raw.decode("latin-1", errors="ignore").strip()
            yield row


def process_cnes_st(dbf_path: Path, target_cnes: set[str]) -> dict[str, dict[str, object]]:
    fields = ["CNES", "CODUFMUN", "TP_UNID", "VINC_SUS", "TPGESTAO", "ATIVIDAD", "CLIENTEL", "TURNO_AT", "DT_ATUAL", "COMPETEN"]
    output: dict[str, dict[str, object]] = {}
    for row in scan_dbf_for_cnes(dbf_path, "CNES", target_cnes, fields):
        cnes = normalize_cnes(row.get("CNES"))
        if cnes not in target_cnes:
            continue
        output[cnes] = {
            "cnes_present_latest_st": True,
            "cnes_competence": row.get("COMPETEN"),
            "cnes_municipality": row.get("CODUFMUN"),
            "cnes_unit_type": row.get("TP_UNID"),
            "cnes_sus_link": row.get("VINC_SUS"),
            "cnes_management": row.get("TPGESTAO"),
            "cnes_activity_code": row.get("ATIVIDAD"),
            "cnes_clientele": row.get("CLIENTEL"),
            "cnes_shift": row.get("TURNO_AT"),
            "cnes_updated_at_competence": row.get("DT_ATUAL"),
        }
    return output


def process_sia_pa(dbf_path: Path, target_cnes: set[str]) -> dict[str, dict[str, object]]:
    fields = ["PA_CODUNI", "PA_CMP", "PA_QTDPRO", "PA_VALPRO", "PA_UFMUN"]
    rows = defaultdict(int)
    quantities = defaultdict(float)
    values = defaultdict(float)
    municipality = {}
    competence = {}
    for row in scan_dbf_for_cnes(dbf_path, "PA_CODUNI", target_cnes, fields):
        cnes = normalize_cnes(row.get("PA_CODUNI"))
        if cnes not in target_cnes:
            continue
        rows[cnes] += 1
        quantities[cnes] += numeric(row.get("PA_QTDPRO"))
        values[cnes] += numeric(row.get("PA_VALPRO"))
        municipality[cnes] = row.get("PA_UFMUN")
        competence[cnes] = row.get("PA_CMP")

    return {
        cnes: {
            "sia_recent_production": True,
            "sia_competence": competence.get(cnes),
            "sia_municipality": municipality.get(cnes),
            "sia_records": rows[cnes],
            "sia_quantity": quantities[cnes],
            "sia_value": values[cnes],
        }
        for cnes in rows
    }


def status_label(cnes_present: bool, sia_present: bool) -> str:
    if cnes_present and sia_present:
        return "cadastral_active_with_recent_sia_production"
    if cnes_present and not sia_present:
        return "cadastral_active_without_recent_sia_production"
    if not cnes_present and sia_present:
        return "not_in_latest_cnes_st_but_has_recent_sia_production"
    return "registered_only_no_current_cnes_or_sia_signal"


def build_operational_status(
    ubs_path: Path,
    output_cnes: Path,
    output_by_uf: Path,
    output_metadata: Path,
    work_dir: Path | None = None,
    keep_raw: bool = False,
) -> None:
    ubs = add_region(normalize_columns(read_ubs_csv(ubs_path)))
    ubs["cnes"] = ubs["cnes"].map(normalize_cnes)
    ubs = ubs.loc[ubs["cnes"].ne("")].copy()
    target_by_uf = {uf: set(ubs.loc[ubs["uf_sigla"].eq(uf), "cnes"]) for uf in UFS}
    all_cnes = set(ubs["cnes"])

    temp_context = tempfile.TemporaryDirectory() if work_dir is None else None
    raw_dir = Path(temp_context.name if temp_context else work_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    cnes_rows: dict[str, dict[str, object]] = {}
    sia_rows: dict[str, dict[str, object]] = {}
    processed_files = []

    ftp = FTP("ftp.datasus.gov.br", timeout=120)
    ftp.login()
    cnes_files = discover_latest_files(ftp, CNES_ST_DIR, "ST")
    sia_files = discover_latest_files(ftp, SIA_PA_DIR, "PA")

    try:
        for uf in UFS:
            uf_targets = target_by_uf.get(uf, set())
            if not uf_targets:
                continue

            for source, remote_dir, files, processor, sink in [
                ("CNES_ST", CNES_ST_DIR, cnes_files, process_cnes_st, cnes_rows),
                ("SIA_PA", SIA_PA_DIR, sia_files, process_sia_pa, sia_rows),
            ]:
                name = files.get(uf)
                if not name:
                    continue
                source_dir = raw_dir / source.lower()
                dbc_path = download_file(ftp, remote_dir, name, source_dir)
                dbf_path = convert_to_dbf(dbc_path)
                sink.update(processor(dbf_path, uf_targets))
                processed_files.append(
                    {
                        "source": source,
                        "uf": uf,
                        "file": name,
                        "compressed_bytes": dbc_path.stat().st_size,
                        "dbf_bytes": dbf_path.stat().st_size,
                    }
                )
                if not keep_raw:
                    dbc_path.unlink(missing_ok=True)
                    dbf_path.unlink(missing_ok=True)
    finally:
        ftp.quit()
        if temp_context is not None:
            temp_context.cleanup()

    rows = []
    for row in ubs[["cnes", "uf_sigla", "region", "ibge", "nome"]].drop_duplicates("cnes").itertuples(index=False):
        cnes = row.cnes
        cnes_info = cnes_rows.get(cnes, {"cnes_present_latest_st": False})
        sia_info = sia_rows.get(cnes, {"sia_recent_production": False, "sia_records": 0, "sia_quantity": 0.0, "sia_value": 0.0})
        cnes_present = bool(cnes_info.get("cnes_present_latest_st"))
        sia_present = bool(sia_info.get("sia_recent_production"))
        rows.append(
            {
                "cnes": cnes,
                "uf_sigla": row.uf_sigla,
                "region": row.region,
                "ibge_municipio": row.ibge,
                "ubs_name": row.nome,
                "cnes_registered_in_project": True,
                **cnes_info,
                **sia_info,
                "operational_status": status_label(cnes_present, sia_present),
            }
        )

    status = pd.DataFrame(rows)
    output_cnes.parent.mkdir(parents=True, exist_ok=True)
    status.to_csv(output_cnes, index=False)

    by_uf = (
        status.groupby(["uf_sigla", "region"], dropna=False)
        .agg(
            ubs_records=("cnes", "size"),
            cnes_active_proxy=("cnes_present_latest_st", "sum"),
            recent_sia_production=("sia_recent_production", "sum"),
            active_with_recent_sia_production=(
                "operational_status",
                lambda s: int((s == "cadastral_active_with_recent_sia_production").sum()),
            ),
            sia_records=("sia_records", "sum"),
            sia_quantity=("sia_quantity", "sum"),
            sia_value=("sia_value", "sum"),
        )
        .reset_index()
    )
    by_uf["cnes_active_proxy_pct"] = by_uf["cnes_active_proxy"] / by_uf["ubs_records"] * 100
    by_uf["recent_sia_production_pct"] = by_uf["recent_sia_production"] / by_uf["ubs_records"] * 100
    by_uf["active_with_recent_sia_production_pct"] = (
        by_uf["active_with_recent_sia_production"] / by_uf["ubs_records"] * 100
    )
    by_uf.sort_values("active_with_recent_sia_production_pct").to_csv(output_by_uf, index=False)

    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "method": "CNES active proxy is presence in the latest CNES ST file. Recent production signal is presence in the latest SIA/SUS PA file.",
        "cnes_source_dir": CNES_ST_DIR,
        "sia_source_dir": SIA_PA_DIR,
        "cnes_latest_files": cnes_files,
        "sia_latest_files": sia_files,
        "ubs_records": int(len(status)),
        "cnes_active_proxy_records": int(status["cnes_present_latest_st"].sum()),
        "recent_sia_production_records": int(status["sia_recent_production"].sum()),
        "active_with_recent_sia_production_records": int(
            status["operational_status"].eq("cadastral_active_with_recent_sia_production").sum()
        ),
        "processed_files": processed_files,
        "important_limit": "SIA/SUS PA is a billing/production record, not direct proof of service quality, opening hours or team availability. Lack of recent PA production may reflect reporting lag or local recording practices.",
    }
    output_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build UBS operational proxy with CNES ST and SIA/SUS PA.")
    parser.add_argument("--ubs", default="projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv")
    parser.add_argument("--output-cnes", default="projects/ubs-healthcare-mapping/data/ubs_operational_status.csv")
    parser.add_argument("--output-by-uf", default="projects/ubs-healthcare-mapping/data/ubs_operational_status_by_uf.csv")
    parser.add_argument("--metadata", default="projects/ubs-healthcare-mapping/data/ubs_operational_status_metadata.json")
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()

    build_operational_status(
        Path(args.ubs),
        Path(args.output_cnes),
        Path(args.output_by_uf),
        Path(args.metadata),
        Path(args.work_dir) if args.work_dir else None,
        args.keep_raw,
    )
    print(f"Saved UBS operational status to {args.output_cnes} and {args.output_by_uf}")


if __name__ == "__main__":
    main()
