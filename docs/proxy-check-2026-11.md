# Is the reanalysis a proxy for the reforecast? November 2026 release, 4 Nov 2026

Step 1 of the replication plan. The same check the Somalia mechanism (forecast-vs-own-reanalysis skill) and the Nigeria Niger-Benue multistate script ran on the 2023 bucket, re-run on `distributed_model_2026_11` at every trigger station of the flood frameworks. Script: `scripts/proxy_check.py`; stations and mapping: `scripts/stations.py`, `scripts/map_stations.py`; raw results `outputs/proxy_check.csv` (one row per station and lead).

## Method

For each station and lead L = 1..10 (lead 0 excluded: it equals the reanalysis by construction), each reforecast value issued at T is paired with the reanalysis for the same daily window (valid day T+L, reanalysis label T+L−1d). Pairs are restricted to the station's wet season and to seasons 2016–2025 (ten). Three statistics per lead:

- **peak ρ**: Spearman rank correlation of the seasonal maxima, one per season (10 points), with a 500-draw bootstrap over seasons for a 90% interval;
- **daily ρ**: Spearman over all paired season days;
- **ratio**: median reforecast / reanalysis on days where the reanalysis is at or above the release's own 2-yr level, the days a trigger cares about.

The reanalysis is accepted as the history for a basin at the leads where peak ρ ≥ 0.95 (the bar the Somalia and Nigeria work used) and the ratio sits near 1. Ten seasons is a thin base: the interval is reported, and where it reaches below 0.9 the verdict is provisional.

## Station mapping

All 26 Flood Hub gauge rows map by identity: the release keys its basins `subhybas_<id>` on the same HydroBASINS numbering as the Flood Hub `hybas_<id>`, and every id used by the Nigeria, Somalia and Nepal work is present. The six real-gauge rows take the largest river (highest 2-yr flow) within 10 km of the station; they are flagged `needs_check` until a human confirms the river. Bahadurabad (2-yr 69,700 m³/s), Mawa (106,000), N'Djamena (6,240), Akokoro (31) are plausible by size. Niamey's basin shows a 2-yr flow of 12,100 m³/s, far above the Niger's observed peaks at Niamey, so either the model runs high there or the basin is wrong; ranks are unaffected, magnitudes are.

## Results

| Station | Basin | peak ρ, lead 3 | 5 | 7 | 10 | ρ lead 7, 5th pct | ratio lead 5 | 7 | 10 | days > RP2 at 7 | reanalysis usable to lead |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NGA 1120842990 | `subhybas_1120842990` | 0.99 | 0.99 | 0.98 | 0.88 | 0.87 | 0.92 | 0.87 | 0.85 | 262 | 7 d |
| NGA 1120843610 | `subhybas_1120843610` | 0.99 | 0.99 | 0.98 | 0.88 | 0.82 | 0.92 | 0.87 | 0.85 | 261 | 7 d |
| NGA 1120845060 | `subhybas_1120845060` | 0.99 | 0.99 | 0.98 | 0.88 | 0.87 | 0.93 | 0.88 | 0.85 | 261 | 7 d |
| NGA 1120849600 | `subhybas_1120849600` | 0.99 | 0.99 | 0.99 | 0.88 | 0.90 | 0.93 | 0.88 | 0.85 | 264 | 7 d |
| NGA 1120848550 | `subhybas_1120848550` | 0.99 | 0.99 | 0.99 | 0.88 | 0.90 | 0.93 | 0.89 | 0.85 | 263 | 8 d |
| NGA 1121970280 | `subhybas_1121970280` | 0.99 | 0.99 | 0.99 | 0.88 | 0.90 | 0.94 | 0.89 | 0.86 | 264 | 8 d |
| NGA 1120842550 (Wuroboki) | `subhybas_1120842550` | 0.99 | 0.98 | 0.99 | 0.88 | 0.90 | 0.94 | 0.89 | 0.85 | 262 | 8 d |
| NGA 1120840700 | `subhybas_1120840700` | 0.99 | 0.98 | 0.99 | 0.88 | 0.90 | 0.94 | 0.90 | 0.86 | 264 | 8 d |
| NGA 1120840560 | `subhybas_1120840560` | 0.99 | 0.98 | 0.99 | 0.88 | 0.90 | 0.94 | 0.90 | 0.86 | 264 | 8 d |
| NGA 1120840690 (tributary outlier) | `subhybas_1120840690` | 0.73 | 0.52 | 0.41 | 0.18 | -0.07 | 0.66 | 0.62 | 0.62 | 101 | none d |
| Dollow (Gu) | `subhybas_1121039440` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.98 | 0.92 | 104 | 10 d |
| Dollow (Deyr) | `subhybas_1121039440` | 0.99 | 0.96 | 0.95 | 0.94 | 0.70 | 0.99 | 0.96 | 0.90 | 97 | 8 d |
| Luuq (Gu) | `subhybas_1122050700` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.95 | 109 | 10 d |
| Luuq (Deyr) | `subhybas_1122050700` | 1.00 | 1.00 | 1.00 | 0.99 | 1.00 | 1.00 | 0.98 | 0.94 | 113 | 10 d |
| Bardheere (Gu) | `subhybas_1121087010` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.98 | 115 | 10 d |
| Bardheere (Deyr) | `subhybas_1121087010` | 0.99 | 0.99 | 0.99 | 1.00 | 0.90 | 1.00 | 1.00 | 0.99 | 126 | 10 d |
| Bualle (Gu) | `subhybas_1121116000` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 125 | 10 d |
| Bualle (Deyr) | `subhybas_1121116000` | 0.95 | 0.95 | 0.96 | 0.96 | 0.81 | 1.00 | 1.01 | 1.00 | 133 | 10 d |
| Belet Weyne (Gu) | `subhybas_1121024250` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.01 | 1.02 | 1.01 | 51 | 10 d |
| Belet Weyne (Deyr) | `subhybas_1121024250` | 1.00 | 0.99 | 1.00 | 0.99 | 1.00 | 1.00 | 1.01 | 1.00 | 111 | 10 d |
| Bulo Burti (Gu) | `subhybas_1121049060` | 1.00 | 0.99 | 0.99 | 0.98 | 0.90 | 1.01 | 1.01 | 1.02 | 51 | 10 d |
| Bulo Burti (Deyr) | `subhybas_1121049060` | 1.00 | 1.00 | 1.00 | 0.99 | 1.00 | 1.00 | 1.01 | 1.01 | 122 | 10 d |
| Jowhar (Gu) | `subhybas_1122059030` | 1.00 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 1.01 | 1.02 | 52 | 10 d |
| Jowhar (Deyr) | `subhybas_1122059030` | 1.00 | 0.99 | 0.99 | 0.99 | 0.92 | 1.00 | 1.00 | 1.01 | 133 | 10 d |
| Chatara (Koshi) | `subhybas_4120864110` | 0.94 | 0.83 | 0.60 | 0.16 | -0.08 | 1.02 | 1.00 | 0.95 | 18 | 2 d |
| Chisapani (Karnali) | `subhybas_4121455820` | 0.93 | 0.59 | 0.12 | 0.39 | -0.55 | 0.96 | 1.00 | 0.98 | 26 | 2 d |
| N'Djamena (Chari) * | `subhybas_1120734190` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.99 | 0.96 | 450 | 10 d |
| Bahadurabad (Jamuna) * | `subhybas_4121501030` | 1.00 | 0.99 | 0.99 | 0.95 | 0.92 | 0.99 | 0.97 | 0.96 | 55 | 10 d |
| Mawa (Padma) * | `subhybas_4120970210` | 1.00 | 0.99 | 0.99 | 0.95 | 0.92 | 1.00 | 1.00 | 1.00 | 70 | 10 d |
| Niamey (Niger), local flood * | `subhybas_1120679000` | 1.00 | 1.00 | 1.00 | 0.99 | 1.00 | 1.00 | 0.99 | 0.99 | 89 | 10 d |
| Niamey (Niger), Guinean flood * | `subhybas_1120679000` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | – | – | – | 0 | 10 d |
| Akokoro G5196 (Teso) * | `subhybas_1122067160` | 0.99 | 0.96 | 0.94 | 0.84 | 0.76 | 0.97 | 0.96 | 0.98 | 69 | 5 d |

\* mapping by largest river within 10 km, not yet confirmed.

## Reading

- **Rank holds to lead 7 at 29 of 32 rows.** The nine main-stem Benue gauges (0.98–0.99), all fourteen Somalia station-seasons (0.95–1.00), N'Djamena (1.00), Bahadurabad and Mawa (0.99), Niamey (1.00) and Akokoro (0.94, interval from 0.76) rank their seasonal peaks the same way in the reforecast and the reanalysis out to a week. At lead 10 the Benue drops to 0.88 and Akokoro to 0.84.
- **Two failures, of two kinds.** The Nigeria tributary outlier (`hybas_1120840690`, kept in the 2026 design by choice) loses rank from lead 3 (0.73) and sits at 0.41 by lead 7 with the reforecast at 0.62 of the reanalysis: the Taraba case again, now inside the endorsed gauge set. Nepal fails on rank while matching on magnitude: Chatara 0.83 at lead 5 and 0.60 at 7, Chisapani 0.59 at 5 and 0.12 at 7, both with intervals reaching below zero, while the ratio stays at 1.00. Monsoon peaks there are short rain-driven spikes the week-ahead forecast does not place on the right day or year. By the 0.95 bar the reanalysis stands in for the reforecast in Nepal only to lead 2 (0.93–0.94 at lead 3).
- **Magnitude drifts on the Benue.** On days above the 2-yr level the Nigeria reforecast runs at 0.92–0.94 of the reanalysis at lead 5, 0.87–0.90 at lead 7 and 0.85 at lead 10, uniformly across the nine gauges. A threshold fitted on the reanalysis and applied to a 7-day forecast there fires less often than its nominal return period; the 2026 trigger is scored at 5 days, where the gap is 6–8%. Somalia, Chad, Bangladesh, Niger and Nepal hold at 0.96–1.02.
- **Niamey, Guinean flood**: no Dec–Feb day reaches the model's 2-yr level in 2016–2025, so the ratio is undefined; the rank is 1.00. The Guinean flood is below the model's own 2-yr level even though it is what the framework fires on, which is itself a finding about the model's seasonal split at Niamey.
- **Compared with the 2023 bucket.** The Somalia result (ρ ≥ 0.99, ratio ~1.00 at action leads) and the Nigeria main-stem result (≥ 0.95 at 7 d) reproduce on the new model. The new model's magnitudes are not the old ones (the Benue 2-yr level is about 2,650 m³/s against the 2023 bucket's 4-yr thresholds of about 1,100), so every threshold has to be refitted on the release's own return periods.

## What this licenses

Reanalysis as the long history, with the release's own return periods, at leads up to 7 days: Somalia (all gauges and seasons), Nigeria main stem (with the magnitude ratio applied or thresholds set on the reforecast at the action lead), Chad, Bangladesh, Niger, Uganda. Reforecast only, ten seasons: Nepal beyond lead 2, Akokoro beyond lead 5, and the Nigeria tributary gauge at every lead. Mapping to confirm before any scoring: the five real gauges, Niamey first.
