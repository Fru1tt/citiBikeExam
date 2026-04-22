from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


# Resolve all paths from project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIONS_PATH = PROJECT_ROOT / "data/processed/stations_master.csv"
TRACTS_PATH = (
    PROJECT_ROOT
    / "data/raw/geography/nyc_tract_boundaries/tl_2024_36_tract/tl_2024_36_tract.shp"
)
OUTPUT_PATH = PROJECT_ROOT / "data/processed/station_tract_lookup.csv"

# NYC county FIPS codes: Bronx, Kings, New York, Queens, Richmond.
NYC_COUNTY_CODES = ["005", "047", "061", "081", "085"]

FINAL_COLUMNS = ["station_id", "station_name", "latitude", "longitude", "GEOID"]


def load_stations(path: Path) -> pd.DataFrame:
    stations = pd.read_csv(path)

    required_columns = {"station_id", "station_name", "latitude", "longitude"}
    missing_columns = required_columns - set(stations.columns)
    if missing_columns:
        raise ValueError(f"Missing required station columns: {sorted(missing_columns)}")

    return stations


def load_nyc_tracts(path: Path) -> gpd.GeoDataFrame:
    tracts = gpd.read_file(path)

    required_columns = {"GEOID", "COUNTYFP", "geometry"}
    missing_columns = required_columns - set(tracts.columns)
    if missing_columns:
        raise ValueError(f"Missing required tract columns: {sorted(missing_columns)}")

    nyc_tracts = tracts[tracts["COUNTYFP"].isin(NYC_COUNTY_CODES)].copy()
    return nyc_tracts[["GEOID", "COUNTYFP", "geometry"]]


def build_station_points(stations: pd.DataFrame, target_crs: str) -> gpd.GeoDataFrame:
    # Station coordinates are longitude/latitude.
    points = gpd.GeoDataFrame(
        stations.copy(),
        geometry=gpd.points_from_xy(stations["longitude"], stations["latitude"]),
        crs="EPSG:4326",
    )

    return points.to_crs(target_crs)


def main() -> None:
    stations = load_stations(STATIONS_PATH)
    nyc_tracts = load_nyc_tracts(TRACTS_PATH)

    station_points = build_station_points(stations, str(nyc_tracts.crs))

    # Left spatial join keeps all stations and adds tract GEOID where matched.
    joined = gpd.sjoin(
        station_points,
        nyc_tracts[["GEOID", "geometry"]],
        how="left",
        predicate="within",
    )

    lookup = joined[FINAL_COLUMNS].copy()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(OUTPUT_PATH, index=False)

    matched_count = lookup["GEOID"].notna().sum()
    unmatched_count = lookup["GEOID"].isna().sum()

    print(f"Stations in stations_master.csv: {len(stations)}")
    print(f"NYC tract polygons used: {len(nyc_tracts)}")
    print(f"Stations matched to tract: {matched_count}")
    print(f"Unmatched stations: {unmatched_count}")
    print(f"Final columns: {', '.join(FINAL_COLUMNS)}")


if __name__ == "__main__":
    main()
