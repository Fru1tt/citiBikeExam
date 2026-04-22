from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRIPS_2025_PATH = PROJECT_ROOT / "data/raw/citibike/trips/2025"


def extract_month_key(name: str) -> str:
    match = re.search(r"(2025\d{2})", name)
    return match.group(1) if match else name


def read_csv_header(csv_path: Path) -> tuple[str, ...]:
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        return tuple(next(reader))


def read_csv_header_from_zip(zip_path: Path, member_name: str) -> tuple[str, ...]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        with archive.open(member_name) as raw_file:
            text_file = io.TextIOWrapper(raw_file, encoding="utf-8")
            reader = csv.reader(text_file)
            return tuple(next(reader))


def inspect_zip_package(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path, "r") as archive:
        csv_members = sorted(
            [name for name in archive.namelist() if name.lower().endswith(".csv")]
        )

    column_sets = [read_csv_header_from_zip(zip_path, name) for name in csv_members]
    unique_column_sets = {cols for cols in column_sets}

    return {
        "month": extract_month_key(zip_path.name),
        "container_name": zip_path.name,
        "container_type": "zip",
        "csv_files": csv_members,
        "column_sets": column_sets,
        "canonical_columns": list(column_sets[0]) if column_sets else [],
        "columns_consistent_within_package": len(unique_column_sets) <= 1,
    }


def inspect_folder_package(folder_path: Path) -> dict:
    csv_files = sorted(folder_path.glob("*.csv"))
    csv_names = [file.name for file in csv_files]
    column_sets = [read_csv_header(file) for file in csv_files]
    unique_column_sets = {cols for cols in column_sets}

    return {
        "month": extract_month_key(folder_path.name),
        "container_name": folder_path.name,
        "container_type": "folder",
        "csv_files": csv_names,
        "column_sets": column_sets,
        "canonical_columns": list(column_sets[0]) if column_sets else [],
        "columns_consistent_within_package": len(unique_column_sets) <= 1,
    }


def print_package_summary(package: dict) -> None:
    print(f"\n{package['month']} ({package['container_type']}: {package['container_name']})")
    print(f"CSV files found ({len(package['csv_files'])}):")
    for csv_name in package["csv_files"]:
        print(f"  - {csv_name}")

    if package["canonical_columns"]:
        print("Column names:")
        print("  " + ", ".join(package["canonical_columns"]))
    else:
        print("Column names: (none)")

    if not package["columns_consistent_within_package"]:
        print("  WARNING: Not all CSV files in this month have the same columns.")


def main() -> None:
    zip_files = sorted(TRIPS_2025_PATH.glob("*.zip"))
    month_folders = sorted([path for path in TRIPS_2025_PATH.iterdir() if path.is_dir()])

    print(f"Monthly zip files found: {len(zip_files)}")

    if zip_files:
        packages = [inspect_zip_package(zip_file) for zip_file in zip_files]
    else:
        print(
            "No zip files found. Inspecting extracted monthly folders instead: "
            f"{len(month_folders)}"
        )
        packages = [inspect_folder_package(folder) for folder in month_folders]

    if not packages:
        print("No monthly trip data packages found.")
        return

    packages = sorted(packages, key=lambda package: package["month"])

    for package in packages:
        print_package_summary(package)

    reference_columns = tuple(packages[0]["canonical_columns"])
    differing_months = []

    for package in packages:
        package_columns = tuple(package["canonical_columns"])
        if package_columns != reference_columns or not package[
            "columns_consistent_within_package"
        ]:
            differing_months.append(package["month"])

    print("\nSchema consistency across months:")
    if not differing_months:
        print("  CONSISTENT (all months have the same columns)")
    else:
        print("  NOT CONSISTENT")
        print("  Months that differ: " + ", ".join(differing_months))


if __name__ == "__main__":
    main()
