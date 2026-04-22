from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = PROJECT_ROOT / "data/processed/final_master_station_day_context_2025.csv"
BY_STATION_OUTPUT_PATH = PROJECT_ROOT / "data/processed/missing_socio_by_station_2025.csv"
BY_GEOID_OUTPUT_PATH = PROJECT_ROOT / "data/processed/missing_socio_by_geoid_2025.csv"

SOCIO_COLUMNS = [
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]


def main() -> None:
    df = pd.read_csv(
        MASTER_PATH,
        usecols=["start_station_id", "start_station_name", "GEOID", *SOCIO_COLUMNS],
        dtype={"start_station_id": "string", "start_station_name": "string", "GEOID": "string"},
    )

    # Numeric conversion keeps non-numeric noise from breaking missingness checks.
    for col in SOCIO_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    missing_any_mask = df[SOCIO_COLUMNS].isna().any(axis=1)
    missing_rows = df[missing_any_mask].copy()

    field_missing_counts = {col: int(df[col].isna().sum()) for col in SOCIO_COLUMNS}
    total_rows = len(df)

    # Station-level diagnostic table.
    station_summary = (
        df.assign(missing_socio=missing_any_mask.astype("int64"))
        .groupby(["start_station_id", "start_station_name"], dropna=False)
        .agg(total_rows=("missing_socio", "size"), missing_rows=("missing_socio", "sum"))
        .reset_index()
    )
    station_summary["missing_share"] = station_summary["missing_rows"] / station_summary["total_rows"]
    station_summary = station_summary.sort_values(
        ["missing_rows", "missing_share"], ascending=[False, False]
    )

    # GEOID-level diagnostic table.
    geoid_summary = (
        df.assign(missing_socio=missing_any_mask.astype("int64"))
        .groupby("GEOID", dropna=False)
        .agg(total_rows=("missing_socio", "size"), missing_rows=("missing_socio", "sum"))
        .reset_index()
    )
    geoid_summary["missing_share"] = geoid_summary["missing_rows"] / geoid_summary["total_rows"]
    geoid_summary = geoid_summary.sort_values(
        ["missing_rows", "missing_share"], ascending=[False, False]
    )

    BY_STATION_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    station_summary.to_csv(BY_STATION_OUTPUT_PATH, index=False)
    geoid_summary.to_csv(BY_GEOID_OUTPUT_PATH, index=False)

    unique_stations_affected = missing_rows["start_station_id"].nunique(dropna=True)
    unique_geoids_affected = missing_rows["GEOID"].nunique(dropna=True)

    print(f"Total rows in master dataset: {total_rows}")
    print("Missing values by socioeconomic field:")
    for col in SOCIO_COLUMNS:
        missing_count = field_missing_counts[col]
        missing_pct = (missing_count / total_rows) * 100 if total_rows else 0
        print(f"  {col}: {missing_count} ({missing_pct:.2f}%)")

    print(f"Unique stations affected by missing socioeconomic values: {unique_stations_affected}")
    print(f"Unique GEOIDs affected by missing socioeconomic values: {unique_geoids_affected}")

    print("Top stations by missing rows:")
    print(
        station_summary.loc[:, ["start_station_id", "start_station_name", "missing_rows"]]
        .head(10)
        .to_string(index=False)
    )

    print("Top GEOIDs by missing rows:")
    print(
        geoid_summary.loc[:, ["GEOID", "missing_rows"]]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
