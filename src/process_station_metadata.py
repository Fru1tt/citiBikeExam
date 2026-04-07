from __future__ import annotations

import csv
import json
from pathlib import Path


# Resolve paths relative to the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data/raw/citibike/stations/station_information.json"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/stations_master.csv"

# Keep only the core station metadata needed for a clean station table.
FINAL_COLUMNS = ["station_id", "station_name", "latitude", "longitude", "capacity"]


def load_station_records(input_path: Path) -> list[dict]:
    with input_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    stations = payload.get("data", {}).get("stations", [])
    if not isinstance(stations, list):
        raise ValueError("Expected station records at data.stations")

    return stations


def extract_station_rows(stations: list[dict]) -> list[dict]:
    rows: list[dict] = []

    for station in stations:
        rows.append(
            {
                "station_id": station.get("station_id"),
                "station_name": station.get("name"),
                "latitude": station.get("lat"),
                "longitude": station.get("lon"),
                "capacity": station.get("capacity"),
            }
        )

    return rows


def remove_exact_duplicates(rows: list[dict]) -> list[dict]:
    unique_rows: list[dict] = []
    seen: set[tuple] = set()

    for row in rows:
        key = tuple(row[column] for column in FINAL_COLUMNS)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    return unique_rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FINAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    stations = load_station_records(INPUT_PATH)
    raw_rows = extract_station_rows(stations)
    cleaned_rows = remove_exact_duplicates(raw_rows)
    write_csv(cleaned_rows, OUTPUT_PATH)

    print(f"Raw station records: {len(raw_rows)}")
    print(f"Cleaned station records: {len(cleaned_rows)}")
    print(f"Final columns: {', '.join(FINAL_COLUMNS)}")


if __name__ == "__main__":
    main()
