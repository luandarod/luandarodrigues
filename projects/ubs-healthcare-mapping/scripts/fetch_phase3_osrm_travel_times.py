"""Attach OSRM travel times to a Phase 3 origin-destination matrix."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests


ROOT = Path("projects/ubs-healthcare-mapping")


def osrm_route_url(endpoint: str, profile: str, row: pd.Series) -> str:
    base = endpoint.rstrip("/")
    origin = f"{row['origin_longitude']},{row['origin_latitude']}"
    destination = f"{row['destination_longitude']},{row['destination_latitude']}"
    return (
        f"{base}/route/v1/{quote(str(profile), safe='')}/{origin};{destination}"
        "?overview=false&alternatives=false&steps=false"
    )


def parse_osrm_route(payload: dict) -> tuple[float, float, str]:
    if payload.get("code") != "Ok" or not payload.get("routes"):
        return pd.NA, pd.NA, f"osrm_{payload.get('code', 'missing_route')}"
    route = payload["routes"][0]
    return route["duration"] / 60, route["distance"] / 1000, "routed"


def route_matrix(frame: pd.DataFrame, endpoint: str, timeout: int = 30) -> pd.DataFrame:
    result = frame.copy()
    measured_at = datetime.now(UTC).isoformat()
    ready = result["routing_readiness_status"].eq("ready_for_network_routing")
    for index, row in result.loc[ready].iterrows():
        response = requests.get(
            osrm_route_url(endpoint, row["routing_profile"], row),
            timeout=timeout,
            headers={"User-Agent": "ubs-healthcare-mapping-phase3/0.1"},
        )
        response.raise_for_status()
        duration_minutes, distance_km, status = parse_osrm_route(response.json())
        result.loc[index, "travel_time_minutes"] = duration_minutes
        result.loc[index, "network_distance_km"] = distance_km
        result.loc[index, "routing_readiness_status"] = status
        result.loc[index, "routing_source"] = endpoint.rstrip("/")
        result.loc[index, "routing_measured_at_utc"] = measured_at
        result.loc[index, "academic_interpretation"] = "phase3_network_travel_time_proxy"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OSRM travel times for Phase 3 OD pairs.")
    parser.add_argument("--input", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_od_matrix.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_phase3_routing_od_matrix_routed.csv")
    parser.add_argument("--endpoint", default=os.environ.get("OSRM_BASE_URL"))
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    if not args.endpoint:
        raise SystemExit("Provide --endpoint or OSRM_BASE_URL. Prefer a local, versioned OSRM backend for papers.")
    frame = pd.read_csv(args.input, dtype={"ibge_municipio_7": str})
    routed = route_matrix(frame, args.endpoint, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    routed.to_csv(args.output, index=False)
    print(f"Saved routed Phase 3 matrix to {args.output}")


if __name__ == "__main__":
    main()
