"""Fetch municipal mobile coverage and fixed-broadband density from Anatel."""

from __future__ import annotations

import argparse
import io
import json
import re
import struct
import unicodedata
import zlib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests


MOBILE_URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/infraestrutura/cobertura_movel.zip"
FIXED_URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip"
FIXED_MEMBER = "Densidade_Banda_Larga_Fixa.csv"
USER_AGENT = "ubs-healthcare-mapping/1.0 (academic data pipeline)"


def _range_get(session: requests.Session, url: str, start: int, end: int) -> bytes:
    response = session.get(
        url,
        headers={"Range": f"bytes={start}-{end}", "User-Agent": USER_AGENT},
        timeout=180,
    )
    response.raise_for_status()
    if response.status_code != 206:
        raise RuntimeError(f"Server ignored byte range for {url}; refusing an unexpected full download")
    return response.content


def list_remote_zip(url: str, session: requests.Session | None = None) -> list[dict[str, object]]:
    """Read a remote ZIP central directory without downloading the entire archive."""
    session = session or requests.Session()
    head = session.head(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    head.raise_for_status()
    size = int(head.headers["Content-Length"])
    tail_start = max(0, size - 131_072)
    tail = _range_get(session, url, tail_start, size - 1)
    eocd_offset = tail.rfind(b"PK\x05\x06")
    if eocd_offset < 0:
        raise ValueError("ZIP end-of-central-directory record not found")
    eocd = struct.unpack_from("<4s4H2LH", tail, eocd_offset)
    central_size, central_offset = eocd[5], eocd[6]
    central = _range_get(session, url, central_offset, central_offset + central_size - 1)

    entries: list[dict[str, object]] = []
    offset = 0
    while offset < len(central):
        if central[offset:offset + 4] != b"PK\x01\x02":
            raise ValueError("Invalid ZIP central-directory entry")
        fields = struct.unpack_from("<4s6H3L5H2L", central, offset)
        name_length, extra_length, comment_length = fields[10:13]
        name_bytes = central[offset + 46:offset + 46 + name_length]
        entries.append({
            "name": name_bytes.decode("utf-8", errors="replace"),
            "compression_method": fields[4],
            "compressed_size": fields[8],
            "uncompressed_size": fields[9],
            "local_header_offset": fields[16],
        })
        offset += 46 + name_length + extra_length + comment_length
    return entries


def extract_remote_zip_member(
    url: str,
    member_name: str,
    session: requests.Session | None = None,
) -> bytes:
    """Download and inflate one member from a range-capable remote ZIP."""
    session = session or requests.Session()
    entry = next((item for item in list_remote_zip(url, session) if item["name"] == member_name), None)
    if entry is None:
        raise KeyError(f"ZIP member not found: {member_name}")
    local_offset = int(entry["local_header_offset"])
    local_header = _range_get(session, url, local_offset, local_offset + 29)
    local = struct.unpack("<4s5H3L2H", local_header)
    data_start = local_offset + 30 + local[9] + local[10]
    compressed_size = int(entry["compressed_size"])
    compressed = _range_get(session, url, data_start, data_start + compressed_size - 1)
    method = int(entry["compression_method"])
    if method == 0:
        return compressed
    if method == 8:
        return zlib.decompress(compressed, -zlib.MAX_WBITS)
    raise ValueError(f"Unsupported ZIP compression method: {method}")


def select_latest_mobile_member(entries: list[dict[str, object]]) -> str:
    candidates: list[tuple[int, int, str]] = []
    for entry in entries:
        match = re.fullmatch(r"Cobertura_(\d{4})_(\d{2})_Municipios\.csv", str(entry["name"]))
        if match:
            candidates.append((int(match.group(1)), int(match.group(2)), str(entry["name"])))
    if not candidates:
        raise ValueError("No municipal mobile-coverage member found")
    return max(candidates)[2]


def _find_column(frame: pd.DataFrame, *terms: str) -> str:
    normalized = {
        re.sub(
            r"[^a-z0-9]",
            "",
            unicodedata.normalize("NFKD", str(column)).encode("ascii", "ignore").decode().lower(),
        ): column
        for column in frame.columns
    }
    for normalized_name, original in normalized.items():
        if all(term in normalized_name for term in terms):
            return original
    raise KeyError(f"Could not find column containing {terms}")


def aggregate_mobile_coverage(raw: pd.DataFrame) -> pd.DataFrame:
    code = _find_column(raw, "codigo", "municipio")
    technology = _find_column(raw, "tecnologia")
    operator = _find_column(raw, "operadora")
    period = _find_column(raw, "periodo")
    residents = _find_column(raw, "moradores", "cobertos")
    filtered = raw.loc[
        raw[operator].astype(str).str.casefold().eq("todas")
        & raw[technology].astype(str).isin(["4G5G", "5G"])
    ].copy()
    filtered["ibge_municipio_7"] = (
        pd.to_numeric(filtered[code], errors="coerce").astype("Int64").astype("string")
    )
    filtered["coverage_pct"] = pd.to_numeric(filtered[residents], errors="coerce") * 100
    invalid = filtered["coverage_pct"].notna() & ~filtered["coverage_pct"].between(0, 100)
    if invalid.any():
        raise ValueError("Mobile resident coverage outside 0-100 after conversion")
    duplicate_audit = filtered.groupby(["ibge_municipio_7", technology])["coverage_pct"].agg(["min", "max"])
    if (duplicate_audit["max"] - duplicate_audit["min"]).fillna(0).gt(1e-9).any():
        raise ValueError("Conflicting duplicate aggregate mobile-coverage rows")
    deduplicated = filtered.drop_duplicates(["ibge_municipio_7", technology])
    values = deduplicated.pivot(index="ibge_municipio_7", columns=technology, values="coverage_pct")
    values = values.rename(columns={
        "4G5G": "mobile_4g5g_resident_coverage_pct",
        "5G": "mobile_5g_resident_coverage_pct",
    }).reset_index()
    parsed_period = pd.to_datetime(filtered[period], format="%m-%Y", errors="coerce").max()
    values["mobile_reference_period"] = parsed_period.strftime("%Y-%m")
    return values


def aggregate_fixed_broadband(raw: pd.DataFrame) -> pd.DataFrame:
    year = _find_column(raw, "ano")
    month = next(
        column for column in raw.columns
        if re.sub(
            r"[^a-z0-9]", "",
            unicodedata.normalize("NFKD", str(column)).encode("ascii", "ignore").decode().lower(),
        ) in {"mes", "ms"}
    )
    code = _find_column(raw, "codigo", "ibge")
    density = _find_column(raw, "densidade")
    try:
        level = _find_column(raw, "nivel", "geografico")
    except KeyError:
        level = _find_column(raw, "nivel")
    municipal = raw.loc[raw[level].astype(str).str.casefold().eq("municipio")].copy()
    municipal[year] = pd.to_numeric(municipal[year], errors="coerce")
    municipal[month] = pd.to_numeric(municipal[month], errors="coerce")
    latest = municipal[[year, month]].dropna().sort_values([year, month]).iloc[-1]
    municipal = municipal.loc[municipal[year].eq(latest[year]) & municipal[month].eq(latest[month])].copy()
    municipal["ibge_municipio_7"] = (
        pd.to_numeric(municipal[code], errors="coerce").astype("Int64").astype("string")
    )
    municipal["fixed_broadband_accesses_per_100_people"] = pd.to_numeric(municipal[density], errors="coerce")
    result = municipal[["ibge_municipio_7", "fixed_broadband_accesses_per_100_people"]]
    if result["ibge_municipio_7"].duplicated().any():
        raise ValueError("Duplicate municipality in latest fixed-broadband period")
    result = result.copy()
    result["fixed_broadband_reference_period"] = f"{int(latest[year]):04d}-{int(latest[month]):02d}"
    return result


def reconcile_universe(mobile: pd.DataFrame, fixed: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    official = universe.copy()
    official["ibge_municipio_7"] = official["ibge_municipio_7"].astype("string").str.replace(r"\.0$", "", regex=True)
    result = official.merge(mobile, on="ibge_municipio_7", how="left", validate="one_to_one")
    result = result.merge(fixed, on="ibge_municipio_7", how="left", validate="one_to_one")
    mobile_available = result["mobile_4g5g_resident_coverage_pct"].notna()
    fixed_available = result["fixed_broadband_accesses_per_100_people"].notna()
    result["anatel_data_status"] = "complete"
    result.loc[mobile_available & ~fixed_available, "anatel_data_status"] = "mobile_only"
    result.loc[~mobile_available & fixed_available, "anatel_data_status"] = "fixed_only"
    result.loc[~mobile_available & ~fixed_available, "anatel_data_status"] = "missing"
    result["anatel_interpretation"] = (
        "mobile coverage is model-estimated; fixed density counts accesses, not unique people or service quality"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch municipal Anatel connectivity proxies.")
    parser.add_argument("--universe", type=Path, default=Path("projects/ubs-healthcare-mapping/data/reference/ibge_municipality_universe.csv"))
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_anatel_connectivity.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("projects/ubs-healthcare-mapping/data/enriched/municipality_anatel_connectivity_metadata.json"))
    args = parser.parse_args()

    session = requests.Session()
    mobile_entries = list_remote_zip(MOBILE_URL, session)
    mobile_member = select_latest_mobile_member(mobile_entries)
    mobile_bytes = extract_remote_zip_member(MOBILE_URL, mobile_member, session)
    fixed_bytes = extract_remote_zip_member(FIXED_URL, FIXED_MEMBER, session)
    mobile_raw = pd.read_csv(io.BytesIO(mobile_bytes), sep=";", decimal=",", encoding="utf-8-sig")
    fixed_raw = pd.read_csv(io.BytesIO(fixed_bytes), sep=";", decimal=",", encoding="utf-8-sig")
    mobile = aggregate_mobile_coverage(mobile_raw)
    fixed = aggregate_fixed_broadband(fixed_raw)
    result = reconcile_universe(mobile, fixed, pd.read_csv(args.universe, dtype=str))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "Anatel open data",
        "mobile_url": MOBILE_URL,
        "mobile_member": mobile_member,
        "mobile_reference_period": mobile["mobile_reference_period"].iloc[0],
        "mobile_definition": "Resident coverage by the union of 4G/5G networks, aggregate operator 'Todas'.",
        "fixed_url": FIXED_URL,
        "fixed_member": FIXED_MEMBER,
        "fixed_reference_period": fixed["fixed_broadband_reference_period"].iloc[0],
        "fixed_definition": "Fixed-broadband accesses in service per 100 inhabitants.",
        "official_universe_rows": len(result),
        "complete_rows": int(result["anatel_data_status"].eq("complete").sum()),
        "important_limits": [
            "Mobile coverage is model-estimated and may differ from field conditions.",
            "Fixed density counts accesses, not unique people, speed, stability or affordability.",
            "Neither measure proves pharmacy-site connectivity or digital literacy.",
        ],
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Anatel connectivity for {len(result):,} official municipalities to {args.output}")


if __name__ == "__main__":
    main()
