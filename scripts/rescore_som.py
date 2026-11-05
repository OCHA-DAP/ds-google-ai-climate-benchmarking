"""Somalia, station-skill layer: GRRR reanalysis against the SWALIM gauges, same code on both releases.

Reproduces the three published tables of `ds-aa-som-floods` (2023 bucket) and re-runs them on
the November 2026 release:

- `som_ms_pair_metrics` (notebook 06): best-lag Spearman of the model's daily discharge against
  the river's reference gauge level (Luuq for the Juba, Belet Weyne for the Shabelle), per
  season, lags -10..30, 1998-2023, at least 60 paired days. Also reported against the station's
  own gauge, which is the question the benchmark asks.
- `som_ms_peak_correlations`: Spearman of seasonal maxima, model vs gauge.
- `som_model_gauge_scores` (notebook 02): episode POD and FAR. Gauge episodes = days at or above
  the station's post-2000 Weibull RP3 level (annual maxima, years >= 2000), grouped with a
  14-day recession gap; model episodes the same on the model's RP3/RP4/RP5 discharge; an
  episode counts as hit when another overlaps it within 7 days; joint window 2002-01-01 to
  2023-12-23. The baseline took Google's RP3/4/5 from the Flood Hub API thresholds; this script
  derives them by Weibull on the reanalysis over the same window (`derived`) and, for 2026,
  also reads the release's shipped table (`shipped`). The difference is reported, not hidden.

Seasons follow the repo: Gu = Mar-May, Deyr = Oct-Dec (the proxy check used Apr-Jun for Gu).

`--release glofas_v5` runs the same code on the proposal's other incumbent leg, the GloFAS v5
reanalysis per station from the spoke's blob (1999-2023); it has no shipped return-period table,
so only the `derived` convention is scored.

Usage:
    uv run scripts/rescore_som.py --release 2023
    uv run scripts/rescore_som.py --release 2026
    uv run scripts/rescore_som.py --release glofas_v5
Writes outputs/rescore_som_<release>.csv (one row per station, season, metric block).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import reanalysis, shipped_return_periods, weibull_threshold
from incumbents import glofas_som

STAGE = "dev"
PREFIX = "ds-aa-som-floods/raw/swalim"
GAUGES = {  # station: (river, SWALIM file, Flood Hub id)   -- from ds-aa-som-floods constants
    "dollow": ("juba", "snrfa_level_data_JB009 - Dollow.csv", "hybas_1121039440"),
    "luuq": ("juba", "snrfa_level_data_JB001 - Luuq.csv", "hybas_1122050700"),
    "bardheere": ("juba", "snrfa_level_data_JB002 - Bardheere.csv", "hybas_1121087010"),
    "bualle": ("juba", "snrfa_level_data_JB010 - Bualle.csv", "hybas_1121116000"),
    "belet_weyne": ("shabelle", "snrfa_level_data_SH001 - Belet Weyne.csv", "hybas_1121024250"),
    "bulo_burti": ("shabelle", "snrfa_level_data_SH002 - Bulo Burti.csv", "hybas_1121049060"),
    "jowhar": ("shabelle", "snrfa_level_data_SH004 - Jowhar.csv", "hybas_1122059030"),
}
REFERENCE = {"juba": "luuq", "shabelle": "belet_weyne"}
SEASONS = {"gu": [3, 4, 5], "deyr": [10, 11, 12]}
YEARS = (1998, 2023)
MIN_LAG, MAX_LAG, MIN_OBS = -10, 30, 60
WINDOW = (pd.Timestamp("2002-01-01"), pd.Timestamp("2023-12-23"))
GAP_DAYS, TOL_DAYS = 14, 7


def load_level(fname: str) -> pd.Series:
    df = stratus.load_csv_from_blob(f"{PREFIX}/{fname}", stage=STAGE)
    if len(df) == 0:
        raise ValueError(f"{fname}: header-only file, no readings")
    fmt = "%d/%m/%Y" if df["date"].str.contains("/", na=False).any() else "%Y-%m-%d"
    df["date"] = pd.to_datetime(df["date"], format=fmt)
    s = df.drop_duplicates("date").set_index("date")["level(m)"].sort_index().dropna()
    return s.rename("level")


def best_lag_corr(model: pd.Series, bench: pd.Series, months: list[int]):
    m = model[model.index.month.isin(months)]
    m = m[(m.index.year >= YEARS[0]) & (m.index.year <= YEARS[1])]
    best = (0.0, None, 0)
    for lag in range(MIN_LAG, MAX_LAG + 1):
        j = pd.concat([m, bench.shift(-lag)], axis=1, join="inner").dropna()
        if len(j) < MIN_OBS:
            continue
        r, _ = stats.spearmanr(j.iloc[:, 0], j.iloc[:, 1])
        if abs(r) > abs(best[0]):
            best = (float(r), lag, len(j))
    return best


def seasonal_max(s: pd.Series, months: list[int]) -> pd.Series:
    sub = s[s.index.month.isin(months)]
    sub = sub[(sub.index.year >= YEARS[0]) & (sub.index.year <= YEARS[1])]
    return sub.groupby(sub.index.year).max().dropna()


def episodes(mask: pd.Series, gap_days: int = GAP_DAYS) -> list[tuple]:
    days = mask.index[mask]
    if not len(days):
        return []
    out, s, p = [], days[0], days[0]
    for d in days[1:]:
        if (d - p).days > gap_days:
            out.append((s, p))
            s = d
        p = d
    out.append((s, p))
    return out


def hits(a: list[tuple], b: list[tuple], tol: int = TOL_DAYS) -> int:
    t = pd.Timedelta(days=tol)
    return sum(any(bs <= e + t and be >= s - t for bs, be in b) for s, e in a)


def rp_interp(rp2: float, rp5: float, target: float) -> float:
    """Notebook 02's interpolation between published RP2 and RP5 on the Gumbel reduced variate."""
    yT = lambda T: -np.log(-np.log(1 - 1 / T))
    return rp2 + (rp5 - rp2) * (yT(target) - yT(2)) / (yT(5) - yT(2))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--release", choices=["2023", "2026", "glofas_v5"], required=True)
    a = p.parse_args(argv)

    levels = {st: load_level(f) for st, (_, f, _) in GAUGES.items()}
    shipped = {}
    if a.release == "glofas_v5":
        models = {st: glofas_som(st) for st in GAUGES}
    else:
        models = {st: reanalysis(a.release, hid) for st, (_, _, hid) in GAUGES.items()}
        for st, (_, _, hid) in GAUGES.items():
            try:
                shipped[st] = shipped_return_periods(a.release, hid)
            except (KeyError, ValueError) as e:
                print(f"note: no shipped return periods for {st}: {e}", file=sys.stderr)

    rows = []
    for st, (river, _, _hid) in GAUGES.items():
        q = models[st]
        own = levels[st]
        ref = levels[REFERENCE[river]]
        # post-2000 RP3 on the gauge, annual maxima of years >= 2000 (notebook 02)
        am_obs = (
            own[own.index.year >= 2000]
            .groupby(own[own.index.year >= 2000].index.year)
            .max()
            .dropna()
        )
        rp3_obs = weibull_threshold(am_obs.values, 3) if len(am_obs) >= 8 else float("nan")
        for season, months in SEASONS.items():
            r_ref, lag_ref, n_ref = best_lag_corr(q, ref, months)
            r_own, lag_own, n_own = best_lag_corr(q, own, months)
            pm, po = seasonal_max(q, months), seasonal_max(own, months)
            j = pd.concat([pm, po], axis=1, join="inner").dropna()
            peak_rho = (
                float(stats.spearmanr(j.iloc[:, 0], j.iloc[:, 1])[0])
                if len(j) >= 8
                else float("nan")
            )
            rows.append(
                {
                    "release": a.release,
                    "river": river,
                    "station": st,
                    "season": season,
                    "block": "correlation",
                    "daily_rho_ref": r_ref,
                    "best_lag_ref": lag_ref,
                    "n_ref": n_ref,
                    "daily_rho_own": r_own,
                    "best_lag_own": lag_own,
                    "n_own": n_own,
                    "peak_rho_own": peak_rho,
                    "n_seasons": len(j),
                }
            )
        # episode scores, annual, joint window
        jw = pd.concat([q, own], axis=1, join="inner").loc[WINDOW[0] : WINDOW[1]].dropna()
        if len(jw) < 1000 or np.isnan(rp3_obs):
            print(
                f"note: {st}: {len(jw)} joint days, rp3_obs={rp3_obs}; episode scores skipped",
                file=sys.stderr,
            )
            continue
        obs_eps = episodes(jw["level"] >= rp3_obs)
        am_q = jw["q"].groupby(jw.index.year).max()
        for conv in ["derived", "shipped"]:
            if conv == "shipped" and st not in shipped:
                continue
            for T in [3, 4, 5]:
                if conv == "derived":
                    thr = weibull_threshold(am_q.values, T)
                else:
                    sp = shipped[st]
                    thr = sp[float(T)] if float(T) in sp else rp_interp(sp[2.0], sp[5.0], T)
                mod_eps = episodes(jw["q"] >= thr)
                pod = hits(obs_eps, mod_eps) / len(obs_eps) if obs_eps else float("nan")
                far = 1 - hits(mod_eps, obs_eps) / len(mod_eps) if mod_eps else float("nan")
                rows.append(
                    {
                        "release": a.release,
                        "river": river,
                        "station": st,
                        "season": "annual",
                        "block": "episodes",
                        "rp_convention": conv,
                        "model_rp": T,
                        "threshold_m3s": thr,
                        "obs_rp3_level_m": rp3_obs,
                        "obs_episodes": len(obs_eps),
                        "model_episodes": len(mod_eps),
                        "POD": pod,
                        "FAR": far,
                        "n_joint_days": len(jw),
                    }
                )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv(f"outputs/rescore_som_{a.release}.csv", index=False)
    pd.set_option("display.width", 250)
    c = df[df.block == "correlation"]
    print(
        c[
            [
                "station",
                "season",
                "daily_rho_ref",
                "best_lag_ref",
                "daily_rho_own",
                "best_lag_own",
                "peak_rho_own",
                "n_seasons",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )
    e = df[(df.block == "episodes") & (df.model_rp == 3)]
    print(
        e[
            [
                "station",
                "rp_convention",
                "threshold_m3s",
                "obs_episodes",
                "model_episodes",
                "POD",
                "FAR",
            ]
        ]
        .round(2)
        .to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
