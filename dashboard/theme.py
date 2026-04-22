"""Shared colors, labels, and ordering for the CitiBike dashboard."""

from __future__ import annotations

INCOME_BAND_ORDER = ["High", "Mid-High", "Mid-Low", "Low"]

INCOME_BAND_COLORS = {
    "High": "#7FB3D5",
    "Mid-High": "#1F4E79",
    "Mid-Low": "#E67E22",
    "Low": "#7D3C98",
}

BOROUGH_ORDER = ["Manhattan", "Brooklyn", "Queens", "Bronx"]

SUBWAY_FILTER_OPTIONS = ["All stations", "Within 500m of subway", "Beyond 500m from subway"]
