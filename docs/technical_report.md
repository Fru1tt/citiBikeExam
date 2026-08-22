# Technical Report: Citi Bike NYC 2025

### Where Citi Bike Is Losing Value — A Neighborhood-Level Analysis of Ridership Gaps and What to Do About Them

EDI 3600 Digital Business Analysis, BI Norwegian Business School, Spring 2026

Dashboard: https://citibikeexam-cbzpwj3bmkpkp2tq5efncv.streamlit.app/ · GitHub repository: https://github.com/Fru1tt/citiBikeExam

---

## 1. Introduction

This report asks a single question: which neighborhood characteristics are linked to low ridership at Citi Bike stations, and what should the company do about it? Answering it required combining five separate data sources into one clean dataset and using both summary comparisons and a regression to test what the patterns mean.

The CitiBike report presents the findings and the recommendations. This report shows the work behind them: how the data was built, what analytical decisions we made, and how those decisions were tested. The dataset covers 43.3 million trips across 2,164 stations in 2025.

---

## 2. Data sources

Five data sources were combined into one station-level dataset.

| Source | What it provides | How it was accessed |
|--------|------------------|---------------------|
| Citi Bike trip records, 2025 (Citi Bike, 2025) | Start station, date, bike type, member or casual status for every trip | Monthly CSV files from the Citi Bike public S3 bucket |
| Citi Bike station feed, GBFS (Citi Bike, 2025) | Dock capacity, GPS coordinates, station names for all active stations | Snapshot taken March 2026 from the GBFS API |
| American Community Survey, 5-year estimates 2020-2024 (U.S. Census Bureau, 2024a) | Median household income, poverty rate, car-free household share, household density per neighborhood | JSON files via the US Census API |
| MTA Subway Stations (Metropolitan Transportation Authority, 2025) | Locations of all 496 subway stations in NYC | CSV from the MTA open-data platform |
| Census tract shapefiles, TIGER/Line 2024 (U.S. Census Bureau, 2024b) | Geographic boundaries for every census tract in New York State | Downloaded from the US Census Bureau |

The five sources together let us link each station to its neighborhood. Citi Bike's trip records and station feed tell us how busy each station is and how many docks it has. The ACS (American community survey) data brings in the neighborhood traits we want to test against ridership: income (economic access), poverty rate (a related affordability check), car-free household share (how reliant the neighborhood already is on alternatives to driving), and household density. The MTA subway data lets us measure transit access at each station, since the subway is the main alternative to bike share in NYC. The census tract shapefiles are the geographic key that lets us attach ACS data to stations through their coordinates.

The GBFS bundle pulled in March 2026 also included a real-time station-status snapshot. We investigated using it to measure broken-bike and broken-dock patterns directly. Why that approach was ruled out is in §6.

---

## 3. Pipeline

The pipeline is a series of Python scripts in `src/`, each producing an output file that feeds into the next. The work maps onto the BI Value Chain (Brohman et al., 2000) used throughout EDI 3600: the Business Problem and Task Definition are stated in §1, §§3.1–3.2 cover the Exploratory Data Analysis stage, §§3.3–3.5 cover the Structured Data Analysis stage, the analytical work in §§4–5 produces the Explanation and Prediction findings, and the Decision Making and Business Value stages live in the CitiBike report.

### 3.1 Understanding the raw data

The first step was to inspect the raw trip files and the station feed: column names, data types, how stations are identified. The inspection surfaced an early problem. The trip data and the station feed use different ID systems for the same stations, so a direct join produced no matches. Fixing that came later.

### 3.2 Aggregating trips to station-day level

The raw trip data contains 43.3 million rows, one per trip. That is more detail than the analysis needs. Trips were grouped by station and date, producing one row per station per day. This step records rides started, member rides, casual rides, and the share of rides taken by members. Trip duration, electric-bike share, and peak-hour share are not built here; they are computed later in the final-table step (§3.5) directly from the raw trip files.

We chose station-day rather than station-month because it keeps enough detail to see weekday-versus-weekend patterns, which turned out to matter for the findings, while keeping the dataset small enough to work with.

### 3.3 Solving the station ID mismatch

The trip records identify stations with short numeric IDs. The station feed uses a different, longer format. A direct join on station ID returned zero matches.

The solution was a crosswalk: a lookup table that matches trip stations to station-feed stations using their names and GPS coordinates instead of their IDs. Each match was given a confidence level based on the distance between the two coordinate sets. Out of 2,343 trip stations, 2,309 were matched at high or medium confidence, roughly 99%. The unmatched 34 stations sit mostly in Jersey City and Hoboken, outside the scope of the analysis.

### 3.4 Adding neighborhood context

Three steps bring in the census data:

1. **Spatial assignment.** Each station's GPS coordinates were matched to the census tract polygon it sits inside, giving every station a GEOID. We used 2024 tract boundaries because the ACS 2020-2024 estimates are also based on the 2024 vintage. Mixing vintages would risk silent boundary mismatches where tract lines have shifted.
2. **Socioeconomic join.** The ACS data (income, poverty rate, car-free share, household density) was joined to each station using the GEOID. The census files use a longer ID format with a state-and-county prefix, so the last 11 digits were extracted to make the join work.
3. **Subway proximity.** For each station, the pipeline computed the straight-line distance to the nearest subway entrance and counted how many subway stations lie within 500 metres.

After these steps, 147 stations still had at least one missing socioeconomic value. This is a known limitation of ACS data: some census tracts have no published estimates. These gaps are handled in the final assembly step.

### 3.5 Final outputs

The last set of scripts joins everything together, computes the trip-level metrics that were not built earlier (trip duration, electric-bike share, peak-hour share), drops rows with missing values, and produces two clean files.

The full master dataset contained 775,587 station-day rows across 2,343 unique trip stations. Two exclusions reduce this to the final analysis set:

1. **Station crosswalk (§3.3).** 2,309 of the 2,343 trip stations match the GBFS station feed. The 34 unmatched stations are mostly outside NYC.
2. **Socioeconomic join (§3.4).** Of the 2,309 matched stations, 147 had at least one missing ACS value for their tract. The final assembly drops the rows that cannot be recovered, leaving 2,164 stations.

At the station-day level, 720,485 of the original 775,587 rows survive these two exclusions (92.9% retention).

| File | What it contains | Rows |
|------|------------------|------|
| `station_summary_2025.csv` | One row per station, full-year averages and neighborhood context | 2,164 |
| `station_daily_2025.csv` | One row per station per day, with the same context attached | 720,485 |

The summary file is what every chart and the dashboard read. The daily file is not read by the dashboard or the charts. We keep it because it shows the station-level summary was built from real day-by-day rows, not from numbers we made up. It is a record of the work, not data for future analysis.

As a final step, each station was assigned to an income band, a poverty band, and a car-free band. Each band holds roughly the same number of stations (about 540), which keeps comparisons across bands fair.

---

## 4. Analytical decisions

This section covers the decisions made before any statistical test was run.

**Variable choice.** Income was chosen as the primary lens because it showed the clearest and most consistent link to ridership. Poverty rate was excluded from the regression because it moves with income at r = -0.70. That is close enough that including both adds nothing; income carries the same signal. Car-free household share was kept because it moves almost independently of income (r = -0.07), so it adds information that income on its own does not capture.

**Trip-level variables we set aside.** The raw Citi Bike trip records include the destination station and the exact end time of every trip, not just the start station and date we used. Pairing starts and ends would let us study trip flows: whether riders cross neighborhood boundaries, how stations connect to commute routes, how ridership links richer and poorer parts of the city. We did not include destination stations because our question is about ridership at each station (a count at one location), not flows between stations (a network). What we kept from the trip data (date, average trip duration, e-bike share) was already enough to spot the commuter pattern the CitiBike report's §4.4 rests on: weekday-heavy usage, longer trips, and e-bike preference at low-income stations. A separate analysis of trip flows was not needed to answer the question. The raw data still supports that analysis if a follow-up project wants to run it.

**Band design.** Stations were grouped into four bands of about 540 each (Low, Mid-Low, Mid-High, High). Equal-count bands keep comparisons across bands fair: no one band drowns out another by sheer size. Bands also read more cleanly for a business audience than regression coefficients. Bands carry the headline numbers; the regression cross-checks them.

**Metric design.** The headline metrics answer both business and access questions at once, instead of treating them as separate concerns. Rides per dock shows where docks are underused and also tells us how heavily each station is used. Member share is a revenue indicator and also flags affordability barriers in low-income neighborhoods. Electric-bike share shows what kind of bikes people are choosing and also flags longer commutes in areas with weaker transit access. Each metric tells two things at once, which keeps the analysis focused on the same numbers throughout.

**Bands vs regression.** Bands carry the narrative because they are easier to read. The regression tests whether the income pattern survives once density, subway access, and car-free share are held fixed at the same time. We ran a four-variable linear regression on average daily rides across all 2,164 stations. It explains 45% of the variation (R² = 0.45), and the income signal survives. The full coefficients are reported in the CitiBike report §5.1.

---

## 5. Robustness checks

The CitiBike report's findings rest on four pieces of evidence: the band comparisons, the regression, a check on which groups the model gets wrong (which points at the Bronx Low cluster), and a within-Low-band test that ruled out a specific ridership-uplift claim. This section shows the checks behind those pieces.

**Predicted vs actual rides by group.** We used the regression to compute each station's predicted ridership and the gap between predicted and actual rides. Averaging by borough and band gives the table below, sorted from biggest under-prediction to biggest over-prediction.

| Group | N | Predicted | Actual | Gap |
|-------|---|-----------|--------|-----|
| Queens High | 27 | 89.65 | 50.89 | -38.76 |
| Bronx Low | 273 | 26.64 | 10.99 | -15.65 |
| Brooklyn High | 199 | 91.89 | 80.19 | -11.70 |
| Bronx Mid-Low | 43 | 18.66 | 10.90 | -7.76 |
| Queens Low | 28 | 26.24 | 18.97 | -7.27 |
| Brooklyn Mid-Low | 197 | 33.57 | 27.93 | -5.65 |
| Queens Mid-High | 165 | 27.41 | 22.54 | -4.87 |
| Brooklyn Mid-High | 249 | 44.95 | 41.08 | -3.87 |
| Brooklyn Low | 92 | 21.07 | 19.41 | -1.66 |
| Queens Mid-Low | 210 | 11.73 | 12.85 | +1.13 |
| Manhattan Low | 149 | 45.01 | 47.94 | +2.93 |
| Manhattan High | 312 | 132.41 | 141.13 | +8.72 |
| Manhattan Mid-Low | 90 | 63.97 | 79.96 | +15.99 |
| Manhattan Mid-High | 130 | 92.79 | 141.91 | +49.12 |

Two patterns matter. First, every outer-borough Low and Mid-Low group rides below what the model predicts. Bronx Low is the biggest gap among the large groups at -16 rides per day. Queens High and Queens Low show big numbers but small samples (n = 27 and n = 28), so they are noisy and we do not lean on them. Second, Manhattan does better than predicted across all bands. The model misses some Manhattan factors, such as the Central Business District activity, tourism, and density beyond household density. That is a separate question, not the focus of the CitiBike recommendations.

**Poisson cross-check.** A linear regression assumes ridership sits on a smooth straight line, but daily rides are non-negative counts. We re-ran the same test using a Poisson regression, a method built for count data. Bronx Low still came out the worst large group. In the Poisson model the gap is actually larger (-19.75 rides per day versus the linear model's -15.65), because Poisson predicts 30.75 rides per day for Bronx Low rather than the linear model's 26.64. The finding holds either way. We also tried a Negative Binomial fit but it did not produce a stable result, so we do not report it.

**Why we kept the linear model anyway.** A linear regression can predict negative ridership at the low end, which is impossible. Across the 2,164 stations, the linear model predicts a negative number for 144 of them. The Poisson check confirms the finding is not a side effect of using the linear model: Poisson produces zero negative predictions and ranks Bronx Low the same way. We kept the linear model as the headline because its coefficients are easier to read in plain English (a $10,000 increase in median income adds 6.1 more rides per day, for example), and used Poisson as the cross-check.

**Within Bronx Low: the over-performers.** Performance is not the same across the 273 Bronx Low stations. A small subset runs at roughly 1.13 rides per dock per day, more than double the 0.49 average across the rest of the group. They sit on the borough's main commercial and commuter streets (Grand Concourse, Fordham Road, 3rd Avenue, Arthur Avenue), not the highest-income or best subway-connected tracts. We trust rides per dock more than the over-performer count itself. The count varies from 6 to 23 stations depending on which model and threshold we use, but rides per dock does not. So the CitiBike report leads with rides per dock (which does not depend on the model) and treats the commercial street cluster as supporting evidence.

**The Recommendation 2 e-bike test.** An earlier version of Recommendation 2 (prioritise e-bikes at low-income, subway-poor stations) carried a 10–15% ridership-uplift estimate. We tested whether the data supported it before keeping it.

Splitting the 542 Low-band stations into quartiles by e-bike share showed the opposite of the expected supply pattern. The top quartile (94% e-bike share) averages 11 rides per day; the bottom quartile (64% e-bike share) averages 47. A regression within the Low band, with income, subway count, density, and car-free share held fixed, returned a coefficient of -12 rides per day for every 10-percentage-point increase in e-bike share (n = 542).

The simplest explanation is that e-bike share is a sign of who uses the station, not how many e-bikes are available. Quiet stations draw a narrow group of long-distance commuters who lean on e-bikes, while busier stations have a wider mix including short-hop casual riders on classic bikes. The data cannot show what would happen if Citi Bike added more e-bikes at a quiet station, so we dropped the uplift claim. R2 is now framed as putting e-bikes where riders already choose them, judged on whether it serves existing riders better, not on a predicted percentage gain.

---

## 6. Limitations

**ACS 5-year averaging.** The ACS estimates cover 2020-2024, not 2025 specifically. They are an average across five years, not a snapshot. They are a reasonable approximation in stable neighborhoods but will understate change in areas that have shifted rapidly.

**Correlation, not causation.** The analysis shows patterns (stations in lower-income areas have fewer rides) but cannot prove that income is what causes the lower ridership. Income is linked to many other things at once: transit access, density, infrastructure quality. Where the report names a likely cause, that is our best read of the data, not proof of cause and effect.

**Excluded stations.** Stations that could not be matched to complete NYC census tract data were dropped. Most sit in Jersey City and Hoboken, outside the scope of the question. The full reconciliation is in §3.5.

**Service quality, what we tried.** One alternative we looked at was using Citi Bike's real-time station-status feed (part of GBFS) to measure broken bikes and broken docks at low-income stations directly. We pulled a snapshot in March 2026 to see what the feed contained. The feed only reports the current state of each station; there is no historical record, and no comprehensive third-party archive of the feed exists for 2025. We cannot rebuild a picture of service quality across the year from a single snapshot, so the CitiBike report cites the Comptroller's 2023 service-quality finding as a contributing factor instead. The snapshot file is kept in `data/raw/citibike/stations/` as a record of what was investigated.

---

## 7. Tools

Python (pandas, numpy, geopandas) for the data pipeline. Streamlit for the interactive dashboard and every chart in the CitiBike report. Git and GitHub for version control. Claude (Anthropic) as a coding assistant during the pipeline phase; the full Use of AI declaration follows.

---

## Use of AI

This declaration covers AI use across the data pipeline and this technical report. AI use on the CitiBike report is documented in the Declaration of AI Use appendix at the end of that report.

**AI tools that have been used in the work on assignment/exam:**

- Claude (Anthropic, Opus 4.7)
- Codex (OpenAI, GPT-5.5)

**Purpose of AI use:**

We have used AI while undertaking our assignment in the following ways:

- To develop research questions on the topic - No
- To generate ideas - Yes
- To create an outline of the topic - Yes
- To explain concepts - Yes
- To support our use of language - Yes
- To organise data - Yes
- To analyse data - Yes (for code and calculation, not for analytical conclusions)
- To visualise data - Yes

**In other ways, as described below:**

AI's main value here was not in writing. It was in making a deeper technical project workable for a two-person group. Combining five datasets, building a station-ID crosswalk, running the regression with both OLS and Poisson, computing per-group prediction errors, and building an interactive Streamlit dashboard would have been out of scope for a typical EDI 3600 project without AI partnership. AI wrote and debugged code, ran calculations, produced diagnostic checks, and pointed at alternative methods we would not have known to try on our own. The result was a much shorter feedback loop: we could test an idea, look at the numbers, and decide whether to keep it or drop it in minutes rather than days.

We worked with two AI systems in parallel: Claude (Anthropic, Opus 4.7) as the primary partner for coding and drafting, and Codex (OpenAI, GPT-5.5) as a secondary reviewer working in a separate session with no shared context. Single AI systems can hallucinate or commit confidently to a wrong answer, especially on detailed factual claims and statistical results. Running substantive work through both partners separately let each AI's output be challenged by the other: where they agreed, our confidence went up; where they disagreed, we knew to look closer. The result was a more nuanced view than either system would have produced alone, and a much lower chance of an AI mistake reaching the final report unnoticed. We kept a persistent file-based memory across sessions that held our methodological decisions and quality-control rules, so each session continued from the previous one without re-explaining context. For larger pieces of work we followed a structured workflow of brainstorming, written spec, written plan, then execution, which forced us to commit to an approach before writing rather than discovering it along the way.

The analytical decisions were ours: which variables to include, which methods to test, which findings to lead with, what to recommend. Every script was checked against diagnostic outputs at each step. Every number in this report was verified against the processed CSV files. Every citation was confirmed against the original source before being kept; AI was unreliable for factual claims and references, so AI-suggested citations were treated as unverified until checked independently. We are responsible for all content in this report.

---

## References

Brohman, M. K., Parent, M., Pearce, M. R., & Wade, M. R. (2000). The business intelligence value chain: Data-driven decision support in a data warehouse environment: An exploratory study. In *Proceedings of the 33rd Annual Hawaii International Conference on System Sciences*. IEEE Computer Society. https://doi.org/10.1109/HICSS.2000.926905

Citi Bike. (2025). *System data: Trip history and station feed* [Data set]. https://citibikenyc.com/system-data

Metropolitan Transportation Authority. (2025). *MTA subway stations* [Data set]. https://data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f

U.S. Census Bureau. (2024a). *American Community Survey 5-year estimates, 2020-2024* [Data set]. https://www.census.gov/data/developers/data-sets/acs-5year.html

U.S. Census Bureau. (2024b). *TIGER/Line shapefiles: Census tracts, New York State, 2024* [Data set]. https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2024.html
