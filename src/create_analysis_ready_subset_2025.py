from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data/processed/final_master_station_day_context_2025.csv"
OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/final_master_station_day_context_analysis_ready_2025.csv"
)

REQUIRED_NON_MISSING = [
    "GEOID",
    "median_household_income",
    "poverty_rate",
    "no_vehicle_share",
]


def main() -> None:
    df = pd.read_csv(INPUT_PATH, dtype={"GEOID": "string"})
    original_rows = len(df)

    # Treat blank GEOID values as missing.
    df["GEOID"] = df["GEOID"].astype("string").str.strip()

    # Ensure numeric fields are properly interpreted before missingness filtering.
    for col in ["median_household_income", "poverty_rate", "no_vehicle_share"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    keep_mask = (
        df["GEOID"].notna()
        & df["GEOID"].ne("")
        & df["median_household_income"].notna()
        & df["poverty_rate"].notna()
        & df["no_vehicle_share"].notna()
    )

    analysis_ready = df.loc[keep_mask].copy()
    retained_rows = len(analysis_ready)
    excluded_rows = original_rows - retained_rows
    retained_pct = (retained_rows / original_rows) * 100 if original_rows else 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    analysis_ready.to_csv(OUTPUT_PATH, index=False)

    print(f"Rows in original master dataset: {original_rows}")
    print(f"Rows in analysis-ready dataset: {retained_rows}")
    print(f"Rows excluded: {excluded_rows}")
    print(f"Percentage retained: {retained_pct:.2f}%")
    print(f"Final columns: {', '.join(analysis_ready.columns)}")


if __name__ == "__main__":
    main()
