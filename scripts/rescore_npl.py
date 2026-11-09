"""Nepal: model exceedance events against DHM danger-level crossings, same code on both releases.

Reproduces `ds-aa-npl-flooding` book chapter 05 (event detection) for GRRR and GloFAS v4 and
re-runs it on the November 2026 release:

- truth: upward crossings of the DHM danger level (Chatara 7.0 m, record to 2012; Chisapani
  10.5 m, to 2015), no recession rule;
- model events: days above the RP2 or RP5 discharge, collapsed with a 7-day gap, only up to the
  end of the DHM record;
- match within ±7 days; hits, misses and false alarms.

Return-period conventions, all reported:
- `quantile_full`: the book's GRRR convention, quantile 1 - 1/RP of the annual maxima over the
  model's whole reanalysis (which reaches past the DHM record);
- `quantile_window`: the same, annual maxima restricted to the DHM record;
- `shipped`: the release's own return-period table;
- GloFAS v4: the Copernicus dashboard values in the repo constants (8,113 / 10,306 at Chatara,
  5,664 / 6,797 at Chisapani).

Needs AA_DATA_DIR (the shared data directory) for the DHM and GloFAS files.

Usage:
    uv run scripts/rescore_npl.py --release 2026
Writes outputs/rescore_npl_<release>.csv.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import empirical_quantile_threshold, reanalysis, shipped_return_periods

STATIONS = {
    "Chatara": {
        "danger_level": 7.0,
        "glofas": {2: 8113.0, 5: 10306.0},
        "hybas": "hybas_4120864110",
    },
    "Chisapani": {
        "danger_level": 10.5,
        "glofas": {2: 5664.0, 5: 6797.0},
        "hybas": "hybas_4121455820",
    },
}
GAP_DAYS, WINDOW_DAYS = 7, 7


def collapse_to_events(dates: pd.DatetimeIndex, gap_days: int = GAP_DAYS) -> pd.DatetimeIndex:
    if len(dates) == 0:
        return pd.DatetimeIndex([])
    dates = dates.sort_values()
    events = [dates[0]]
    for d in dates[1:]:
        if (d - events[-1]).days > gap_days:
            events.append(d)
    return pd.DatetimeIndex(events)


def match_events(
    source: pd.DatetimeIndex, reference: pd.DatetimeIndex, window_days: int = WINDOW_DAYS
):
    w = pd.Timedelta(days=window_days)
    matched = [s for s in source if any(abs(s - r) <= w for r in reference)]
    ref_hit = [r for r in reference if any(abs(s - r) <= w for s in source)]
    return {
        "n_reference": len(reference),
        "n_source": len(source),
        "n_matched": len(ref_hit),
        "misses": len(reference) - len(ref_hit),
        "false_alarms": len(source) - len(matched),
    }


def detect(series: pd.Series, threshold: float, refs: pd.DatetimeIndex, end: pd.Timestamp) -> dict:
    s = series[~series.index.duplicated()]
    s = s[s.index <= end]
    events = collapse_to_events(s[s > threshold].index)
    return match_events(events, refs)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--release", choices=["2023", "2026"], required=True)
    a = p.parse_args(argv)
    root = Path(os.environ["AA_DATA_DIR"])
    dhm = pd.read_csv(root / "private/exploration/npl/dhm/processed/waterl_level_procssed.csv")
    dhm["date"] = pd.to_datetime(dhm["date"])
    dhm = dhm.set_index("date")
    glofas = (
        xr.open_dataset(root / "public/processed/npl/glofas/npl_cems-glofas-historical_v4.nc")
        .to_dataframe()
        .reset_index()
        .set_index("time")
    )
    glofas.index = pd.to_datetime(glofas.index).normalize()

    rows = []
    for name, cfg in STATIONS.items():
        lvl = dhm[name].dropna()
        cross = (lvl > cfg["danger_level"]).astype(int).diff() == 1
        refs = lvl[cross].index
        end = lvl.index.max()
        print(
            f"{name}: DHM {lvl.index.min().date()} to {end.date()}, {len(refs)} crossings of {cfg['danger_level']} m"
        )

        q = reanalysis(a.release, cfg["hybas"])
        am_full = q.groupby(q.index.year).max()
        qw = q[q.index <= end]
        am_win = qw.groupby(qw.index.year).max()
        shipped = shipped_return_periods(a.release, cfg["hybas"])
        conventions = {
            "quantile_full": {rp: empirical_quantile_threshold(am_full, rp) for rp in (2, 5)},
            "quantile_window": {rp: empirical_quantile_threshold(am_win, rp) for rp in (2, 5)},
            "shipped": {rp: shipped[float(rp)] for rp in (2, 5)},
        }
        for conv, thr in conventions.items():
            for rp in (2, 5):
                m = detect(q, thr[rp], refs, end)
                rows.append(
                    {
                        "release": a.release,
                        "station": name,
                        "source": "GRRR",
                        "rp_convention": conv,
                        "rp": rp,
                        "threshold_m3s": thr[rp],
                        **m,
                    }
                )
        gl = glofas[name].dropna()
        for rp in (2, 5):
            m = detect(gl, cfg["glofas"][rp], refs, end)
            rows.append(
                {
                    "release": "glofas_v4",
                    "station": name,
                    "source": "GloFAS v4",
                    "rp_convention": "dashboard",
                    "rp": rp,
                    "threshold_m3s": cfg["glofas"][rp],
                    **m,
                }
            )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv(f"outputs/rescore_npl_{a.release}.csv", index=False)
    pd.set_option("display.width", 250)
    print(df.round(0).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
