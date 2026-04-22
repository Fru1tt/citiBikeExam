"""CitiBike NYC 2025 Streamlit dashboard entry point.

Run with:
    streamlit run app.py

Data: data/processed/station_summary_2025.csv (one row per station, full year 2025).
"""

from __future__ import annotations

import streamlit as st

from dashboard.data import load_stations
from dashboard.tabs import explore, overview, prediction, recommendations


def _overview_page() -> None:
    overview.render(load_stations())


def _explore_page() -> None:
    explore.render(load_stations())


def _prediction_page() -> None:
    prediction.render(load_stations())


def _recommendations_page() -> None:
    recommendations.render(load_stations())


def main() -> None:
    st.set_page_config(
        page_title="Citi Bike 2025: Ridership Gap",
        page_icon=":bike:",
        layout="wide",
    )
    pages = [
        st.Page(_overview_page, title="Overview", default=True),
        st.Page(_explore_page, title="Explore"),
        st.Page(_prediction_page, title="Prediction"),
        st.Page(_recommendations_page, title="Recommendations"),
    ]
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
