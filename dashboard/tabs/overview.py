"""Overview tab: 10-second answer to the business problem."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.theme import INCOME_BAND_COLORS, INCOME_BAND_ORDER


def render(df: pd.DataFrame) -> None:
    st.header("The ridership gap in one view")
    st.caption("Business Problem in the BI value chain.")
    st.markdown(
        "One row per station, full year 2025. 2,164 stations, 43.3 million trips."
    )
    st.caption(
        "Citi Bike's NYC operating contract is up for renewal in May 2029. "
        "The Independent Budget Office (2025) and the Comptroller's Office (2023) "
        "have both said outer-borough service and reach will be central to that renewal."
    )

    system_avg = df["avg_daily_rides"].mean()
    band_avg = df.groupby("income_band")["avg_daily_rides"].mean()
    bronx_low_avg = df[(df["borough"] == "Bronx") & (df["income_band"] == "Low")][
        "avg_daily_rides"
    ].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("System average", f"{system_avg:.0f} rides/day")
    k2.metric("High income band", f"{band_avg['High']:.0f} rides/day")
    k3.metric("Low income band", f"{band_avg['Low']:.0f} rides/day")
    k4.metric("Bronx Low stations", f"{bronx_low_avg:.0f} rides/day")

    st.subheader("Station ridership and income band across NYC")
    st.caption(
        "Each dot is one station. Color shows the neighborhood income band. "
        "Dot size shows average daily rides."
    )

    map_df = df.dropna(subset=["latitude", "longitude", "avg_daily_rides"]).copy()
    map_df["avg_daily_rides_display"] = map_df["avg_daily_rides"].clip(lower=1)

    fig = px.scatter_map(
        map_df,
        lat="latitude",
        lon="longitude",
        color="income_band",
        size="avg_daily_rides_display",
        size_max=18,
        zoom=10,
        height=560,
        category_orders={"income_band": INCOME_BAND_ORDER},
        color_discrete_map=INCOME_BAND_COLORS,
        hover_name="matched_station_name",
        hover_data={
            "borough": True,
            "income_band": True,
            "avg_daily_rides": ":.1f",
            "capacity": True,
            "latitude": False,
            "longitude": False,
            "avg_daily_rides_display": False,
        },
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend_title_text="Income band",
    )
    st.plotly_chart(fig, width='stretch')

    st.subheader("What the data shows")
    lines = [
        "The gap is fivefold and affects more than 500 stations.",
        "It is not a supply problem. Low-income stations cycle rides through each dock at about a third the rate of high-income stations (median 0.53 rides per dock).",
        "Riders who do use low-income stations ride like commuters: weekday-heavy, longer trips, 81% on e-bikes.",
        "The gap is concentrated in the Bronx, where 86% of stations fall in the lowest income band.",
    ]
    for line in lines:
        st.markdown(f"- {line}")
