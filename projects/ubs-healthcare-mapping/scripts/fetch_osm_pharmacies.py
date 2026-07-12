"""Fetch georeferenced Brazilian pharmacies from OpenStreetMap Overpass."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
QUERY = """[out:json][timeout:900];
area["ISO3166-1"="BR"][admin_level=2]->.br;
nwr["amenity"="pharmacy"](area.br);
out center tags;
"""
USER_AGENT = "ubs-healthcare-mapping/1.0 (academic spatial accessibility study)"


def parse_overpass(payload: dict) -> tuple[pd.DataFrame, str | None]:
    rows = []
    for element in payload.get("elements", []):
        latitude = element.get("lat", element.get("center", {}).get("lat"))
        longitude = element.get("lon", element.get("center", {}).get("lon"))
        if latitude is None or longitude is None:
            continue
        tags = element.get("tags", {})
        rows.append({
            "osm_feature_id": f"{element.get('type')}/{element.get('id')}",
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "name": tags.get("name"),
            "operator": tags.get("operator"),
            "brand": tags.get("brand"),
            "latitude": pd.to_numeric(latitude, errors="coerce"),
            "longitude": pd.to_numeric(longitude, errors="coerce"),
            "source": "OpenStreetMap amenity=pharmacy",
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=[
            "osm_feature_id", "osm_type", "osm_id", "name", "operator", "brand",
            "latitude", "longitude", "source", "valid_coordinates",
        ])
    else:
        frame = frame.drop_duplicates("osm_feature_id").reset_index(drop=True)
        frame["valid_coordinates"] = (
            frame["latitude"].between(-34, 6) & frame["longitude"].between(-74, -28)
        )
    return frame, payload.get("osm3s", {}).get("timestamp_osm_base")


def fetch() -> tuple[dict, str]:
    errors = []
    for url in OVERPASS_URLS:
        try:
            response = requests.post(
                url,
                data=QUERY.encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT},
                timeout=960,
            )
            response.raise_for_status()
            return response.json(), url
        except (requests.RequestException, ValueError) as error:
            errors.append(f"{url}: {error}")
    raise RuntimeError("All Overpass endpoints failed: " + " | ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OSM pharmacies in Brazil.")
    parser.add_argument("--output", type=Path, default=Path("projects/ubs-healthcare-mapping/data/spatial/osm_pharmacies.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("projects/ubs-healthcare-mapping/data/spatial/osm_pharmacies_metadata.json"))
    args = parser.parse_args()
    payload, endpoint = fetch()
    frame, osm_timestamp = parse_overpass(payload)
    if frame.empty:
        raise RuntimeError("Overpass returned no georeferenced pharmacies")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "OpenStreetMap contributors via Overpass API",
        "license": "ODbL 1.0",
        "endpoint": endpoint,
        "query": QUERY,
        "osm_timestamp": osm_timestamp,
        "records": len(frame),
        "valid_coordinate_records": int(frame["valid_coordinates"].sum()),
        "important_limits": [
            "OSM completeness varies geographically and is not an official pharmacy registry.",
            "The layer is not equivalent to Programa Farmacia Popular accreditation.",
            "A mapped pharmacy may be closed, duplicated, inaccessible or operationally unsuitable.",
        ],
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(frame):,} georeferenced OSM pharmacies to {args.output}")


if __name__ == "__main__":
    main()
