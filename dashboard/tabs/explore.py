"""Explore tab: six charts plus sidebar filters (diagnosis mode)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data import apply_filters
from dashboard.theme import (
    BOROUGH_ORDER,
    INCOME_BAND_COLORS,
    INCOME_BAND_ORDER,
    SUBWAY_FILTER_OPTIONS,
)


def _band_mean_chart(
    df: pd.DataFrame,
    value_col: str,
    title: str,
    y_label: str,
    y_range: tuple[float, float] | None = None,
    fmt: str = ".2f",
) -> None:
    if df.empty:
        st.info("No stations match the current filters.")
        return
    grouped = (
        df.groupby("income_band")[value_col]
        .mean()
        .reindex(INCOME_BAND_ORDER)
        .dropna()
        .reset_index()
    )
    fig = px.bar(
        grouped,
        x="income_band",
        y=value_col,
        color="income_band",
        color_discrete_map=INCOME_BAND_COLORS,
        category_orders={"income_band": INCOME_BAND_ORDER},
        title=title,
        text=grouped[value_col].map(lambda v: format(v, fmt)),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        xaxis_title="Income band",
        yaxis_title=y_label,
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
        height=360,
    )
    if y_range:
        fig.update_yaxes(range=list(y_range))
    st.plotly_chart(fig, width='stretch')


def _weekday_weekend_chart(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No stations match the current filters.")
        return
    grouped = (
        df.groupby("income_band")[["avg_weekday_rides", "avg_weekend_rides"]]
        .mean()
        .reindex(INCOME_BAND_ORDER)
        .dropna()
        .reset_index()
    )
    long = grouped.melt(
        id_vars="income_band",
        value_vars=["avg_weekday_rides", "avg_weekend_rides"],
        var_name="day_type",
        value_name="rides",
    )
    long["day_type"] = long["day_type"].map(
        {"avg_weekday_rides": "Weekday", "avg_weekend_rides": "Weekend"}
    )
    fig = px.bar(
        long,
        x="income_band",
        y="rides",
        color="day_type",
        barmode="group",
        category_orders={"income_band": INCOME_BAND_ORDER, "day_type": ["Weekday", "Weekend"]},
        color_discrete_map={"Weekday": "#1F4E79", "Weekend": "#E67E22"},
        title="Weekday vs Weekend Rides by Income Band",
        text=long["rides"].map(lambda v: f"{v:.1f}"),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        xaxis_title="Income band",
        yaxis_title="Average rides per day",
        legend_title_text="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=360,
    )
    st.plotly_chart(fig, width='stretch')


def _borough_stack_chart(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No stations match the current filters.")
        return
    counts = (
        df.groupby(["borough", "income_band"]).size().reset_index(name="stations")
    )
    fig = px.bar(
        counts,
        x="stations",
        y="borough",
        color="income_band",
        orientation="h",
        category_orders={"borough": BOROUGH_ORDER, "income_band": INCOME_BAND_ORDER},
        color_discrete_map=INCOME_BAND_COLORS,
        title="Station Count by Borough and Income Band",
        text="stations",
    )
    fig.update_traces(textposition="inside")
    fig.update_layout(
        xaxis_title="Number of stations",
        yaxis_title="Borough",
        legend_title_text="Income band",
        margin=dict(l=10, r=10, t=50, b=10),
        height=360,
    )
    st.plotly_chart(fig, width='stretch')


def render(df: pd.DataFrame) -> None:
    st.header("Explore the evidence")
    st.caption("Diagnosis in the BI value chain.")
    st.markdown(
        "Use the sidebar filters to drill into a borough, income band, or subway access group. "
        "All charts update together."
    )

    with st.sidebar:
        st.header("Filters")
        boroughs = st.multiselect(
            "Borough",
            options=BOROUGH_ORDER,
            default=[],
            help="Leave empty to include all boroughs.",
        )
        bands = st.multiselect(
            "Income band",
            options=INCOME_BAND_ORDER,
            default=[],
            help="Leave empty to include all bands.",
        )
        subway = st.radio(
            "Subway access",
            options=SUBWAY_FILTER_OPTIONS,
            index=0,
        )

    filtered = apply_filters(df, boroughs=boroughs, income_bands=bands, subway_filter=subway)

    st.caption(f"Stations in view: {len(filtered):,} of {len(df):,}")

    row1a, row1b = st.columns(2)
    with row1a:
        _band_mean_chart(
            filtered,
            value_col="avg_daily_rides",
            title="Average Daily Rides by Income Band",
            y_label="Average daily rides",
            fmt=".1f",
        )
    with row1b:
        _band_mean_chart(
            filtered,
            value_col="avg_member_share",
            title="Average Member Share by Income Band",
            y_label="Member share",
            y_range=(0.70, 1.0),
            fmt=".2f",
        )

    row2a, row2b = st.columns(2)
    with row2a:
        _band_mean_chart(
            filtered,
            value_col="rides_per_dock",
            title="Average Rides per Dock by Income Band",
            y_label="Rides per dock",
            fmt=".2f",
        )
    with row2b:
        _weekday_weekend_chart(filtered)

    row3a, row3b = st.columns(2)
    with row3a:
        _band_mean_chart(
            filtered,
            value_col="ebike_share",
            title="Electric Bike Share by Income Band",
            y_label="E-bike share",
            y_range=(0.60, 0.90),
            fmt=".2f",
        )
    with row3b:
        _borough_stack_chart(filtered)

    row4a, row4b = st.columns(2)
    with row4a:
        _band_mean_chart(
            filtered,
            value_col="subway_count_500m",
            title="Average Subway Stations Within 500m by Income Band",
            y_label="Subway stations within 500m",
            fmt=".2f",
        )
    with row4b:
        _band_mean_chart(
            filtered,
            value_col="avg_trip_duration_min",
            title="Average Trip Duration by Income Band",
            y_label="Minutes per trip",
            fmt=".1f",
        )
