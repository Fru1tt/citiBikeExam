from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_READY_PATH = (
    PROJECT_ROOT / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
)
STATION_SUMMARY_PATH = PROJECT_ROOT / "data/processed/station_summary_bands_2025.csv"
OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
)

ENRICH_COLUMNS = [
    "rides_per_dock",
    "stations_in_tract",
]


def main() -> None:
    df = pd.read_csv(ANALYSIS_READY_PATH, dtype={"start_station_id": "string", "GEOID": "string"})
    summary = pd.read_csv(STATION_SUMMARY_PATH, dtype={"start_station_id": "string"})

    original_rows = len(df)

    # Join station-level metrics back to the station-day file.
    enrichment = summary[["start_station_id", *ENRICH_COLUMNS]].copy()
    df = df.merge(enrichment, on="start_station_id", how="left")

    missing = df[ENRICH_COLUMNS].isna().sum()

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Rows in station-day file: {original_rows}")
    print(f"Rows after enrichment: {len(df)}")
    print(f"Missing values after join: {missing.to_dict()}")
    print(f"Columns now: {len(df.columns)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
