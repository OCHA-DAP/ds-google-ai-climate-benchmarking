# ds-google-ai-climate-benchmarking

Benchmark of Google's AI flood forecasts against the models used in the OCHA/CERF
anticipatory action (AA) frameworks. Deliverable 1 of the Google.org AA grant: an
independent evidence base on where AI climate models add value for anticipatory action
across the CERF portfolio, due 30 June 2027. Floods first; cyclones when Google's cyclone
data arrives.

**Status (4 Nov 2026):** stock-take and data checks. No benchmark protocol has been
agreed yet; see [the stock-take](docs/stock-take-2026-11-03.md) for the working note the
team is commenting on, and [docs/grrr-2026-11.md](docs/grrr-2026-11.md) for what we know
about Google's November 2026 data release.

## The plan the team agreed

1. **Check the new Google release.** Google published a new model and dataset in
   November 2026 (reanalysis 1981 to 2025, reforecast 2016 to 2025, leads 0 to 10 days,
   every HydroBasins sub-basin). Confirm the reforecast and reanalysis follow the same
   pattern over the same dates before using either. Done for the identity at lead 0 and
   for coverage; the per-lead check is the first analysis task.
2. **Framework by framework, which can be evaluated against Google.** Subset to where
   Google has usable output at the framework's trigger station. The dataset has a basin
   for every CERF country; whether the basin at the station is any good is the question.
3. **Framework by framework, what each used and how it was evaluated.** Gauge data where
   it exists, and the humanitarian impact record that was brought in, formally or in
   charts: EM-DAT affected people and past CERF rapid-response flood allocations.
4. **If the reforecast is too short, use the reanalysis as its proxy.** Only where the
   step-1 check shows the lead-L reforecast tracks the reanalysis at that basin. It does
   in Somalia (rank correlation 0.99) and not in Taraba, Nigeria (0.59).

## What is here

| Path | What |
|---|---|
| `docs/stock-take-2026-11-03.md` | Export of the team's working note (a Claude Doc; the live version is the doc, this copy is for the record) |
| `docs/grrr-2026-11.md` | Google's November 2026 release: contents, dates, the lead-0 identity, coverage in the CERF countries, caveats, questions for Google |
| `docs/decisions/` | Architecture decision records (MADR) |
| `docs/superpowers/specs/` | Design specs, once the protocol is agreed |
| `scripts/grrr_2026_11.py` | Open the public GRRR release anonymously, fetch one basin, verify the lead-0 identity |
| `scripts/check_grrr_coverage.py` | Map every basin outlet to a country, count basins with and without predictions, sample time series for missing values |
| `scripts/stations.py` | The trigger stations of the flood frameworks, one entry per station and season, with the Flood Hub id or coordinates each framework uses |
| `scripts/map_stations.py` | Map each station to a sub-basin of the release: identity for Flood Hub ids (they share the HydroBASINS numbering), largest river within 10 km for real gauges, flagged for a human check |
| `scripts/proxy_check.py` | Is the reanalysis a proxy for the reforecast? Per station and lead 1 to 10: daily and seasonal-peak Spearman, bootstrap interval, reforecast-to-reanalysis ratio above the 2-yr level. Results in `docs/proxy-check-2026-11.md` |
| `scripts/grrr_releases.py` | One loader for both public releases (2023 bucket, November 2026), so a re-score runs the same code on each |
| `scripts/rescore_som.py` | Somalia: GRRR reanalysis against the SWALIM gauges, best-lag daily Spearman and RP3 episode POD/FAR, reproducing `ds-aa-som-floods` notebooks 02 and 06 |
| `scripts/rescore_npl.py` | Nepal: model exceedance events against DHM danger-level crossings at RP2 and RP5, reproducing `ds-aa-npl-flooding` book chapter 05, GloFAS v4 included |
| `scripts/rescore_nga.py` | Nigeria: GRRR reanalysis against GRDC observed discharge, daily and annual-peak Spearman and 3/5-yr exceedance F1, reproducing `ds-aa-nga-flooding` notebook 08. Results of all three in `docs/rescore-2026-11.md` |
| `scripts/rescore_tcd.py` | Chad: model annual peaks at N'Djamena against the DRE observed level, 4-yr exceedance years, peak correlation and days early, reproducing the 2025 document's annex; GloFAS v4 included |
| `scripts/rescore_bgd.py` | Bangladesh: GRRR and GloFAS v4 reanalysis events above RP5 against FFWC severe floods (danger level + 0.85 m for 3 days) at Bahadurabad |
| `scripts/incumbents.py` | The model each framework actually ran on, as daily reanalysis series: GloFAS v4 at Bahadurabad, Chatara/Chisapani and N'Djamena, GloFAS v5 at the Somali gauges; labels and trigger-source lines per framework |
| `scripts/fetch_glofas_recent.py` | Extends each incumbent GloFAS series past the spoke copy's end from the Copernicus Early Warning Data Store (same version, same cell; requests queue there for hours, so it submits all then polls). `outputs/glofas_recent.parquet`, appended by `incumbents.py` |
| `scripts/page/` | The working page: `build.py` aggregates the step-1 coverage outputs (`data.py`), adds the incumbent legs to the rescore summary (`summary.py`), draws every figure as inline SVG from the `outputs/` files (`charts.py`) and writes `outputs/page/index.html`, which is published as the Claude artifact. Decision: `docs/decisions/0002` |
| `scripts/year_ledger.py` | Year by year per framework: the framework's backtest, the model it ran on, each Google release's reanalysis at the framework's level, the observed record, EM-DAT affected and CERF flood allocations, plus each column's correlation with them and, for the key pair, the 2x2 over framework-years (impact years caught, false alarms, CSI) with bootstrap intervals. `outputs/year_ledger.csv`, `year_ledger_rates.csv`, `year_ledger_impact_corr.csv`, `year_ledger_paired.csv` |

## Running

```bash
uv sync
uv run scripts/grrr_2026_11.py subhybas_1121902040          # one basin, prints shapes and the identity check
uv run scripts/check_grrr_coverage.py --iso NGA SOM NPL     # coverage for named countries, writes outputs/
uv run scripts/map_stations.py                              # outputs/stations_mapped.csv
uv run scripts/proxy_check.py                               # outputs/proxy_check.csv, needs the mapping first
uv run scripts/rescore_npl.py --release 2026                # also 2023; needs AA_DATA_DIR
uv run scripts/rescore_som.py --release 2026                # needs DSCI_AZ_BLOB_DEV_SAS
uv run scripts/rescore_nga.py --release 2026                # needs DSCI_AZ_BLOB_DEV_SAS
uv run scripts/rescore_tcd.py --release 2026                # needs DSCI_AZ_BLOB_DEV_SAS
uv run scripts/rescore_bgd.py --release 2026                # needs AA_DATA_DIR; also runs the GloFAS v4 leg
uv run scripts/rescore_som.py --release glofas_v5           # the Somalia proposal's GloFAS v5 leg
uv run scripts/fetch_glofas_recent.py                       # needs ~/.cdsapirc; hours of EWDS queue, resumable
uv run scripts/year_ledger.py                               # needs blob and AA_DATA_DIR; writes outputs/year_ledger.csv
uv run scripts/page/build.py                                # the working page, outputs/page/index.html, from the outputs above
```

The Google data is public (CC-BY-4.0) and read anonymously from
`gs://flood-forecasting/hydrologic_predictions/distributed_model_2026_11/`. No credentials
needed. The reforecast store is 156 GB and the reanalysis 64 GB; the scripts read one
128-basin chunk at a time and never download the whole thing.

## Related

- [ds-knowledge-base](https://github.com/OCHA-DAP/ds-knowledge-base): the frameworks
  (`frameworks/*-flooding/`), the Somalia multi-source analysis, trigger-design and
  return-period methods. This repo is a spoke of that hub.
- [ds-google-flood-hub](https://github.com/OCHA-DAP/ds-google-flood-hub): the live Flood
  Forecasting API, its gauges and events. Live forecasts are gauge-keyed; this release is
  HydroBasins-keyed. Mapping between the two is open work.
- [ds-aa-nga-flooding](https://github.com/OCHA-DAP/ds-aa-nga-flooding),
  [ds-aa-som-floods](https://github.com/OCHA-DAP/ds-aa-som-floods),
  [ds-aa-npl-flooding](https://github.com/OCHA-DAP/ds-aa-npl-flooding): the three
  existing Google-vs-GloFAS comparisons.
- Google's reading notebook for the release (a Colab shared with the team): the source for
  the dataset description in `docs/grrr-2026-11.md`.
