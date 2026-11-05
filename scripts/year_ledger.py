"""Year ledger: per framework and year, who said flood.

The table the frameworks have used themselves (the Somalia deck's "activations, impact and
response, year by year"), built for every framework with a Google-evaluable station:

- framework_fired: the framework's own published backtest years (knowledge-base pages);
- incumbent / grrr_2023 / grrr_2026 / observed: one rule for all four. The incumbent is the
  model the framework ran on (incumbents.py: GRRR 2023 for Nigeria, GloFAS for Somalia, Nepal,
  Chad and Bangladesh, the gauge for Niger), scored by its own reanalysis. The threshold is the empirical
  Weibull level at the framework's return period, fitted on seasonal maxima over the same
  BASELINE years (1998-2023, restricted to years the observed record covers), and a year is
  flagged when its seasonal maximum reaches it. Nigeria applies the endorsed rule on top
  (>= 6 of 10 gauges over their own level on the same day) and its observed record is GRDC
  discharge at Yidere Bode; Somalia uses the reference gauge of each river (Luuq, Belet Weyne)
  in either season; Chad the DRE level at N'Djamena; Nepal the DHM level at Chatara (record
  ends 2012); Niger has no model trigger, so its observed column is the published 604 cm years.
  Bangladesh's FFWC file holds only days above the danger level, so its observed column keeps
  the framework's own definition (danger level + 0.85 m for 3 days) and its model columns use
  the Weibull rule; the two are not on the same footing and the header says so.
  Each column header carries fires / baseline years, the empirical return period.
- emdat_affected: EM-DAT total affected by floods in the country that year (team blob mirror;
  check its vintage);
- cerf_flood_usd: CERF rapid-response flood allocations for the country that year, and
  cerf_aa_usd the anticipatory ones, from the team's OneGMS mirror (dev database, via the tunnel).

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
from grrr_releases import reanalysis, weibull_threshold
from incumbents import (
    INCUMBENT,
    TRIGGER_SOURCE,
    glofas_bgd_bahadurabad,
    glofas_npl,
    glofas_som,
    glofas_tcd_ndjamena,
)
from rescore_bgd import load_ffwc_bahadurabad, observed_events
from rescore_som import GAUGES as SOM_GAUGES
from rescore_som import load_level
from rescore_tcd import load_dre_tp

YEARS = list(range(1998, 2026))
BASELINE = (1998, 2023)
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
    "Nigeria 2026": 4.0,
    "Somalia": 5.0,
    "Nepal 2025 (Chatara)": 5.0,
    "Chad 2025": 4.0,
    "Bangladesh 2025 (Bahadurabad)": 5.0,
    "Niger 2025": 5.0,
}


def seasonal_max(s: pd.Series, months: list[int] | None) -> pd.Series:
    x = s if months is None else s[s.index.month.isin(months)]
    return x.groupby(x.index.year).max().dropna()


def weibull_flags(
    s: pd.Series, months, rp: float, baseline: tuple[int, int]
) -> tuple[set[int], float, int]:
    """Years whose seasonal maximum reaches the Weibull level at `rp` fitted on the baseline years.

    Returns (years flagged over the whole record, threshold, number of baseline years used).
    """
    pk = seasonal_max(s, months)
    base = pk[(pk.index >= baseline[0]) & (pk.index <= baseline[1])]
    if len(base) < 8:
        raise ValueError(f"only {len(base)} baseline years, cannot fit a Weibull level")
    thr = weibull_threshold(base.values, rp)
    if np.isnan(thr):
        raise ValueError(f"return period {rp} exceeds the {len(base)}-year baseline")
    return {int(y) for y, v in pk.items() if v >= thr}, thr, len(base)


def rate(years: set[int], baseline: tuple[int, int]) -> tuple[int, int]:
    n = sum(1 for y in range(baseline[0], baseline[1] + 1) if y in years)
    return n, baseline[1] - baseline[0] + 1


def model_flags(release: str, baselines: dict[str, tuple[int, int]]) -> dict[str, set[int]]:
    out = {}
    # Nigeria: per gauge, Weibull 4-yr on Aug-Nov maxima over the baseline; >= 6 of 10 the same day
    daily = pd.DataFrame({g: reanalysis(release, g) for g in NGA_GAUGES})
    b = baselines["Nigeria 2026"]
    over = {}
    for g in NGA_GAUGES:
        _, thr, _ = weibull_flags(daily[g], [8, 9, 10, 11], 4.0, b)
        over[g] = daily[g] >= thr
    cnt = pd.DataFrame(over).sum(axis=1)
    cnt = cnt[cnt.index.month.isin([8, 9, 10, 11])]
    out["Nigeria 2026"] = {int(y) for y, v in cnt.groupby(cnt.index.year).max().items() if v >= 6}
    # Somalia: reference gauges, either season, Weibull RP5 per season over the baseline
    yrs = set()
    for st in ["luuq", "belet_weyne"]:
        q = reanalysis(release, SOM_GAUGES[st][2])
        for months in ([3, 4, 5], [10, 11, 12]):
            f, _, _ = weibull_flags(q, months, 5.0, baselines["Somalia"])
            yrs |= f
    out["Somalia"] = yrs
    for fw, hid in STATION.items():
        q = reanalysis(release, hid)
        out[fw], _, _ = weibull_flags(q, FRAMEWORKS[fw]["season"], RP_LEVEL[fw], baselines[fw])
    return out


def covered(s: pd.Series, months, baseline: tuple[int, int]) -> tuple[int, int]:
    """The baseline cut to the years the series has a seasonal maximum for."""
    pk = seasonal_max(s, months)
    yrs = [int(y) for y in pk.index if baseline[0] <= y <= baseline[1]]
    if not yrs:
        raise ValueError("series has no seasonal maxima inside the baseline")
    return (min(yrs), max(yrs))


def incumbent_flags(
    baselines: dict[str, tuple[int, int]], g23: dict[str, set[int]], obs: dict[str, set[int]]
) -> dict[str, tuple[set[int], tuple[int, int]]]:
    """Years flagged by the model each framework ran on, under the same Weibull rule.

    Nigeria 2026 ran on the GRRR 2023 bucket and Niger on the gauge alone, so those columns
    repeat grrr_2023 and observed; the rest ran on GloFAS (see incumbents.py). Returns, per
    framework, the flagged years and the baseline years the incumbent record covers.
    """
    out = {
        "Nigeria 2026": (
            g23["Nigeria 2026"],
            (baselines["Nigeria 2026"][0], min(baselines["Nigeria 2026"][1], 2023)),
        )
    }
    out["Niger 2025"] = (obs["Niger 2025"], baselines["Niger 2025"])
    yrs, cov = set(), None
    for st in ["luuq", "belet_weyne"]:
        q = glofas_som(st)
        for months in ([3, 4, 5], [10, 11, 12]):
            f, _, _ = weibull_flags(q, months, 5.0, baselines["Somalia"])
            yrs |= f
        cov = covered(q, [3, 4, 5], baselines["Somalia"])
    out["Somalia"] = (yrs, cov)
    series = {
        "Nepal 2025 (Chatara)": glofas_npl("Chatara"),
        "Chad 2025": glofas_tcd_ndjamena(),
        "Bangladesh 2025 (Bahadurabad)": glofas_bgd_bahadurabad(),
    }
    for fw, q in series.items():
        months, b = FRAMEWORKS[fw]["season"], baselines[fw]
        f, _, _ = weibull_flags(q, months, RP_LEVEL[fw], b)
        out[fw] = (f, covered(q, months, b))
    return out


def observed_series() -> dict[str, tuple[pd.Series, list[int] | None]]:
    """The observed record per framework as a daily series, with the season months to use."""
    out = {}
    out["Chad 2025"] = (load_dre_tp(), [8, 9, 10, 11])
    import tempfile

    import ocha_stratus as stratus
    import xarray as xr

    cc = stratus.get_container_client("projects", stage="dev")
    raw = cc.get_blob_client("ds-aa-nga-flooding/raw/grdc/GRDC-Daily.nc").download_blob().readall()
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
        tmp.write(raw)
    ds = xr.open_dataset(tmp.name)
    g = ds["runoff_mean"].sel(id=1834110).to_series()  # Yidere Bode
    g = g.where(g > -900).dropna()
    g.index = pd.to_datetime(g.index).normalize()
    out["Nigeria 2026"] = (g, [7, 8, 9, 10, 11])
    dhm = (
        pd.read_csv(
            Path(os.environ["AA_DATA_DIR"])
            / "private/exploration/npl/dhm/processed/waterl_level_procssed.csv",
            parse_dates=["date"],
        )
        .set_index("date")["Chatara"]
        .dropna()
    )
    out["Nepal 2025 (Chatara)"] = (dhm, [6, 7, 8, 9])
    return out


OBSERVED_YEARS: dict[str, int] = {}  # baseline years the observed record actually has


def observed_flags(baselines: dict[str, tuple[int, int]]) -> dict[str, set[int]]:
    """Years the observed record flags; OBSERVED_YEARS gets the baseline years each record has."""
    out = {}
    obs = observed_series()
    for fw, (s, months) in obs.items():
        out[fw], _, OBSERVED_YEARS[fw] = weibull_flags(s, months, RP_LEVEL[fw], baselines[fw])
    # Somalia: reference gauge levels, Weibull RP5 per season on the same baseline
    yrs = set()
    for st in ["luuq", "belet_weyne"]:
        lv = load_level(SOM_GAUGES[st][1])
        for months in ([3, 4, 5], [10, 11, 12]):
            f, _, _ = weibull_flags(lv, months, 5.0, baselines["Somalia"])
            yrs |= f
    out["Somalia"] = yrs
    OBSERVED_YEARS["Somalia"] = baselines["Somalia"][1] - baselines["Somalia"][0] + 1
    out["Bangladesh 2025 (Bahadurabad)"] = {
        int(d.year) for d in observed_events(load_ffwc_bahadurabad())
    }
    out["Niger 2025"] = set(FRAMEWORKS["Niger 2025"]["fired"])
    for fw in ("Bangladesh 2025 (Bahadurabad)", "Niger 2025"):
        OBSERVED_YEARS[fw] = baselines[fw][1] - baselines[fw][0] + 1
    return out


def baselines_from_records() -> dict[str, tuple[int, int]]:
    """1998-2023, cut to the years each observed record covers with a full season."""
    b = {}
    obs = observed_series()
    for fw, (s, months) in obs.items():
        pk = seasonal_max(s, months)
        yrs = [int(y) for y in pk.index if BASELINE[0] <= y <= BASELINE[1]]
        b[fw] = (min(yrs), max(yrs))
    lv = load_level(SOM_GAUGES["luuq"][1])
    pk = seasonal_max(lv, [3, 4, 5])
    yrs = [int(y) for y in pk.index if BASELINE[0] <= y <= BASELINE[1]]
    b["Somalia"] = (min(yrs), max(yrs))
    b["Bangladesh 2025 (Bahadurabad)"] = BASELINE
    b["Niger 2025"] = BASELINE
    return b


def emdat_affected(iso3: str) -> dict[int, float]:
    em = emdat.load_emdat_from_blob(iso3=iso3)
    fl = em[em["Disaster Type"].astype(str).str.contains("Flood", case=False)]
    return (
        fl.groupby("Start Year")["Total Affected"].sum(min_count=1).dropna().astype(float).to_dict()
    )


def cerf_flood(iso3: str) -> tuple[dict[int, float], dict[int, float]]:
    """CERF flood allocations by year: (rapid response, anticipatory action).

    From the team's OneGMS mirror `aa.cerf_allocation` in the dev database, read through the
    Databricks SSH tunnel on 4 Nov 2026 into outputs/cerf_flood_allocations_dev.csv (window,
    emergency type Flood, `aa_keyword` marks the anticipatory allocations). Re-read with:
        DSCI_AZ_DB_DEV_HOST=127.0.0.1:15432 after `db-tunnel up` (internal KB, local-db-access).
    """
    f = Path("outputs/cerf_flood_allocations_dev.csv")
    if not f.exists():
        raise FileNotFoundError(
            "outputs/cerf_flood_allocations_dev.csv missing: read aa.cerf_allocation through the tunnel first"
        )
    df = pd.read_csv(f)
    sub = df[df.country_iso3 == iso3]
    rr = (
        sub[(sub.window_name == "Rapid Response") & (~sub.aa_keyword.astype(bool))]
        .groupby("year")["usd"]
        .sum()
    )
    aa = sub[sub.aa_keyword.astype(bool)].groupby("year")["usd"].sum()
    return rr.astype(float).to_dict(), aa.astype(float).to_dict()


def main() -> int:
    baselines = baselines_from_records()
    print("baselines:", baselines)
    g23, g26, obs = (
        model_flags("2023", baselines),
        model_flags("2026", baselines),
        observed_flags(baselines),
    )
    inc = incumbent_flags(baselines, g23, obs)
    rows, hdr = [], []
    for fw, cfg in FRAMEWORKS.items():
        em = emdat_affected(cfg["iso3"])
        cf, ca = cerf_flood(cfg["iso3"])
        b = baselines[fw]
        b23 = (b[0], min(b[1], 2023))
        hdr.append(
            {
                "framework": fw,
                "baseline_start": b[0],
                "baseline_end": b[1],
                "rp": RP_LEVEL[fw],
                "fired_n": rate(set(cfg["fired"]), b)[0] if cfg["fired"] else np.nan,
                "grrr_2023_n": rate(g23[fw], b23)[0],
                "grrr_2023_years": b23[1] - b23[0] + 1,
                "incumbent_label": INCUMBENT[fw],
                "incumbent_n": rate(inc[fw][0], inc[fw][1])[0],
                "incumbent_years": inc[fw][1][1] - inc[fw][1][0] + 1,
                "trigger_source": TRIGGER_SOURCE[fw],
                "grrr_2026_n": rate(g26[fw], b)[0],
                "observed_n": rate(obs[fw], b)[0],
                "observed_years": OBSERVED_YEARS[fw],
                "baseline_years": b[1] - b[0] + 1,
            }
        )
        for y in YEARS:
            rows.append(
                {
                    "framework": fw,
                    "iso3": cfg["iso3"],
                    "year": y,
                    "framework_fired": int(y in cfg["fired"]) if cfg["fired"] else np.nan,
                    "grrr_2023": int(y in g23[fw]) if y <= 2023 else np.nan,
                    "incumbent": int(y in inc[fw][0]) if y <= inc[fw][1][1] else np.nan,
                    "grrr_2026": int(y in g26[fw]),
                    "observed": int(y in obs[fw])
                    if (fw != "Nepal 2025 (Chatara)" or y <= 2012)
                    else np.nan,
                    "emdat_affected": em.get(y, np.nan),
                    "cerf_flood_usd": cf.get(y, np.nan) if y >= 2006 else np.nan,
                    "cerf_aa_usd": ca.get(y, np.nan) if y >= 2020 else np.nan,
                }
            )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv("outputs/year_ledger.csv", index=False)
    pd.DataFrame(hdr).to_csv("outputs/year_ledger_rates.csv", index=False)
    for h in hdr:
        print(h)
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
