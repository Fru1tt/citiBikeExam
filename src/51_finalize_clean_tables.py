"""
finalize_clean_tables_2025.py

Final cleanup pass on both output files based on column audit.

station_summary_2025.csv:
  - Remove: peak_hour_share (flat across bands, no finding), no_vehicle_band (income_band is the correct lens)
  - Result: 25 columns

station_daily_2025.csv:
  - Remove 12 station-level yearly averages that don't belong in a daily file
  - Add: is_weekend (boolean), daily_rides_per_dock (rides_started / capacity)
  - Result: 19 columns
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = PROJECT_ROOT / "data/processed/station_summary_2025.csv"
DAILY_PATH = PROJECT_ROOT / "data/processed/station_daily_2025.csv"

SUMMARY_DROP = [
    "peak_hour_share",   # flat across all income bands, no finding uses it
    "no_vehicle_band",   # income_band is the correct lens per section 4.7 conclusion
]

DAILY_DROP = [
    "start_station_name",     # raw uncleaned name, matched_station_name is canonical
    "month",                  # derivable from date
    "casual_rides_started",   # exactly rides_started - member_rides_started
    "nearest_subway_name",    # text label constant, belongs in summary only
    "rides_per_dock",         # misleading: yearly avg joined in, not daily utilization
    "stations_in_tract",      # unused in analysis
    "avg_weekday_rides",      # station-level yearly constant, no daily meaning
    "avg_weekend_rides",      # station-level yearly constant, no daily meaning
    "weekday_weekend_ratio",  # station-level yearly constant, no daily meaning
    "avg_trip_duration_min",  # station-level yearly constant, no daily meaning
    "peak_hour_share",        # station-level yearly constant, no daily meaning
    "ebike_share",            # station-level yearly constant, no daily meaning
]


def main() -> None:
    # --- Station summary ---
    print("Loading station summary...")
    summary = pd.read_csv(SUMMARY_PATH, dtype={"start_station_id": "string", "GEOID": "string"})
    print(f"  Before: {len(summary.columns)} columns")

    summary = summary.drop(columns=[c for c in SUMMARY_DROP if c in summary.columns])
    summary.to_csv(SUMMARY_PATH, index=False)
    print(f"  After: {len(summary.columns)} columns")
    print(f"  Removed: {SUMMARY_DROP}")
    print(f"  Saved: {SUMMARY_PATH}")

    print("\nFinal columns in station_summary_2025.csv:")
    for i, c in enumerate(summary.columns):
        print(f"  {i+1}. {c}")

    # --- Station day ---
    print("\nLoading station-day file (this may take a moment)...")
    daily = pd.read_csv(
        DAILY_PATH,
        dtype={"start_station_id": "string", "GEOID": "string"},
    )
    print(f"  Before: {len(daily.columns)} columns, {len(daily):,} rows")

    daily = daily.drop(columns=[c for c in DAILY_DROP if c in daily.columns])

    # Add is_weekend
    daily["date"] = pd.to_datetime(daily["date"])
    daily["is_weekend"] = (daily["date"].dt.dayofweek >= 5).astype(int)

    # Add daily_rides_per_dock (true daily utilization, not yearly average)
    daily["daily_rides_per_dock"] = (
        daily["rides_started"] / daily["capacity"]
    ).where(daily["capacity"] > 0).round(3)

    daily.to_csv(DAILY_PATH, index=False)
    print(f"  After: {len(daily.columns)} columns")
    print(f"  Removed: {DAILY_DROP}")
    print(f"  Added: is_weekend, daily_rides_per_dock")
    print(f"  Saved: {DAILY_PATH}")

    print("\nFinal columns in station_daily_2025.csv:")
    for i, c in enumerate(daily.columns):
        print(f"  {i+1}. {c}")

    print("\nDone.")


if __name__ == "__main__":
    main()
