"""Recommendations tab: four action panels tied to the DBA report."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import BOROUGH_ORDER, INCOME_BAND_COLORS, INCOME_BAND_ORDER

DEFAULT_TARGET = 29
DOCK_THRESHOLD = 1.5


def _small_map(df: pd.DataFrame, color_band: str | None = None, height: int = 380) -> None:
    if df.empty:
        st.info("No stations in this filter.")
        return
    map_df = df.dropna(subset=["latitude", "longitude", "avg_daily_rides"]).copy()
    map_df["size_val"] = map_df["avg_daily_rides"].clip(lower=1)
    color_arg = {"color": "income_band", "color_discrete_map": INCOME_BAND_COLORS}
    if color_band is not None:
        map_df["_single"] = color_band
        color_arg = {"color": "_single", "color_discrete_map": {color_band: INCOME_BAND_COLORS.get(color_band, "#7D3C98")}}
    fig = px.scatter_map(
        map_df,
        lat="latitude",
        lon="longitude",
        size="size_val",
        size_max=14,
        zoom=10,
        height=height,
        hover_name="matched_station_name",
        hover_data={"borough": True, "avg_daily_rides": ":.1f", "size_val": False},
        **color_arg,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig, width='stretch')


def _panel_r1(df: pd.DataFrame) -> None:
    st.subheader("R1: Subsidized membership, starting in the Bronx")
    st.caption(
        "Focus: the 273 Bronx stations in the lowest income band. "
        "These stations average 11 rides per day against a system average of 56."
    )

    subset = df[(df["borough"] == "Bronx") & (df["income_band"] == "Low")]
    total_current = len(subset) * subset["avg_daily_rides"].mean() * 365
    total_target = len(subset) * DEFAULT_TARGET * 365
    gain = total_target - total_current

    left, right = st.columns([3, 4])
    with left:
        m1, m2 = st.columns(2)
        m1.metric("Stations", f"{len(subset):,}")
        m2.metric("Current avg rides/day", f"{subset['avg_daily_rides'].mean():.1f}")
        m3, m4 = st.columns(2)
        m3.metric("Current member share", f"{subset['avg_member_share'].mean():.2f}")
        m4.metric("Potential annual ride gain", f"{gain/1_000_000:+,.2f} M")
        st.markdown(
            "**Business case.** Reaching the Mid-Low band average of 29 rides per day "
            "at these 273 stations adds roughly **1.79 million rides per year** with no new infrastructure. "
            "The scenario calculator on the Prediction tab shows how the number moves under other targets."
        )
    with right:
        _small_map(subset, color_band="Low")


def _panel_r2(df: pd.DataFrame) -> None:
    st.subheader("R2: E-bikes at low-income, subway-poor stations")
    st.caption(
        "Focus: Low income band stations that are more than 500 meters from the nearest subway. "
        "These are the stations where an e-bike most extends useful range."
    )

    subset = df[(df["income_band"] == "Low") & (df["nearest_subway_dist_m"] > 500)]

    left, right = st.columns([3, 4])
    with left:
        m1, m2 = st.columns(2)
        m1.metric("Stations", f"{len(subset):,}")
        m2.metric("Current avg rides/day", f"{subset['avg_daily_rides'].mean():.1f}")
        m3, m4 = st.columns(2)
        m3.metric("E-bike share", f"{subset['ebike_share'].mean():.2f}")
        m4.metric("Avg distance to subway", f"{subset['nearest_subway_dist_m'].mean():,.0f} m")
        st.markdown(
            "**Action.** Prioritize consistent e-bike availability at these stations in daily "
            "fleet management. Riders here already choose e-bikes at the highest rate in the system."
        )
    with right:
        _small_map(subset, color_band="Low")


def _panel_r3(df: pd.DataFrame) -> None:
    st.subheader("R3: Dock investment should wait for demand")
    st.caption(
        "Rides per dock measures how many rides each dock generates per day on average. "
        f"A value of {DOCK_THRESHOLD} is used here as a threshold for genuine demand on the existing docks."
    )

    below = df[df["rides_per_dock"] < DOCK_THRESHOLD]
    above = df[df["rides_per_dock"] >= DOCK_THRESHOLD]

    left, right = st.columns([4, 3])
    with left:
        d = df.dropna(subset=["rides_per_dock"]).copy()
        d["rides_per_dock_clipped"] = d["rides_per_dock"].clip(upper=8)
        fig = px.histogram(
            d,
            x="rides_per_dock_clipped",
            color="income_band",
            category_orders={"income_band": INCOME_BAND_ORDER},
            color_discrete_map=INCOME_BAND_COLORS,
            nbins=40,
            title="Rides per Dock Distribution (capped at 8 for readability)",
        )
        fig.add_vline(
            x=DOCK_THRESHOLD,
            line_dash="dash",
            line_color="black",
            annotation_text=f"Demand threshold ({DOCK_THRESHOLD})",
            annotation_position="top",
        )
        fig.update_layout(
            xaxis_title="Rides per dock per day",
            yaxis_title="Stations",
            legend_title_text="Income band",
            height=400,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig, width='stretch')
    with right:
        table = (
            df.assign(
                band=pd.Categorical(df["income_band"], categories=INCOME_BAND_ORDER, ordered=True),
                above=df["rides_per_dock"] >= DOCK_THRESHOLD,
            )
            .groupby("band", observed=True)["above"]
            .agg(stations="count", above_threshold="sum")
        )
        table["below_threshold"] = table["stations"] - table["above_threshold"]
        table = table[["stations", "below_threshold", "above_threshold"]]
        table.columns = ["Stations", f"Below {DOCK_THRESHOLD}", f"At or above {DOCK_THRESHOLD}"]
        st.dataframe(table, width='stretch')
        st.markdown(
            "At current utilization, building more docks in low-income areas is not supported by the data. "
            f"{len(below):,} stations are below the {DOCK_THRESHOLD} threshold, "
            f"{len(above):,} are at or above it."
        )


def _panel_r4(df: pd.DataFrame) -> None:
    st.subheader("R4: Borough accountability matrix")
    st.caption(
        "Current average daily rides by borough and income band. "
        f"Targets default to {DEFAULT_TARGET} (the Mid-Low band average) as a floor for low-volume cells; "
        "higher-performing cells already exceed this and show green by default. "
        "Adjust any cell to set a more demanding target."
    )

    current = (
        df.groupby(["borough", "income_band"])["avg_daily_rides"]
        .mean()
        .unstack("income_band")
        .reindex(index=BOROUGH_ORDER, columns=INCOME_BAND_ORDER)
    )
    counts = (
        df.groupby(["borough", "income_band"]).size().unstack("income_band")
        .reindex(index=BOROUGH_ORDER, columns=INCOME_BAND_ORDER).fillna(0).astype(int)
    )

    st.markdown("**Current average daily rides per station**")
    header_cols = st.columns([1.2, 1, 1, 1, 1])
    header_cols[0].markdown("&nbsp;")
    for i, band in enumerate(INCOME_BAND_ORDER, start=1):
        header_cols[i].markdown(f"**{band}**")

    targets: dict[tuple[str, str], int] = {}
    for borough in BOROUGH_ORDER:
        row_cols = st.columns([1.2, 1, 1, 1, 1])
        row_cols[0].markdown(f"**{borough}**")
        for j, band in enumerate(INCOME_BAND_ORDER, start=1):
            cur = current.loc[borough, band]
            n = counts.loc[borough, band]
            key = f"target_{borough}_{band}"
            with row_cols[j]:
                if pd.isna(cur) or n == 0:
                    st.markdown("—")
                    st.caption("0 stations")
                    continue
                tgt = st.number_input(
                    f"Target for {borough} {band}",
                    min_value=0,
                    max_value=300,
                    value=DEFAULT_TARGET,
                    step=1,
                    key=key,
                    label_visibility="collapsed",
                )
                targets[(borough, band)] = tgt
                gap = cur - tgt
                if gap < 0:
                    st.markdown(
                        f"<div style='background-color:#F8D7DA;color:#1a1a1a;"
                        f"padding:6px;border-radius:4px'>"
                        f"<b>{cur:.1f}</b> / target {tgt}<br>"
                        f"<span style='color:#721c24'><b>gap: {gap:+.1f}</b></span><br>"
                        f"<small>{n} stations</small></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='background-color:#D4EDDA;color:#1a1a1a;"
                        f"padding:6px;border-radius:4px'>"
                        f"<b>{cur:.1f}</b> / target {tgt}<br>"
                        f"<span style='color:#155724'><b>at or above</b></span><br>"
                        f"<small>{n} stations</small></div>",
                        unsafe_allow_html=True,
                    )

    st.caption(
        "This view makes the gap visible by borough and income band, "
        "rather than averaging it into one system-wide number."
    )


def render(df: pd.DataFrame) -> None:
    st.header("From analysis to action")
    st.caption("Business Value in the BI value chain.")
    st.markdown("Four recommendations, each tied to the specific stations it targets.")

    _panel_r1(df)
    st.divider()
    _panel_r2(df)
    st.divider()
    _panel_r3(df)
    st.divider()
    _panel_r4(df)
