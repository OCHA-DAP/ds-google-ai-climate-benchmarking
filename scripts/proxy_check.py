"""Is the reanalysis a proxy for the reforecast? Per trigger station, per lead 1 to 10.

The same check the Somalia mechanism (forecast-vs-own-reanalysis skill) and the Nigeria
Niger-Benue multistate script (`check_reforecast_skill.py`) ran on the 2023 bucket, on the
November 2026 release. Lead 0 is excluded: it equals the reanalysis by construction.

For each station and lead L in 1..10:

- pair every reforecast value issued at T with lead L (valid day T+L, right-labelled) with the
  reanalysis for the day [T+L-1d, T+L], i.e. reanalysis time T+L-1d;
- restrict to the station's wet-season months;
- **daily rho**: Spearman over all paired season days 2016-2025;
- **peak rho**: Spearman over the seasonal maxima, one per season (10 points), with a
  bootstrap 90% interval over seasons;
- **ratio**: median reforecast / reanalysis on days where the reanalysis is above the
  release's own 2-yr level (the days a trigger cares about); NaN if no such day.

Writes outputs/proxy_check.csv (one row per station and lead) and prints a summary at the
leads 3, 5, 7 and 10.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).parent))
from grrr_2026_11 import open_release

LEADS = range(1, 11)
SEASONS = range(2016, 2026)


def season_months(code: str) -> list[int]:
    return [int(c) if c.isdigit() else ord(c) - 55 for c in code]


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return np.nan
    return float(pd.Series(a).corr(pd.Series(b), method="spearman"))


def check_station(
    ra: xr.DataArray, rf: xr.DataArray, rp2: float, months: list[int], rng
) -> list[dict]:
    ra_s = ra.to_series()  # index: time (left-labelled day)
    rows = []
    for lead in LEADS:
        f = rf.sel(lead_time=np.timedelta64(lead, "D")).to_series()  # index: issue_time
        valid_end = f.index + pd.Timedelta(days=lead)
        ra_day = valid_end - pd.Timedelta(days=1)  # reanalysis label for the same daily window
        df = pd.DataFrame({"issue": f.index, "day": ra_day, "rf": f.values})
        df["ra"] = ra_s.reindex(df.day).values
        df = df.dropna()
        df = df[df.day.dt.month.isin(months)]
        df["season"] = df.day.dt.year
        d = df[df.season.isin(SEASONS)]
        if d.empty:
            raise ValueError(f"no paired days at lead {lead}")
        peaks = d.groupby("season").agg(ra=("ra", "max"), rf=("rf", "max"))
        boot = []
        for _ in range(500):
            idx = rng.integers(0, len(peaks), len(peaks))
            boot.append(spearman(peaks.ra.values[idx], peaks.rf.values[idx]))
        boot = np.array(boot)
        above = d[d.ra >= rp2]
        rows.append(
            {
                "lead": lead,
                "n_days": len(d),
                "daily_rho": spearman(d.ra.values, d.rf.values),
                "peak_rho": spearman(peaks.ra.values, peaks.rf.values),
                "peak_rho_p05": float(np.nanpercentile(boot, 5)),
                "peak_rho_p95": float(np.nanpercentile(boot, 95)),
                "n_seasons": len(peaks),
                "ratio_above_rp2": float((above.rf / above.ra).median()) if len(above) else np.nan,
                "n_days_above_rp2": len(above),
                "peak_ratio": float((peaks.rf / peaks.ra).median()),
            }
        )
    return rows


def main() -> int:
    st = pd.read_csv("outputs/stations_mapped.csv")
    reanalysis, reforecast, return_periods, _ = open_release()
    rng = np.random.default_rng(0)
    out = []
    cache: dict[str, tuple[xr.DataArray, xr.DataArray]] = {}  # one basin serves two seasons
    for s in st.itertuples():
        if s.subhybas not in cache:
            ra = reanalysis.streamflow.sel(gauge_id=s.subhybas).compute()
            rf = reforecast.streamflow.sel(gauge_id=s.subhybas).compute()
            if int(ra.isnull().sum()) or int(rf.isnull().sum()):
                raise ValueError(f"{s.station}: NaN in the stores")
            cache[s.subhybas] = (ra, rf)
        ra, rf = cache[s.subhybas]
        rp2 = float(return_periods.loc[s.subhybas, 2.0])
        rows = check_station(ra, rf, rp2, season_months(str(s.season_months)), rng)
        for r in rows:
            r.update(
                station=s.station,
                framework=s.framework,
                iso3=s.iso3,
                subhybas=s.subhybas,
                needs_check=s.needs_check,
            )
        out.extend(rows)
        r7 = next(r for r in rows if r["lead"] == 7)
        print(
            f"{s.station:28s} lead 7: daily rho {r7['daily_rho']:.3f}  peak rho {r7['peak_rho']:.2f} [{r7['peak_rho_p05']:.2f}, {r7['peak_rho_p95']:.2f}]  ratio>RP2 {r7['ratio_above_rp2']:.2f} (n={r7['n_days_above_rp2']})",
            flush=True,
        )
    df = pd.DataFrame(out)
    df.to_csv("outputs/proxy_check.csv", index=False)
    pd.set_option("display.width", 250)
    piv = (
        df[df.lead.isin([1, 3, 5, 7, 10])]
        .pivot(index="station", columns="lead", values="peak_rho")
        .round(2)
    )
    print("\nseasonal-peak Spearman by lead:\n", piv.to_string())
    piv = (
        df[df.lead.isin([1, 3, 5, 7, 10])]
        .pivot(index="station", columns="lead", values="ratio_above_rp2")
        .round(2)
    )
    print(
        "\nmedian reforecast/reanalysis on days above the 2-yr level, by lead:\n", piv.to_string()
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
