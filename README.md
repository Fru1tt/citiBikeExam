# citiBike

Exam project for EDI 36001 — Digital Business Analysis at BI Norwegian Business School, spring 2026.

The exam asks for a data-driven business analysis delivered as a DBA report, an interactive dashboard, and a short video. We chose NYC Citi Bike because it has detailed open trip data and clear real-world implications around equity and urban mobility.

The analysis covers 43.3 million trips across 2,164 stations in 2025, enriched with ACS census socioeconomics (income, poverty, vehicle access) at the tract level, MTA subway proximity, and borough context. The central question: are low-income neighbourhoods being underserved by Citi Bike — and what does the data say about why?

## Live dashboard

The deployed dashboard is at https://citibikeexam-cbzpwj3bmkpkp2tq5efncv.streamlit.app/

It has four tabs (Overview, Explore, Prediction, Recommendations) and reads the same `station_summary_2025.csv` produced by the pipeline below.

## Repository structure

- `app.py` — Streamlit dashboard entry point
- `dashboard/` — dashboard tabs, data loader, theme
- `src/` — Python pipeline scripts (numbered by stage, see below)
- `data/raw/` — original source data (Citi Bike, ACS census, MTA subway, shapefiles)
- `data/processed/` — cleaned analysis-ready datasets
- `docs/data_dictionary.md` — column-level description of the final datasets

## Reproducing the pipeline

Scripts in `src/` are numbered by stage — run them in numerical order to rebuild every processed dataset from the raw sources.

| Stage | Purpose |
|-------|---------|
| `00_` | Inspect raw trip file structure |
| `10_`–`15_` | Build station metadata, census socioeconomics, tract lookup, subway proximity |
| `20_`–`22_` | Build station-day usage from raw trips; diagnose and approve station crosswalk |
| `30_`–`33_` | Build the master station-day table and analysis-ready subset |
| `40_`–`42_` | Build and enrich the station-level summary with income/poverty bands, borough, weekday/weekend metrics |
| `50_`–`51_` | Final cleanup — produce `station_summary_2025.csv` and `station_daily_2025.csv` |

Raw trip CSVs are not committed (too large). They are available from the Citi Bike public S3 bucket under `citibike-tripdata/2025/`.

## Final datasets

- `station_summary_2025.csv` — 2,164 rows (one per station). Full-year averages plus neighborhood context. Used by the dashboard and all report charts.
- `station_daily_2025.csv` — 720,485 rows (one per station per day). Generated as a bridge artifact by stages 20–33 and used by stages 40–51 to build the summary. Not committed (120 MB); reproduce by running the pipeline.

See `docs/data_dictionary.md` for a full column-level description.

## Running locally (optional)

The deployed Streamlit instance above is the primary access path. To run the dashboard locally instead:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The dashboard reads `data/processed/station_summary_2025.csv` (one row per station, 2,164 rows).
