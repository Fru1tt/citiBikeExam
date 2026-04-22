from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STARTS_PATH = PROJECT_ROOT / "data/processed/station_day_starts_2025.csv"
CONTEXT_PATH = PROJECT_ROOT / "data/processed/stations_with_tract_context.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/master_station_day_context_2025.csv"

FINAL_COLUMNS = [
    "start_station_id",
    "start_station_name",
    "date",
    "year",
    "month",
    "rides_started",
    "member_rides_started",
    "casual_rides_started",
    "member_share_started",
    "casual_share_started",
    "station_name",
    "latitude",
    "longitude",
    "GEOID",
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]

CONTEXT_FIELDS = [
    "station_id",
    "station_name",
    "latitude",
    "longitude",
    "GEOID",
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]

CONTEXT_CHECK_COLUMNS = [
    "GEOID",
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]


def normalize_station_id(series: pd.Series) -> pd.Series:
    """Normalize join keys to clean strings for a stable station-ID join."""
    return series.astype("string").str.strip()


def main() -> None:
    starts = pd.read_csv(STARTS_PATH, dtype={"start_station_id": "string"})
    context = pd.read_csv(CONTEXT_PATH, dtype={"station_id": "string", "GEOID": "string"})

    starts_rows = len(starts)
    context_rows = len(context)

    starts["start_station_id"] = normalize_station_id(starts["start_station_id"])
    context["station_id"] = normalize_station_id(context["station_id"])

    # Keep one row per station_id in context table to avoid accidental row multiplication.
    context_unique = context[CONTEXT_FIELDS].drop_duplicates(subset=["station_id"]).copy()

    # Left join keeps all station-day rows and attaches context where station IDs match.
    master = starts.merge(
        context_unique,
        how="left",
        left_on="start_station_id",
        right_on="station_id",
    )

    master = master[FINAL_COLUMNS].copy()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(OUTPUT_PATH, index=False)

    missing_context_rows = int(master[CONTEXT_CHECK_COLUMNS].isna().any(axis=1).sum())

    print(f"Rows in station_day_starts_2025.csv: {starts_rows}")
    print(f"Rows in stations_with_tract_context.csv: {context_rows}")
    print(f"Final rows after join: {len(master)}")
    print(
        "Station-day rows with missing tract/socioeconomic context after join: "
        f"{missing_context_rows}"
    )
    print(f"Final columns: {', '.join(FINAL_COLUMNS)}")


if __name__ == "__main__":
    main()
