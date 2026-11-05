"""Bangladesh: GRRR reanalysis against FFWC observed water level at Bahadurabad, same code on both releases.

The framework's severe flood is defined on the FFWC gauge: water level at Bahadurabad above the
danger level (19.5 m) plus 0.85 m for three consecutive days (2021 framework; the 2025 document
keeps DL + 0.85 m). This script:

- builds the observed daily water level from the repo's two files on the shared drive
  (`2020-06-07 Water level data Bahadurabad Upper danger level.xlsx`, 1987-2019, and
  `SW46.9L_19-11-2020.xls`, 2016-2020 at 3-hourly, averaged per day);
- takes observed events as the first day of each spell of >= 3 consecutive days at or above
  DL + 0.85 m, spells more than 7 days apart being separate events;
- takes model events as days above the RP5 discharge (the release's own table, and the quantile
  1 - 1/5 of annual maxima over the reanalysis), collapsed with a 7-day gap;
- matches within +-7 days (hits, misses, false alarms), only over the years both records cover;
- no annual-peak comparison: the 1987-2019 file holds only days above the danger level.

No published detection number is carried on the KB page for this station. The incumbent is
GloFAS v4 at Bahadurabad (the framework was calibrated on v3.1 and runs on v4), read from the
spoke's station-extracted yearly files on the shared drive (`incumbents.glofas_bgd_bahadurabad`)
and scored by the same event matching at the quantile 1 - 1/5 of its own annual maxima; its rows
carry release `glofas_v4` and are written with either GRRR release.

Usage:
    uv run scripts/rescore_bgd.py --release 2026
Writes outputs/rescore_bgd_<release>.csv.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import empirical_quantile_threshold, reanalysis, shipped_return_periods
from incumbents import glofas_bgd_bahadurabad
from rescore_npl import collapse_to_events, match_events

HYBAS = (
    "hybas_4121501030"  # largest river within 10 km of the Bahadurabad reporting point; to confirm
)
DANGER_LEVEL, OFFSET, RUN_DAYS = 19.5, 0.85, 3
WET = [6, 7, 8, 9]


def load_ffwc_bahadurabad() -> pd.Series:
    d = Path(os.environ["AA_DATA_DIR"]) / "private/exploration/bgd/ffwc"
    old = pd.read_excel(
        d / "2020-06-07 Water level data Bahadurabad Upper danger level.xlsx", sheet_name="Raw Data"
    )
    old = old.set_index(pd.to_datetime(old["Date"]).dt.normalize())["WL"].astype(float)
    new = pd.read_excel(d / "SW46.9L_19-11-2020.xls", sheet_name="Sheet 1")
    new = new.set_index(pd.to_datetime(new["DateTime"]).dt.normalize())["WL(m)"].astype(float)
    new = new.groupby(level=0).mean()
    s = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
    s = s[~s.index.duplicated()].dropna()
    if s.empty:
        raise ValueError("no FFWC readings loaded")
    return s.rename("wl")


def observed_events(wl: pd.Series) -> pd.DatetimeIndex:
    thr = DANGER_LEVEL + OFFSET
    full = wl.reindex(pd.date_range(wl.index.min(), wl.index.max()))
    above = (full >= thr).astype(int)
    run = above.groupby((above != above.shift()).cumsum()).cumsum()
    starts = run.index[(run == RUN_DAYS)] - pd.Timedelta(days=RUN_DAYS - 1)
    return collapse_to_events(pd.DatetimeIndex(starts))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--release", choices=["2023", "2026"], required=True)
    a = p.parse_args(argv)
    wl = load_ffwc_bahadurabad()
    refs = observed_events(wl)
    print(
        f"FFWC Bahadurabad: {wl.index.min().date()} to {wl.index.max().date()}, {len(wl)} days, {len(refs)} severe events: {[d.date().isoformat() for d in refs]}"
    )
    q = reanalysis(a.release, HYBAS)
    q = q[(q.index >= wl.index.min()) & (q.index <= wl.index.max())]
    am = q.groupby(q.index.year).max()
    thr = {
        "shipped": shipped_return_periods(a.release, HYBAS)[5.0],
        "quantile_full": empirical_quantile_threshold(am, 5),
    }
    rows = []
    for conv, t in thr.items():
        ev = collapse_to_events(q[q > t].index)
        m = match_events(ev, refs)
        rows.append(
            {
                "release": a.release,
                "block": "events",
                "rp_convention": conv,
                "rp": 5,
                "threshold_m3s": t,
                **m,
            }
        )
    # the incumbent: GloFAS v4 at Bahadurabad, same matching, quantile 1 - 1/5 of its annual maxima
    gl = glofas_bgd_bahadurabad()
    gl = gl[(gl.index >= wl.index.min()) & (gl.index <= wl.index.max())]
    t = empirical_quantile_threshold(gl.groupby(gl.index.year).max(), 5)
    refs_gl = refs[refs <= gl.index.max()]
    rows.append(
        {
            "release": "glofas_v4",
            "block": "events",
            "rp_convention": "quantile_full",
            "rp": 5,
            "threshold_m3s": t,
            **match_events(collapse_to_events(gl[gl > t].index), refs_gl),
            "note": f"GloFAS v4 ends {gl.index.max().date()}; {len(refs_gl)} of {len(refs)} observed events in range",
        }
    )
    # No annual-peak comparison: the 1987-2019 file holds only days above the danger level,
    # so it is not a continuous daily record and seasonal maxima cannot be formed from it.
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv(f"outputs/rescore_bgd_{a.release}.csv", index=False)
    pd.set_option("display.width", 250)
    print(df.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
