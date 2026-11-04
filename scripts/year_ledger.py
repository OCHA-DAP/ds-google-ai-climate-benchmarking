"""Year ledger: per framework and year, who said flood.

The table the frameworks have used themselves (the Somalia deck's "activations, impact and
response, year by year"), built for every framework with a Google-evaluable station:

- framework_fired: the framework's own published backtest years (knowledge-base pages);
- grrr_2023 / grrr_2026: GRRR reanalysis of each release, seasonal peak at or above the
  release's own return period at the framework's level (Nigeria: the endorsed rule, >= 6 of 10
  gauges over their own 4-yr level on the same day; Somalia: the reference gauge's basin over
  RP5 in either season);
- observed: the framework's validation record says flood that year (DRE 4-yr level at N'Djamena;
  GRDC 3-yr wet-season peak at Yidere Bode; SWALIM post-2000 RP3 episode at the reference
  gauges; DHM danger-level crossing; FFWC danger level + 0.85 m for 3 days; ABN 604 cm);
- emdat_affected: EM-DAT total affected by floods in the country that year (team blob mirror;
  check its vintage);
- cerf_flood_usd: CERF rapid-response allocations tagged Flood for the country that year, from
  the shared drive export (covers 2006-2021 only; later years are blank, not zero).

Writes outputs/year_ledger.csv. Needs blob and AA_DATA_DIR access.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from ocha_stratus import emdat

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import reanalysis, shipped_return_periods
from rescore_bgd import load_ffwc_bahadurabad, observed_events
from rescore_som import GAUGES as SOM_GAUGES
from rescore_som import episodes, load_level, weibull_threshold
from rescore_tcd import load_dre_tp

YEARS = list(range(1998, 2026))
FRAMEWORKS = {
    "Nigeria 2026": {
        "iso3": "NGA",
        "fired": [1998, 1999, 2012, 2018, 2019, 2022],
        "season": [8, 9, 10, 11],
    },
    "Somalia": {
        "iso3": "SOM",
        "fired": [2006, 2010, 2014, 2016, 2018, 2019, 2020, 2023],
        "season": None,
    },
    "Nepal 2025 (Chatara)": {"iso3": "NPL", "fired": [], "season": [6, 7, 8, 9]},
    "Chad 2025": {"iso3": "TCD", "fired": [2003, 2005, 2010, 2012, 2022], "season": [8, 9, 10, 11]},
    "Bangladesh 2025 (Bahadurabad)": {"iso3": "BGD", "fired": [], "season": [6, 7, 8, 9]},
    "Niger 2025": {
        "iso3": "NER",
        "fired": [1998, 1999, 2010, 2012, 2013, 2015, 2019, 2020, 2024],
        "season": [8, 9],
    },
}
NGA_GAUGES = [
    "hybas_1120842990",
    "hybas_1120843610",
    "hybas_1120845060",
    "hybas_1120849600",
    "hybas_1120848550",
    "hybas_1121970280",
    "hybas_1120842550",
    "hybas_1120840700",
    "hybas_1120840560",
    "hybas_1120840690",
]
STATION = {
    "Nepal 2025 (Chatara)": "hybas_4120864110",
    "Chad 2025": "hybas_1120734190",
    "Bangladesh 2025 (Bahadurabad)": "hybas_4121501030",
    "Niger 2025": "hybas_1120679000",
}
RP_LEVEL = {
    "Nepal 2025 (Chatara)": 5.0,
    "Chad 2025": 4.0,
    "Bangladesh 2025 (Bahadurabad)": 5.0,
    "Niger 2025": 5.0,
}


def rp_at(release: str, hid: str, T: float) -> float:
    sp = shipped_return_periods(release, hid)
    if T in sp:
        return sp[T]
    yT = lambda x: -np.log(-np.log(1 - 1 / x))
    return sp[2.0] + (sp[5.0] - sp[2.0]) * (yT(T) - yT(2)) / (yT(5) - yT(2))


def season_peak_years(q: pd.Series, months: list[int] | None, thr: float) -> set[int]:
    s = q if months is None else q[q.index.month.isin(months)]
    pk = s.groupby(s.index.year).max()
    return {int(y) for y, v in pk.items() if v >= thr}


def grrr_flags(release: str) -> dict[str, set[int]]:
    out = {}
    # Nigeria: >= 6 of 10 gauges over their own 4-yr level on the same day, Aug-Nov
    daily = pd.DataFrame({g: reanalysis(release, g) for g in NGA_GAUGES})
    over = pd.DataFrame({g: daily[g] >= rp_at(release, g, 4.0) for g in NGA_GAUGES})
    cnt = over.sum(axis=1)
    cnt = cnt[cnt.index.month.isin([8, 9, 10, 11])]
    out["Nigeria 2026"] = {int(y) for y, v in cnt.groupby(cnt.index.year).max().items() if v >= 6}
    # Somalia: reference gauges Luuq (Juba) and Belet Weyne (Shabelle), either season, RP5
    yrs = set()
    for st in ["luuq", "belet_weyne"]:
        hid = SOM_GAUGES[st][2]
        q = reanalysis(release, hid)
        thr = rp_at(release, hid, 5.0)
        for months in ([3, 4, 5], [10, 11, 12]):
            yrs |= season_peak_years(q, months, thr)
    out["Somalia"] = yrs
    for fw, hid in STATION.items():
        q = reanalysis(release, hid)
        out[fw] = season_peak_years(q, FRAMEWORKS[fw]["season"], rp_at(release, hid, RP_LEVEL[fw]))
    return out


def observed_flags() -> dict[str, set[int]]:
    out = {}
    # Chad: DRE 4-yr level on annual peaks (same rule as rescore_tcd)
    dre = load_dre_tp()
    pk = dre.groupby(dre.index.year).max()
    out["Chad 2025"] = {int(y) for y, v in pk.items() if v >= pk.quantile(0.75)}
    # Nigeria: GRDC Yidere Bode 3-yr wet-season years from the re-score output
    g = pd.read_csv("outputs/rescore_nga_2026.csv")
    row = g[g.station == "Yidere Bode"].iloc[0]
    out["Nigeria 2026"] = {int(y) for y in str(row.obs_years_3yr).split(",") if y}
    # Somalia: post-2000 RP3 episodes at the reference gauges, year of episode start
    yrs = set()
    for st in ["luuq", "belet_weyne"]:
        lv = load_level(SOM_GAUGES[st][1])
        am = lv[lv.index.year >= 2000].groupby(lv[lv.index.year >= 2000].index.year).max()
        thr = weibull_threshold(am.values, 3)
        for s, _e in episodes(lv >= thr):
            yrs.add(int(s.year))
    out["Somalia"] = yrs
    # Nepal: DHM danger-level crossings at Chatara
    dhm = (
        pd.read_csv(
            Path(os.environ["AA_DATA_DIR"])
            / "private/exploration/npl/dhm/processed/waterl_level_procssed.csv",
            parse_dates=["date"],
        )
        .set_index("date")["Chatara"]
        .dropna()
    )
    cross = (dhm > 7.0).astype(int).diff() == 1
    out["Nepal 2025 (Chatara)"] = {int(y) for y in dhm[cross].index.year}
    # Bangladesh: FFWC severe floods
    out["Bangladesh 2025 (Bahadurabad)"] = {
        int(d.year) for d in observed_events(load_ffwc_bahadurabad())
    }
    # Niger: the trigger is the gauge; the observed record is the published threshold years
    out["Niger 2025"] = set(FRAMEWORKS["Niger 2025"]["fired"])
    return out


def emdat_affected(iso3: str) -> dict[int, float]:
    em = emdat.load_emdat_from_blob(iso3=iso3)
    fl = em[em["Disaster Type"].astype(str).str.contains("Flood", case=False)]
    return (
        fl.groupby("Start Year")["Total Affected"].sum(min_count=1).dropna().astype(float).to_dict()
    )


def cerf_flood(iso3: str) -> dict[int, float]:
    f = Path(os.environ["AA_DATA_DIR"]) / "public/raw/glb/cerf/CERF Allocations.csv"
    df = pd.read_csv(f, encoding="latin-1")
    sub = df[
        (df.countryCode == iso3)
        & (df.emergencyTypeName == "Flood")
        & (df.windowFullName == "Rapid Response")
    ]
    return sub.groupby("year")["totalAmountApproved"].sum().astype(float).to_dict()


def main() -> int:
    g23, g26, obs = grrr_flags("2023"), grrr_flags("2026"), observed_flags()
    rows = []
    for fw, cfg in FRAMEWORKS.items():
        em, cf = emdat_affected(cfg["iso3"]), cerf_flood(cfg["iso3"])
        for y in YEARS:
            rows.append(
                {
                    "framework": fw,
                    "iso3": cfg["iso3"],
                    "year": y,
                    "framework_fired": int(y in cfg["fired"]) if cfg["fired"] else np.nan,
                    "grrr_2023": int(y in g23[fw]) if y <= 2023 else np.nan,
                    "grrr_2026": int(y in g26[fw]),
                    "observed": int(y in obs[fw]),
                    "emdat_affected": em.get(y, np.nan),
                    "cerf_flood_usd": cf.get(y, np.nan) if 2006 <= y <= 2021 else np.nan,
                }
            )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv("outputs/year_ledger.csv", index=False)
    for fw in FRAMEWORKS:
        d = df[df.framework == fw]
        print(
            fw,
            "fired",
            sorted(d[d.framework_fired == 1].year),
            "| 2023",
            sorted(d[d.grrr_2023 == 1].year),
            "| 2026",
            sorted(d[d.grrr_2026 == 1].year),
            "| observed",
            sorted(d[d.observed == 1].year),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
