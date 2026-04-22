"""
build_final_clean_tables_2025.py

Produces two clean, analysis-ready output files:

    data/processed/station_summary_2025.csv
        One row per station. All redundant/unused columns removed.
        Adds: avg_trip_duration_min, peak_hour_share, ebike_share.
        Uses households_per_sqkm to contextualise no_vehicle findings.

    data/processed/station_daily_2025.csv
        One row per station per day. Redundant pipeline artefacts removed.
        Adds: avg_trip_duration_min, peak_hour_share, ebike_share
        as station-level constants joined back in.

Both files are self-contained for Power BI or any further analysis.
"""

from __future__ import annotations

from pathlib import Path

import glob
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_TRIPS_GLOB = str(PROJECT_ROOT / "data/raw/citibike/trips/2025/**/*.csv")
SUMMARY_PATH = PROJECT_ROOT / "data/processed/station_summary_bands_2025.csv"
ANALYSIS_PATH = PROJECT_ROOT / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
OUTPUT_SUMMARY = PROJECT_ROOT / "data/processed/station_summary_2025.csv"
OUTPUT_ANALYSIS = PROJECT_ROOT / "data/processed/station_daily_2025.csv"

# Columns to drop from station summary (redundant or unused)
SUMMARY_DROP = [
    "median_daily_rides",        # avg_daily_rides used consistently
    "avg_member_rides",          # raw count — avg_member_share is used
    "avg_casual_rides",          # raw count — avg_member_share is used
    "active_days",               # QA column, not used in analysis
    "avg_rides_per_active_day",  # avg_daily_rides used consistently
    "total_households",          # raw count behind no_vehicle_share
    "households_no_vehicle",     # raw count behind no_vehicle_share
    "avg_weekday_member_share",  # not used in analysis or charts
    "avg_weekend_member_share",  # not used in analysis or charts
    "stations_in_tract",         # computed but not used in findings
]

# Columns to drop from station-day file (artefacts and redundancies)
ANALYSIS_DROP = [
    "matched_station_id",   # duplicate of start_station_id
    "match_method",         # pipeline QA artefact
    "confidence_note",      # pipeline QA artefact
    "casual_share_started", # exactly 1 - member_share_started
    "total_households",     # raw count behind no_vehicle_share
    "households_no_vehicle",# raw count behind no_vehicle_share
    "year",                 # every row is 2025
]

PEAK_HOURS = range(7, 10)  # 07:00 – 09:59  (morning commute)
MAX_TRIP_MINUTES = 180     # cap outliers at 3 hours


def load_raw_trips() -> pd.DataFrame:
    """Load all raw trip CSVs, keeping only columns needed for aggregation."""
    files = sorted(glob.glob(RAW_TRIPS_GLOB, recursive=True))
    print(f"Found {len(files)} raw trip files — loading...")

    chunks = []
    for f in files:
        df = pd.read_csv(
            f,
            usecols=["started_at", "ended_at", "start_station_id", "rideable_type"],
            dtype={"start_station_id": "string"},
        )
        chunks.append(df)

    trips = pd.concat(chunks, ignore_index=True)
    print(f"Total raw trips loaded: {len(trips):,}")
    return trips


def compute_trip_metrics(trips: pd.DataFrame) -> pd.DataFrame:
    """
    Per-station aggregations from raw trip data:
      - avg_trip_duration_min  : average trip length in minutes (outliers capped)
      - peak_hour_share        : share of rides starting between 7–9am
      - ebike_share            : share of rides on electric bikes
    """
    trips = trips.copy()

    trips["started_at"] = pd.to_datetime(trips["started_at"], errors="coerce")
    trips["ended_at"] = pd.to_datetime(trips["ended_at"], errors="coerce")

    # Duration in minutes, cap at MAX_TRIP_MINUTES
    trips["duration_min"] = (
        (trips["ended_at"] - trips["started_at"]).dt.total_seconds() / 60
    ).clip(upper=MAX_TRIP_MINUTES)

    trips["is_peak"] = trips["started_at"].dt.hour.isin(PEAK_HOURS)
    trips["is_ebike"] = trips["rideable_type"] == "electric_bike"

    # Drop rows with missing station id or invalid duration
    trips = trips.dropna(subset=["start_station_id", "duration_min"])
    trips = trips[trips["duration_min"] > 0]

    agg = (
        trips.groupby("start_station_id")
        .agg(
            avg_trip_duration_min=("duration_min", "mean"),
            peak_hour_share=("is_peak", "mean"),
            ebike_share=("is_ebike", "mean"),
        )
        .reset_index()
    )

    agg["avg_trip_duration_min"] = agg["avg_trip_duration_min"].round(2)
    agg["peak_hour_share"] = agg["peak_hour_share"].round(3)
    agg["ebike_share"] = agg["ebike_share"].round(3)

    return agg


def main() -> None:
    # --- Load and compute trip-level metrics ---
    trips = load_raw_trips()
    trip_metrics = compute_trip_metrics(trips)
    del trips  # free memory

    print(f"\nTrip metrics computed for {len(trip_metrics):,} stations")
    print("\nSample trip metrics by income band (will show after join):")

    # --- Clean station summary ---
    print("\nLoading station summary...")
    summary = pd.read_csv(SUMMARY_PATH, dtype={"start_station_id": "string", "GEOID": "string"})

    summary = summary.drop(columns=[c for c in SUMMARY_DROP if c in summary.columns])
    summary = summary.merge(trip_metrics, on="start_station_id", how="left")

    # Final column order for summary
    summary_cols = [
        "start_station_id",
        "matched_station_name",
        "borough",
        "GEOID",
        "latitude",
        "longitude",
        "capacity",
        "total_rides_2025",
        "avg_daily_rides",
        "avg_member_share",
        "avg_trip_duration_min",
        "peak_hour_share",
        "ebike_share",
        "avg_weekday_rides",
        "avg_weekend_rides",
        "weekday_weekend_ratio",
        "rides_per_dock",
        "median_household_income",
        "poverty_rate",
        "no_vehicle_share",
        "households_per_sqkm",
        "nearest_subway_dist_m",
        "subway_count_500m",
        "nearest_subway_name",
        "income_band",
        "poverty_band",
        "no_vehicle_band",
    ]
    summary = summary[[c for c in summary_cols if c in summary.columns]]
    summary.to_csv(OUTPUT_SUMMARY, index=False)
    print(f"\nStation summary saved: {len(summary)} rows, {len(summary.columns)} columns")
    print(f"  -> {OUTPUT_SUMMARY}")

    # Diagnostic
    print("\nAvg trip duration by income band:")
    print(summary.groupby("income_band")["avg_trip_duration_min"].mean().round(2).to_string())
    print("\nPeak hour share by income band:")
    print(summary.groupby("income_band")["peak_hour_share"].mean().round(3).to_string())
    print("\nEbike share by income band:")
    print(summary.groupby("income_band")["ebike_share"].mean().round(3).to_string())

    # --- Clean station-day file ---
    print("\nLoading station-day file (this may take a moment)...")
    analysis = pd.read_csv(
        ANALYSIS_PATH,
        dtype={"start_station_id": "string", "GEOID": "string"},
    )

    analysis = analysis.drop(columns=[c for c in ANALYSIS_DROP if c in analysis.columns])

    # Join station-level trip metrics as constants
    analysis = analysis.merge(
        trip_metrics[["start_station_id", "avg_trip_duration_min", "peak_hour_share", "ebike_share"]],
        on="start_station_id",
        how="left",
    )

    analysis.to_csv(OUTPUT_ANALYSIS, index=False)
    print(f"\nStation-day file saved: {len(analysis):,} rows, {len(analysis.columns)} columns")
    print(f"  -> {OUTPUT_ANALYSIS}")

    print("\nDone.")


if __name__ == "__main__":
    main()
