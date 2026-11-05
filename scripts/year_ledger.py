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
  in either season; Chad the DRE level at N'Djamena; Nepal the DHM level at Chatara from the
  drive's updated file (record to 2019; the spoke's book used the earlier file, to 2012); Niger has no model trigger, so its observed column is the published 604 cm years.
  Bangladesh's FFWC file holds only days above the danger level, so its observed column keeps
  the framework's own definition (danger level + 0.85 m for 3 days) and its model columns use
  the Weibull rule; the two are not on the same footing and the header says so.
  Each column header carries fires / baseline years, the empirical return period.
- emdat_affected: EM-DAT total affected by floods in the country that year (team blob mirror;
  check its vintage);
- cerf_flood_usd: CERF rapid-response flood allocations for the country that year,
  cerf_aa_usd the anticipatory ones, cerf_total_usd the two combined (the figure shows the
  total), from the team's OneGMS mirror (dev database, via the tunnel).
- year_ledger_impact_corr.csv: per flag column, Spearman against EM-DAT affected and against
  the CERF total, and phi against whether any CERF flood allocation was made (2006 on).

Writes outputs/year_ledger.csv. Needs blob and AA_DATA_DIR access.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from ocha_stratus import emdat
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import reanalysis, weibull_threshold
from incumbents import (
    INCUMBENT,
    TAINT,
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
    # fired: the framework's published backtest years; window: the years that backtest covered
    # (cells outside it are blank, not zero)
    "Nigeria 2026": {
        "iso3": "NGA",
        "fired": [1998, 1999, 2012, 2018, 2019, 2022],
        "window": (1998, 2023),
        "season": [8, 9, 10, 11],
    },
    "Somalia": {
        "iso3": "SOM",
        "fired": [2006, 2010, 2014, 2016, 2018, 2019, 2020, 2023],
        "window": (1999, 2023),
        "season": None,
    },
    "Nepal 2025 (Chatara)": {"iso3": "NPL", "fired": [], "window": None, "season": [6, 7, 8, 9]},
    "Chad 2025": {
        "iso3": "TCD",
        "fired": [2003, 2005, 2010, 2012, 2022],
        "window": (2003, 2022),
        "season": [8, 9, 10, 11],
    },
    "Bangladesh 2025 (Bahadurabad)": {
        "iso3": "BGD",
        "fired": [],
        "window": None,
        "season": [6, 7, 8, 9],
    },
    "Niger 2025": {
        "iso3": "NER",
        "fired": [1998, 1999, 2010, 2012, 2013, 2015, 2019, 2020, 2024],
        "window": (1979, 2024),
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
OBSERVED_LABEL = {  # the local gauge behind each observed column
    "Nigeria 2026": "GRDC Yidere Bode",
    "Somalia": "SWALIM gauges",
    "Nepal 2025 (Chatara)": "DHM Chatara",
    "Chad 2025": "DRE N'Djamena",
    "Bangladesh 2025 (Bahadurabad)": "FFWC Bahadurabad",
    "Niger 2025": "ABN Niamey",
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
) -> dict[str, tuple[set[int], tuple[int, int], int]]:
    """Years flagged by the model each framework ran on, under the same Weibull rule.

    Nigeria 2026 ran on the GRRR 2023 bucket and Niger on the gauge alone, so those columns
    repeat grrr_2023 and observed; the rest ran on GloFAS (see incumbents.py). Returns, per
    framework, the flagged years, the baseline years the incumbent record covers, and the last
    year it has data for (years after it are blank in the ledger, not zero).
    """
    out = {
        "Nigeria 2026": (
            g23["Nigeria 2026"],
            (baselines["Nigeria 2026"][0], min(baselines["Nigeria 2026"][1], 2023)),
            2023,
        )
    }
    out["Niger 2025"] = (obs["Niger 2025"], baselines["Niger 2025"], max(obs["Niger 2025"]))
    yrs, cov = set(), None
    for st in ["luuq", "belet_weyne"]:
        q = glofas_som(st)
        for months in ([3, 4, 5], [10, 11, 12]):
            f, _, _ = weibull_flags(q, months, 5.0, baselines["Somalia"])
            yrs |= f
        cov = covered(q, [3, 4, 5], baselines["Somalia"])
    out["Somalia"] = (yrs, cov, int(q.index.year.max()))
    series = {
        "Nepal 2025 (Chatara)": glofas_npl("Chatara"),
        "Chad 2025": glofas_tcd_ndjamena(),
        "Bangladesh 2025 (Bahadurabad)": glofas_bgd_bahadurabad(),
    }
    for fw, q in series.items():
        months, b = FRAMEWORKS[fw]["season"], baselines[fw]
        f, _, _ = weibull_flags(q, months, RP_LEVEL[fw], b)
        out[fw] = (f, covered(q, months, b), int(q.index.year.max()))
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
            / "private/exploration/npl/dhm/processed/water_level_processed_updated.csv",
            parse_dates=["date"],
        )
        .set_index("date")["Chatara"]
        .dropna()
    )
    out["Nepal 2025 (Chatara)"] = (dhm, [6, 7, 8, 9])
    return out


OBSERVED_YEARS: dict[str, int] = {}  # baseline years the observed record actually has
OBSERVED_END: dict[str, int] = {}  # last year the observed record covers


def observed_flags(baselines: dict[str, tuple[int, int]]) -> dict[str, set[int]]:
    """Years the observed record flags; OBSERVED_YEARS gets the baseline years each record has."""
    out = {}
    obs = observed_series()
    for fw, (s, months) in obs.items():
        out[fw], _, OBSERVED_YEARS[fw] = weibull_flags(s, months, RP_LEVEL[fw], baselines[fw])
        OBSERVED_END[fw] = int(s.index.year.max())
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


# EM-DAT is national; these words in an event's Location, Admin Units or River Basin text mark
# it as touching the monitored basin. Whole-event totals are kept (EM-DAT does not split them).
BASIN_WORDS = {
    "Nigeria 2026": [
        "adamawa",
        "taraba",
        "benue",
        "kogi",
        "nasarawa",
        "lokoja",
        "yola",
        "numan",
        "makurdi",
    ],
    "Somalia": [
        "juba",
        "jubba",
        "shabel",
        "shabeel",
        "gedo",
        "hiraan",
        "hiran",
        "hirshabelle",
        "jubaland",
        "belet",
        "beled",
        "jowhar",
        "luuq",
        "bardheere",
        "baardheere",
        "bualle",
        "bu'aale",
        "dollow",
        "doolow",
        "bulo burti",
        "buulo",
        "jilib",
        "afgooye",
    ],
    "Nepal 2025 (Chatara)": [
        "koshi",
        "kosi",
        "sunsari",
        "saptari",
        "udayapur",
        "morang",
        "chatara",
        "province 1",
        "province no. 1",
        "eastern",
    ],
    "Chad 2025": ["djamena", "chari", "logone", "hadjer", "baguirmi", "mayo-kebbi", "mayo kebbi"],
    "Bangladesh 2025 (Bahadurabad)": [
        "jamuna",
        "brahmaputra",
        "kurigram",
        "gaibandha",
        "jamalpur",
        "bogra",
        "bogura",
        "sirajganj",
        "tangail",
        "lalmonirhat",
        "nilphamari",
        "rangpur",
    ],
    "Niger 2025": ["niamey", "tillab", "dosso", "niger river", "fleuve niger", "fleuve"],
}


def emdat_affected(iso3: str, basin_words: list[str] | None = None) -> dict[int, float]:
    """People affected by floods per start year; with basin_words, only events whose location
    text mentions the monitored basin (whole-event totals)."""
    em = emdat.load_emdat_from_blob(iso3=iso3)
    fl = em[em["Disaster Type"].astype(str).str.contains("Flood", case=False)]
    if basin_words:
        text = (
            fl["Location"].fillna("").astype(str)
            + " "
            + fl["Admin Units"].fillna("").astype(str)
            + " "
            + fl["River Basin"].fillna("").astype(str)
        ).str.lower()
        hit = text.apply(lambda s: any(w in s for w in basin_words))
        fl = fl[hit]
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


FLAG_COLS = ["framework_fired", "incumbent", "grrr_2026", "observed", "grrr_2023"]
IMPACT = [  # (impact column, first year the source covers)
    ("emdat_basin", 1998),
    ("cerf_flood_usd", 2006),
]
BOOT = 1000


def pair_window(d: pd.DataFrame, start: int, b0: int, b1: int) -> tuple[list[int], set[int]]:
    """The years a framework's key pair is compared on: baseline years inside the measure's
    coverage where both the incumbent and GRRR 2026 have a record, minus the years the
    framework's own anticipatory allocation was made. Returns (years, aa_years_removed)."""
    aa = set(d.loc[d["cerf_aa_usd"].fillna(0) > 0, "year"].astype(int))
    ok = d[
        (d.year >= max(start, b0))
        & (d.year <= b1)
        & d["incumbent"].notna()
        & d["grrr_2026"].notna()
    ]
    years = [int(y) for y in ok.year if int(y) not in aa]
    return years, aa & {int(y) for y in ok.year}


def impact_stats(
    df: pd.DataFrame, rates: dict[str, dict], rng=None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per framework, flag column and impact measure: how the yearly flags line up with impact.

    Two measures, both independent of the models: EM-DAT people affected in events touching the
    monitored basin (1998 on) and CERF rapid-response flood US$ (2006 on). Everything is scored on
    the framework's pair window (`pair_window`): the baseline years both models of the key pair
    cover, minus the years the framework's own anticipatory allocation was made, since that
    allocation is the framework firing and rapid response under-reads in those years. The
    impact years are fixed once per framework and measure on that window: the years whose
    amount reaches the empirical Weibull level at the framework's return period. Years a source
    covers but has no record for count as zero.

    - rho: Spearman of the 0/1 flag against the amount, with a bootstrap 90% interval over years.
    - hits / misses / false_alarms against the impact years, over the window years the column has.
    Also returns the paired difference, GRRR 2026 minus incumbent in impact years caught, with a
    bootstrap 90% interval over the window years, per framework and pooled.
    """
    rng = rng or np.random.default_rng(0)
    rows, paired = [], []
    pooled = {imp: [] for imp, _ in IMPACT}
    for fw, d in df.groupby("framework", sort=False):
        b0, b1, rp = rates[fw]["baseline_start"], rates[fw]["baseline_end"], rates[fw]["rp"]
        for imp, start in IMPACT:
            years, aa_out = pair_window(d, start, b0, b1)
            w = d[d.year.isin(years)].set_index("year")
            amount = w[imp].fillna(0.0).astype(float)
            thr = weibull_threshold(amount.values, rp) if len(w) >= 8 else np.nan
            impact_years = (
                {int(y) for y in amount.index[amount >= thr]} if not np.isnan(thr) else set()
            )
            for col in FLAG_COLS:
                have = [y for y in years if pd.notna(w.loc[y, col])]
                x = w.loc[have, col].astype(float).values
                y_ = w.loc[have, imp].fillna(0.0).astype(float).values
                r = lo = hi = np.nan
                if len(have) >= 3 and len(set(x)) > 1 and len(set(y_)) > 1:
                    r = float(stats.spearmanr(x, y_)[0])
                    bs = []
                    for _ in range(BOOT):
                        i = rng.integers(0, len(x), len(x))
                        if len(set(x[i])) > 1 and len(set(y_[i])) > 1:
                            bs.append(stats.spearmanr(x[i], y_[i])[0])
                    if bs:
                        lo, hi = (float(v) for v in np.percentile(bs, [5, 95]))
                flagged = {y for y in have if w.loc[y, col] == 1}
                scored = set(have)
                rows.append(
                    {
                        "framework": fw,
                        "column": col,
                        "impact": imp,
                        "r": r,
                        "r_lo": lo,
                        "r_hi": hi,
                        "n": len(have),
                        "window_start": min(years) if years else np.nan,
                        "window_end": max(years) if years else np.nan,
                        "impact_threshold": thr,
                        "impact_years": ",".join(str(v) for v in sorted(impact_years & scored)),
                        "hits": len(flagged & impact_years),
                        "misses": len((impact_years & scored) - flagged),
                        "false_alarms": len(flagged - impact_years),
                        "n_scored": len(scored),
                        "aa_years_excluded": ",".join(str(v) for v in sorted(aa_out)),
                    }
                )
            # paired difference on the window, both columns present on every window year
            inc = w["incumbent"].astype(float).values
            g26 = w["grrr_2026"].astype(float).values
            isimp = np.array([int(y) in impact_years for y in w.index])
            diff = int(((g26 == 1) & isimp).sum() - ((inc == 1) & isimp).sum())
            bs = []
            for _ in range(BOOT):
                i = rng.integers(0, len(w), len(w))
                bs.append(int(((g26[i] == 1) & isimp[i]).sum() - ((inc[i] == 1) & isimp[i]).sum()))
            pooled[imp].append(np.array(bs))
            paired.append(
                {
                    "framework": fw,
                    "impact": imp,
                    "n_years": len(w),
                    "n_impact_years": int(isimp.sum()),
                    "hits_incumbent": int(((inc == 1) & isimp).sum()),
                    "hits_grrr_2026": int(((g26 == 1) & isimp).sum()),
                    "fa_incumbent": int(((inc == 1) & ~isimp).sum()),
                    "fa_grrr_2026": int(((g26 == 1) & ~isimp).sum()),
                    "diff": diff,
                    "diff_lo": float(np.percentile(bs, 5)),
                    "diff_hi": float(np.percentile(bs, 95)),
                }
            )
    for imp, parts in pooled.items():
        if not parts:
            continue
        tot = np.sum(parts, axis=0)
        sub = [p_ for p_ in paired if p_["impact"] == imp]
        paired.append(
            {
                "framework": "All frameworks",
                "impact": imp,
                "n_years": sum(p_["n_years"] for p_ in sub),
                "n_impact_years": sum(p_["n_impact_years"] for p_ in sub),
                "hits_incumbent": sum(p_["hits_incumbent"] for p_ in sub),
                "hits_grrr_2026": sum(p_["hits_grrr_2026"] for p_ in sub),
                "fa_incumbent": sum(p_["fa_incumbent"] for p_ in sub),
                "fa_grrr_2026": sum(p_["fa_grrr_2026"] for p_ in sub),
                "diff": sum(p_["diff"] for p_ in sub),
                "diff_lo": float(np.percentile(tot, 5)),
                "diff_hi": float(np.percentile(tot, 95)),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(paired)


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
        emb = emdat_affected(cfg["iso3"], BASIN_WORDS[fw])
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
                "taint": TAINT[fw],
                "grrr_2026_n": rate(g26[fw], b)[0],
                "observed_n": rate(obs[fw], b)[0],
                "observed_years": OBSERVED_YEARS[fw],
                "observed_label": OBSERVED_LABEL[fw],
                "baseline_years": b[1] - b[0] + 1,
            }
        )
        for y in YEARS:
            rows.append(
                {
                    "framework": fw,
                    "iso3": cfg["iso3"],
                    "year": y,
                    "framework_fired": int(y in cfg["fired"])
                    if cfg["window"] and cfg["window"][0] <= y <= cfg["window"][1]
                    else np.nan,
                    "grrr_2023": int(y in g23[fw]) if y <= 2023 else np.nan,
                    "incumbent": int(y in inc[fw][0]) if y <= inc[fw][2] else np.nan,
                    "grrr_2026": int(y in g26[fw]),
                    "observed": int(y in obs[fw]) if y <= OBSERVED_END.get(fw, 2025) else np.nan,
                    "emdat_affected": em.get(y, np.nan),
                    "emdat_basin": emb.get(y, np.nan),
                    "cerf_flood_usd": cf.get(y, np.nan) if y >= 2006 else np.nan,
                    "cerf_aa_usd": ca.get(y, np.nan) if y >= 2020 else np.nan,
                    "cerf_total_usd": (cf.get(y, 0.0) + ca.get(y, 0.0))
                    if (y >= 2006 and (y in cf or y in ca))
                    else np.nan,
                }
            )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv("outputs/year_ledger.csv", index=False)
    pd.DataFrame(hdr).to_csv("outputs/year_ledger_rates.csv", index=False)
    corr, paired = impact_stats(df, {h["framework"]: h for h in hdr})
    corr.to_csv("outputs/year_ledger_impact_corr.csv", index=False)
    paired.to_csv("outputs/year_ledger_paired.csv", index=False)
    print(paired.to_string(index=False))
    print(corr.pivot_table(index=["framework", "impact"], columns="column", values="r").round(2))
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
