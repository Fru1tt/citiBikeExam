from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC_PATH = PROJECT_ROOT / "data/processed/station_crosswalk_diagnostic_2025.csv"

LOW_CONFIDENCE_OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/low_confidence_station_matches_2025.csv"
)
UNMATCHED_OUTPUT_PATH = PROJECT_ROOT / "data/processed/unmatched_trip_stations_2025.csv"
APPROVED_OUTPUT_PATH = PROJECT_ROOT / "data/processed/approved_station_crosswalk_2025.csv"

APPROVED_COLUMNS = [
    "start_station_id",
    "start_station_name",
    "matched_station_id",
    "matched_station_name",
    "GEOID",
    "match_method",
    "confidence_note",
]


def main() -> None:
    diagnostic = pd.read_csv(
        DIAGNOSTIC_PATH,
        dtype={
            "start_station_id": "string",
            "start_station_name": "string",
            "matched_station_id": "string",
            "matched_station_name": "string",
            "GEOID": "string",
            "match_method": "string",
            "confidence_note": "string",
        },
    )

    diagnostic["confidence_note"] = diagnostic["confidence_note"].astype("string").str.strip()
    diagnostic["matched_station_id"] = diagnostic["matched_station_id"].astype("string").str.strip()

    is_high = diagnostic["confidence_note"].str.startswith("high", na=False)
    is_medium = diagnostic["confidence_note"].str.startswith("medium", na=False)
    is_low = diagnostic["confidence_note"].str.startswith("low", na=False)
    is_unmatched = diagnostic["matched_station_id"].isna() | diagnostic["confidence_note"].str.startswith(
        "unmatched", na=False
    )

    low_confidence = diagnostic.loc[is_low].copy()
    unmatched = diagnostic.loc[is_unmatched].copy()

    approved = diagnostic.loc[(is_high | is_medium) & ~is_unmatched, APPROVED_COLUMNS].copy()

    LOW_CONFIDENCE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    low_confidence.to_csv(LOW_CONFIDENCE_OUTPUT_PATH, index=False)
    unmatched.to_csv(UNMATCHED_OUTPUT_PATH, index=False)
    approved.to_csv(APPROVED_OUTPUT_PATH, index=False)

    print(f"High-confidence matches: {int(is_high.sum())}")
    print(f"Medium-confidence matches: {int(is_medium.sum())}")
    print(f"Low-confidence matches: {int(is_low.sum())}")
    print(f"Unmatched stations: {int(is_unmatched.sum())}")


if __name__ == "__main__":
    main()
