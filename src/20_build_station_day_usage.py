from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRIPS_2025_PATH = PROJECT_ROOT / "data/raw/citibike/trips/2025"
STARTS_OUTPUT_PATH = PROJECT_ROOT / "data/processed/station_day_starts_2025.csv"
ENDS_OUTPUT_PATH = PROJECT_ROOT / "data/processed/station_day_ends_2025.csv"

USE_COLUMNS = [
    "started_at",
    "ended_at",
    "start_station_id",
    "start_station_name",
    "end_station_id",
    "end_station_name",
    "member_casual",
]

STARTS_COLUMNS = [
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
]

ENDS_COLUMNS = [
    "end_station_id",
    "end_station_name",
    "date",
    "year",
    "month",
    "rides_ended",
]

CHUNK_SIZE = 250_000


def list_trip_csv_files(trips_root: Path) -> list[Path]:
    csv_files: list[Path] = []
    month_folders = sorted([path for path in trips_root.iterdir() if path.is_dir()])

    for folder in month_folders:
        csv_files.extend(sorted(folder.glob("*.csv")))

    return csv_files


def process_trip_data(csv_files: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    # Running aggregated series indexed by (station_id, date).
    start_index = pd.MultiIndex.from_arrays(
        [pd.Index([], dtype="string"), pd.Index([], dtype="string")],
        names=["start_station_id", "date"],
    )
    end_index = pd.MultiIndex.from_arrays(
        [pd.Index([], dtype="string"), pd.Index([], dtype="string")],
        names=["end_station_id", "date"],
    )

    start_total = pd.Series(dtype="float64", index=start_index)
    start_member = pd.Series(dtype="float64", index=start_index)
    start_casual = pd.Series(dtype="float64", index=start_index)
    start_name = pd.Series(dtype="string", index=start_index)

    end_total = pd.Series(dtype="float64", index=end_index)
    end_name = pd.Series(dtype="string", index=end_index)

    total_trip_rows = 0
    excluded_missing_start_station_id = 0

    for file_index, csv_file in enumerate(csv_files, start=1):
        for chunk in pd.read_csv(csv_file, usecols=USE_COLUMNS, dtype="string", chunksize=CHUNK_SIZE):
            total_trip_rows += len(chunk)

            chunk["started_at"] = pd.to_datetime(chunk["started_at"], errors="coerce")
            chunk["ended_at"] = pd.to_datetime(chunk["ended_at"], errors="coerce")

            # STARTS: keep rows with non-empty start_station_id and valid started_at.
            start_station_id = chunk["start_station_id"].fillna("").astype("string").str.strip()
            missing_start_id_mask = start_station_id == ""
            excluded_missing_start_station_id += int(missing_start_id_mask.sum())

            starts = chunk.loc[~missing_start_id_mask].copy()
            starts["start_station_id"] = (
                starts["start_station_id"].astype("string").str.strip()
            )
            starts["start_station_name"] = (
                starts["start_station_name"].astype("string").str.strip()
            )
            starts.loc[starts["start_station_name"] == "", "start_station_name"] = pd.NA
            starts["date"] = starts["started_at"].dt.strftime("%Y-%m-%d")
            starts = starts.dropna(subset=["date"])

            start_groups = starts.groupby(["start_station_id", "date"], sort=False).size()
            start_total = start_total.add(start_groups, fill_value=0)

            start_name_groups = starts.groupby(
                ["start_station_id", "date"], sort=False
            )["start_station_name"].first()
            start_name = start_name.combine_first(start_name_groups)

            member_mask = starts["member_casual"].astype("string").str.strip().str.lower() == "member"
            casual_mask = starts["member_casual"].astype("string").str.strip().str.lower() == "casual"

            member_groups = (
                starts.loc[member_mask].groupby(["start_station_id", "date"], sort=False).size()
            )
            start_member = start_member.add(member_groups, fill_value=0)

            casual_groups = (
                starts.loc[casual_mask].groupby(["start_station_id", "date"], sort=False).size()
            )
            start_casual = start_casual.add(casual_groups, fill_value=0)

            # ENDS: supporting output with rides ended per station-day.
            ends = chunk.copy()
            ends["end_station_id"] = ends["end_station_id"].fillna("").astype("string").str.strip()
            ends = ends[ends["end_station_id"] != ""]
            ends["end_station_name"] = ends["end_station_name"].astype("string").str.strip()
            ends.loc[ends["end_station_name"] == "", "end_station_name"] = pd.NA
            ends["date"] = ends["ended_at"].dt.strftime("%Y-%m-%d")
            ends = ends.dropna(subset=["date"])

            end_groups = ends.groupby(["end_station_id", "date"], sort=False).size()
            end_total = end_total.add(end_groups, fill_value=0)

            end_name_groups = ends.groupby(
                ["end_station_id", "date"], sort=False
            )["end_station_name"].first()
            end_name = end_name.combine_first(end_name_groups)

        if file_index % 10 == 0 or file_index == len(csv_files):
            print(f"Processed files: {file_index}/{len(csv_files)}")

    starts_df = start_total.rename("rides_started").to_frame()
    starts_df["member_rides_started"] = start_member
    starts_df["casual_rides_started"] = start_casual
    starts_df["start_station_name"] = start_name
    starts_df = starts_df.reset_index()
    starts_df["rides_started"] = starts_df["rides_started"].fillna(0).astype("int64")
    starts_df["member_rides_started"] = starts_df["member_rides_started"].fillna(0).astype("int64")
    starts_df["casual_rides_started"] = starts_df["casual_rides_started"].fillna(0).astype("int64")
    starts_df["year"] = starts_df["date"].str.slice(0, 4).astype("int64")
    starts_df["month"] = starts_df["date"].str.slice(5, 7).astype("int64")
    starts_df["member_share_started"] = starts_df["member_rides_started"] / starts_df["rides_started"]
    starts_df["casual_share_started"] = starts_df["casual_rides_started"] / starts_df["rides_started"]
    starts_df = starts_df[STARTS_COLUMNS].sort_values(by=["date", "start_station_id"])

    ends_df = end_total.rename("rides_ended").to_frame()
    ends_df["end_station_name"] = end_name
    ends_df = ends_df.reset_index()
    ends_df["rides_ended"] = ends_df["rides_ended"].fillna(0).astype("int64")
    ends_df["year"] = ends_df["date"].str.slice(0, 4).astype("int64")
    ends_df["month"] = ends_df["date"].str.slice(5, 7).astype("int64")
    ends_df = ends_df[ENDS_COLUMNS].sort_values(by=["date", "end_station_id"])

    metrics = {
        "raw_csv_files_processed": len(csv_files),
        "total_trip_rows_processed": total_trip_rows,
        "excluded_missing_start_station_id": excluded_missing_start_station_id,
        "unique_start_stations": starts_df["start_station_id"].nunique(),
        "station_day_rows_starts": len(starts_df),
    }

    return starts_df, ends_df, metrics


def main() -> None:
    csv_files = list_trip_csv_files(TRIPS_2025_PATH)
    if not csv_files:
        raise ValueError(f"No trip CSV files found under {TRIPS_2025_PATH}")

    starts_df, ends_df, metrics = process_trip_data(csv_files)

    STARTS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    starts_df.to_csv(STARTS_OUTPUT_PATH, index=False)
    ends_df.to_csv(ENDS_OUTPUT_PATH, index=False)

    print(f"Raw CSV files processed: {metrics['raw_csv_files_processed']}")
    print(f"Total trip rows processed: {metrics['total_trip_rows_processed']}")
    print(
        "Rows excluded from starts (missing start_station_id): "
        f"{metrics['excluded_missing_start_station_id']}"
    )
    print(f"Unique start stations: {metrics['unique_start_stations']}")
    print(f"Station-day rows in starts dataset: {metrics['station_day_rows_starts']}")
    print(f"Final starts columns: {', '.join(STARTS_COLUMNS)}")


if __name__ == "__main__":
    main()
