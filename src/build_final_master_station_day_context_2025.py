from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STARTS_PATH = PROJECT_ROOT / "data/processed/station_day_starts_2025.csv"
CROSSWALK_PATH = PROJECT_ROOT / "data/processed/approved_station_crosswalk_2025.csv"
CONTEXT_PATH = PROJECT_ROOT / "data/processed/stations_with_tract_context.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/final_master_station_day_context_2025.csv"

SOCIO_COLUMNS = [
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]

SUBWAY_COLUMNS = [
    "nearest_subway_name",
    "nearest_subway_dist_m",
    "subway_count_500m",
]

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
    "matched_station_id",
    "matched_station_name",
    "GEOID",
    "latitude",
    "longitude",
    "capacity",
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
    "households_per_sqkm",
    "nearest_subway_name",
    "nearest_subway_dist_m",
    "subway_count_500m",
    "match_method",
    "confidence_note",
]


def normalize_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def main() -> None:
    starts = pd.read_csv(STARTS_PATH, dtype={"start_station_id": "string"})
    crosswalk = pd.read_csv(
        CROSSWALK_PATH,
        dtype={
            "start_station_id": "string",
            "matched_station_id": "string",
            "GEOID": "string",
            "match_method": "string",
            "confidence_note": "string",
        },
    )
    context = pd.read_csv(
        CONTEXT_PATH,
        dtype={"station_id": "string", "GEOID": "string"},
    )

    starts_rows = len(starts)
    crosswalk_rows = len(crosswalk)

    # Normalize join keys explicitly before merging.
    starts["start_station_id"] = normalize_id(starts["start_station_id"])
    crosswalk["start_station_id"] = normalize_id(crosswalk["start_station_id"])
    crosswalk["matched_station_id"] = normalize_id(crosswalk["matched_station_id"])
    context["station_id"] = normalize_id(context["station_id"])

    crosswalk = crosswalk[
        [
            "start_station_id",
            "matched_station_id",
            "matched_station_name",
            "GEOID",
            "match_method",
            "confidence_note",
        ]
    ].copy()

    # Step 1: attach approved station crosswalk to station-day starts.
    station_day_with_matches = starts.merge(
        crosswalk,
        how="left",
        on="start_station_id",
        validate="m:1",
    )

    # Step 2: attach station context through matched_station_id.
    context_subset = context[
        [
            "station_id",
            "station_name",
            "latitude",
            "longitude",
            "capacity",
            "GEOID",
            *SOCIO_COLUMNS,
            "households_per_sqkm",
            *SUBWAY_COLUMNS,
        ]
    ].copy()

    final = station_day_with_matches.merge(
        context_subset,
        how="left",
        left_on="matched_station_id",
        right_on="station_id",
        validate="m:1",
        suffixes=("", "_context"),
    )

    # Keep crosswalk GEOID as primary, but backfill from station context if needed.
    final["GEOID"] = final["GEOID"].combine_first(final["GEOID_context"])
    final["matched_station_name"] = final["matched_station_name"].combine_first(
        final["station_name"]
    )

    final = final[FINAL_COLUMNS].copy()

    rows_retained_after_approved_matching = int(final["matched_station_id"].notna().sum())
    rows_excluded_no_approved_match = int(len(final) - rows_retained_after_approved_matching)
    rows_missing_socio_context = int(final[SOCIO_COLUMNS].isna().any(axis=1).sum())

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUTPUT_PATH, index=False)

    print(f"Rows in station_day_starts_2025.csv: {starts_rows}")
    print(f"Rows in approved_station_crosswalk_2025.csv: {crosswalk_rows}")
    print(f"Final rows after joins: {len(final)}")
    print(f"Station-day rows retained after approved matching: {rows_retained_after_approved_matching}")
    print(
        "Station-day rows excluded (no approved station match): "
        f"{rows_excluded_no_approved_match}"
    )
    print(f"Rows with missing socioeconomic context after final join: {rows_missing_socio_context}")
    print(f"Final columns: {', '.join(FINAL_COLUMNS)}")


if __name__ == "__main__":
    main()
