from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRIPS_2025_PATH = PROJECT_ROOT / "data/raw/citibike/trips/2025"
CONTEXT_PATH = PROJECT_ROOT / "data/processed/stations_with_tract_context.csv"

TRIP_REFERENCE_OUTPUT_PATH = PROJECT_ROOT / "data/processed/trip_start_station_reference_2025.csv"
DIAGNOSTIC_OUTPUT_PATH = PROJECT_ROOT / "data/processed/station_crosswalk_diagnostic_2025.csv"

USE_COLUMNS = ["start_station_id", "start_station_name", "start_lat", "start_lng"]
CHUNK_SIZE = 250_000

# Distance thresholds for confidence labels.
HIGH_CONFIDENCE_MAX_METERS = 200
MEDIUM_CONFIDENCE_MAX_METERS = 500
COORD_ONLY_MAX_METERS = 100


def normalize_station_name(name_series: pd.Series) -> pd.Series:
    return (
        name_series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


def haversine_distance_meters(
    lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """Distance from one point to many points, in meters."""
    earth_radius_m = 6_371_000

    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    return earth_radius_m * c


def list_trip_csv_files(root_path: Path) -> list[Path]:
    csv_files: list[Path] = []
    for folder in sorted(path for path in root_path.iterdir() if path.is_dir()):
        csv_files.extend(sorted(folder.glob("*.csv")))
    return csv_files


def build_trip_station_reference(csv_files: list[Path]) -> pd.DataFrame:
    """
    Build one row per unique trip start station id with:
    - most frequent station name
    - representative coordinates (mean)
    """
    name_index = pd.MultiIndex.from_arrays(
        [pd.Index([], dtype="string"), pd.Index([], dtype="string")],
        names=["start_station_id", "start_station_name"],
    )
    name_count_series = pd.Series(dtype="float64", index=name_index)
    coord_stats = pd.DataFrame(
        columns=["start_station_id", "lat_sum", "lat_count", "lng_sum", "lng_count"]
    )

    for file_index, csv_file in enumerate(csv_files, start=1):
        for chunk in pd.read_csv(csv_file, usecols=USE_COLUMNS, dtype="string", chunksize=CHUNK_SIZE):
            chunk["start_station_id"] = chunk["start_station_id"].astype("string").str.strip()
            chunk = chunk[chunk["start_station_id"].notna() & chunk["start_station_id"].ne("")]

            chunk["start_station_name"] = chunk["start_station_name"].astype("string").str.strip()
            chunk.loc[chunk["start_station_name"] == "", "start_station_name"] = pd.NA

            name_chunk = chunk.dropna(subset=["start_station_name"]).groupby(
                ["start_station_id", "start_station_name"], sort=False
            ).size()
            name_count_series = name_count_series.add(name_chunk, fill_value=0)

            chunk["start_lat"] = pd.to_numeric(chunk["start_lat"], errors="coerce")
            chunk["start_lng"] = pd.to_numeric(chunk["start_lng"], errors="coerce")

            coord_chunk = (
                chunk.groupby("start_station_id", sort=False)
                .agg(
                    lat_sum=("start_lat", "sum"),
                    lat_count=("start_lat", "count"),
                    lng_sum=("start_lng", "sum"),
                    lng_count=("start_lng", "count"),
                )
                .reset_index()
            )

            if coord_stats.empty:
                coord_stats = coord_chunk
            else:
                coord_stats = (
                    coord_stats.set_index("start_station_id")
                    .add(coord_chunk.set_index("start_station_id"), fill_value=0)
                    .reset_index()
                )

        if file_index % 10 == 0 or file_index == len(csv_files):
            print(f"Processed trip files: {file_index}/{len(csv_files)}")

    if name_count_series.empty:
        best_name = pd.DataFrame(columns=["start_station_id", "start_station_name"])
    else:
        best_name = (
            name_count_series.rename("name_count")
            .reset_index()
            .sort_values(["start_station_id", "name_count"], ascending=[True, False])
            .drop_duplicates(subset=["start_station_id"])
            [["start_station_id", "start_station_name"]]
        )

    trip_ref = coord_stats.merge(best_name, on="start_station_id", how="left")

    trip_ref["start_lat"] = np.where(
        trip_ref["lat_count"] > 0, trip_ref["lat_sum"] / trip_ref["lat_count"], np.nan
    )
    trip_ref["start_lng"] = np.where(
        trip_ref["lng_count"] > 0, trip_ref["lng_sum"] / trip_ref["lng_count"], np.nan
    )

    trip_ref = trip_ref[
        ["start_station_id", "start_station_name", "start_lat", "start_lng"]
    ].sort_values("start_station_id")

    return trip_ref


def build_diagnostic_crosswalk(
    trip_ref: pd.DataFrame, context: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    context = context.copy()
    context["name_norm"] = normalize_station_name(context["station_name"])

    context_by_name: dict[str, pd.DataFrame] = {
        name: group.reset_index(drop=True)
        for name, group in context.groupby("name_norm", dropna=True)
    }

    all_context_lat = context["latitude"].to_numpy()
    all_context_lng = context["longitude"].to_numpy()

    rows = []

    for trip_row in trip_ref.itertuples(index=False):
        start_station_id = trip_row.start_station_id
        start_station_name = trip_row.start_station_name
        start_lat = trip_row.start_lat
        start_lng = trip_row.start_lng

        name_norm = (
            pd.Series([start_station_name], dtype="string").pipe(normalize_station_name).iloc[0]
            if pd.notna(start_station_name)
            else pd.NA
        )

        matched_station_id = pd.NA
        matched_station_name = pd.NA
        matched_geoid = pd.NA
        match_method = "unmatched"
        confidence_note = "no suitable match"

        has_coords = pd.notna(start_lat) and pd.notna(start_lng)

        # Step 1: exact station-name candidates.
        if pd.notna(name_norm) and name_norm in context_by_name:
            candidates = context_by_name[name_norm]

            if has_coords:
                distances = haversine_distance_meters(
                    float(start_lat),
                    float(start_lng),
                    candidates["latitude"].to_numpy(),
                    candidates["longitude"].to_numpy(),
                )
                nearest_idx = int(np.argmin(distances))
                nearest_dist = float(distances[nearest_idx])
                nearest = candidates.iloc[nearest_idx]

                if nearest_dist <= HIGH_CONFIDENCE_MAX_METERS:
                    matched_station_id = nearest["station_id"]
                    matched_station_name = nearest["station_name"]
                    matched_geoid = nearest["GEOID"]
                    match_method = "exact_name_plus_nearest_coord"
                    confidence_note = f"high (distance {nearest_dist:.1f} m)"
                elif nearest_dist <= MEDIUM_CONFIDENCE_MAX_METERS:
                    matched_station_id = nearest["station_id"]
                    matched_station_name = nearest["station_name"]
                    matched_geoid = nearest["GEOID"]
                    match_method = "exact_name_plus_nearest_coord"
                    confidence_note = f"medium (distance {nearest_dist:.1f} m)"
                else:
                    match_method = "exact_name_but_coordinate_far"
                    confidence_note = f"unmatched (nearest {nearest_dist:.1f} m)"
            else:
                if len(candidates) == 1:
                    nearest = candidates.iloc[0]
                    matched_station_id = nearest["station_id"]
                    matched_station_name = nearest["station_name"]
                    matched_geoid = nearest["GEOID"]
                    match_method = "exact_name_no_coordinates"
                    confidence_note = "low (name only)"
                else:
                    match_method = "exact_name_multiple_no_coordinates"
                    confidence_note = "unmatched (ambiguous name)"

        # Step 2: optional coordinate-only fallback for very close points.
        elif has_coords and len(context) > 0:
            distances_all = haversine_distance_meters(
                float(start_lat), float(start_lng), all_context_lat, all_context_lng
            )
            nearest_idx = int(np.argmin(distances_all))
            nearest_dist = float(distances_all[nearest_idx])
            nearest = context.iloc[nearest_idx]

            if nearest_dist <= COORD_ONLY_MAX_METERS:
                matched_station_id = nearest["station_id"]
                matched_station_name = nearest["station_name"]
                matched_geoid = nearest["GEOID"]
                match_method = "coordinate_only_fallback"
                confidence_note = f"low (distance {nearest_dist:.1f} m)"
            else:
                match_method = "no_name_match_coordinate_far"
                confidence_note = f"unmatched (nearest {nearest_dist:.1f} m)"

        rows.append(
            {
                "start_station_id": start_station_id,
                "start_station_name": start_station_name,
                "start_lat": start_lat,
                "start_lng": start_lng,
                "matched_station_id": matched_station_id,
                "matched_station_name": matched_station_name,
                "GEOID": matched_geoid,
                "match_method": match_method,
                "confidence_note": confidence_note,
            }
        )

    diagnostic = pd.DataFrame(rows)

    summary = {
        "trip_unique_start_stations": len(diagnostic),
        "matched_total": int(diagnostic["matched_station_id"].notna().sum()),
        "matched_high": int(diagnostic["confidence_note"].str.startswith("high").sum()),
        "matched_medium": int(diagnostic["confidence_note"].str.startswith("medium").sum()),
        "matched_low": int(diagnostic["confidence_note"].str.startswith("low").sum()),
        "unmatched_total": int(diagnostic["matched_station_id"].isna().sum()),
        "exact_name_method_rows": int(
            diagnostic["match_method"].str.startswith("exact_name").sum()
        ),
        "coordinate_only_method_rows": int(
            (diagnostic["match_method"] == "coordinate_only_fallback").sum()
        ),
    }

    return diagnostic, summary


def main() -> None:
    trip_csv_files = list_trip_csv_files(TRIPS_2025_PATH)
    if not trip_csv_files:
        raise ValueError(f"No trip CSV files found under {TRIPS_2025_PATH}")

    trip_ref = build_trip_station_reference(trip_csv_files)
    TRIP_REFERENCE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    trip_ref.to_csv(TRIP_REFERENCE_OUTPUT_PATH, index=False)

    context = pd.read_csv(
        CONTEXT_PATH,
        dtype={"station_id": "string", "station_name": "string", "GEOID": "string"},
    )
    context["station_id"] = context["station_id"].astype("string").str.strip()
    context["station_name"] = context["station_name"].astype("string").str.strip()
    context["latitude"] = pd.to_numeric(context["latitude"], errors="coerce")
    context["longitude"] = pd.to_numeric(context["longitude"], errors="coerce")
    context = context.dropna(subset=["station_id", "station_name", "latitude", "longitude"])

    diagnostic, summary = build_diagnostic_crosswalk(trip_ref, context)
    diagnostic.to_csv(DIAGNOSTIC_OUTPUT_PATH, index=False)

    print(f"Trip station reference rows: {len(trip_ref)}")
    print(f"Station context rows available: {len(context)}")
    print(f"Total matched trip stations: {summary['matched_total']}")
    print(
        "Confident matches (high + medium): "
        f"{summary['matched_high'] + summary['matched_medium']}"
    )
    print(f"Low-confidence matches: {summary['matched_low']}")
    print(f"Unmatched trip stations: {summary['unmatched_total']}")
    print(f"Rows using exact-name methods: {summary['exact_name_method_rows']}")
    print(f"Rows using coordinate-only fallback: {summary['coordinate_only_method_rows']}")


if __name__ == "__main__":
    main()
