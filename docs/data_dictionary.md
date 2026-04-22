# Data Dictionary — Citi Bike NYC 2025

Two files are used in this project. Both are in `data/processed/`.

---

## station_summary_2025.csv

**What it is:** One row per Citi Bike station. 2,164 stations. All numbers cover the full year 2025.
**Use this file for:** Streamlit dashboard, all charts, all report findings.

| Column | What it is |
|--------|------------|
| `start_station_id` | Unique ID for each station |
| `matched_station_name` | Station name (cleaned and standardized) |
| `borough` | Which NYC borough the station is in (Bronx, Brooklyn, Manhattan, Queens) |
| `GEOID` | Census tract identifier — links the station to its neighborhood in the census data |
| `latitude` | GPS latitude of the station — used for the map |
| `longitude` | GPS longitude of the station — used for the map |
| `capacity` | Number of docks at the station |
| `total_rides_2025` | Total number of rides started at this station in all of 2025 |
| `avg_daily_rides` | Average number of rides per day across the full year |
| `avg_member_share` | Share of rides taken by members (vs casual users paying per trip). 0.85 means 85% of rides were by members |
| `avg_trip_duration_min` | Average length of a trip starting at this station, in minutes |
| `ebike_share` | Share of rides taken on electric bikes. 0.81 means 81% of rides used an e-bike |
| `avg_weekday_rides` | Average rides per day on weekdays (Monday to Friday) |
| `avg_weekend_rides` | Average rides per day on weekends (Saturday and Sunday) |
| `weekday_weekend_ratio` | avg_weekday_rides divided by avg_weekend_rides. Above 1.0 means the station is busier on weekdays — a commuter signal |
| `rides_per_dock` | Average daily rides divided by dock capacity. Shows how heavily the station is being used relative to its size. 0.5 means each dock is used about once every two days |
| `median_household_income` | Median household income in the census tract where the station is located (in USD) |
| `poverty_rate` | Share of people in the tract living below the poverty line. 0.25 means 25% poverty rate |
| `no_vehicle_share` | Share of households in the tract that do not own a car (called "car-free household share" in the reports) |
| `households_per_sqkm` | How densely populated the neighborhood is — households per square kilometer |
| `nearest_subway_dist_m` | Distance in meters from the station to the nearest subway entrance |
| `subway_count_500m` | Number of subway stations within 500 meters of this Citi Bike station |
| `nearest_subway_name` | Name of the closest subway station (e.g. "125 St") |
| `income_band` | Which of four equal-count income groups the station falls in: Low, Mid-Low, Mid-High, or High, based on median_household_income |
| `poverty_band` | Which of four equal-count poverty groups the station falls in: Low, Moderate, Elevated, or High, based on poverty_rate |

---

## station_daily_2025.csv

**What it is:** One row per station per day. 720,485 rows. Each row is one station on one specific date.
**Use this file for:** Time-series charts showing how ridership changes over months or seasons. Not needed for the main report or dashboard.

| Column | What it is |
|--------|------------|
| `start_station_id` | Unique ID for each station — links back to the summary file |
| `date` | The specific date of that row (e.g. 2025-03-15) |
| `rides_started` | Number of rides that started at this station on this day |
| `member_rides_started` | Number of those rides taken by members |
| `member_share_started` | Share of that day's rides taken by members |
| `matched_station_name` | Station name (cleaned and standardized) |
| `GEOID` | Census tract identifier |
| `latitude` | GPS latitude |
| `longitude` | GPS longitude |
| `capacity` | Number of docks at the station |
| `median_household_income` | Median household income of the station's neighborhood |
| `poverty_rate` | Poverty rate of the station's neighborhood |
| `no_vehicle_share` | Car-free household share of the station's neighborhood (called "car-free household share" in the reports) |
| `households_per_sqkm` | Neighborhood density |
| `nearest_subway_dist_m` | Distance to nearest subway in meters |
| `subway_count_500m` | Number of subway stations within 500 meters |
| `borough` | Which NYC borough the station is in |
| `is_weekend` | 1 if the date is a Saturday or Sunday, 0 if it is a weekday |
| `daily_rides_per_dock` | Rides on that specific day divided by dock capacity — true daily utilization rate |
