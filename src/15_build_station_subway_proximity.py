from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIONS_PATH = PROJECT_ROOT / "data/processed/stations_master.csv"
SUBWAY_PATH = PROJECT_ROOT / "data/raw/subway/MTA_Subway_Stations.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/station_subway_proximity.csv"

# Radius of Earth in metres
EARTH_RADIUS_M = 6_371_000


def haversine_matrix(
    lat1: np.ndarray,
    lon1: np.ndarray,
    lat2: np.ndarray,
    lon2: np.ndarray,
) -> np.ndarray:
    """
    Compute pairwise haversine distances in metres between two sets of coordinates.

    Parameters
    ----------
    lat1, lon1 : arrays of shape (N,)  — Citi Bike stations
    lat2, lon2 : arrays of shape (M,)  — subway stations

    Returns
    -------
    distances : array of shape (N, M)
    """
    lat1_r = np.radians(lat1)[:, None]
    lon1_r = np.radians(lon1)[:, None]
    lat2_r = np.radians(lat2)[None, :]
    lon2_r = np.radians(lon2)[None, :]

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return EARTH_RADIUS_M * 2 * np.arcsin(np.sqrt(a))


def main() -> None:
    stations = pd.read_csv(STATIONS_PATH)
    subway = pd.read_csv(SUBWAY_PATH)

    # Drop subway rows missing coordinates.
    subway = subway.dropna(subset=["GTFS Latitude", "GTFS Longitude"]).copy()

    citi_lat = stations["latitude"].to_numpy(dtype=float)
    citi_lon = stations["longitude"].to_numpy(dtype=float)
    sub_lat = subway["GTFS Latitude"].to_numpy(dtype=float)
    sub_lon = subway["GTFS Longitude"].to_numpy(dtype=float)
    sub_names = subway["Stop Name"].to_numpy()

    print(f"Citi Bike stations: {len(stations)}")
    print(f"Subway stations: {len(subway)}")
    print("Computing pairwise haversine distances...")

    dist_matrix = haversine_matrix(citi_lat, citi_lon, sub_lat, sub_lon)

    nearest_idx = dist_matrix.argmin(axis=1)
    nearest_dist_m = dist_matrix[np.arange(len(stations)), nearest_idx]
    nearest_name = sub_names[nearest_idx]
    count_500m = (dist_matrix <= 500).sum(axis=1)

    result = pd.DataFrame(
        {
            "station_id": stations["station_id"],
            "nearest_subway_name": nearest_name,
            "nearest_subway_dist_m": np.round(nearest_dist_m, 1),
            "subway_count_500m": count_500m,
        }
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print(f"\nOutput rows: {len(result)}")
    print(f"Median nearest subway distance: {np.median(nearest_dist_m):.0f} m")
    print(f"Stations within 500 m of a subway: {(nearest_dist_m <= 500).sum()} "
          f"({(nearest_dist_m <= 500).mean() * 100:.1f}%)")
    print(f"Stations with 0 subway stations within 500 m: {(count_500m == 0).sum()}")
    print(f"Max subway count within 500 m: {count_500m.max()}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
