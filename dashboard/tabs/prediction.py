"""Prediction tab: regression diagnostic + scenario calculator."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import BOROUGH_ORDER, INCOME_BAND_COLORS, INCOME_BAND_ORDER

SLIDER_KEY = "scenario_target"
BOROUGH_KEY = "scenario_borough"
BAND_KEY = "scenario_band"

REGRESSION_BOROUGH_KEY = "regression_borough"
REGRESSION_BAND_KEY = "regression_band"

BOROUGH_CHOICES = ["Bronx", "Brooklyn", "Manhattan", "Queens", "All boroughs"]
BAND_CHOICES = ["Low", "Mid-Low", "Mid-High", "High", "All bands"]

DIAGNOSTIC_BOROUGHS = ["Bronx", "Brooklyn", "Manhattan", "Queens"]
DIAGNOSTIC_BANDS = ["Low", "Mid-Low", "Mid-High", "High"]

PREDICTORS = [
    "median_household_income",
    "subway_count_500m",
    "households_per_sqkm",
    "no_vehicle_share",
]
PREDICTOR_LABELS = {
    "median_household_income": "Median household income (USD)",
    "subway_count_500m": "Subway stations within 500m (count)",
    "households_per_sqkm": "Household density (per km²)",
    "no_vehicle_share": "Car-free household share (0–1)",
}


@st.cache_data(show_spinner=False)
def _fit_regression(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["avg_daily_rides"] + PREDICTORS).copy()
    X = np.column_stack([np.ones(len(d))] + [d[c].values for c in PREDICTORS])
    y = d["avg_daily_rides"].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    per_station = d[["borough", "income_band"]].copy()
    per_station["predicted"] = yhat
    per_station["actual"] = y
    per_station["is_bronx_low"] = (
        (per_station["borough"] == "Bronx") & (per_station["income_band"] == "Low")
    )

    bl_mask = per_station["is_bronx_low"]
    predicted = float(per_station.loc[bl_mask, "predicted"].mean())
    actual = float(per_station.loc[bl_mask, "actual"].mean())

    return {
        "n": len(d),
        "r2": float(r2),
        "coef": dict(zip(["intercept"] + PREDICTORS, beta.tolist())),
        "bronx_low_n": int(bl_mask.sum()),
        "bronx_low_predicted": predicted,
        "bronx_low_actual": actual,
        "residual": predicted - actual,
        "per_station": per_station,
    }


def _group_stats(fit: dict, borough: str, band: str) -> dict:
    ps = fit["per_station"]
    mask = (ps["borough"] == borough) & (ps["income_band"] == band)
    n = int(mask.sum())
    if n == 0:
        return {"n": 0, "predicted": float("nan"), "actual": float("nan"), "residual": float("nan")}
    predicted = float(ps.loc[mask, "predicted"].mean())
    actual = float(ps.loc[mask, "actual"].mean())
    return {
        "n": n,
        "predicted": predicted,
        "actual": actual,
        "residual": actual - predicted,
    }


def _regression_selectors() -> tuple[str, str]:
    if REGRESSION_BOROUGH_KEY not in st.session_state:
        st.session_state[REGRESSION_BOROUGH_KEY] = "Bronx"
    if REGRESSION_BAND_KEY not in st.session_state:
        st.session_state[REGRESSION_BAND_KEY] = "Low"

    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        borough = st.selectbox(
            "Borough",
            options=DIAGNOSTIC_BOROUGHS,
            key=REGRESSION_BOROUGH_KEY,
            help="Pick a borough to compare against what the model predicts for that group.",
        )
    with sel_col2:
        band = st.selectbox(
            "Income band",
            options=DIAGNOSTIC_BANDS,
            key=REGRESSION_BAND_KEY,
            help="The diagnostic uses one borough × income-band cell at a time.",
        )
    return borough, band


def _regression_tile(df: pd.DataFrame, borough: str, band: str) -> None:
    st.subheader("What a model of the whole network predicts")

    fit = _fit_regression(df)
    group = _group_stats(fit, borough, band)
    group_label = f"{borough} {band}"
    band_color = INCOME_BAND_COLORS.get(band, INCOME_BAND_COLORS["Low"])

    col_text, col_chart = st.columns([3, 2])
    with col_text:
        st.markdown(
            f"A linear regression across all {fit['n']:,} stations uses median household income, "
            f"subway stations within 500m, household density, and car-free household share "
            f"to predict average daily rides. Together these structural factors explain "
            f"**{fit['r2']*100:.0f}% of the variation in daily ridership** (R² = {fit['r2']:.2f})."
        )

        if group["n"] == 0:
            st.warning(
                f"No stations match {group_label}. "
                "(The Bronx has no High or Mid-High income-band stations in this dataset.)"
            )
        else:
            st.markdown(
                f"For the {group['n']} {group_label} stations, the model predicts "
                f"**{group['predicted']:.1f} rides per day**. "
                f"The actual average is **{group['actual']:.1f} rides per day**."
            )
            direction = "below" if group["residual"] < 0 else "above"
            st.markdown(
                f"That leaves a gap of **{group['residual']:+.1f} rides per day** ({direction} "
                "what neighborhood factors alone would predict). A negative number means the group "
                "rides less than those factors forecast; a positive number means more."
            )

        with st.expander("Coefficients"):
            coef_df = pd.DataFrame(
                {
                    "Predictor": [PREDICTOR_LABELS.get(k, k) for k in fit["coef"].keys()],
                    "Coefficient": [f"{v:.6f}" for v in fit["coef"].values()],
                }
            )
            st.dataframe(coef_df, width="stretch", hide_index=True)
            st.caption(
                "Each coefficient shows how daily rides change when that predictor goes up by one unit. "
                "Fit by linear regression on rows with complete data. "
                "Standard checks confirm none of the four variables is measuring the same thing as another."
            )

    with col_chart:
        if group["n"] == 0:
            st.info("Pick a borough × band that has stations.")
            return
        pred = group["predicted"]
        actual = group["actual"]
        fig = go.Figure(
            data=[
                go.Bar(
                    x=["Model predicts", "Actual average"],
                    y=[pred, actual],
                    marker_color=["#1F4E79", band_color],
                    text=[f"{pred:.1f}", f"{actual:.1f}"],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            title=f"{group_label} stations (n={group['n']})",
            yaxis_title="Rides per day",
            height=300,
            margin=dict(l=10, r=10, t=50, b=10),
            showlegend=False,
        )
        fig.update_yaxes(range=[0, max(pred, actual) * 1.3])
        st.plotly_chart(fig, width='stretch')


def _regression_scatter(df: pd.DataFrame, borough: str, band: str) -> None:
    st.subheader("Predicted vs actual rides across every station")

    fit = _fit_regression(df)
    ps = fit["per_station"].copy()
    group_mask = (ps["borough"] == borough) & (ps["income_band"] == band)
    group_label = f"{borough} {band}"
    band_color = INCOME_BAND_COLORS.get(band, INCOME_BAND_COLORS["Low"])

    others = ps[~group_mask]
    group = ps[group_mask]

    axis_max = float(max(ps["predicted"].max(), ps["actual"].max())) * 1.05
    axis_min = float(min(ps["predicted"].min(), ps["actual"].min(), 0))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=others["predicted"],
            y=others["actual"],
            mode="markers",
            name="Other stations",
            marker=dict(color="#B0B7BE", size=6, opacity=0.55),
            hovertemplate="Predicted: %{x:.1f}<br>Actual: %{y:.1f}<extra></extra>",
        )
    )
    if len(group) > 0:
        fig.add_trace(
            go.Scatter(
                x=group["predicted"],
                y=group["actual"],
                mode="markers",
                name=f"{group_label} stations",
                marker=dict(color=band_color, size=8, opacity=0.9),
                hovertemplate="Predicted: %{x:.1f}<br>Actual: %{y:.1f}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[axis_min, axis_max],
            y=[axis_min, axis_max],
            mode="lines",
            name="Predicted = actual",
            line=dict(color="#1F4E79", dash="dash", width=1.5),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        title=f"Regression fit: where do {group_label} stations land?",
        xaxis_title="Model-predicted rides per day",
        yaxis_title="Actual rides per day",
        height=480,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(range=[axis_min, axis_max])
    fig.update_yaxes(range=[axis_min, axis_max])

    st.plotly_chart(fig, width="stretch")

    group_stats = _group_stats(fit, borough, band)
    if group_stats["n"] == 0:
        st.caption(
            f"No {group_label} stations in this dataset — the scatter shows the rest of the network "
            "against the regression line. Pick a group that has stations to see its position."
        )
        return

    side = "below" if group_stats["residual"] < 0 else "above"
    st.caption(
        "Each point is one station. The dashed line is where the model's prediction equals the actual "
        f"average. The {group_stats['n']} {group_label} stations sit {side} the line on average: the model "
        f"expects ~{group_stats['predicted']:.0f} rides per day, actual is ~{group_stats['actual']:.0f} "
        f"(gap {group_stats['residual']:+.1f})."
    )


def _literature_anchor() -> None:
    st.markdown(
        "<div style='background-color:#EEF3F8;color:#1a1a1a;padding:12px 14px;"
        "border-left:4px solid #1F4E79;border-radius:4px'>"
        "<b>Why the unexplained gap is plausible.</b> "
        "In a survey of residents in underserved neighborhoods in Philadelphia, Brooklyn, and Chicago, "
        "McNeil et al. (2017) found that only <b>31%</b> knew about reduced-price membership options, "
        "<b>48%</b> of lower-income respondents cited membership cost as a big barrier, and "
        "<b>34%</b> of lower-income people said not knowing enough about how to use bike share "
        "was a big barrier. <b>80%</b> said a discounted membership would make them more likely to use it. "
        "These are exactly the cost and awareness barriers the structural model cannot see — "
        "and service quality is a third plausible factor the data cannot isolate directly (see report §3.3)."
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "McNeil, N., Dill, J., MacArthur, J., Broach, J., and Howland, S. (2017). "
        "*Breaking Barriers to Bike Share: Insights from Residents of Traditionally Underserved Neighborhoods.* "
        "NITC-RR-884b. Portland, OR: TREC, Portland State University. "
        "https://doi.org/10.15760/trec.176"
    )


def _scenario_section(df: pd.DataFrame) -> None:
    st.subheader("Scenario calculator")
    st.caption(
        "Pick a group of stations and a ridership target. "
        "The calculator shows how many rides per year that would mean."
    )

    if SLIDER_KEY not in st.session_state:
        st.session_state[SLIDER_KEY] = 29
    if BOROUGH_KEY not in st.session_state:
        st.session_state[BOROUGH_KEY] = "Bronx"
    if BAND_KEY not in st.session_state:
        st.session_state[BAND_KEY] = "Low"

    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        borough = st.selectbox("Borough", options=BOROUGH_CHOICES, key=BOROUGH_KEY)
    with sel_col2:
        band = st.selectbox("Income band", options=BAND_CHOICES, key=BAND_KEY)

    subset = df
    if borough != "All boroughs":
        subset = subset[subset["borough"] == borough]
    if band != "All bands":
        subset = subset[subset["income_band"] == band]

    station_count = len(subset)
    current_avg = subset["avg_daily_rides"].mean() if station_count else 0.0

    st.markdown("**Presets**")
    p1, p2, p3, _ = st.columns([1, 1, 1, 3])
    if p1.button("Conservative (20)"):
        st.session_state[SLIDER_KEY] = 20
    if p2.button("Realistic (29)"):
        st.session_state[SLIDER_KEY] = 29
    if p3.button("Aspirational (60)"):
        st.session_state[SLIDER_KEY] = 60

    target = st.slider(
        "If these stations averaged this many rides per day",
        min_value=0,
        max_value=150,
        step=1,
        key=SLIDER_KEY,
    )

    if station_count == 0:
        st.warning("No stations match this selection.")
        return

    current_annual = station_count * current_avg * 365
    projected_annual = station_count * target * 365
    gain = projected_annual - current_annual
    uplift_pct = (gain / current_annual * 100) if current_annual > 0 else 0.0

    total_docks = subset["capacity"].sum()
    current_per_dock = (station_count * current_avg / total_docks) if total_docks > 0 else 0.0
    projected_per_dock = (station_count * target / total_docks) if total_docks > 0 else 0.0
    network_per_dock = df["avg_daily_rides"].sum() / df["capacity"].sum()

    lbs_per_trip = 1_553_484 / 2_140_234
    co2_avoided_lbs = gain * lbs_per_trip

    st.markdown(" ")
    m1, m2, m3 = st.columns(3)
    m1.metric("Stations in selection", f"{station_count:,}")
    m2.metric("Current average", f"{current_avg:.1f} rides/day")
    m3.metric("Target", f"{target} rides/day")

    n1, n2, n3 = st.columns(3)
    n1.metric("Current annual rides", f"{current_annual/1_000_000:,.2f} M")
    n2.metric("Projected annual rides", f"{projected_annual/1_000_000:,.2f} M")
    n3.metric("Annual ride gain", f"{gain/1_000_000:+,.2f} M", f"{uplift_pct:+.0f}% vs current")

    d1, d2, d3 = st.columns(3)
    d1.metric("Docks in selection", f"{int(total_docks):,}")
    d2.metric("Current rides per dock", f"{current_per_dock:.2f} /day")
    d3.metric(
        "Projected rides per dock",
        f"{projected_per_dock:.2f} /day",
        f"network avg {network_per_dock:.2f} /day",
        delta_color="off",
    )

    st.caption(
        f"Formula: {station_count:,} stations × ({target} − {current_avg:.1f}) rides/day × 365 days "
        f"= {gain:,.0f} extra rides per year. "
        f"Rides per dock = selection rides/day ÷ {int(total_docks):,} docks."
    )

    co2_direction = "avoided" if co2_avoided_lbs >= 0 else "added"
    st.markdown(
        f"**Estimated CO₂ {co2_direction} from this scenario: {abs(co2_avoided_lbs)/1_000_000:,.2f} million lbs per year** "
        f"(0.73 lbs per trip, from Citi Bike's December 2025 operating report using the 2012 MTA Sustainability Report methodology)."
    )


def render(df: pd.DataFrame) -> None:
    st.header("Prediction: what the model says and what it would mean")
    st.caption("Decision Support in the BI value chain.")
    st.markdown(
        "Two pieces. First, what a regression across the network predicts for the Bronx. "
        "Second, a calculator to translate a ridership target into annual rides."
    )

    borough, band = _regression_selectors()
    _regression_tile(df, borough, band)
    _regression_scatter(df, borough, band)
    _literature_anchor()
    st.divider()
    _scenario_section(df)
