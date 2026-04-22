"""Data loader for the CitiBike dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "station_summary_2025.csv"


@st.cache_data(show_spinner=False)
def load_stations() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["income_band"] = df["income_band"].astype(str)
    df["borough"] = df["borough"].astype(str)
    return df


def apply_filters(
    df: pd.DataFrame,
    boroughs: list[str] | None = None,
    income_bands: list[str] | None = None,
    subway_filter: str = "All stations",
) -> pd.DataFrame:
    out = df
    if boroughs:
        out = out[out["borough"].isin(boroughs)]
    if income_bands:
        out = out[out["income_band"].isin(income_bands)]
    if subway_filter == "Within 500m of subway":
        out = out[out["nearest_subway_dist_m"] <= 500]
    elif subway_filter == "Beyond 500m from subway":
        out = out[out["nearest_subway_dist_m"] > 500]
    return out
