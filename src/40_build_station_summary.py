from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
)
OUTPUT_PATH = PROJECT_ROOT / "data/processed/station_summary_bands_2025.csv"

# Context columns that are station-level constants (same value every day).
# Take the first occurrence when aggregating.
STATION_CONTEXT_COLUMNS = [
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
]

BAND_LABELS = {
    "income_band": ["Low", "Mid-Low", "Mid-High", "High"],
    "poverty_band": ["Low", "Moderate", "Elevated", "High"],
    "no_vehicle_band": ["Low", "Moderate", "High", "Very High"],
}


def compute_bands(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add quartile-based band columns for the three main socioeconomic variables.
    Quartiles are computed on the station-level distribution (one value per station),
    not on the full station-day rows, to avoid weighting busier stations more heavily.
    """
    for col, labels in [
        ("median_household_income", BAND_LABELS["income_band"]),
        ("poverty_rate", BAND_LABELS["poverty_band"]),
        ("no_vehicle_share", BAND_LABELS["no_vehicle_band"]),
    ]:
        band_col = col.replace("median_household_income", "income") \
                      .replace("poverty_rate", "poverty") \
                      .replace("no_vehicle_share", "no_vehicle") + "_band"

        df[band_col], bins = pd.qcut(
            df[col],
            q=4,
            labels=labels,
            retbins=True,
            duplicates="drop",
        )

        print(f"\n{band_col} cutpoints:")
        for i, label in enumerate(labels):
            lo = bins[i]
            hi = bins[i + 1]
            count = (df[band_col] == label).sum()
            print(f"  {label}: {lo:.2f} to {hi:.2f}  ({count} stations)")

    return df


def main() -> None:
    df = pd.read_csv(
        INPUT_PATH,
        dtype={"start_station_id": "string", "GEOID": "string"},
        parse_dates=["date"],
    )

    print(f"Input rows: {len(df)}")
    print(f"Unique stations: {df['start_station_id'].nunique()}")

    # Aggregate usage metrics to station level.
    usage = (
        df.groupby("start_station_id")
        .agg(
            total_rides_2025=("rides_started", "sum"),
            avg_daily_rides=("rides_started", "mean"),
            median_daily_rides=("rides_started", "median"),
            avg_member_rides=("member_rides_started", "mean"),
            avg_casual_rides=("casual_rides_started", "mean"),
            avg_member_share=("member_share_started", "mean"),
            active_days=("rides_started", lambda x: (x > 0).sum()),
        )
        .reset_index()
    )

    # Rides per active day (avoids penalising stations that were offline some days).
    usage["avg_rides_per_active_day"] = (
        usage["total_rides_2025"] / usage["active_days"]
    ).round(1)

    # Round float metrics.
    for col in ["avg_daily_rides", "avg_member_rides", "avg_casual_rides", "avg_member_share"]:
        usage[col] = usage[col].round(3)
    usage["median_daily_rides"] = usage["median_daily_rides"].round(1)

    # Take the first occurrence of station-level context columns.
    context = (
        df.groupby("start_station_id")[STATION_CONTEXT_COLUMNS]
        .first()
        .reset_index()
    )

    station_summary = usage.merge(context, on="start_station_id", how="left")

    # Rides per dock — utilization rate proxy.
    # Exclude stations with zero capacity to avoid division by zero.
    station_summary["rides_per_dock"] = (
        station_summary["avg_daily_rides"] / station_summary["capacity"]
    ).where(station_summary["capacity"] > 0).round(2)

    # Station count per census tract — how many stations share the same tract.
    tract_station_counts = (
        station_summary.groupby("GEOID")["start_station_id"]
        .count()
        .reset_index()
        .rename(columns={"start_station_id": "stations_in_tract"})
    )
    station_summary = station_summary.merge(tract_station_counts, on="GEOID", how="left")

    # Compute quartile bands on the station-level distribution.
    station_summary = compute_bands(station_summary)

    # Final column order.
    ordered_columns = [
        "start_station_id",
        "matched_station_name",
        "GEOID",
        "latitude",
        "longitude",
        "capacity",
        "total_rides_2025",
        "avg_daily_rides",
        "median_daily_rides",
        "avg_member_rides",
        "avg_casual_rides",
        "avg_member_share",
        "active_days",
        "avg_rides_per_active_day",
        "median_household_income",
        "poverty_rate",
        "no_vehicle_share",
        "households_per_sqkm",
        "nearest_subway_dist_m",
        "subway_count_500m",
        "nearest_subway_name",
        "rides_per_dock",
        "stations_in_tract",
        "income_band",
        "poverty_band",
        "no_vehicle_band",
        "total_households",
        "households_no_vehicle",
    ]
    station_summary = station_summary[ordered_columns]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    station_summary.to_csv(OUTPUT_PATH, index=False)

    print(f"\nOutput rows: {len(station_summary)}")
    print(f"Output columns: {len(station_summary.columns)}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nSummary stats:")
    print(f"  Total rides 2025: {station_summary['total_rides_2025'].sum():,.0f}")
    print(f"  Avg daily rides (mean across stations): {station_summary['avg_daily_rides'].mean():.1f}")
    print(f"  Avg member share (mean across stations): {station_summary['avg_member_share'].mean():.3f}")
    print(f"  Rides per dock — median: {station_summary['rides_per_dock'].median():.2f}, max: {station_summary['rides_per_dock'].max():.2f}")
    print(f"  Stations per tract — median: {station_summary['stations_in_tract'].median():.0f}, max: {station_summary['stations_in_tract'].max():.0f}")
    print(f"  Tracts with only 1 station: {(station_summary['stations_in_tract'] == 1).sum()}")


if __name__ == "__main__":
    main()
