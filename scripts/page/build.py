"""Build the working page (outputs/page/index.html) from the repo outputs: step-1 coverage, proxy check, rescores, year ledger."""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import charts
import data
import gauge
import summary

PAGE = Path(charts.REPO) / "page"
PAGE.mkdir(exist_ok=True)
data.write()
summary.patch()
GAUGE = gauge.write()
GV = gauge.verdicts(GAUGE)
d = json.load(open(PAGE / "page_data.json"))
T = d["totals"]


def n(x):
    return f"{x:,}"


mx = max(c["basins"] for c in d["countries"])
crow = "".join(
    f"<tr class='{'flood' if c['flood'] else ''}'><td class='iso'>{c['iso']}</td><td>{c['country']}{' <span class=tag>flood framework</span>' if c['flood'] else ''}</td><td class='num'>{n(c['basins'])}</td><td class='num'>{n(c['with_prediction'])}</td><td class='num {'warn' if c['missing'] else 'ok'}'>{c['missing'] if c['missing'] else '0'}</td><td class='bar'><span style='width:{100 * c['basins'] / mx:.1f}%'></span></td></tr>"
    for c in d["countries"]
)
mmx = d["missing_top"][0]["n"]
names = {
    "CAN": "Canada",
    "GRL": "Greenland",
    "USA": "United States (Alaska)",
    "RUS": "Russia",
    "FJI": "Fiji",
}
mrow = "".join(
    f"<tr><td class='iso'>{m['iso']}</td><td>{names.get(m['iso'], m['iso'])}</td><td class='num'>{n(m['n'])}</td><td class='bar'><span class='miss' style='width:{100 * m['n'] / mmx:.1f}%'></span></td></tr>"
    for m in d["missing_top"]
)
srow = "".join(
    f"<tr><td class='iso'>{s['iso']}</td><td class='num'>{s['chunks']}</td><td class='num'>{s['basins']}</td><td class='num ok'>{s['ra']:.1f}%</td><td class='num ok'>{s['rf']:.1f}%</td><td class='num ok'>{s['allnan']}</td></tr>"
    for s in d["sample"]
)
tot_s = {"ch": sum(s["chunks"] for s in d["sample"]), "b": sum(s["basins"] for s in d["sample"])}
KB = "https://github.com/OCHA-DAP/ds-knowledge-base/blob/main/"

# framework review rows: (framework, trigger, evaluation, truth_gauge, truth_impact, metric, page)
F = [
    (
        "Nigeria 2026<br><small>endorsed, live</small>",
        "GRRR, 6 of 10 gauges over own 4-yr Weibull level (action); GloFAS v4 at Wuroboki, 3,132 m³/s, ≤12 d (readiness)",
        "Gauge selection by skill, then threshold calibration; readiness lead-time evaluation; reforecast-vs-reanalysis rank check",
        "FloodScan SFED extent, daily Spearman per gauge (1998–2023), for selection and for the accuracy table (4-yr FloodScan indicator). GRDC observed flow at 5 stations, annual-peak Spearman (0.76 at Yidere Bode)",
        'Not scored. The document says the sources are "grounded by national historical observational and impact data"; the scoping note lists "flooding impact data (where available)"; NEMA and NiHSA records picked the LGAs. No impact year appears in the accuracy statistics<sup>P D</sup>',
        "context",
        "Simulated fire years 1998, 1999, 2012, 2018, 2019, 2022 (6 of 26). Readiness POD 0.75, false alarm 25%, scored against reanalysis fire years. Reforecast-vs-reanalysis rank ρ ≥0.95 at 7 d in most states, 0.59 in Taraba (2016–2022)",
        "frameworks/nga-flooding/2026-07-27.md",
        "analysis/nga-niger-benue-multistate.md",
    ),
    (
        "Nigeria 2025<br><small>superseded; activated 8 Sep 2025</small>",
        "GloFAS OR GRRR at Wuroboki, single station",
        "Threshold calibration by grid search over (GloFAS rank, GRRR rank) pairs with OR logic, target 4.5-yr overall RP",
        "FloodScan SFED wet-season annual maxima (1998–2023), as the flood record. No gauge",
        'Design input. The trigger specification set the target as "major events based on historical impact data"<sup>D</sup>; the 2024 notebooks overlay the CERF flood years 2013, 2018, 2022 on the reanalysis peaks and 2022 is presented as "the most recent CERF allocation year"<sup>R D</sup>; an impact-comparison notebook lines up NEMA 2022, the NiHSA flood record, UNICEF and IOM records against FloodScan exposure, without a written conclusion<sup>R</sup>. Scoring stayed on FloodScan',
        "design",
        "F1 0.80 (detection 47%, false alarm 10%) at the 5-yr FloodScan benchmark; F1 0.55 at 4-yr. PDF prose and table disagree on which benchmarks. Fire years 1998, 1999, 2003, 2012, 2019, 2022",
        "frameworks/nga-flooding/2025-08-11.md",
        None,
    ),
    (
        "Chad 2025<br><small>endorsed; activated 28 Sep 2024 under 2024 version</small>",
        "GloFAS v4 ensemble mean at N'Djamena (Chari), 4,542 m³/s; ≤10 d action, ≤14 d readiness",
        "Reforecast backtest of the threshold against the reanalysis, then an accuracy table against the observed river level; province check against flood extent",
        "DRE observed level at N'Djamena, 18 usable years: accuracy table at an observational 4-yr level (false negatives 2019, 2020; false positives 2003, 2005), and the 31-day early bias. FloodScan extent defines the five most severe Mayo-Kebbi Est years (2024, 2012, 2022, 2010, 2003), all caught<sup>P</sup>",
        "Shown, before the framework. The June 2022 exploration compared FloodScan and GloFAS with CERF allocations, EM-DAT and an IFRC list: all agree on 2012, EM-DAT and IFRC show high needs in 2020–2021 that FloodScan and GloFAS do not<sup>D R</sup>. Chad's 2024 timing notes replay 2012 and 2022, the CERF flood years<sup>D</sup>. The team's spec template uses N'Djamena as its worked example with \"must detect all relevant CERF allocation years\"; Chad's own filled spec was not located<sup>D</sup>",
        "shown",
        "Action fires 2003, 2005, 2010, 2012, 2022; readiness adds 2007, 2018 (2003–2022 GloFAS v4 reforecast). Against DRE level: 2 false negatives, 2 false positives in 18 years. The 2024 activation is outside the backtest",
        "frameworks/tcd-flooding/2025-07-31.md",
        None,
    ),
    (
        "Bangladesh 2025<br><small>endorsed; activated 2020, 2024 under earlier versions</small>",
        "GloFAS RP5 at Bahadurabad, Baruria (readiness); FFWC forecast danger level + 0.85 / 0.5 m at Bahadurabad, Mawa (action)",
        "Detection statistics of the GloFAS reforecast against its reanalysis and against FFWC observed levels (repo notebooks 02–08); GloFAS v3 vs v4 comparison (09, 10)",
        "FFWC observed water levels at Hardinge Bridge, Goalando, Bahadurabad, Mawa; record length not stated in the KB",
        "Design input, in the 2020 pilot. The impact-based trigger analysis set the severe level from a household survey and historic damage records: DL + 1 m at Bahadurabad meant about 25% of household assets damaged, 25% of houses fully damaged and 40% of people affected; NDRCC affected-population counts by year were shown<sup>P D</sup>. The 2025 document carries that definition (>40% affected, >20% assets) with DL + 0.85 m. No impact record in the detection statistics",
        "design",
        "POD / FAR per station; values not carried on the KB page. Calibrated on GloFAS v3.1, service runs v4 since Jul 2023; v4 mismatch at Bahadurabad in 2024",
        "frameworks/bgd-flooding/2025-04-25.md",
        "frameworks/bgd-flooding/2020-06-26.md",
    ),
    (
        "Nepal 2025<br><small>endorsed; activated 2022, 2024 under earlier versions</small>",
        "GloFAS ≥50% over RP5 at Chatara (readiness); DHM 3-day bulletin, three qualitative conditions (action)",
        "Independent skill test in the GEOGloWS evaluation: GloFAS, GEOGloWS v2 and GRRR exceedance events matched to DHM danger-level crossings within ±7 d. The endorsed trigger itself was set on the Copernicus Gumbel RP",
        "DHM danger-level crossings: Chatara 7.0 m (record to 2012), Chisapani 10.5 m (to 2015). Water level only, no rating curve",
        'Shown. The 2025 trigger presentation lists historical events per station with EM-DAT ticks and CERF allocations ("for any floods in Nepal, not necessarily in Chatara") beside the GloFAS and DHM dates<sup>D</sup>; the repo lists EM-DAT as an input<sup>R</sup>. Caution: several events in that list are marked "identified by Google reanalysis" or "identified by GloFAS reanalysis", so part of the truth set comes from the models under test. The document says the link between water level and impact "has not yet been clearly established"<sup>P</sup>',
        "shown",
        "GRRR 6 of 7 DHM events at Chisapani (KB page, RP2, ±7 d) vs 4 of 7 (technical note, RP5); GloFAS 5 of 7; GEOGloWS 0 of 7. GloFAS 10–35% low on extremes. GEOGloWS forecast ≈ half its retrospective",
        "frameworks/npl-flooding/draft-geoglows.md",
        "frameworks/npl-flooding/2025-08-25.md",
    ),
    (
        "Niger 2025<br><small>endorsed; activated Nov 2024, Jan 2026</small>",
        "Observed ABN level at Niamey: 592 cm mobilisation, 604 cm action. No forecast model",
        "Return-period calibration of the gauge itself: annual peaks by flood phase (local, Guinean) from GRDC discharge converted by a rating curve",
        "GRDC Niamey 1979–2024 (46 seasons); ABN levels 2005–2024. The gauge is the trigger, so there is nothing to validate it against",
        "Targeting and context. The pre-framework exploration correlated FloodScan with the ANADIA flood database (houses destroyed, people affected) per commune to pick the target communes<sup>R</sup>; the document cites the DesInventar 1973–2013 loss retrospective as context<sup>P</sup>; OCHA country-office flood tables sit in the Drive folder<sup>D</sup>. No impact year is set against the threshold years",
        "context",
        "592 cm = 3.0-yr, 604 cm = 5.1-yr; threshold reached in 8 local-flood years (1998, 2010, 2012, 2013, 2015, 2019, 2020, 2024) and 2 Guinean (1999, 2024). GloFAS at Garbe-Kourou explored, not endorsed",
        "frameworks/ner-flooding/2025-11-04.md",
        None,
    ),
    (
        "Burkina Faso 2025<br><small>endorsed; activated 8 Sep 2025, judged a false activation</small>",
        "SEAS5 monthly rain over 5 regions, 3-yr RP per region and month (Jul–Sep)",
        "Threshold calibration only, on the SEAS5 hindcast 1993–2024. No skill test",
        "None. River-gauge scenarios (Mouhoun, DGRE) deferred to 2026 with no code",
        "Context only. The document's Table 4 gives CONASUR flood victims by year 2013–2024 (299,077 in total) and the regions hit; it is not set against the SEAS5 threshold years<sup>P</sup>. The after-action review asks for local hydrometric and rain data",
        "context",
        "No metric. First activation produced no flood and activities ran out of season",
        "frameworks/bfa-flooding/2025-08.md",
        None,
    ),
    (
        "Uganda<br><small>in development, never activated</small>",
        "GloFAS v4 (reanalysis as perfect forecast, reforecast at G5196), CHIRPS-GEFS rain, lake altimetry, FloodScan fallback; four zones, Oct–Dec",
        "Backtest against an impact record: each zone's activation rate matched to its major-season frequency, then catches, misses and false alarms by lead window",
        "FloodScan per district, rank-based usability check. No river gauge",
        "Scored. The truth set is EM-DAT, DesInventar, curated press and IOM DTM, 2000–2024; major = ≥5 deaths or ≥5,000 affected, zone share. CERF rapid-response flood allocations 2007 and 2020 shown per zone<sup>K R</sup>",
        "scored",
        "Oct–Dec seasons 2000–2024 (25). Catch windows 30 d rain, 45 d GloFAS, 150 d lake. The KB page states Google Flood Hub has no gauges in Uganda; the November 2026 release has 1,849 basins there",
        "frameworks/uga-flooding/development.md",
        None,
    ),
    (
        "Somalia<br><small>analysis, no CERF framework yet</small>",
        "GRRR, GloFAS v5 and GEOGloWS pairs at 5 SWALIM gauges; consensus per basin and season, own RP5–6 levels",
        "Independent skill test against gauges, then station selection and a bounded trigger search; forecast-vs-own-reanalysis skill by lead; FloodScan cross-check",
        "FAO SWALIM river levels, 7 of 16 gauges, 1999–2023; seasonal maxima at Belet Weyne and Luuq as the benchmark, own empirical RP3/RP5",
        "Design input and shown. EM-DAT affected and deaths plus CERF allocations, basin-attributed, give the 47/53 impact shares behind the basin split; the trigger deck's year table sets trigger counts beside EM-DAT and CERF by year back to 1999 (Juba Deyr 2023: 2.8M affected, $10M CERF)<sup>K D</sup>. An impact threshold is left to the working group",
        "design",
        "Median Spearman per river and season; F1 0.80 (TPR 0.86, PPV 0.75) against 7 severe gauge years after the lookahead fix; GRRR and GloFAS v4 reforecast-vs-reanalysis ρ ≥0.99 at action leads; GEOGloWS live 0.85–0.91× its retrospective",
        "analysis/som-flooding-multisource.md",
        None,
    ),
    (
        "Yemen 2023<br><small>retired, not activated</small>",
        "CHIRPS-GEFS 3-day rain over IDP-site hulls, 2-yr RP (24 mm Hajjah, 20 mm Marib)",
        "Threshold and window choice tested against reported flood damage",
        "None (rain trigger)",
        "Design input. CCCM flood site reports 2021–2022 (shelter damage at IDP sites) chose the 3-day window and confirmed the 2-yr level; the repo starts from an impact-data exploration notebook<sup>K R</sup>",
        "design",
        "No formal score recorded",
        "frameworks/yem-flooding/2023.md",
        None,
    ),
    (
        "South Sudan 2022<br><small>retired, one allocation</small>",
        "No quantitative trigger; risk analysis and judgement",
        "None. Forecasts judged unreliable for the Sudd system",
        "None",
        "None<sup>K</sup>",
        "none",
        "None",
        "frameworks/ssd-flood/2022-05.md",
        None,
    ),
]
LEVEL = {
    "scored": ("Scored", "lv-scored"),
    "design": ("Design input", "lv-design"),
    "shown": ("Shown", "lv-shown"),
    "context": ("Targeting or context", "lv-context"),
    "none": ("None", "lv-none"),
}


def link(p):
    return f"<a href='{KB}{p}'>{p.split('/')[-1].replace('.md', '')}</a>" if p else ""


frow = "".join(
    f"<tr class='{LEVEL[l][1]}'><td class='fw'>{a}</td><td>{b}</td><td>{c}</td><td>{g}</td><td class='lvl'><span class='chip {LEVEL[l][1]}'>{LEVEL[l][0]}</span></td><td>{i}</td><td>{m}</td><td class='pg'>{link(p1)}{'<br>' + link(p2) if p2 else ''}</td></tr>"
    for a, b, c, g, i, l, m, p1, p2 in F
)

# replication plan rows: (framework, same evaluation means, needs first, kind)
R = [
    (
        "Nepal",
        "GRRR exceedance events (own return periods from the release, RP2 and RP5) matched to DHM danger-level crossings at Chatara and Chisapani within ±7 d; hits, misses, false alarms. Settle the 4 of 7 vs 6 of 7 protocol first, and drop or label the events the presentation marks as identified by a model reanalysis",
        "DHM record (held, to 2012 and 2015); outlet basin for each station",
        "EM-DAT-ticked events in the 2025 presentation; CERF flood allocations for Nepal (six rapid-response, two AA)",
        "re-score",
    ),
    (
        "Somalia",
        "Median Spearman per river and season against SWALIM levels; F1 at the 1-in-3 gauge benchmark with thresholds fitted before the scored period; reforecast-vs-reanalysis by lead at the 5 live gauges",
        "SWALIM series (held); map the 7 Flood Hub gauge ids to outlet basins",
        "The deck's year table: EM-DAT affected and CERF by basin and season back to 1999",
        "re-score",
    ),
    (
        "Nigeria 2026",
        "Annual-peak Spearman against GRDC at the 5 stations; daily Spearman against FloodScan for the 10 Adamawa gauges; the simulated fire years at the endorsed 6-of-10 rule with the release's own levels",
        "GRDC series (held); outlet basin for each GRDC station and each of the 10 gauges",
        "CERF flood years 2013, 2018, 2022 (the repo constant); NEMA 2022, NiHSA record, IOM and UNICEF records in the impact-comparison notebook",
        "re-score",
    ),
    (
        "Nigeria 2025",
        "Re-running the grid search with new GRRR re-tunes a trigger. It does not evaluate the model. Skip, or report only the FloodScan F1 of the existing thresholds re-applied",
        "nothing new",
        "as above",
        "re-tune, not an evaluation",
    ),
    (
        "Bangladesh",
        "Detection statistics of GRRR at Bahadurabad and Mawa against FFWC observed danger-level crossings, same POD/FAR code as the repo",
        "FFWC record (length unknown, question 6 in the stock-take); outlet basins for the two stations",
        "NDRCC affected-population series in the 2020 trigger analysis; CERF flood allocations 2017, 2019, 2020, 2024",
        "re-score",
    ),
    (
        "Chad",
        "Fire years 2003–2025 at N'Djamena for GRRR at the release's 4-yr level, ≤10 d and ≤14 d, beside GloFAS's 2003, 2005, 2010, 2012, 2022; the same accuracy table against the DRE observed 4-yr level; FloodScan extent for Mayo-Kebbi Est",
        "DRE series (used in the PDF, holding unconfirmed); outlet basin for the Chari at N'Djamena",
        "CERF flood allocation 2012 (2009, 2011 on displacement); EM-DAT and IFRC lists from the 2022 exploration; 2022 and 2024 people affected from the document",
        "re-score",
    ),
    (
        "Uganda",
        "GRRR reanalysis as a leg in the impact backtest, same catch windows and major-event rule, Oct–Dec 2000–2024. New: Google was not evaluable before",
        "Zone-to-basin mapping (largest river cell per district, as the IFRC rule does)",
        "The record itself: EM-DAT, DesInventar, press, DTM 2000–2024; CERF 2007, 2020",
        "re-score",
    ),
    (
        "Niger",
        "No model to replicate. A new question instead: rank of GRRR annual peaks at Niamey against GRDC, and whether a forecast leg would have led the 604 cm crossings",
        "Outlet basin for Niamey",
        "ANADIA commune-level events; the OCHA country-office flood tables (2014, 2016, 2023)",
        "new evaluation",
    ),
    (
        "Burkina Faso, Yemen, South Sudan",
        "Nothing to replicate: rain triggers or no trigger, no river truth set",
        "",
        "CONASUR victims by year (Burkina Faso) if a rain comparison is ever wanted",
        "out of scope",
    ),
]

import csv as _csv

_rows = list(_csv.DictReader(open(charts.REPO + "proxy_check_summary.csv")))


def _f(x):
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "–"


def _cls(v, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    return "ok" if v >= hi else ("warn" if v < lo else "")


prow = ""
for r in _rows:
    lead = int(r["lead_ok"])
    flag = ' <span class="tag">check basin</span>' if r["check"] == "True" else ""
    prow += f"<tr><td class='fw'>{r['station']}{flag}</td><td class='iso'>{r['subhybas'].replace('subhybas_', '')}</td>"
    for k in ("rho3", "rho5", "rho7", "rho10"):
        prow += f"<td class='num {_cls(r[k], 0.9, 0.95)}'>{_f(r[k])}</td>"
    prow += f"<td class='num'>{_f(r['lo7'])}</td>"
    for k in ("ratio5", "ratio7", "ratio10"):
        prow += f"<td class='num {_cls(r[k], 0.9, 0.95)}'>{_f(r[k])}</td>"
    prow += f"<td class='num'>{r['n7']}</td><td class='num {'ok' if lead >= 7 else ('warn' if lead < 3 else '')}'>{lead if lead else 'none'}</td></tr>"


_rs = json.load(open(charts.REPO + "rescore_summary.json"))


def _c(v):
    try:
        return "ok" if float(v) >= 0.8 else ("warn" if float(v) < 0.5 else "")
    except (TypeError, ValueError):
        return ""


som_corr_rows = "".join(
    f"<tr><td class='fw'>{r['station']}</td><td>{r['season']}</td><td class='num'>{r['pub']}</td><td class='num'>{r['cinc']}</td><td class='num'>{r['c23']}</td><td class='num {_c(r['c26'])}'>{r['c26']}</td><td class='num'>{r['laginc']} / {r['lag23']} / {r['lag26']}</td><td class='num'>{r['owninc']} / {r['own23']} / {r['own26']}</td></tr>"
    for r in _rs["som_corr"]
)
som_ep_rows = "".join(
    f"<tr><td class='fw'>{r['station']}</td><td class='num'>{r['obs']}</td><td class='num'>{r['pub_mod']} / {r['modinc']} / {r['mod23']} / {r['mod26']}</td><td class='num'>{r['pub_pod']} / {r['podinc']} / {r['pod23']} / <b>{r['pod26']}</b></td><td class='num'>{r['pub_far']} / {r['farinc']} / {r['far23']} / <b>{r['far26']}</b></td></tr>"
    for r in _rs["som_ep"]
)
npl_rows = "".join(
    f"<tr><td class='fw'>{r['station']}</td><td>{r['rp']}</td><td>{r['source']}</td><td>{r['conv']}</td><td>{r['pub']}</td><td class='num'>{r['m23']}, {r['fa23']} FA</td><td class='num'>{r['m26']}, {r['fa26']} FA</td></tr>"
    for r in _rs["npl"]
    if r["conv"] in ("quantile_full", "dashboard")
)
nga_rows = "".join(
    (
        f"<tr><td class='fw'>{r['station']}</td><td class='iso'>{r['hybas'].replace('hybas_', '')}</td><td colspan='6' style='color:var(--muted)'>{r['excluded']}; daily ρ {r['daily23']} / {r['daily26']}</td></tr>"
        if r["excluded"]
        else f"<tr><td class='fw'>{r['station']}</td><td class='iso'>{r['hybas'].replace('hybas_', '')}</td><td class='num'>{r['years']}</td><td class='num'>{r['daily23']} / {r['daily26']}</td><td class='num'>{r['pub_peak']} {r['peak23']} / <b>{r['peak26']}</b></td><td class='num'>{r['hit3_23']} → {r['hit3_26']}</td><td class='num'>{r['f1_3_23']} / <b>{r['f1_3_26']}</b></td><td class='num'>{r['f1_5_23']} / <b>{r['f1_5_26']}</b></td></tr>"
    )
    for r in _rs["nga"]
)

FIG_PROXY = charts.fig_proxy_heatmap()
FIG_SOM = charts.fig_som_corr()
FIG_SOM_POD = charts.fig_som_pod()
FIG_NPL = charts.fig_npl()
FIG_NGA = charts.fig_nga()
FIG_TCD = charts.fig_tcd()
FIG_BGD = charts.fig_bgd()
FIG_SUMMARY = charts.fig_proxy_summary()
import os

FIG_LEDGER = charts.fig_ledger() if os.path.exists(charts.REPO + "year_ledger.csv") else ""
FIG_PAIRED = charts.fig_paired() if os.path.exists(charts.REPO + "year_ledger_paired.csv") else ""
FIG_GAUGE = charts.fig_gauge()
_pd = {
    (r["framework"], r["impact"]): r
    for r in csv.DictReader(open(charts.REPO + "year_ledger_paired.csv"))
}
_cs = {
    r["framework"]: r
    for r in csv.DictReader(open(charts.REPO + "year_ledger_impact_corr.csv"))
    if r["column"] == "grrr_2026" and r["impact"] == "emdat_basin"
}
_rt = {r["framework"]: r for r in csv.DictReader(open(charts.REPO + "year_ledger_rates.csv"))}
SCORE = [  # framework key, basin status, forecast-proxy status
    ("Nigeria 2026", "Flood Hub gauges, known", "licensed to lead 7 on the main stem"),
    ("Somalia", "Flood Hub gauges, known", "licensed to lead 7"),
    ("Nepal 2025 (Chatara)", "Flood Hub gauge, known", "not licensed past lead 2"),
    ("Chad 2025", "largest river within 10 km, unconfirmed", "licensed to lead 7"),
    (
        "Bangladesh 2025 (Bahadurabad)",
        "largest river within 10 km, unconfirmed",
        "licensed to lead 7",
    ),
    (
        "Niger 2025",
        "largest river within 10 km, 2-yr flow implausible",
        "no forecast in the trigger",
    ),
]


def _verdict(fw):
    """On the critical success index of each measure: same, higher, lower, or mixed; Niger's basin is in doubt."""
    if fw == "Niger 2025":
        return "cannot tell", "warn"
    s = [float(_pd[(fw, m)]["csi_diff"]) for m in ("emdat_basin", "cerf_flood_usd")]
    if all(abs(v) < 1e-9 for v in s):
        return "same", "ok"
    if all(v <= 1e-9 for v in s):
        return "lower", "warn"
    if all(v >= -1e-9 for v in s):
        return "higher", "ok"
    return "mixed", ""


def _cell(r):
    return f"{r['hits_grrr_2026']} vs {r['hits_incumbent']} of {r['n_impact_years']} caught<br>FA {r['fa_grrr_2026']} vs {r['fa_incumbent']} · CSI {float(r['csi_grrr_2026']):.2f} vs {float(r['csi_incumbent']):.2f}"


score_rows = ""
for fw, basin, proxy in SCORE:
    gv, gd = GV[fw]
    gcls = {"higher": "ok", "lower": "warn", "same": "ok"}.get(gv, "")
    e, c = _pd[(fw, "emdat_basin")], _pd[(fw, "cerf_flood_usd")]
    v, cls = _verdict(fw)
    yrs = f"{_cs[fw]['window_start'][:4]}–{_cs[fw]['window_end'][:4]}" if _cs.get(fw) else ""
    aa = (_cs[fw]["aa_years_excluded"] or "none").replace(",", ", ") if _cs.get(fw) else ""
    score_rows += f"<tr><td class='fw'>{fw.replace(' (Chatara)', '').replace(' (Bahadurabad)', '')}</td><td>{_rt[fw]['incumbent_label']}</td><td class='{gcls}'><b>{gv}</b><br><span style='font-size:12px;color:var(--muted)'>{gd}</span></td><td class='num'>{_cell(e)}</td><td class='num'>{_cell(c)}</td><td class='{cls}'><b>{v}</b></td><td style='font-size:12px;color:var(--muted)'>{yrs}, AA out: {aa}; {basin}; {proxy}; hindcast</td></tr>"
pe, pc = _pd[("All frameworks", "emdat_basin")], _pd[("All frameworks", "cerf_flood_usd")]


def _pool(r):
    d, lo, hi = (int(float(r[k])) for k in ("diff", "diff_lo", "diff_hi"))
    w = {
        0: "no",
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
    }[abs(d)]
    return (
        f"{w} fewer" if d < 0 else f"{w} more" if d > 0 else "the same number of"
    ), lo <= 0 <= hi


def _gauge_clause():
    short = lambda fw: fw.replace(" (Chatara)", "").replace(" (Bahadurabad)", "")
    groups = {}
    for fw, (v, _) in GV.items():
        if v != "not applicable":
            groups.setdefault(v, []).append(short(fw))
    word = {
        "higher": "higher in",
        "lower": "lower in",
        "same": "level in",
        "mixed by station": "mixed by station in",
    }
    parts = [f"{word[v]} {' and '.join(groups[v])}" for v in word if v in groups]
    rho = [
        (float(r["rho_grrr_2026"]), float(r["rho_incumbent"]))
        for r in GAUGE
        if r.get("rho_grrr_2026") is not None
    ]
    up = sum(a > b for a, b in rho)
    return ", ".join(parts), up, len(rho)


gauge_clause, rho_up, rho_n = _gauge_clause()
pooled_e, _ne = _pool(pe)
pooled_c, _nc = _pool(pc)
pooled_noise = {
    (True, True): "both differences are within noise",
    (True, False): "the first difference is within noise, the second is not",
    (False, True): "the first difference is outside noise, the second is not",
    (False, False): "neither difference is within noise",
}[(_ne, _nc)]
score_rows += f"<tr style='font-weight:600'><td class='fw'>All six</td><td></td><td></td><td class='num'>{_cell(pe)}<br>CSI {float(pe['csi_diff']):+.2f} [{float(pe['csi_diff_lo']):+.2f}, {float(pe['csi_diff_hi']):+.2f}]</td><td class='num'>{_cell(pc)}<br>CSI {float(pc['csi_diff']):+.2f} [{float(pc['csi_diff_lo']):+.2f}, {float(pc['csi_diff_hi']):+.2f}]</td><td></td><td></td></tr>"

tcd_rows = "".join(
    f"<tr><td class='fw'>{r['model']}</td><td class='num'>{r['n']}</td><td class='num'>{r['hits23']} / <b>{r['hits26']}</b></td><td>{r['fn23']} / <b>{r['fn26']}</b></td><td>{r['fp23']} / <b>{r['fp26']}</b></td><td class='num'>{r['rho23']:.2f} / <b>{r['rho26']:.2f}</b></td><td class='num'>{r['early23']:.0f} / <b>{r['early26']:.0f}</b></td></tr>"
    for r in _rs["tcd"]
)
bgd_rows = "".join(
    f"<tr><td class='fw'>{ {'glofas_v4': 'GloFAS v4 (ran on)', '2023': 'GRRR 2023', '2026': 'GRRR 2026'}[r['release']] }</td><td>{r['conv']}</td><td class='num'>{r['thr']:,}</td><td class='num'>{r['n_ref']}</td><td class='num'>{r['n_model']}</td><td class='num'>{r['matched']}</td><td class='num'>{r['n_ref'] - r['matched']}</td><td class='num'>{r['fa']}</td></tr>"
    for r in _rs["bgd"]
)

rrow = "".join(
    f"<tr><td class='fw'>{a}</td><td>{b}</td><td>{c}</td><td>{y}</td><td><span class='kind'>{k}</span></td></tr>"
    for a, b, c, y, k in R
)

html = f"""<title>Google Flood Benchmark</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,600&display=swap">
<style>
/* layout: one reading column; a short contents strip; Groundwork first, then the framework review, then the replication plan; numbers in mono */
:root{{--bg:#f7f8f8;--panel:#ffffff;--fg:#182026;--muted:#5b6770;--line:#d9dfe3;--accent:#0f6e8c;--accent-soft:#d6ecf2;--ok:#2a7a3b;--warn:#b2561a;--miss:#b2561a;--inc:#7b4fa0;
--display:"Source Serif 4",Georgia,"Times New Roman",serif;--body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#13191d;--panel:#1b2329;--fg:#e6ebee;--muted:#9aa7b0;--line:#2e3a42;--accent:#5fb6d1;--accent-soft:#163a46;--ok:#6cc47f;--warn:#e39a60;--miss:#e39a60;--inc:#b995dc;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#13191d;--panel:#1b2329;--fg:#e6ebee;--muted:#9aa7b0;--line:#2e3a42;--accent:#5fb6d1;--accent-soft:#163a46;--ok:#6cc47f;--warn:#e39a60;--miss:#e39a60;--inc:#b995dc;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:15px;line-height:1.5;padding-inline:16px;padding-block:32px 64px}}
main{{max-width:960px;margin:0 auto}}
h1{{font-family:var(--display);font-weight:600;font-size:clamp(28px,4.5vw,38px);line-height:1.15;margin:0 0 8px;text-wrap:balance}}
h2{{font-family:var(--display);font-weight:600;font-size:24px;margin:48px 0 6px;padding-top:16px;border-top:2px solid var(--line);text-wrap:balance}}
h3{{font-family:var(--display);font-weight:600;font-size:19px;margin:28px 0 8px;text-wrap:balance}}
p{{max-width:70ch;margin:0 0 12px}}
.eyebrow{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
.lede{{color:var(--muted);font-size:16px}}
nav.toc{{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:14px;margin:16px 0 8px}}
nav.toc a{{text-decoration:none;border-bottom:1px solid var(--line)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 8px}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px;min-width:0}}
.tile b{{display:block;font-family:var(--mono);font-size:24px;font-weight:500;font-variant-numeric:tabular-nums;color:var(--accent)}}
.tile span{{font-size:13px;color:var(--muted)}}
.tile.good b{{color:var(--ok)}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--panel);margin:0 0 12px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th{{text-align:left;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:500;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:bottom}}
td{{padding:7px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
td.iso{{font-family:var(--mono);font-weight:500;white-space:nowrap}}
td.num,th.num{{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
td.ok{{color:var(--ok)}} td.warn{{color:var(--warn);font-weight:500}}
td.bar{{width:28%;min-width:120px}} td.bar span{{display:block;height:10px;border-radius:2px;background:var(--accent);opacity:.75}} td.bar span.miss{{background:var(--miss)}}
tr.flood td{{background:var(--accent-soft)}}
.tag{{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--accent);margin-left:6px;white-space:nowrap}}
table.review{{min-width:1380px;font-size:13px}} table.review td{{line-height:1.4}} td.fw{{font-weight:600;white-space:nowrap}} td.fw small{{display:block;font-weight:400;color:var(--muted);font-size:12px;white-space:normal;max-width:150px}} td.pg{{white-space:nowrap}}
table.plan{{min-width:820px;font-size:13.5px}}
.chip{{display:inline-block;font-size:11px;letter-spacing:.04em;text-transform:uppercase;padding:2px 8px;border-radius:3px;white-space:nowrap;font-weight:500;border:1px solid transparent}}
.lv-scored.chip{{background:var(--ok);color:var(--bg)}} .lv-design.chip{{background:var(--accent);color:var(--bg)}} .lv-shown.chip{{background:var(--accent-soft);color:var(--accent);border-color:var(--accent)}} .lv-context.chip{{background:transparent;color:var(--muted);border-color:var(--line)}} .lv-none.chip{{background:transparent;color:var(--muted);border-color:var(--line);text-decoration:line-through}}
tr.lv-scored td{{box-shadow:inset 4px 0 0 var(--ok)}} tr.lv-design td:first-child{{box-shadow:inset 4px 0 0 var(--accent)}} tr.lv-scored td:first-child{{box-shadow:inset 4px 0 0 var(--ok)}} tr.lv-scored td:not(:first-child){{box-shadow:none}}
td.lvl{{white-space:nowrap}} sup{{font-size:10px;color:var(--muted);margin-left:2px}}
.legend{{font-size:13px;color:var(--muted);line-height:2;margin:0 0 12px;max-width:none}} .legend .chip{{margin:0 4px 0 8px}}
figure.fig{{margin:12px 0 8px;padding:12px 12px 6px;background:var(--panel);border:1px solid var(--line);border-radius:6px;overflow-x:auto}} figure.fig svg{{width:100%;height:auto;min-width:560px;display:block}}
details{{margin:0 0 12px}} summary{{cursor:pointer;color:var(--accent);font-size:13.5px;margin:6px 0 8px}} details[open] summary{{margin-bottom:10px}}
.kind{{display:inline-block;font-size:11.5px;letter-spacing:.04em;text-transform:uppercase;padding:2px 8px;border-radius:3px;background:var(--accent-soft);color:var(--accent);white-space:nowrap}}
code{{font-family:var(--mono);font-size:13px;background:var(--accent-soft);padding:1px 5px;border-radius:3px}}
pre{{font-family:var(--mono);font-size:13px;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px;overflow-x:auto;margin:0 0 12px}}
ul,ol{{max-width:70ch;padding-left:20px;margin:0 0 12px}} li{{margin-bottom:6px}}
.note{{border-left:3px solid var(--accent);padding:4px 0 4px 14px;color:var(--muted);max-width:70ch;margin:12px 0}}
.finding{{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:12px 16px;max-width:76ch;margin:16px 0}}
a{{color:var(--accent)}} a:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.foot{{margin-top:40px;font-size:13px;color:var(--muted)}}
</style>
<main>
<div class="eyebrow">Google.org grant · Deliverable 1 · floods · working page, updated 9 November 2026, gauge and impact tests both as a 2x2 against the model each framework ran on</div>
<h1>Google Flood Benchmark</h1>
<p class="lede">Benchmarking Google's AI flood forecasts against the models used in the CERF anticipatory action frameworks. The answer so far is at the top; under it, the groundwork on Google's November 2026 release, what each framework actually evaluated and against which record, and the re-run of those evaluations with the new data.</p>
<nav class="toc"><a href="#answer">The answer so far</a><a href="#groundwork">1. Groundwork</a><a href="#review">2. What each framework evaluated</a><a href="#plan">3. Replication plan</a><a href="#impact">Where the impact data lives</a></nav>

<h2 id="answer">The answer so far: no evidence the 2026 model would have served the frameworks better on the humanitarian record</h2>
<p>The question is whether Google's November 2026 model would have served each framework better than the model it actually runs on. On the frameworks' own gauge tests (section 3), each reduced to the same 2x2 on the framework's own observed record, it tracks the record more closely wherever the test reports a correlation ({rho_up} of {rho_n} stations), but once false alarms count its critical success index is {gauge_clause}. Niger's trigger is the gauge itself, so there is no model to compare. On the humanitarian record, EM-DAT people affected in the basin and CERF rapid-response flood funding, it never catches more impact years than the incumbent, and in some frameworks one fewer. Pooled across the six frameworks it catches {pooled_e} EM-DAT impact years of {pe["n_impact_years"]} and {pooled_c} CERF years of {pc["n_impact_years"]}; {pooled_noise}. Counting every framework-year, false alarms included, the picture is: on EM-DAT ({pe["n_years"]} framework-years) it also raises {int(pe["fa_grrr_2026"])} false alarms against the incumbent's {int(pe["fa_incumbent"])}, so its critical success index is level, {float(pe["csi_grrr_2026"]):.2f} against {float(pe["csi_incumbent"]):.2f}; on CERF ({pc["n_years"]} framework-years) false alarms are equal, {int(pc["fa_grrr_2026"])} each, so the index is lower, {float(pc["csi_grrr_2026"]):.2f} against {float(pc["csi_incumbent"]):.2f}, with an interval of [{float(pc["csi_diff_lo"]):+.2f}, {float(pc["csi_diff_hi"]):+.2f}] that only just excludes zero. The CERF record is also the one the incumbents' own forecasts helped shape. These records cannot resolve a difference smaller than about one flood in five. Every number is a hindcast, each model's own reanalysis flagging years, scored against the frameworks' own thresholds, with the framework's anticipatory years removed.</p>
<figure class="fig">{FIG_GAUGE}</figure>
<figure class="fig">{FIG_PAIRED}</figure>
<div class="wrap"><table class="plan">
<tr><th>Framework</th><th>Runs on</th><th>Gauge test, CSI 2026 vs incumbent (section 3)</th><th class="num">EM-DAT basin, 2026 vs incumbent</th><th class="num">CERF rapid response, 2026 vs incumbent</th><th>Impact verdict</th><th>Window and confidence</th></tr>
{score_rows}
</table></div>
<p><strong>How to read the verdict.</strong> The verdict is on the critical success index (CSI, impact years caught over caught plus missed plus false alarms) of each measure over the framework-years of the comparison window: "same" when both models flag the same years; "lower" when the 2026 model's CSI is below the incumbent's on at least one measure and above on none; "higher" the reverse; "mixed" when one measure goes each way; "cannot tell" when the basin mapping is in doubt. Cells read: impact years caught (2026 vs incumbent, of N), then false alarms and CSI. The gauge column is the same 2x2 on each framework's own observed record from section 3 (first figure), verdict on CSI, "mixed by station" where the framework's stations disagree; it has no pooled row because the event units differ. The window is the baseline years both models cover, minus the years the framework's own anticipatory allocation was made (that allocation is the framework firing). Impact years are the years whose EM-DAT or CERF amount reaches the framework's own return-period level on that window. Confidence names three things: whether the Google basin is a known Flood Hub gauge or a nearest-river guess, whether the reanalysis stands in for the forecast at the framework's lead (step 1), and that this is a hindcast rather than a forecast-at-lead test.</p>
<p><strong>What would change the answer.</strong> Confirming the three guessed basins (Niamey first); the forecast-level pass on the 2016 to 2025 reforecast overlap at each framework's action lead, which is the question as asked; and a basin-level impact record such as FloodScan exposure, which is deferred. Until then the defensible statement is closer tracking of the observed record, no consistent gain once false alarms count, and no evidence of superiority on the humanitarian record.</p>

<h2 id="groundwork">1. Groundwork: Google's November 2026 release has a basin in every CERF country</h2>
<p>What was verified in the new <code>distributed_model_2026_11</code> release before the benchmark uses it, read anonymously from <code>gs://flood-forecasting</code>. The question that remains is not whether a basin exists but whether the one at each trigger station is any good.</p>

<div class="tiles">
<div class="tile"><b>{n(T["with_pred"])}</b><span>sub-basins with predictions, of {n(T["outlets"])} outlets</span></div>
<div class="tile"><b>{n(T["missing"])}</b><span>without predictions, all in the Arctic</span></div>
<div class="tile good"><b>28 of 28</b><span>CERF countries fully covered (one coastal basin in Fiji excepted)</span></div>
<div class="tile good"><b>0</b><span>missing values in {n(tot_s["b"])} basins sampled</span></div>
<div class="tile good"><b>3,653 / 3,653</b><span>days where lead 0 equals the reanalysis exactly</span></div>
</div>

<h3>What the release contains</h3>
<div class="wrap"><table>
<tr><th></th><th>2023 bucket</th><th>November 2026 release</th></tr>
<tr><td>Model</td><td>per-gauge LSTM (Nearing et al., Nature 2024)</td><td>semi-distributed AI model on the HydroBasins river graph</td></tr>
<tr><td>Keyed by</td><td>Flood Hub gauge id</td><td>HydroBasins sub-basin, <code>subhybas_&lt;id&gt;</code></td></tr>
<tr><td>Reanalysis</td><td>1980-01-01 to 2023-12-23</td><td>1980-12-31 to 2025-12-30 (16,436 days)</td></tr>
<tr><td>Reforecast</td><td>issues 2016-01-01 to 2023-06-30, leads 0 to 7 d</td><td>issues 2016-01-01 to 2025-12-31 (3,653), leads 0 to 10 d</td></tr>
<tr><td>Thresholds</td><td>none shipped</td><td>return periods 1.01, 2, 5, 10, 20, 25, 50, 100 yr from the reanalysis, no gaps</td></tr>
<tr><td>Inputs (Google's description)</td><td>ERA5-Land, IMERG, CPC; HRES for forecast days</td><td>CPC and IMERG rain to issue time; HRES and GraphCast forecasts. ERA5-Land not mentioned</td></tr>
</table></div>

<h3>Basins per CERF country</h3>
<p>Every basin outlet was joined to a Natural Earth country polygon. Shaded rows are countries with a CERF flood framework or the Somalia flood analysis. Bars are the basin count.</p>
<div class="wrap"><table>
<tr><th>ISO</th><th>Country</th><th class="num">Basins</th><th class="num">With prediction</th><th class="num">Missing</th><th></th></tr>
{crow}
</table></div>
<p class="note">{n(T["nojoin"])} outlets fall inside no country polygon (coasts, lakes); {n(T["nojoin_pred"])} of those have predictions. The outlet file is labelled unofficial by Google and picks one arbitrary outlet for coastal basins.</p>

<details><summary>Show the detail tables: where the missing basins are, and the missing-value sample</summary>
<h3>Where the {n(T["missing"])} missing basins are</h3>
<div class="wrap"><table>
<tr><th>ISO</th><th>Country</th><th class="num">Basins without predictions</th><th></th></tr>
{mrow}
</table></div>

<h3>Missing values inside the stores</h3>
<p>A basin can exist and still be all NaN. For each flood country, 3 basins were drawn at random and each one's full 128-basin storage chunk was read from both the reanalysis and the reforecast store. Chunks are contiguous basin ids, so the sample is {n(tot_s["b"])} basins in {tot_s["ch"]} chunks that each contain a basin in the named country, not {n(tot_s["b"])} basins inside those countries.</p>
<div class="wrap"><table>
<tr><th>ISO</th><th class="num">Chunks</th><th class="num">Basins</th><th class="num">NaN, reanalysis</th><th class="num">NaN, reforecast</th><th class="num">All-NaN basins</th></tr>
{srow}
</table></div>

</details>
<h3>Lead 0 is not a forecast</h3>
<p>Google's notebook states the labelling: reanalysis day T covers [T, T+1d]; reforecast lead L issued at T covers [T+L−1d, T+L]. So the lead-0 value issued on T+1 is the reanalysis for day T:</p>
<pre>Reanalysis[time = T]  ==  Reforecast[issue_time = T + 1d, lead_time = 0]</pre>
<p>Verified at <code>subhybas_1121902040</code> (Nigeria, a large river): equal to the float on all 3,653 issue days. A "reforecast matches reanalysis" check at lead 0 is therefore true by construction. The consistency check has to run at leads 1 to 10 against the reanalysis on the same valid day, per basin, at the leads each framework fires on. That is the first item of the replication plan below.</p>
<p class="note">Google also states the reforecast ignores the few hours of operational data delay, so it is slightly optimistic relative to a live forecast issued the same day.</p>

<h3>What "coverage" still means</h3>
<ul>
<li><strong>Station to sub-basin.</strong> Which outlet corresponds to each trigger station (SWALIM gauges, Chatara and Chisapani, Niamey, Bahadurabad, N'Djamena, the Benue gauges). The 2023 bucket and the live API are Flood Hub gauge-keyed; the Somalia and Nigeria work needs a gauge-to-basin mapping before it can be re-run on this release.</li>
<li><strong>Live product versus dataset.</strong> The dataset is global; Flood Hub's published forecasts are not. Which of the two defines "Google coverage" for the benchmark is a team decision.</li>
<li><strong>Model version.</strong> Which model the API serves today (this release, the frozen 2023 id, or a third), whether ERA5-Land is still an input, and whether the reforecast will be extended each year. All on the list for Google.</li>
</ul>

<h2 id="review">2. What each framework evaluated, and against what</h2>
<p>Read from four tiers of source: the knowledge-base page of each framework version (linked in the last column), the full text of each framework document, the spoke repository's notebooks, and the team's internal Drive extracts (trigger specifications, presentations, exploration decks). Two questions per framework: was the evaluation a <em>calibration</em> (set a threshold to hit a target return period) or an independent <em>skill test</em> (score the model against something it did not see), and what was the truth set: a gauge or observational record, a humanitarian impact record, or both.</p>
<div class="finding"><strong>The pattern.</strong> Impact data entered most frameworks as a requirement or a sanity check, and only one as the scoring record. Uganda scores its triggers against an impact record. Bangladesh's severity level, Yemen's rain window, Somalia's basin split and Nigeria 2025's target events were set with impact data, then scored against a gauge or FloodScan. Nepal and Chad set impact years beside trigger years without scoring them. Niger, Burkina Faso and Nigeria 2026 used impact data to pick areas or as narrative. Where a gauge exists, it is the truth set; the knowledge-base summaries undersold the impact side for Chad, Bangladesh, Nigeria 2025 and Nepal, and the extra evidence sits in the framework documents, the repo notebooks and the Drive folders.</div>
<div class="legend"><span class="chip lv-scored">Scored</span> impact record is the truth set <span class="chip lv-design">Design input</span> set the threshold, the target events or the budget split <span class="chip lv-shown">Shown</span> impact years displayed beside trigger years, not scored <span class="chip lv-context">Targeting or context</span> picked areas or narrative only <span class="chip lv-none">None</span> no use found. Evidence: <sup>K</sup> KB page · <sup>P</sup> framework document full text · <sup>R</sup> spoke-repo notebook · <sup>D</sup> internal Drive extract.</div>
<div class="wrap"><table class="review">
<tr><th>Framework</th><th>Trigger product and station</th><th>What the evaluation was</th><th>Truth set: gauge or observation</th><th>Impact in the decision?</th><th>Humanitarian impact data: how it was used</th><th>Metric and period reported</th><th>KB page</th></tr>
{frow}
</table></div>
<p class="note">Status and activation dates are as recorded on the KB pages on 4 November 2026. The impact column is graded on the highest use found; where a framework sits at two levels the cell names both. "None" means no use was found in any of the four tiers. Where a page gives two different numbers for the same test (Nepal), both are shown.</p>

<h2 id="plan">3. Replication plan: the same evaluations with the November 2026 release</h2>
<p>The order the team agreed: first confirm the reforecast and the reanalysis tell the same story, then re-run each framework's evaluation with Google's new reanalysis and reforecast, using the reanalysis as the long record only where the first step holds. Step 1 has been run; step 2 has been run for Somalia, Nepal, Nigeria, Chad and Bangladesh, each against the model the framework actually ran on.</p>

<h3>Step 1: is the reanalysis a proxy for the reforecast?</h3>
<p>The check exists in two places already and has the same shape in both: the Somalia mechanism's forecast-vs-own-reanalysis skill section (rank ρ ≥ 0.99 and ratio about 1.00 at action leads for GRRR and GloFAS v4) and the Nigeria Niger-Benue multistate script <code>check_reforecast_skill.py</code> (seasonal-peak rank ρ by lead, 2016–2022, ≥ 0.95 at 7 d in most states, 0.59 in Taraba). The protocol for the new release, per trigger basin:</p>
<ol>
<li>For each issue day 2016-01-01 to 2025-12-31 and each lead 1 to 10, pair the reforecast value with the reanalysis on the same valid day. Lead 0 is excluded: it is the reanalysis by construction.</li>
<li>Per wet season, take the seasonal peak of each series and compute Spearman ρ across seasons, by lead. Also the median ratio reforecast / reanalysis on days above the release's 2-yr level, by lead.</li>
<li>Accept the reanalysis as the history for that basin at the leads where ρ holds (the Somalia and Nigeria work used about 0.95) and the ratio sits near 1. Where it fails, as in Taraba, only the reforecast counts and the record is ten seasons.</li>
</ol>
<p>Ten seasons is a thin base for a rank correlation, so the result is reported with its confidence interval and the per-basin decision is written down before any scoring.</p>
<h3>Step 1 result (run 4 Nov 2026)</h3>
<p>32 station-seasons, every trigger basin of the flood frameworks, leads 1 to 10 on the November 2026 release. Green is at or above 0.95 (the bar the Somalia and Nigeria work used), orange below 0.90. Full table with daily ρ and the bootstrap intervals in <code>docs/proxy-check-2026-11.md</code> and <code>outputs/proxy_check.csv</code> on the <code>proxy-check</code> branch.</p>
<figure class="fig">{FIG_SUMMARY}</figure>
<p>The row for each framework is the range of leads where its trigger stations keep seasonal-peak ρ at or above 0.95, set against the leads the framework fires at. Reading it: for Chad, Bangladesh, Niger and Uganda the reanalysis is a safe history at the action lead; for Somalia and the Benue main stem it is, but one gauge in each design is not; for Nepal it is not beyond two days, so Nepal has to be scored on the reforecast. Station-level detail follows.</p>
<figure class="fig">{FIG_PROXY}</figure>
<details><summary>Show the numbers</summary>
<div class="wrap"><table class="plan">
<tr><th>Station</th><th>Basin</th><th class="num">peak ρ, lead 3</th><th class="num">5</th><th class="num">7</th><th class="num">10</th><th class="num">ρ 7, 5th pct</th><th class="num">ratio, lead 5</th><th class="num">7</th><th class="num">10</th><th class="num">days > 2-yr at 7</th><th class="num">reanalysis usable to lead</th></tr>
{prow}
</table></div></details>
<div class="finding"><strong>Reading.</strong> Rank holds to lead 7 at 29 of 32 rows: the nine Benue main-stem gauges, all fourteen Somalia station-seasons, N'Djamena, Bahadurabad, Mawa, Niamey and Akokoro rank their seasonal peaks the same way in the reforecast and the reanalysis out to a week. Two failures of two kinds. The Nigeria tributary outlier, kept in the 2026 design by choice, loses rank from lead 3 and runs at 0.62 of the reanalysis by lead 7: the Taraba case, now inside the endorsed gauge set. Nepal fails on rank while matching on magnitude: Chatara 0.60 and Chisapani 0.12 at lead 7 with intervals reaching below zero, ratio 1.00. Monsoon peaks there are short spikes the week-ahead forecast does not place; the reanalysis stands in only to lead 2. And a drift that is not a failure: on days above the 2-yr level the Benue reforecast runs at 0.92 to 0.94 of the reanalysis at lead 5 and 0.87 to 0.90 at lead 7, so a reanalysis-fitted threshold applied to a week-ahead forecast there fires less often than its nominal return period.</div>
<p>What this licenses: the reanalysis as the long history, with the release's own return periods, at leads up to 7 days in Somalia, on the Nigeria main stem (with the magnitude ratio applied, or thresholds set on the reforecast at the action lead), Chad, Bangladesh, Niger and Uganda. Reforecast only, ten seasons, in Nepal beyond lead 2 and at the Nigeria tributary gauge. Two things to confirm before scoring: the five real-gauge basins were picked as the largest river within 10 km and need a human check, Niamey first, since its 2-yr flow of 12,100 m³/s is far above the Niger's observed peaks; and every threshold must be refitted on the release's own return periods, because the new model's magnitudes are not the 2023 bucket's (Benue 2-yr about 2,650 m³/s against 4-yr thresholds of about 1,100 before).</p>

<h3>Step 2: per framework</h3>
<p>"Same evaluation" means the same truth set, station and metric as the original study, with GRRR from the release in place of (or beside) the original model. The distinction that matters: re-scoring an existing evaluation tells us about the model; re-running a threshold search tunes a trigger and tells us little.</p>
<div class="wrap"><table class="plan">
<tr><th>Framework</th><th>What "the same evaluation" means here</th><th>Needed first</th><th>Impact years already named in the framework's own material</th><th>Kind</th></tr>
{rrow}
</table></div>
<h3>Step 2 result, five frameworks (run 4 Nov 2026)</h3>
<p>The comparison that matters is GRRR November 2026 against the model each framework actually ran on. That is the GRRR 2023 bucket only for Nigeria 2026 (and one leg of the Somalia proposal); Chad, Nepal and Bangladesh ran on GloFAS, Niger on the ABN gauge alone. So every figure below joins the incumbent (purple for GloFAS, grey where the incumbent is the 2023 bucket) to GRRR 2026 (blue), with the 2023 bucket as a small grey dot where it is not the incumbent and the published value as a hollow ring. The same code scores every model from its own reanalysis, so the reproduction of the published number is the check that the method is right, and the GloFAS side carries the same reanalysis-as-proxy caveat as the Google side (the Somalia spoke found GloFAS v4 drifting to about 0.9 of its reanalysis by lead 12, and no GloFAS v5 reforecast exists to test). Tables under each figure read: published, incumbent, 2023 bucket, 2026 release. Full tables, conventions and the reading in <code>docs/rescore-2026-11.md</code> on the <code>rescore</code> branch.</p>
<h3 style="font-size:16px">Somalia: daily rank correlation against the reference gauge, and RP3 episode detection against each gauge's post-2000 RP3</h3>
<figure class="fig">{FIG_SOM}</figure>
<figure class="fig">{FIG_SOM_POD}</figure>
<details><summary>Show the numbers</summary>
<div class="wrap"><table class="plan">
<tr><th>Station</th><th>Season</th><th class="num">published ρ (GRRR 2023)</th><th class="num">GloFAS v5</th><th class="num">GRRR 2023</th><th class="num">GRRR 2026</th><th class="num">best lag, days: GloFAS / 23 / 26</th><th class="num">vs own gauge GloFAS / 23 / 26</th></tr>
{som_corr_rows}
</table></div>
<div class="wrap"><table class="plan">
<tr><th>Station</th><th class="num">gauge episodes</th><th class="num">model episodes pub / GloFAS v5 / 23 / 26</th><th class="num">POD pub / GloFAS v5 / 23 / 26</th><th class="num">FAR pub / GloFAS v5 / 23 / 26</th></tr>
{som_ep_rows}
</table></div></details>
<div class="finding"><strong>Somalia.</strong> The proposal votes three models, so both GloFAS v5 and the GRRR 2023 bucket are incumbents here. Against GloFAS v5, GRRR 2026 tracks every gauge more closely in both seasons (daily ρ 0.85 to 0.90 against 0.69 to 0.87) and catches as many or more RP3 episodes at every gauge, with a clearly higher catch at Dollow, Bardheere, Bualle and Belet Weyne; the false-alarm ratio is lower at Bardheere and Bualle and higher at Belet Weyne and Bulo Burti. The answer figure at the top scores both models of a pair at their own quantile, so its GRRR 2026 false-alarm counts are lower than the shipped-level ones in this table and it catches one fewer episode at Luuq, Bardheere, Bualle and Belet Weyne. Against the 2023 bucket the gain is concentrated in Deyr (Juba 0.46 to 0.59 before, 0.85 to 0.90 now), with the same two costs as before: the best lag moves from the model leading the river to lagging it, and Dollow fires more often (FAR 0.40 to 0.62). Jowhar stays poor for all three.</div>
<h3 style="font-size:16px">Nepal: model exceedance events matched to DHM danger-level crossings within 7 days</h3>
<figure class="fig">{FIG_NPL}</figure>
<details><summary>Show the numbers</summary>
<div class="wrap"><table class="plan">
<tr><th>Station</th><th>RP</th><th>Source</th><th>convention</th><th>published</th><th class="num">2023: matched, false alarms</th><th class="num">2026: matched, false alarms</th></tr>
{npl_rows}
</table></div></details>
<div class="finding"><strong>Nepal.</strong> The 2023 column gives GRRR 6 of 7 at Chisapani at RP2, the KB number, and 4 of 7 at RP5, the technical note's number: the two published figures were one test at two return periods. On the 2026 release Chisapani drops to 5 of 7 at RP2 and 2 of 7 at RP5 with false alarms unchanged, and Chatara, the live trigger station, is poor for every model including GloFAS v4 (2 of 9 crossings at RP2, 1 of 9 at RP5, for both). Against GloFAS v4, the model the framework runs on, GRRR 2026 matches the same crossings at Chatara with more false alarms (5 against 1 at the 2025 trigger's RP5) and is level at Chisapani RP2 with the same false alarms. With step 1's finding that Nepal's reanalysis does not stand in for its forecast beyond lead 2, this test says little about a trigger there.</div>
<h3 style="font-size:16px">Nigeria: GRRR reanalysis against GRDC observed discharge, wet season Jul to Nov</h3>
<figure class="fig">{FIG_NGA}</figure>
<details><summary>Show the numbers</summary>
<div class="wrap"><table class="plan">
<tr><th>Station</th><th>basin</th><th class="num">years</th><th class="num">daily ρ 23 / 26</th><th class="num">annual-peak ρ pub / 23 / 26</th><th class="num">3-yr hits/FA/misses 23 → 26</th><th class="num">F1 3-yr 23 / 26</th><th class="num">F1 5-yr 23 / 26</th></tr>
{nga_rows}
</table></div></details>
<div class="finding"><strong>Nigeria.</strong> The 2023 column gives the published 0.76 annual-peak correlation at Yidere Bode. Both releases are scored on the years both cover, 1981 to 2023. On the 2026 release the annual-peak correlation rises at Yidere Bode, Lokoja and Kende and falls at Makurdi; 3-yr exceedance agreement improves at Lokoja, is unchanged at Kende and worsens at Yidere Bode and Makurdi. Mixed on 16 to 37 years per station, no single direction. Four of nine GRDC stations pass the completeness filters; Wuroboki, the 2025 trigger gauge, has fewer than 15 valid years.</div>
<h3 style="font-size:16px">Chad: annual peaks at N'Djamena against the DRE observed level, 2003 to 2022</h3>
<figure class="fig">{FIG_TCD}</figure>
<details><summary>Show the numbers</summary>
<div class="wrap"><table class="plan">
<tr><th>Model</th><th class="num">years</th><th class="num">hits of 5, 23 / 26</th><th>false negatives 23 / 26</th><th>false positives 23 / 26</th><th class="num">peak ρ 23 / 26</th><th class="num">days early 23 / 26</th></tr>
{tcd_rows}
</table></div></details>
<div class="finding"><strong>Chad.</strong> The framework runs on GloFAS v4, and GloFAS through this code gives the document's annex exactly: 3 of the 5 observed 4-yr flood years, misses 2019 and 2020, false alarms 2003 and 2005, 31 days early. Against that, GRRR 2026 flags 4 of 5 (it catches 2019 and 2020, misses 2010, adds 2018), with a higher peak correlation (0.74 against 0.69) and the same 31-day lead on the observed peak. So on the framework's own test the new Google model is better than the model Chad runs on, while the 2023 bucket was better still (5 of 5, no false alarm, 20 days early). Basin still to confirm.</div>
<h3 style="font-size:16px">Bangladesh: severe floods at Bahadurabad matched by GRRR reanalysis events</h3>
<figure class="fig">{FIG_BGD}</figure>
<details><summary>Show the numbers</summary>
<div class="wrap"><table class="plan">
<tr><th>Release</th><th>RP5 convention</th><th class="num">threshold m³/s</th><th class="num">observed events</th><th class="num">model events</th><th class="num">matched</th><th class="num">misses</th><th class="num">false alarms</th></tr>
{bgd_rows}
</table></div></details>
<div class="finding"><strong>Bangladesh.</strong> Seven severe floods in the FFWC record (water level at danger level + 0.85 m for three days): 1988, 2012, 2016, 2017, 2019 and two in 2020. GloFAS v4, which the framework runs on, matches 3 of 7 with 6 false alarms; the GRRR 2023 bucket the same 3 with 5 or 6; GRRR 2026 3 of 7 with 8 false alarms at the release's RP5, or 2 of 7 with 6 at the quantile. Nothing separates the three at this station, and 1988 and 2012 go unmatched by all. The answer figure at the top uses the quantile for both models, so it shows 2 of 7 against GloFAS v4's 3, with 6 false alarms each. This is a reanalysis stand-in for a 15-day ensemble readiness trigger, so a station-skill reading only.</div>
<p>Still to do in step 2: Uganda, whose impact backtest is a pipeline with zones and catch windows that needs a GRRR leg added inside it; the Niger new question; the five real-gauge basin mappings first. None of the above is a trigger-outcome result: those need each framework's thresholds refitted on the release and the reforecast on the forecast side.</p>
<p>Every row needs the station-to-sub-basin mapping from the groundwork section. The gauge records already held by the team (SWALIM, GRDC Niamey and the five Nigerian stations, DHM crossings) make Somalia, Nigeria 2026, Nepal and Niger the rows that can start first.</p>

<h3>Year by year</h3>
<p>The table the frameworks themselves use, built for every framework with a Google-evaluable station. Each panel's second line says what the framework's trigger ran on and where its backtest years come from. The first column is that published backtest. The bracketed pair is the comparison: the model the framework ran on (its own reanalysis) against GRRR 2026. Then the observed record, and the 2023 bucket as a secondary column where it is not the incumbent. The four model and gauge columns are on one rule: a year is flagged when its seasonal maximum reaches the empirical Weibull level at the framework's return period, fitted on the same baseline years (1998 to 2023, cut to what the observed record covers). Nigeria applies the endorsed 6-of-10 same-day rule on top; Somalia uses the reference gauge of each river in either season. Under each header: how many baseline years are flagged and the implied return period, so the columns can be read against each other. The GloFAS incumbents are the spokes' reanalysis copies extended to mid-2026 from the Copernicus Early Warning Data Store at the same cell and version, so the ran-on column runs to 2025 wherever a framework runs on GloFAS; the GRRR 2023 bucket is a frozen research dataset that ends in December 2023, so its column stops there (dashed cells). EM-DAT is people affected by flood events whose location text names the monitored basin, from the team's mirror. The CERF column is flood allocations from the OneGMS mirror in the team database, orange for rapid response and green for anticipatory, the label the total. The four rows under each panel give, per flag column and over the framework's comparison window (the boxed baseline years both models of the key pair cover, minus the years its own anticipatory allocation was made): the Spearman correlation of the yearly flag with EM-DAT affected and with CERF rapid-response US$, each with half the bootstrap 90% interval, then hits / misses / false alarms against the impact years, the years whose amount reaches the framework's return-period level on that window. Bangladesh's observed column keeps the framework's own definition (danger level plus 0.85 m for three days) because its FFWC file holds only days above the danger level; Niger's observed column is the published threshold years, there being no model trigger.</p>
<figure class="fig">{FIG_LEDGER}</figure>
<h2 id="impact">Where the impact data lives</h2>
<ul>
<li><strong>EM-DAT</strong>: knowledge-base dataset page <a href="{KB}infrastructure/datasets/emdat.md">infrastructure/datasets/emdat.md</a>; used as the truth set in Uganda and for the basin split in Somalia.</li>
<li><strong>CERF allocations</strong>: the OneGMS mirror in the prod database, tables <code>aa.cerf_allocation</code>, <code>aa.cerf_project</code> and siblings, copied daily from the CERF GMS API; dataset page <a href="{KB}infrastructure/datasets/cerf-onegms.md">infrastructure/datasets/cerf-onegms.md</a>. Uganda's page lists the two rapid-response flood allocations (2007, 2020); Somalia uses CERF beside EM-DAT.</li>
<li><strong>Caveat.</strong> A rapid-response allocation records a response, driven by appeals and funding as much as by the hazard. It can confirm that a year was bad; it cannot rank years, and its absence does not mean no flood. EM-DAT carries the same limits for small events. That is why the frameworks with a gauge score against the gauge.</li>
</ul>

<p class="foot">Scripts and write-up: <a href="https://github.com/OCHA-DAP/ds-google-ai-climate-benchmarking/pull/1">OCHA-DAP/ds-google-ai-climate-benchmarking, PR #1</a> (<code>scripts/check_grrr_coverage.py</code>, <code>scripts/grrr_2026_11.py</code>, <code>docs/grrr-2026-11.md</code>). Working note: <a href="https://claude.ai/artifact/9bZjp1k49Yfz51H3d5zrbV">Google flood AI benchmark: stock-take and directions</a>. Framework facts: <a href="https://github.com/OCHA-DAP/ds-knowledge-base">ds-knowledge-base</a>, pages linked above. Country boundaries: Natural Earth 50m admin-0. Data licence CC-BY-4.0, Google.</p>
</main>
"""
(PAGE / "index.html").write_text(html)
print(PAGE / "index.html", len(html))
