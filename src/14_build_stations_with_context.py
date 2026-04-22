from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOOKUP_PATH = PROJECT_ROOT / "data/processed/station_tract_lookup.csv"
SOCIO_PATH = PROJECT_ROOT / "data/processed/nyc_tract_socioeconomic.csv"
SUBWAY_PATH = PROJECT_ROOT / "data/processed/station_subway_proximity.csv"
STATIONS_MASTER_PATH = PROJECT_ROOT / "data/processed/stations_master.csv"
SHAPEFILE_PATH = (
    PROJECT_ROOT
    / "data/raw/geography/nyc_tract_boundaries/tl_2024_36_tract/tl_2024_36_tract.shp"
)
OUTPUT_PATH = PROJECT_ROOT / "data/processed/stations_with_tract_context.csv"

SOCIO_COLUMNS = [
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]

SUBWAY_COLUMNS = [
    "nearest_subway_name",
    "nearest_subway_dist_m",
    "subway_count_500m",
]

FINAL_COLUMNS = [
    "station_id",
    "station_name",
    "latitude",
    "longitude",
    "capacity",
    "GEOID",
    *SOCIO_COLUMNS,
    "households_per_sqkm",
    *SUBWAY_COLUMNS,
]


def normalize_tract_geoid(series: pd.Series) -> pd.Series:
    """
    Keep only the 11-digit tract GEOID.
    This converts values like '1400000US36005000100' to '36005000100'.
    """
    text = series.astype("string").str.strip()
    return text.str.extract(r"(\d{11})$")[0]


def main() -> None:
    lookup = pd.read_csv(LOOKUP_PATH, dtype={"GEOID": "string"})
    socioeconomic = pd.read_csv(SOCIO_PATH, dtype={"GEOID": "string"})
    subway = pd.read_csv(SUBWAY_PATH, dtype={"station_id": "string"})
    stations_master = pd.read_csv(STATIONS_MASTER_PATH, dtype={"station_id": "string"})

    # Keep only stations that were already matched to a tract.
    matched = lookup[lookup["GEOID"].notna() & lookup["GEOID"].str.strip().ne("")].copy()
    matched["GEOID"] = normalize_tract_geoid(matched["GEOID"])
    matched_count_before_join = len(matched)

    # Normalize socioeconomic GEOID format to match station lookup GEOID.
    socioeconomic["GEOID"] = normalize_tract_geoid(socioeconomic["GEOID"])
    socioeconomic = socioeconomic[["GEOID", *SOCIO_COLUMNS]].copy()

    # Attach tract socioeconomic context to each matched station.
    stations_with_context = matched.merge(socioeconomic, on="GEOID", how="left")

    # Convert socioeconomic fields to numeric where appropriate.
    for column in SOCIO_COLUMNS:
        stations_with_context[column] = pd.to_numeric(
            stations_with_context[column], errors="coerce"
        )

    # Attach dock capacity from station master.
    stations_master["station_id"] = stations_master["station_id"].astype("string").str.strip()
    stations_with_context["station_id"] = stations_with_context["station_id"].astype("string").str.strip()
    stations_with_context = stations_with_context.merge(
        stations_master[["station_id", "capacity"]],
        on="station_id",
        how="left",
    )

    # Compute household density per km² from tract land area in the shapefile.
    # ALAND is in square metres; convert to km².
    tract_areas = gpd.read_file(SHAPEFILE_PATH)[["GEOID", "ALAND"]].copy()
    tract_areas["GEOID"] = tract_areas["GEOID"].astype("string").str.strip()
    tract_areas["tract_area_sqkm"] = pd.to_numeric(tract_areas["ALAND"], errors="coerce") / 1_000_000
    stations_with_context = stations_with_context.merge(
        tract_areas[["GEOID", "tract_area_sqkm"]],
        on="GEOID",
        how="left",
    )
    stations_with_context["households_per_sqkm"] = (
        stations_with_context["total_households"] / stations_with_context["tract_area_sqkm"]
    ).round(1)
    stations_with_context.drop(columns=["tract_area_sqkm"], inplace=True)

    # Attach subway proximity data to each station.
    subway["station_id"] = subway["station_id"].astype("string").str.strip()
    stations_with_context = stations_with_context.merge(
        subway[["station_id", *SUBWAY_COLUMNS]],
        on="station_id",
        how="left",
    )

    stations_with_context = stations_with_context[FINAL_COLUMNS]

    missing_socio_count = stations_with_context[SOCIO_COLUMNS].isna().any(axis=1).sum()
    missing_capacity = stations_with_context["capacity"].isna().sum()
    missing_density = stations_with_context["households_per_sqkm"].isna().sum()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stations_with_context.to_csv(OUTPUT_PATH, index=False)

    print(f"Matched stations before join: {matched_count_before_join}")
    print(f"Final row count after join: {len(stations_with_context)}")
    print(f"Stations missing socioeconomic values after join: {missing_socio_count}")
    print(f"Stations missing capacity: {missing_capacity}")
    print(f"Stations missing households_per_sqkm: {missing_density}")
    print(f"Final columns: {', '.join(FINAL_COLUMNS)}")


if __name__ == "__main__":
    main()
