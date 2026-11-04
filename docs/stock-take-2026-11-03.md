# Google flood AI benchmark: stock-take and directions

> Exported on 4 Nov 2026 (rev 17) from the team's Claude Doc,
> <https://claude.ai/artifact/9bZjp1k49Yfz51H3d5zrbV>, where comments and edits continue.
> This copy is for the record. The embedded timeline chart does not export; it is in the doc.
> Written before Google's November 2026 release was known: the GRRR archive table and the
> ERA5 paragraph below describe the previous bucket. See `grrr-2026-11.md` for the update.

Nov 3, 2026 · Zack Arno

## Purpose

This is the working note for Deliverable 1 of the Google.org anticipatory action grant: an independent evidence base on where Google's AI flood and cyclone models add value, across the CERF portfolio, due 30 June 2027. Scope for now is **riverine floods only**; the cyclone side waits for Google's cyclone data. It feeds Deliverable 2 (integrate where the model adds value, structured product feedback to Google where it does not) and Deliverable 3 (an AI product on HDX Signals), so the output has to be reproducible, not a one-off report.

The question this note sets up: the team has already compared Google's model with GloFAS three times, with three different methods that give different answers. Deliverable 1 needs one protocol that works across frameworks built in different ways. Edit inline or comment; the open questions are at the end.

## What we have already done

Three comparisons of Google's model against GloFAS exist, each built for one framework and each with its own method. They cannot be stacked into one evidence base as they stand.

| Study | Date | Models | Ground truth | Method | Verdict | Where |
| --- | --- | --- | --- | --- | --- | --- |
| Nepal technical note | Jun 2026 | GloFAS, GEOGloWS v2, GRRR | DHM danger-level crossings at Chatara and Chisapani | hits, misses, false alarms at RP5 | GRRR 4 of 7 at Chisapani vs GloFAS 1; GEOGloWS rejected; "run a proper evaluation of GRRR" | ds-aa-npl-flooding, book/05-07 |
| Nigeria 2025 framework | Aug 2025 | GloFAS, GRRR at one gauge | FloodScan wet-season maxima | grid search of threshold pairs, OR logic, F1 | both kept, OR'd; F1 0.80 at 5-yr | ds-aa-nga-flooding, exploration/2025 |
| Nigeria 2026 framework | Jul 2026 | 42 Google and GloFAS gauges | FloodScan extent (daily Spearman); GRDC observed flow (annual-peak Spearman, 0.76 at Yidere Bode) | gauge selection by skill, 6-of-10 consensus, Weibull RP | Google is the action trigger, GloFAS the readiness trigger | ds-aa-nga-flooding, exploration/2026 |
| Somalia multi-source | Aug 2026 | GloFAS v4/v5, GRRR, GEOGloWS | SWALIM gauges, 1999-2023 | median Spearman per river and season; F1 against gauge events | Google carries the Gu action legs, GloFAS the Deyr; mixed vs one-model F1 identical at 0.80 | ds-aa-som-floods, analysis/11 |

Two things stand out. First, the same Nepal study is reported two ways: the technical note gives GRRR 4 of 7 at Chisapani, the KB page gives 6 of 7 at RP2 with a 7-day matching window. Same station, same models, a different threshold and possibly a different window; which of the two explains the gap is not yet written down. Second, every study picked a different ground truth: observed gauge crossings, FloodScan extent, or observed-flow ranks. The disagreement is in the protocol, not the model.

## The flood portfolio

Six endorsed CERF flood frameworks, one in development, plus Somalia (an analysis, not yet a CERF framework). Only the triggers marked "yes" below run on a forecast model at a station Google could also forecast; the others are gauge readings, seasonal outlooks, bulletins or flood-extent observations, where the question is whether Google could add a leg, not whether it beats the incumbent.

| Framework | Trigger | Product | Station or unit | Variable | Threshold | Lead | Like-for-like with Google? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Nigeria 2026 | action | Google GRRR | 10 gauges, Benue (Adamawa) | discharge | per-gauge 4-yr RP, 6 of 10 same day | <= 7 d | already Google |
| Nigeria 2026 | readiness | GloFAS v4 | Wuroboki | discharge | 3,132 m3/s (3-yr) | <= 12 d | yes, at 7 d |
| Chad 2025 | readiness + action | GloFAS v4 ensemble mean | N'Djamena (Chari) | discharge | 4,542 m3/s (\~4-yr) | <= 14 d, <= 10 d | yes |
| Bangladesh 2025 | readiness | GloFAS (doc v3.1, runs v4) | Bahadurabad, Baruria | discharge | >50% prob > RP5 for 3 days | <= 15 d | yes |
| Bangladesh 2025 | action | FFWC forecast + GloFAS/RIMES trend | Bahadurabad, Mawa | water level | danger level + 0.85 / 0.5 m | <= 5 d | partly: Google vs FFWC |
| Nepal 2025 | readiness | GloFAS ensemble | Chatara (Koshi) | discharge | >= 50% > RP5 (10,300 m3/s) | <= 7 d | yes |
| Nepal 2025 | action | DHM bulletin | Chatara | qualitative | 3 conditions | <= 3 d | no |
| Niger 2025 | action | ABN gauge (observed) | Niamey | water level | 592 / 604 cm (3- and 5-yr) | 0 | no: could add a forecast leg |
| Burkina Faso 2025 | action | SEAS5 monthly; CONASUR + IMERG | 5 regions | precipitation | 3-yr RP per region | 0-25 d | no |
| Uganda (dev) | Teso zone | GloFAS v4 (IBF portal) | district zonal max | discharge | >= 60% > 5-yr | <= 5 d | no: Google has no gauges in Uganda |
| Somalia (analysis) | action | GRRR (Gu), GloFAS v5 (Deyr) | 7 SWALIM gauges, Juba and Shabelle | discharge rank | per-gauge RP5-6, 3 of 4 / 2 of 3 | <= 6 d | already mixed |

The frameworks also differ in how the threshold is set (Gumbel on the dashboard, empirical Weibull, government danger level plus an offset), how ensembles are read (>= 50% of members, >= 60%, the mean, deterministic), and what counts as a flood in the historical record. Each of those is a parameter the protocol has to fix.

## Data we can use

The Google archive is public and long enough to start on; the limiting data is observed river records at our own stations.

Four kinds of record appear in this note, and only one of them is a measurement:

- **Gauge observation**: a sensor in the river. The only record that was measured rather than modelled.
- **Reanalysis** (also called historical simulation or retrospective): the river model run over the past on reconstructed past weather. Long and gap-free, no prediction involved; every system computes its return-period thresholds from it.
- **Reforecast**: the forecasting process replayed for past issue dates with the weather forecasts that were available then. The only record that shows what a trigger would have seen.
- **Live forecast**: today's run, the thing the trigger fires on. GloFAS archives its forecasts on the Copernicus store and GEOGloWS has kept its own since July 2024; Google's API returns today only, so our snapshots are the only Google record after mid-2023.

**Google GRRR** (bucket `gs://flood-forecasting/hydrologic_predictions/model_id_8583a5c2_v0/`, anonymous access, read 3 Nov 2026):

| Product | Period | Gauges | Leads |
| --- | --- | --- | --- |
| Reanalysis | daily, 1980-01-01 to 2023-12-23 | 1,031,646 | none |
| Reforecast | daily issues, 2016-01-01 to 2023-06-30 (2,738 issues) | 1,031,646 | 0 to 7 days |

The archive stops mid-2023. After that, only the live API exists, and it returns today's forecast only. The team's daily snapshots in blob (Somalia, Nigeria, since 2025) are the only issued-forecast record for 2023 onward. **GloFAS** v4 has a reforecast archive (Chad used 2003-2022 at N'Djamena); no v5 reforecast exists yet, so a reforecast-to-reforecast comparison is a v4 comparison.

**What feeds the reanalyses.** The 'observed past weather' behind a river reanalysis is itself a product. All three river systems run on ECMWF's ERA5 weather reanalysis: GloFAS Historical on ERA5, GEOGloWS on ERA5 runoff, and GRRR on ERA5-Land plus two rainfall products, IMERG (satellite) and CPC (gauge-based), that the model learns to weigh; for forecast days GRRR switches to ECMWF's HRES weather forecast. That description is from the published model paper (Nearing et al., Nature 2024). Our own material never states the inputs, and whether the model running today uses the same ones is a question for Google. Rain is the field ERA5 handles worst, because rainfall is barely assimilated and comes from the model's own short-range runs, which is why GRRR's extra rainfall inputs matter most in the tropics. Two consequences for the benchmark: the three systems share an upstream error source, so agreement between them proves little, and a river gauge is the only record in this note that was measured rather than modelled.

**Observed river records**, by how usable they are today:

| Tier | Framework | Station(s) | Variable | Record | Source |
| --- | --- | --- | --- | --- | --- |
| 1, ready | Niger | Niamey (GRDC 1234150), Garbe-Kourou | discharge, level via rating curve | 1979-2024, 46 seasons | GRDC, ABN |
| 1, ready | Nigeria | 5 GRDC stations with >= 15 wet seasons (Yidere Bode, Lokoja, Makurdi, Kende, Ibi); NiHSA gauges | discharge | patchy | GRDC via Niger Basin Authority, NiHSA |
| 1, ready | Somalia | 7 of 16 SWALIM gauges | level | 1999-2023 | FAO SWALIM |
| 2, level only | Bangladesh | Bahadurabad, Baruria, Mawa, Goalando | level vs FFWC danger level | unknown | FFWC |
| 2, level only | Nepal | Chatara, Chisapani | level vs DHM danger level | to 2012 and 2015, no rating curve | DHM |
| 3, thin | Chad | N'Djamena | level | unknown; GloFAS peaks \~31 days early | DRE |
| 3, thin | Burkina Faso | Yaran, Tenado, Pa (Mouhoun) | level | none in hand | DGRE |
| 3, none | Uganda | none |  |  |  |

Tier 2 can be compared by rank and by event crossing, not by magnitude. Tier 3 needs a GRDC catalogue search (the Chari at N'Djamena is a long-standing GRDC station) and a request through the country offices. **FloodScan SFED** (1998 to present, every country) is the one observed-hazard record that exists everywhere; Nigeria used it to select gauges and Uganda and Chad use it where gauges are missing.

## Record lengths at a glance

&#91;embedded content: typed from the KB framework pages, the Somalia analysis and the Nepal technical note, 3 Nov 2026 · 1978 to 2026\]

The Google reforecast starts in 2016, and every threshold in the portfolio was calibrated on a record that starts in 2003 or earlier, so a trigger-level Google backtest at a framework's own return period rests on at most seven seasons. The reanalysis is the only Google record that spans the calibration windows, which is why the reforecast-to-reanalysis check comes first. Dashed bars are records whose exact years are not written down in the KB: the GRDC series behind Nigeria's rank check, the DHM record behind Nepal's danger-level crossings (it ends in 2012 at Chatara and 2015 at Chisapani), and the reanalysis years behind Bangladesh's thresholds. Four records have no dates anywhere in the KB and are left off the chart: the FFWC record for Bangladesh, the GloFAS reforecast Nepal's 2024 design was tested on, the GloFAS reforecast at Uganda's Teso reporting point, and the CHIRPS-GEFS v2 hindcast behind Uganda's rain thresholds. Filling those in is a comment on this paragraph.

## Lessons already recorded

The past studies left five rules that any protocol has to build in. Each one cost a framework something when it was missed.

1. **Reforecast, not reanalysis, is what a trigger sees.** GEOGloWS looked fine on its retrospective and its live forecast ran at about half that magnitude, so a threshold set on the retrospective was never crossed (Nepal). Before any reanalysis-based calibration, measure how well the model's reforecast tracks its own reanalysis at that station: GRRR scored rank rho >= 0.99 at action leads in Somalia and >= 0.95 at 7 days in most of Nigeria, but 0.59 in Taraba. GloFAS v4 is also self-consistent at action leads (ratio about 1.00) and drifts to about 0.90 of its reanalysis by lead 12; GEOGloWS runs at 0.85 to 0.91 of its retrospective even at lead 1. The property holds per system and per lead, so it is measured, never assumed.
2. **Compare ranks, not magnitudes.** Google's modelled flow differs from observed flow by large factors at every Nigerian GRDC station, yet annual peaks rank consistently (Spearman 0.76 at Yidere Bode). Rank-based scoring also works at level-only stations, which magnitude-based scoring cannot.
3. **Few events, so bound the search.** Somalia's first mixed-model result scored F1 0.93; constraining the search from 57,600 to 4,608 configurations against 7 severe events brought it to 0.80, equal to the one-model design. Report confidence intervals, and fix the protocol before looking at results.
4. **No lookahead in the truth set.** Somalia's gauge benchmark fitted return levels on 2000-2026 while counting events in 1999-2023; removing that changed the truth set from 8 to 7 years and every score with it. Fit thresholds only on data before the period being scored.
5. **Model versions drift.** The doc for Bangladesh calibrates on GloFAS v3.1 and the monitor runs v4; Nigeria pins v4 while v5 rolls out; no GloFAS v5 reforecast exists. The GRRR bucket is one model id, and the live API may be newer. Every number needs a model version next to it.

Two smaller ones: stated lead times can be inflated (the Nigeria 2025 doc claims 14-25 days, its own footnotes give 5-7), and a model that assimilates no gauge data cannot reproduce dam-driven floods (Nigeria 2012).

## Possible directions

The choice is not "integrate Google into each framework" against "one standard". The thing that can be standard is the **protocol**; the thing that has to stay local is the **station, the target return period and the lead time** each framework was designed around. Three ways to cut it:

| Direction | What it means | For | Against |
| --- | --- | --- | --- |
| A. Per-framework integration | Build a Google leg into each framework's own repo, the way Nigeria and Somalia did, and read the results across | Answers the operational question directly (Deliverable 2 falls out of it); uses each repo's existing event definitions and code | Six methods again; results not comparable; most frameworks have no like-for-like trigger; expensive per framework |
| B. One shared protocol, applied locally | One repo holds the scoring code and the rules (event definition, matching window, RP method, no lookahead, version tags); it is run at every framework's station with that framework's target RP and lead | Comparable numbers across the portfolio; one place to fix a rule; reruns when a model version changes; what the training cohorts can learn | Loses framework-specific nuance (consensus rules, basin splits); needs a station-to-gauge mapping per framework; a second codebase next to the framework repos |
| C. Two layers | B for the evidence base (station-level skill, portfolio-wide); A only where B says Google adds value, as the Deliverable 2 step | Separates "is the model good here" from "should the trigger change"; the second only happens where the first says yes | Two phases, so the first results are skill scores, not trigger recommendations |

Within B or C, the protocol itself has two levels, and the evidence base probably needs both:

- **Station skill**: does the model's reanalysis rank floods the way the observed record does, and does its reforecast track its reanalysis at the leads the framework uses. Needs only the public bucket, GloFAS reforecasts and the observed record. Possible now at tier-1 stations.
- **Trigger outcome**: at the framework's own threshold and lead, which years would each model have fired, against the impact record. This is the number CERF and the working groups act on, and the one most exposed to the few-events problem.

Where Google has no gauge near the station (unknown for Chad, Niger, Bangladesh, Nepal; none in Uganda), the question changes to whether a nearby Google gauge adds a leg, and that belongs in Deliverable 2.

## Proposed first steps

All of these run on data we already hold or can read anonymously, and none commits us to a direction. The first two answer the premise a colleague raised: if GRRR's reforecast tracks its reanalysis closely, reanalysis against observed gauges is a valid first pass.

- [ ] Reforecast-vs-reanalysis check at every trigger station in the table above: rank rho by lead, 2016-2023, from the public bucket. Where it holds, the 44-year reanalysis becomes usable as the history.
- [ ] Reanalysis-vs-observed at the tier-1 stations (Niamey, the five Nigerian GRDC stations, the Somali SWALIM gauges): annual-peak Spearman and event hits, GRRR and GloFAS side by side, same protocol. Nigeria and Somalia have done one of the two already; the work is to rerun both under one rule.
- [ ] Google gauge coverage at every trigger station: which `hybas_` id, how far from the station, quality-verified or not. Needs the API key the monitors use; the Uganda "no gauges" claim gets checked at the same time.
- [ ] Start saving the daily API forecast at every trigger station now, the way Somalia and Nigeria already do. The public archive ends June 2023; the issued-forecast record for 2027 is whatever we save between now and then.
- [ ] GRDC catalogue search for the Chari at N'Djamena, the Mouhoun stations and the Brahmaputra at Bahadurabad; a data request through the Chad, Burkina Faso and Bangladesh offices for what GRDC lacks.
- [ ] Reconcile the two Nepal numbers (4 of 7 vs 6 of 7 at Chisapani) and write down which return period and matching window produced which. That is the first protocol decision, and it is cheap.

## Open questions for the team

Answer in comments on the line, or edit the text.

1. **Audience.** Is the evidence base written for CERF and the country working groups (per-framework recommendations), for Google's product team (per-model diagnostics, the Deliverable 2 feedback), or both? It sets whether the headline is a framework table or a model table.
2. **Somalia.** It is the richest Google-vs-GloFAS precedent but not a CERF framework. In scope as a test case?
3. **Protocol decisions.** Event matching window (same day, 3, 7 days), return-period method (Weibull on the reanalysis), ensemble rule for GloFAS, and the impact record per country. Who decides, and by when?
4. **Repo.** A separate repo (working name `ds-google-ai-climate-benchmarking`) that imports station definitions from the framework repos, or code inside each framework repo? Direction B or C implies the separate repo.
5. **Google contact.** Does the grant bring a technical contact? The ask would be a reforecast from the model version running live, for 2023 onward, at the gauges we name. The 2016-2023 archive we already have. Two more asks: which weather products drive the model now, for the reanalysis and for forecast days, and whether the public bucket's model id is the one running live.
6. **Gauge data not in the KB.** How long are the FFWC and NiHSA records, and does anyone hold DRE (Chad) or DGRE (Burkina Faso) data from past missions?
7. **Cyclones.** When does Google's cyclone data arrive, and does the same protocol structure (station skill, then trigger outcome) carry over to track and wind triggers?

## Sources

- [ds-knowledge-base](https://github.com/OCHA-DAP/ds-knowledge-base): `frameworks/*-flooding/`, `analysis/som-flooding-multisource.md`, `methods/trigger-design.md`, `methods/return-periods.md`
- [Technical note: Evaluating GEOGLOWS, GloFAS and Google GRRR](https://docs.google.com/document/d/1iORZn8POkhJCNTVdCWicOdP1zfRgjHBkPNseOhuotFw/edit) (team Drive, Jun 2026)
- [03: Model Validation - Google](https://docs.google.com/presentation/d/1wOM0ULfrAoe80evv0L5rCuo02jf-jd5kdIV1kBs2Cw8/edit), Nigeria 2026 framework (team Drive, Apr 2026)
- [AI4AA workshop deck, Google Berlin, 23 Oct 2026](https://docs.google.com/presentation/d/1vNCwjokzCeyVgcSZBl2hsZb4XmpV_SAdbIebwKlBWyQ/edit) (team Drive)
- [ds-aa-nga-flooding](https://github.com/OCHA-DAP/ds-aa-nga-flooding), [ds-aa-som-floods](https://github.com/OCHA-DAP/ds-aa-som-floods), [ds-aa-npl-flooding](https://github.com/OCHA-DAP/ds-aa-npl-flooding), [ds-google-flood-hub](https://github.com/OCHA-DAP/ds-google-flood-hub)
- GRRR bucket periods and gauge counts: read directly from `gs://flood-forecasting`, 3 Nov 2026
- &#91;INTERNAL VERSION\] OCHA x Anticipatory Action Funding Proposal 2026 (team Drive, Grants/Google.org 2026)
