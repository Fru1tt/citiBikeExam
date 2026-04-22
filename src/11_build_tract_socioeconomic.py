from __future__ import annotations

import csv
import json
from pathlib import Path


# Resolve all paths from project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INCOME_PATH = PROJECT_ROOT / "data/raw/census/acs_2024_5yr/acs_income_2024.json"
VEHICLE_PATH = PROJECT_ROOT / "data/raw/census/acs_2024_5yr/acs_vehicle_2024.json"
POVERTY_PATH = PROJECT_ROOT / "data/raw/census/acs_2024_5yr/acs_poverty_2024.json"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/nyc_tract_socioeconomic.csv"

# Census uses special placeholders for missing/unavailable values.
MISSING_PLACEHOLDERS = {"-666666666", "-666666666.0"}

FINAL_COLUMNS = [
    "GEOID",
    "tract_name",
    "median_household_income",
    "total_households",
    "households_no_vehicle",
    "poverty_rate",
    "no_vehicle_share",
]


def load_json_table(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Expected a non-empty list in {path}")

    headers = payload[0]
    rows = payload[1:]

    if not isinstance(headers, list):
        raise ValueError(f"Expected header row as first list item in {path}")

    return headers, rows


def clean_raw_value(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if text == "" or text in MISSING_PLACEHOLDERS:
        return None

    return text


def get_cell(row: list[str], index_map: dict[str, int], column_name: str) -> str | None:
    column_index = index_map[column_name]
    if column_index >= len(row):
        return None
    return row[column_index]


def parse_dataset(
    path: Path, value_mapping: dict[str, str]
) -> tuple[dict[str, dict], int, bool]:
    headers, rows = load_json_table(path)
    index_map = {column_name: idx for idx, column_name in enumerate(headers)}

    required_columns = ["GEO_ID", *value_mapping.keys()]
    missing_required = [column for column in required_columns if column not in index_map]
    if missing_required:
        raise ValueError(f"Missing required columns in {path}: {missing_required}")

    has_name_column = "NAME" in index_map
    records_by_geoid: dict[str, dict] = {}

    for row in rows:
        geoid = clean_raw_value(get_cell(row, index_map, "GEO_ID"))
        if geoid is None:
            continue

        record = {"GEOID": geoid}
        record["tract_name"] = (
            clean_raw_value(get_cell(row, index_map, "NAME")) if has_name_column else None
        )

        for raw_column, clean_column in value_mapping.items():
            record[clean_column] = clean_raw_value(get_cell(row, index_map, raw_column))

        records_by_geoid[geoid] = record

    return records_by_geoid, len(rows), has_name_column


def to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def merge_datasets(
    income_data: dict[str, dict],
    vehicle_data: dict[str, dict],
    poverty_data: dict[str, dict],
) -> list[dict]:
    shared_geoids = sorted(set(income_data) & set(vehicle_data) & set(poverty_data))
    merged_rows: list[dict] = []

    for geoid in shared_geoids:
        income_row = income_data[geoid]
        vehicle_row = vehicle_data[geoid]
        poverty_row = poverty_data[geoid]

        median_household_income = to_int(income_row.get("median_household_income"))
        total_households = to_int(vehicle_row.get("total_households"))
        households_no_vehicle = to_int(vehicle_row.get("households_no_vehicle"))
        poverty_rate = to_float(poverty_row.get("poverty_rate"))

        no_vehicle_share = None
        if total_households not in (None, 0) and households_no_vehicle is not None:
            no_vehicle_share = households_no_vehicle / total_households

        merged_rows.append(
            {
                "GEOID": geoid,
                "tract_name": first_non_empty(
                    income_row.get("tract_name"),
                    vehicle_row.get("tract_name"),
                    poverty_row.get("tract_name"),
                ),
                "median_household_income": median_household_income,
                "total_households": total_households,
                "households_no_vehicle": households_no_vehicle,
                "poverty_rate": poverty_rate,
                "no_vehicle_share": no_vehicle_share,
            }
        )

    return merged_rows


def count_missing(rows: list[dict], column_name: str) -> int:
    return sum(1 for row in rows if row.get(column_name) is None)


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FINAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    income_data, income_raw_rows, income_has_name = parse_dataset(
        INCOME_PATH, {"DP03_0062E": "median_household_income"}
    )
    vehicle_data, vehicle_raw_rows, vehicle_has_name = parse_dataset(
        VEHICLE_PATH,
        {
            "B08201_001E": "total_households",
            "B08201_002E": "households_no_vehicle",
        },
    )
    poverty_data, poverty_raw_rows, poverty_has_name = parse_dataset(
        POVERTY_PATH, {"S1701_C03_001E": "poverty_rate"}
    )

    merged_rows = merge_datasets(income_data, vehicle_data, poverty_data)
    write_csv(merged_rows, OUTPUT_PATH)

    print(f"Raw rows - income: {income_raw_rows}")
    print(f"Raw rows - vehicle: {vehicle_raw_rows}")
    print(f"Raw rows - poverty: {poverty_raw_rows}")
    print(f"Final merged rows: {len(merged_rows)}")
    print(f"Final columns: {', '.join(FINAL_COLUMNS)}")
    print(
        "Missing values - median_household_income: "
        f"{count_missing(merged_rows, 'median_household_income')}"
    )
    print(f"Missing values - poverty_rate: {count_missing(merged_rows, 'poverty_rate')}")
    print(f"Missing values - no_vehicle_share: {count_missing(merged_rows, 'no_vehicle_share')}")

    if not any([income_has_name, vehicle_has_name, poverty_has_name]):
        print("Note: NAME column is not present in these raw files; tract_name is blank.")


if __name__ == "__main__":
    main()
