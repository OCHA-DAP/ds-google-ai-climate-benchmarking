# Re-scoring the frameworks' own evaluations on the November 2026 release, 4–5 Nov 2026

Step 2 of the replication plan, five frameworks. The comparison that matters is GRRR November 2026 against the model each framework actually ran on, the incumbent (`scripts/incumbents.py`): the GRRR 2023 bucket (`model_id_8583a5c2_v0`) for Nigeria 2026 and one leg of the Somalia proposal; GloFAS v4 for Chad, Nepal and Bangladesh; GloFAS v5 as the Somalia proposal's other leg; the ABN gauge alone for Niger. Each script runs the same code on every model from its own reanalysis, so every table reads: the number the team published, the incumbent through this code, the 2023 bucket, the 2026 release (`distributed_model_2026_11`). Where the reproduction matches the published number the method is right and the rest is like-for-like. The GloFAS side carries the same reanalysis-as-proxy caveat as the Google side: the Somalia spoke found GloFAS v4 drifting to about 0.9 of its reanalysis by lead 12, and no GloFAS v5 reforecast exists to test. Scripts: `scripts/rescore_{som,npl,nga,tcd,bgd}.py`, loaders `scripts/grrr_releases.py` and `scripts/incumbents.py`; raw results `outputs/rescore_*.csv`.

## Somalia: GRRR reanalysis against the SWALIM gauges

Reproduces the station-skill layer of `ds-aa-som-floods` (notebooks 02 and 06): best-lag Spearman of daily model discharge against the river's reference gauge level (Luuq for the Juba, Belet Weyne for the Shabelle), lags −10 to +30 days, 1998–2023, Gu = Mar–May, Deyr = Oct–Dec; and episode POD and FAR against each gauge's post-2000 Weibull RP3 level with the 14-day recession rule, 2002–2023, at the model's RP3 taken from the release's own return-period table (the baseline used the Flood Hub API thresholds, which the 2023 bucket's `return_periods.zarr` reproduces). The trigger-level F1 of 0.80 is a re-tune of the whole mechanism search and is not re-run here.

### Daily rank correlation against the reference gauge (best lag in days; negative = model lags the river)

| Station | Season | published ρ | 2023 ρ | 2026 ρ | lag pub / 23 / 26 | vs own gauge 23 / 26 | seasonal-peak ρ vs own gauge 23 / 26 |
|---|---|---|---|---|---|---|---|
| Dollow | Gu | 0.85 | 0.87 | 0.89 | 3 / 0 / -2 | 0.86 / 0.87 | 0.78 / 0.82 |
| Dollow | Deyr | 0.60 | 0.59 | 0.90 | -2 / -5 / 1 | 0.58 / 0.89 | 0.75 / 0.34 |
| Luuq | Gu | 0.87 | 0.87 | 0.89 | 0 / 0 / -3 | 0.87 / 0.89 | 0.85 / 0.86 |
| Luuq | Deyr | 0.58 | 0.58 | 0.89 | -5 / -5 / 0 | 0.58 / 0.89 | 0.74 / 0.62 |
| Bardheere | Gu | 0.87 | 0.87 | 0.87 | -1 / 0 / -7 | 0.86 / 0.88 | 0.67 / 0.75 |
| Bardheere | Deyr | 0.50 | 0.50 | 0.87 | -10 / -10 / -3 | 0.49 / 0.86 | 0.56 / 0.72 |
| Bualle | Gu | 0.86 | 0.86 | 0.86 | -1 / -1 / -10 | 0.88 / 0.87 | 0.69 / 0.75 |
| Bualle | Deyr | 0.46 | 0.46 | 0.85 | -10 / -10 / -5 | 0.66 / 0.83 | 0.61 / 0.73 |
| Belet Weyne | Gu | 0.81 | 0.81 | 0.89 | 6 / 6 / -2 | 0.81 / 0.89 | 0.85 / 0.85 |
| Belet Weyne | Deyr | 0.64 | 0.63 | 0.88 | 4 / 4 / 3 | 0.63 / 0.88 | 0.78 / 0.78 |
| Bulo Burti | Gu | 0.79 | 0.78 | 0.88 | 4 / 4 / -4 | 0.79 / 0.90 | 0.85 / 0.89 |
| Bulo Burti | Deyr | 0.62 | 0.62 | 0.87 | 2 / 2 / 1 | 0.55 / 0.82 | 0.70 / 0.66 |
| Jowhar | Gu | 0.78 | 0.78 | 0.87 | 4 / 4 / -6 | 0.78 / 0.84 | 0.36 / 0.28 |
| Jowhar | Deyr | 0.62 | 0.62 | 0.86 | 2 / 2 / -1 | 0.58 / 0.81 | 0.38 / 0.30 |

### Episodes at model RP3 against the gauge's post-2000 RP3 (shipped return periods)

| Station | gauge episodes | model episodes pub / 23 / 26 | POD pub / 23 / 26 | FAR pub / 23 / 26 | RP3 threshold m³/s 23 / 26 |
|---|---|---|---|---|---|
| Dollow | 3 | 5 / 5 / 8 | 1.00 / 1.00 / 1.00 | 0.40 / 0.40 / 0.62 | 534 / 928 |
| Luuq | 9 | 8 / 8 / 11 | 0.44 / 0.44 / 0.56 | 0.50 / 0.50 / 0.55 | 446 / 923 |
| Bardheere | 4 | 7 / 7 / 11 | 0.50 / 0.50 / 1.00 | 0.71 / 0.71 / 0.64 | 422 / 905 |
| Bualle | 7 | 6 / 6 / 9 | 0.43 / 0.43 / 0.71 | 0.50 / 0.50 / 0.44 | 423 / 891 |
| Belet Weyne | 10 | 8 / 8 / 11 | 0.50 / 0.50 / 0.70 | 0.38 / 0.38 / 0.36 | 334 / 507 |
| Bulo Burti | 9 | 8 / 8 / 10 | 0.44 / 0.44 / 0.44 | 0.50 / 0.50 / 0.60 | 343 / 504 |
| Jowhar | 10 | 10 / 10 / 10 | 0.20 / 0.20 / 0.20 | 0.80 / 0.80 / 0.80 | 348 / 501 |

**Reading.** The 2023 column reproduces the published daily ρ to two decimals at 12 of 14 station-seasons (Dollow differs by 0.02 and in lag; its record starts in 2015) and the published episode POD and FAR at all seven gauges. On the 2026 release the daily correlation against the reference gauge rises everywhere, most in Deyr (Juba 0.46–0.59 → 0.86–0.91; Shabelle 0.62–0.64 → 0.87–0.88), and the best lag moves from the model leading the river by 2–6 days in Gu to lagging it by 2–10 days, so the new model tracks the gauge more closely but later. Episode detection at RP3 improves at Bardheere (POD 0.50 → 1.00), Bualle (0.43 → 0.71), Belet Weyne (0.50 → 0.70) and Luuq (0.44 → 0.56) with FAR unchanged or lower, except Dollow where the model fires more often (FAR 0.40 → 0.62). Jowhar stays poor on both (POD 0.20), as it was. The seasonal-peak correlation against each gauge's own record is the one statistic that does not improve uniformly (Dollow Deyr 0.76 → 0.34), on 22 seasons. Bardheere's gauge is right-censored at bank-full and has a magnet value at 9.00 m, so its ranks carry ties.

### The proposal's GloFAS v5 leg through the same code (`--release glofas_v5`)

GloFAS v5 reanalysis per station from the spoke's blob (1999–2023), no shipped return periods so `derived` only. Columns: GloFAS v5 / 2023 bucket / 2026 release.

| Station | Gu ρ (lag) | Deyr ρ (lag) | gauge episodes | POD at RP3 | FAR at RP3 |
|---|---|---|---|---|---|
| dollow | 0.83 (-1) / 0.87 (0) / 0.89 (-2) | 0.87 (5) / 0.59 (-5) / 0.90 (1) | 3 | 0.33 / 1.00 / 1.00 | 0.67 / 0.40 / 0.62 |
| luuq | 0.85 (0) / 0.87 (0) / 0.89 (-3) | 0.85 (3) / 0.58 (-5) / 0.89 (0) | 9 | 0.44 / 0.44 / 0.56 | 0.50 / 0.50 / 0.55 |
| bardheere | 0.83 (-2) / 0.87 (0) / 0.87 (-7) | 0.80 (0) / 0.50 (-10) / 0.87 (-3) | 4 | 0.50 / 0.50 / 1.00 | 0.75 / 0.71 / 0.64 |
| bualle | 0.80 (-7) / 0.86 (-1) / 0.86 (-10) | 0.79 (-2) / 0.46 (-10) / 0.85 (-5) | 7 | 0.29 / 0.43 / 0.71 | 0.67 / 0.50 / 0.44 |
| belet_weyne | 0.78 (-3) / 0.81 (6) / 0.89 (-2) | 0.83 (4) / 0.63 (4) / 0.88 (3) | 10 | 0.60 / 0.50 / 0.70 | 0.14 / 0.38 / 0.36 |
| bulo_burti | 0.75 (-7) / 0.78 (4) / 0.88 (-4) | 0.82 (2) / 0.62 (2) / 0.87 (1) | 9 | 0.44 / 0.44 / 0.44 | 0.43 / 0.50 / 0.60 |
| jowhar | 0.69 (-10) / 0.78 (4) / 0.87 (-6) | 0.81 (0) / 0.62 (2) / 0.86 (-1) | 10 | 0.20 / 0.20 / 0.20 | 0.71 / 0.80 / 0.80 |

**Reading.** Against GloFAS v5, GRRR 2026 tracks every gauge more closely in both seasons (0.85–0.90 against 0.69–0.87) and catches as many or more RP3 episodes at every gauge, clearly more at Dollow, Bardheere, Bualle and Belet Weyne; FAR is lower at Bardheere and Bualle, higher at Belet Weyne and Bulo Burti. Jowhar is poor for all three.

## Nepal: model exceedance events against DHM danger-level crossings

Reproduces book chapter 05 of `ds-aa-npl-flooding`: DHM crossings of the danger level (Chatara 7.0 m, 9 crossings to 2012; Chisapani 10.5 m, 7 crossings to 2015), model days above RP2 or RP5 collapsed with a 7-day gap, matched within ±7 days. GRRR thresholds by the book's convention (quantile 1 − 1/RP of annual maxima over the full reanalysis) and from the release's table; GloFAS v4 at the Copernicus dashboard values, run through the same code.

| Station | RP | Source | convention | published | 2023: matched, false alarms | 2026: matched, false alarms | threshold 23 / 26 |
|---|---|---|---|---|---|---|---|
| Chatara | RP2 | GRRR | quantile_full |  | 1 of 9, 19 | 2 of 9, 27 | 4605 / 5555 |
| Chatara | RP2 | GRRR | shipped |  | 1 of 9, 17 | 2 of 9, 26 | 4626 / 5580 |
| Chatara | RP2 | GloFAS v4 | dashboard |  | 2 of 9, 14 | 2 of 9, 14 | 8113 / 8113 |
| Chatara | RP5 | GRRR | quantile_full |  | 1 of 9, 7 | 1 of 9, 5 | 5334 / 6592 |
| Chatara | RP5 | GRRR | shipped |  | 1 of 9, 7 | 1 of 9, 5 | 5298 / 6616 |
| Chatara | RP5 | GloFAS v4 | dashboard |  | 1 of 9, 1 | 1 of 9, 1 | 10306 / 10306 |
| Chisapani | RP2 | GRRR | quantile_full | 6 of 7 (KB page) | 6 of 7, 26 | 5 of 7, 32 | 5508 / 5094 |
| Chisapani | RP2 | GRRR | shipped |  | 6 of 7, 25 | 5 of 7, 31 | 5521 / 5117 |
| Chisapani | RP2 | GloFAS v4 | dashboard | 5 of 7 (KB page) | 5 of 7, 32 | 5 of 7, 32 | 5664 / 5664 |
| Chisapani | RP5 | GRRR | quantile_full | 4 of 7 (technical note) | 4 of 7, 7 | 2 of 7, 9 | 6399 / 6271 |
| Chisapani | RP5 | GRRR | shipped |  | 3 of 7, 6 | 2 of 7, 7 | 6459 / 6516 |
| Chisapani | RP5 | GloFAS v4 | dashboard |  | 1 of 7, 9 | 1 of 7, 9 | 6797 / 6797 |

**Reading.** The 2023 column gives GRRR 6 of 7 at Chisapani at RP2 and GloFAS 5 of 7, the knowledge-base numbers, and GRRR 4 of 7 at RP5, the technical note's number: the two published figures were the same test at two return periods, not two windows. On the 2026 release Chisapani drops to 5 of 7 at RP2 (6 of 7 with thresholds fitted inside the DHM window) and 2 of 7 at RP5, with false alarms as numerous as before (31–35 model events for 7 real crossings at RP2). Chatara is poor for every model and release (2 of 9 at best). The step 1 result applies: Nepal's peaks are short spikes, and a reanalysis exceedance test says little about what a 7-day forecast would do. Part of the presentation's event list was itself identified from model reanalyses; only the DHM crossings are used here.

## Nigeria: GRRR reanalysis against GRDC observed discharge

Reproduces notebook 08 on the multistate branch of `ds-aa-nga-flooding`: GRDC daily discharge from blob, daily Spearman on overlapping days, wet-season (Jul–Nov) annual maxima with the notebook's completeness filters (≥120 wet-season days, no gap over 14 days in Aug–Oct, ≥15 valid years), empirical 3-yr and 5-yr thresholds on each side, hits, false alarms, misses and F1. The notebook's GRDC-to-gauge mapping is carried as is; Lokoja and Wuroboki have two candidate basins each and both are shown.

| Station | basin | years | daily ρ 23 / 26 | peak ρ published / 23 / 26 | 3-yr hits/FA/misses 23 → 26 | F1 3-yr 23 / 26 | F1 5-yr 23 / 26 | note |
|---|---|---|---|---|---|---|---|---|
| Makurdi | `1120911340` | 16 | 0.85 / 0.94 |  0.43 / 0.34 | 4/2/2 → 3/2/3 | 0.67 / 0.55 | 0.25 / 0.50 | nan |
| Umaisha | `1120904190` | – | 0.74 / 0.80 | – | – | – | – | excluded: only 8 valid wet-season years; nan |
| Lokoja | `1120908000` | 38 | 0.69 / 0.80 |  0.57 / 0.76 | 7/6/7 → 10/3/4 | 0.52 / 0.74 | 0.50 / 0.62 | notebook's first choice |
| Lokoja | `1120909890` | 38 | 0.69 / 0.80 |  0.58 / 0.77 | 7/6/7 → 10/3/4 | 0.52 / 0.74 | 0.50 / 0.62 | notebook's alternative |
| Kende | `1120750570` | 17 | 0.83 / 0.70 |  0.45 / 0.57 | 4/2/2 → 5/1/1 | 0.67 / 0.83 | 0.75 / 0.50 | nan |
| Yidere Bode | `1120755820` | 36 | 0.85 / 0.80 | 0.76 (KB page) 0.76 / 0.83 | 10/2/2 → 9/4/4 | 0.83 / 0.69 | 0.62 / 0.62 | nan |
| Wuroboki | `1121971560` | – | 0.55 / 0.44 | – | – | – | – | excluded: only 8 valid wet-season years; notebook's first choice |
| Wuroboki | `1120842550` | – | 0.52 / 0.53 | – | – | – | – | excluded: only 8 valid wet-season years; notebook's alternative; the 2025 trigger gauge |
| Ibi | `1120887720` | – | 0.89 / 0.93 | – | – | – | – | excluded: only 10 valid wet-season years; nan |
| Baro | `1120870480` | – | 0.52 / 0.58 | – | – | – | – | excluded: only 8 valid wet-season years; nan |
| Onitsha | `1120975380` | – | 0.75 / 0.92 | – | – | – | – | excluded: only 7 valid wet-season years; not QA'd in the notebook |

**Reading.** The 2023 column gives the published annual-peak Spearman of 0.76 at Yidere Bode. Five of the nine GRDC stations pass the notebook's completeness filters; Wuroboki, Umaisha, Ibi, Baro and Onitsha have 7–10 valid years and are reported for daily correlation only. On the 2026 release the annual-peak correlation rises at Yidere Bode (0.76 → 0.83), Lokoja (0.57 → 0.76) and Kende (0.45 → 0.57) and falls at Makurdi (0.43 → 0.34); daily correlation rises at Makurdi and Lokoja and falls at Kende and Yidere Bode. The 3-yr exceedance agreement improves at Lokoja (F1 0.52 → 0.74) and Kende (0.67 → 0.83) and worsens at Yidere Bode (0.83 → 0.69) and Makurdi (0.67 → 0.55). Mixed, on 16–38 years per station; no single direction.

## Chad: model annual peaks at N'Djamena against the DRE observed level

Reproduces `pa-aa-tcd-flooding/exploration/dre_glofas.md` and the 2025 document's annex: annual peak of the DRE observed level at N'Djamena (station TP) and of the model, 2003–2022 with 2006 and 2008 dropped for incomplete observations (18 years); the 4-yr level on each side as the quantile 1 − 1/4 of the annual peaks; years each side flags; Spearman of the peaks; mean days the model peak precedes the observed peak. GloFAS v4 reanalysis from the repo's processed blob is run through the same code. The GRRR basin is the largest river within 10 km of the GloFAS cell (`hybas_1120734190`), not yet confirmed.

| Model | years | observed 4-yr years | model 4-yr years | hits of 5 | false negatives | false positives | peak ρ | days early, mean |
|---|---|---|---|---|---|---|---|---|
| GloFAS v4 reanalysis (published: 3 of 5, FN 2019 2020, FP 2003 2005, 31 d early) | 18 | 2010,2012,2019,2020,2022 | 2003,2005,2010,2012,2022 | 3 | 2019,2020 | 2003,2005 | 0.69 | 31 |
| GRRR, 2023 bucket | 18 | 2010,2012,2019,2020,2022 | 2010,2012,2019,2020,2022 | 5 | none | none | 0.83 | 20 |
| GRRR, November 2026 release | 18 | 2010,2012,2019,2020,2022 | 2012,2018,2019,2020,2022 | 4 | 2010 | 2018 | 0.74 | 31 |

**Reading.** The framework runs on GloFAS v4, and GloFAS through this code gives the document's numbers exactly. Against it, the November 2026 release flags 4 of 5 (catches 2019 and 2020, misses 2010, adds 2018), peak ρ 0.74 against 0.69, and the same 31-day lead on the observed peak: better than the incumbent on years flagged, level on timing. The 2023 bucket was better still, the same five years as the gauge with no miss and no false alarm, ρ 0.83, 20 days early. Eighteen years and five flood years.

## Bangladesh: GRRR reanalysis events against FFWC severe floods at Bahadurabad

Observed events from the FFWC record on the shared drive: water level at or above the danger level (19.5 m) plus 0.85 m for three consecutive days, as the framework defines a severe flood; seven events, 1988, 2012, 2016, 2017, 2019 and two in 2020 (the 1987–2019 file holds only days above the danger level, which is enough for this definition but not for annual peaks). Model events above RP5, collapsed with a 7-day gap, matched within ±7 days, 1987–2020. No published detection figure for this station is on the KB page. The incumbent is GloFAS v4 at Bahadurabad (the framework was calibrated on v3.1 and runs on v4), from the spoke's station-extracted yearly files on the shared drive (1979–2022), scored the same way at the quantile 1 − 1/5 of its own annual maxima. Basin `hybas_4121501030`, largest river within 10 km, 2-yr flow 69,700 m³/s, plausible for the Jamuna but unconfirmed.

| Release | RP5 convention | threshold m³/s | observed events | model events | matched | misses | false alarms |
|---|---|---|---|---|---|---|---|
| 2023 | shipped | 57,063 | 7 | 10 | 3 | 4 | 6 |
| 2023 | quantile_full | 57,295 | 7 | 9 | 3 | 4 | 5 |
| 2026 | shipped | 80,205 | 7 | 11 | 3 | 4 | 8 |
| 2026 | quantile_full | 82,242 | 7 | 8 | 2 | 5 | 6 |
| GloFAS v4 (ran on) | quantile_full | 97,393 | 7 | 9 | 3 | 4 | 6 |

**Reading.** GloFAS v4, which the framework runs on, matches 3 of 7 with 6 false alarms; the 2023 bucket the same 3 with 5 or 6; the 2026 release 3 of 7 with 8 false alarms at the shipped RP5, or 2 of 7 with 6 at the quantile. Nothing separates the three at this station. 1988 and 2012 go unmatched by all; the miss set for GRRR is 1988, 2016, 2017 and one of the 2020 pair. A reanalysis above RP5 is a crude stand-in for the framework's readiness trigger (≥50% of the GloFAS ensemble above RP5 at up to 15 days), so this is a station-skill reading, not a trigger one.

## Year by year

`scripts/year_ledger.py` builds the table the frameworks use themselves: per framework and year, the framework's published backtest; the model it ran on (the incumbent, scored from its own reanalysis); then, on one rule, whether the incumbent, the 2023 bucket, the 2026 release and the observed record each reach the empirical Weibull level at the framework's return period fitted on the same baseline years (1998–2023, cut to the observed record's coverage); EM-DAT people affected by floods; and CERF flood allocations from the OneGMS mirror in the team database (read through the Databricks SSH tunnel; the figure shows rapid response and anticipatory combined, the CSV keeps them apart). Each column's flags over the baseline and the implied return period are written to `outputs/year_ledger_rates.csv` and printed in the figure headers, so the columns are comparable; the rates file also carries each framework's trigger source line, shown under the panel title. On the incumbent column: Nigeria 6 of 26 (same six years on all three models); Somalia GloFAS v5 9 of 22 against GRRR 2026 7 and the gauges 10; Chad GloFAS v4 5 of 20 against 5 and the gauge's 4; Nepal 4 of 22 all round on the drive's updated DHM file (Chatara to 2019; the book and the rescore above use the earlier file, to 2012, to reproduce the published numbers); Bangladesh 5 of 26 against 5. The incumbent GloFAS series are the spokes' copies extended to mid-2026 from the Copernicus Early Warning Data Store at the same cells and versions (`scripts/fetch_glofas_recent.py`), so the ran-on column runs to 2025 wherever the framework runs on GloFAS; EWDS stamps each daily mean at the end of its 24-hour window; the spoke copies differ (Chad, Nepal and Somalia at the start of the day, Bangladesh at the end), so the fetched days are shifted per spoke to join. Checked on overlap years the spokes already hold (`outputs/glofas_recent/verify/`): once shifted, the EWDS cell equals the spoke copy to the decimal at N'Djamena (2024) and Belet Weyne (2023); at Chatara and Bahadurabad the gauge coordinates pointed at neighbouring cells, and the cells that reproduce the spoke series (26.825 N 87.125 E; 25.175 N 89.675 E, where the 2022 peak matches exactly and the rest within GRIB packing of the spoke's larger box) are the ones fetched. The flags did not change at either station. The GRRR 2023 bucket ends in December 2023 and stays blank after it. Under each panel, four rows per flag column against two impact measures that are independent of the models: EM-DAT people affected in events whose location text mentions the monitored basin (1998 on; whole-event totals, matched on the words in `BASIN_WORDS`), and CERF rapid-response flood US$ (2006 on). Years with a CERF anticipatory allocation are dropped from every statistic for that framework: the allocation is the framework firing, so keeping them would score the backtest and the incumbent against themselves, and rapid response under-reads in those years. Rows: Spearman of the 0/1 flag against the amount with a bootstrap 90% interval (shown as a half-width; columns closer than that are not distinguishable), then hits / misses / false alarms against the impact years, defined as the years whose amount reaches the empirical Weibull level at the framework's return period on the same baseline. Each panel carries a taint line saying which columns share a source with the trigger and whether impact data went into the design (from the framework review). Years with no record in a source count as zero within the years it covers (`outputs/year_ledger_impact_corr.csv`). Output: `outputs/year_ledger.csv`; figure on the working page.

### The paired answer

`outputs/year_ledger_paired.csv`: per framework and impact measure, on the comparison window (baseline years both models of the key pair cover, minus the framework's own anticipatory years), the impact years caught by GRRR 2026 and by the incumbent, their difference, and a bootstrap 90% interval over years; plus the pooled row. 5 Nov 2026:

| Measure | 2026 vs incumbent, pooled | difference [90%] | per framework (2026 vs incumbent of N) |
|---|---|---|---|
| EM-DAT basin, people affected | 15 vs 17 of 29 | −2 [−7, +3] | NGA 3 v 3 of 6; SOM 3 v 3 of 4; NPL 2 v 2 of 4; TCD 3 v 3 of 5; BGD 2 v 3 of 5; NER 2 v 3 of 5 |
| CERF rapid response, US$ | 8 vs 12 of 16 | −4 [−7, −1] | NGA 3 v 3 of 3; SOM 2 v 3 of 3; NPL 0 v 1 of 2; TCD 2 v 2 of 2; BGD 0 v 1 of 3; NER 1 v 2 of 3 |

The EM-DAT difference is within noise; the CERF one is not, but CERF rapid response is the record the incumbents' own forecasts helped shape (the people allocating were watching GloFAS or Flood Hub), and three of the six rows sit on unconfirmed basins. The defensible statement is non-inferiority on the gauge tests and no evidence of superiority on the humanitarian record; a difference smaller than about one flood in five cannot be resolved on these records. The working page carries this as its top section with a per-framework scorecard.

## What this says so far

- The published station-skill numbers are reproducible from the public buckets and the team's gauge records, which is the precondition for any benchmark claim.
- Against the models the frameworks actually run on: GRRR 2026 is better than GloFAS v5 at every Somali gauge (closer tracking, more episodes caught) and better than GloFAS v4 at N'Djamena on the annex test (4 of 5 against 3 of 5); level with GloFAS v4 at Chatara and Bahadurabad, where every model is poor. Against the 2023 bucket, the only incumbent that is Google's own, Nigeria is mixed, Somalia better in Deyr with a later signal, Chad worse (the 2023 bucket had 5 of 5).
- None of this is a trigger-outcome result. Those need the frameworks' own thresholds refitted on the release (the magnitudes differ) and, for the forecast side, the ten-season reforecast rather than the reanalysis.

Still to do in step 2: Uganda (the impact backtest is a pipeline with zones and catch windows; adding a GRRR leg means running it through that pipeline), the Niger new question, Nigeria 2025's GloFAS leg at Wuroboki, and Chad's FloodScan province check; the five real-gauge basin mappings remain to be confirmed first.
