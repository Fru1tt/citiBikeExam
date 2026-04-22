from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_READY_PATH = (
    PROJECT_ROOT / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
)
SUMMARY_PATH = PROJECT_ROOT / "data/processed/station_summary_bands_2025.csv"
OUTPUT_SUMMARY_PATH = PROJECT_ROOT / "data/processed/station_summary_bands_2025.csv"
OUTPUT_ANALYSIS_PATH = (
    PROJECT_ROOT / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
)

COUNTY_TO_BOROUGH = {
    "005": "Bronx",
    "047": "Brooklyn",
    "061": "Manhattan",
    "081": "Queens",
    "085": "Staten Island",
}


def extract_borough(geoid_series: pd.Series) -> pd.Series:
    """Extract borough from 11-digit GEOID using county FIPS digits 3-5."""
    county = geoid_series.astype("string").str.strip().str[2:5]
    return county.map(COUNTY_TO_BOROUGH).fillna("Unknown")


def compute_weekday_weekend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-station weekday and weekend averages from the station-day file.
    Weekday = Monday to Friday. Weekend = Saturday and Sunday.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["is_weekend"] = df["date"].dt.dayofweek >= 5

    weekday = (
        df[~df["is_weekend"]]
        .groupby("start_station_id")
        .agg(
            avg_weekday_rides=("rides_started", "mean"),
            avg_weekday_member_share=("member_share_started", "mean"),
        )
        .reset_index()
    )

    weekend = (
        df[df["is_weekend"]]
        .groupby("start_station_id")
        .agg(
            avg_weekend_rides=("rides_started", "mean"),
            avg_weekend_member_share=("member_share_started", "mean"),
        )
        .reset_index()
    )

    result = weekday.merge(weekend, on="start_station_id", how="outer")

    # Weekday vs weekend ratio — how much busier is a station on weekdays?
    result["weekday_weekend_ratio"] = (
        result["avg_weekday_rides"] / result["avg_weekend_rides"]
    ).round(2)

    for col in ["avg_weekday_rides", "avg_weekend_rides",
                "avg_weekday_member_share", "avg_weekend_member_share"]:
        result[col] = result[col].round(3)

    return result


def main() -> None:
    print("Loading files...")
    summary = pd.read_csv(SUMMARY_PATH, dtype={"start_station_id": "string", "GEOID": "string"})
    analysis = pd.read_csv(
        ANALYSIS_READY_PATH,
        dtype={"start_station_id": "string", "GEOID": "string"},
    )

    # Borough from GEOID.
    print("Extracting borough from GEOID...")
    summary["borough"] = extract_borough(summary["GEOID"])
    analysis["borough"] = extract_borough(analysis["GEOID"])

    print("Borough distribution in station summary:")
    print(summary["borough"].value_counts().to_string())

    # Weekday / weekend split from station-day file.
    print("\nComputing weekday/weekend split...")
    weekday_weekend = compute_weekday_weekend(analysis)

    # Add to station summary.
    summary = summary.merge(
        weekday_weekend,
        on="start_station_id",
        how="left",
    )

    # Add weekday/weekend to the full analysis-ready file as station-level constants.
    analysis = analysis.merge(
        weekday_weekend[["start_station_id", "avg_weekday_rides",
                         "avg_weekend_rides", "weekday_weekend_ratio"]],
        on="start_station_id",
        how="left",
    )

    # Save both files.
    summary.to_csv(OUTPUT_SUMMARY_PATH, index=False)
    analysis.to_csv(OUTPUT_ANALYSIS_PATH, index=False)

    print(f"\nStation summary columns: {len(summary.columns)}")
    print(f"Analysis-ready file columns: {len(analysis.columns)}")

    # Quick diagnostic: weekday vs weekend by income band.
    print("\nWeekday vs weekend rides by income_band (mean):")
    print(
        summary.groupby("income_band")[
            ["avg_weekday_rides", "avg_weekend_rides", "weekday_weekend_ratio"]
        ]
        .mean()
        .round(2)
        .to_string()
    )

    print("\nBorough vs income_band crosstab (station counts):")
    print(pd.crosstab(summary["borough"], summary["income_band"]))


if __name__ == "__main__":
    main()
