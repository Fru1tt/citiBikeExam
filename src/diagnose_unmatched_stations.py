from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOOKUP_PATH = PROJECT_ROOT / "data/processed/station_tract_lookup.csv"
STATIONS_PATH = PROJECT_ROOT / "data/processed/stations_master.csv"
TRACTS_PATH = (
    PROJECT_ROOT
    / "data/raw/geography/nyc_tract_boundaries/tl_2024_36_tract/tl_2024_36_tract.shp"
)
OUTPUT_PATH = PROJECT_ROOT / "data/processed/unmatched_stations_diagnostic.csv"

NYC_COUNTY_CODES = ["005", "047", "061", "081", "085"]
DIAGNOSTIC_COLUMNS = ["station_id", "station_name", "latitude", "longitude", "GEOID"]


def load_unmatched_lookup_rows(lookup_path: Path, stations_path: Path) -> pd.DataFrame:
    lookup = pd.read_csv(lookup_path)
    stations = pd.read_csv(stations_path)[["station_id", "station_name", "latitude", "longitude"]]

    # Unmatched means GEOID is missing or blank.
    unmatched = lookup[
        lookup["GEOID"].isna() | lookup["GEOID"].astype(str).str.strip().eq("")
    ].copy()

    # Keep the latest station metadata columns from stations_master.
    unmatched = unmatched[["station_id", "GEOID"]].merge(
        stations, on="station_id", how="left"
    )

    unmatched["latitude"] = pd.to_numeric(unmatched["latitude"], errors="coerce")
    unmatched["longitude"] = pd.to_numeric(unmatched["longitude"], errors="coerce")

    return unmatched[DIAGNOSTIC_COLUMNS]


def nyc_tract_bounds_wgs84(tracts_path: Path) -> tuple[float, float, float, float]:
    tracts = gpd.read_file(tracts_path)
    nyc_tracts = tracts[tracts["COUNTYFP"].isin(NYC_COUNTY_CODES)].copy()
    nyc_tracts = nyc_tracts.to_crs("EPSG:4326")
    return tuple(nyc_tracts.total_bounds)


def main() -> None:
    unmatched = load_unmatched_lookup_rows(LOOKUP_PATH, STATIONS_PATH)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    unmatched.to_csv(OUTPUT_PATH, index=False)

    total_unmatched = len(unmatched)
    min_lat = unmatched["latitude"].min()
    max_lat = unmatched["latitude"].max()
    min_lon = unmatched["longitude"].min()
    max_lon = unmatched["longitude"].max()

    # Extent check only: are unmatched points outside overall NYC tract bounding box?
    minx, miny, maxx, maxy = nyc_tract_bounds_wgs84(TRACTS_PATH)
    outside_extent_mask = (
        (unmatched["longitude"] < minx)
        | (unmatched["longitude"] > maxx)
        | (unmatched["latitude"] < miny)
        | (unmatched["latitude"] > maxy)
    )
    outside_extent_count = int(outside_extent_mask.sum())

    print(f"Total unmatched stations: {total_unmatched}")
    print(f"Latitude range: {min_lat} to {max_lat}")
    print(f"Longitude range: {min_lon} to {max_lon}")
    print("Sample unmatched stations (name, latitude, longitude):")
    print(
        unmatched[["station_name", "latitude", "longitude"]]
        .head(8)
        .to_string(index=False)
    )
    print(
        "Unmatched stations outside overall NYC tract extent: "
        f"{outside_extent_count} of {total_unmatched}"
    )
    print(f"Final columns: {', '.join(DIAGNOSTIC_COLUMNS)}")


if __name__ == "__main__":
    main()
