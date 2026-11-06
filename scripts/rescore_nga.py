"""Nigeria: GRRR reanalysis against GRDC observed discharge, same code on both releases.

Reproduces `ds-aa-nga-flooding` notebook `exploration/2026/08_grdc_gauge_compare.ipynb`
(branch feat/niger-benue-multistate-monitoring) and re-runs it on the November 2026 release:

- GRDC daily discharge from blob (`ds-aa-nga-flooding/raw/grdc/GRDC-Daily.nc`), -999 masked;
- daily Spearman over the overlapping days;
- wet-season (Jul-Nov) annual maxima, years kept only with >= 120 wet-season observations and
  no gap > 14 days in Aug-Oct; stations kept with >= 15 valid years;
- empirical 3-yr and 5-yr thresholds on each side (quantile 1 - 1/RP of the annual maxima);
  years each side flags; hits, misses, false alarms, F1; annual-peak Spearman.

The notebook's GRDC-to-gauge mapping is carried as is, including both candidates where it
marks one as uncertain (Lokoja, Wuroboki) and Onitsha, which it marks "not qa".

Usage:
    uv run scripts/rescore_nga.py --release 2026
Writes outputs/rescore_nga_<release>.csv.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import ocha_stratus as stratus
import pandas as pd
import xarray as xr
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import reanalysis

MAPPING = [  # (grdc_id, station, hybas id, note)
    (1835020, "Makurdi", "hybas_1120911340", ""),
    (1835025, "Umaisha", "hybas_1120904190", ""),
    (1834101, "Lokoja", "hybas_1120908000", "notebook's first choice"),
    (1834101, "Lokoja", "hybas_1120909890", "notebook's alternative"),
    (1834010, "Kende", "hybas_1120750570", ""),
    (1834110, "Yidere Bode", "hybas_1120755820", ""),
    (1835010, "Wuroboki", "hybas_1121971560", "notebook's first choice"),
    (1835010, "Wuroboki", "hybas_1120842550", "notebook's alternative; the 2025 trigger gauge"),
    (1835900, "Ibi", "hybas_1120887720", ""),
    (1834015, "Baro", "hybas_1120870480", ""),
    (1834020, "Onitsha", "hybas_1120975380", "not QA'd in the notebook"),
]
WET = [7, 8, 9, 10, 11]
PEAK = [8, 9, 10]
MIN_WET_OBS, MAX_GAP, MIN_YEARS = 120, 14, 15
RPS = [3, 5]


def load_grdc() -> pd.DataFrame:
    cc = stratus.get_container_client("projects", stage="dev")
    raw = cc.get_blob_client("ds-aa-nga-flooding/raw/grdc/GRDC-Daily.nc").download_blob().readall()
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
        tmp.write(raw)
    ds = xr.open_dataset(tmp.name)
    df = (
        ds["runoff_mean"]
        .to_dataframe()
        .reset_index()
        .rename(columns={"time": "date", "id": "grdc_id", "runoff_mean": "obs"})
    )
    df["obs"] = df["obs"].where(df["obs"] > -900)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.dropna()


def valid_wet_years(obs: pd.Series) -> list[int]:
    out = []
    w = obs[obs.index.month.isin(WET)]
    for y, g in w.groupby(w.index.year):
        if len(g) < MIN_WET_OBS:
            continue
        pk = g[g.index.month.isin(PEAK)]
        if pk.empty:
            continue
        days = pd.date_range(pk.index.min(), pk.index.max())
        present = pd.Series(False, index=days)
        present[pk.index] = True
        runs = (~present).astype(int).groupby(present.cumsum()).sum()
        if runs.max() > MAX_GAP:
            continue
        out.append(int(y))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--release", choices=["2023", "2026"], required=True)
    a = p.parse_args(argv)
    grdc = load_grdc()
    rows = []
    for gid, station, hid, note in MAPPING:
        obs = grdc[grdc.grdc_id == gid].set_index("date")["obs"].sort_index()
        if obs.empty:
            raise KeyError(f"GRDC {gid} ({station}) has no data in GRDC-Daily.nc")
        q = reanalysis(a.release, hid)
        j = pd.concat([obs, q], axis=1, join="inner").dropna()
        daily_rho = float(stats.spearmanr(j["obs"], j["q"])[0]) if len(j) > 30 else float("nan")
        years = valid_wet_years(obs)
        years = [y for y in years if y in set(q.index.year)]
        row = {
            "release": a.release,
            "grdc_id": gid,
            "station": station,
            "hybas": hid,
            "note": note,
            "n_days_overlap": len(j),
            "daily_rho": daily_rho,
            "n_valid_years": len(years),
        }
        if len(years) < MIN_YEARS:
            row["excluded"] = f"only {len(years)} valid wet-season years"
            rows.append(row)
            continue
        ow = obs[obs.index.month.isin(WET)]
        qw = q[q.index.month.isin(WET)]
        ann = pd.DataFrame(
            {"obs_max": ow.groupby(ow.index.year).max(), "q_max": qw.groupby(qw.index.year).max()}
        ).loc[years]
        # a release that starts on 31 Dec leaves its first year without a wet season: drop it
        ann = ann.dropna()
        years = [int(y) for y in ann.index]
        row["n_valid_years"] = len(years)
        row["peak_rho"] = float(stats.spearmanr(ann.obs_max, ann.q_max)[0])
        for rp in RPS:
            to, tq = ann.obs_max.quantile(1 - 1 / rp), ann.q_max.quantile(1 - 1 / rp)
            oe, qe = ann.obs_max >= to, ann.q_max >= tq
            tp, fp, fn = int((oe & qe).sum()), int((~oe & qe).sum()), int((oe & ~qe).sum())
            row[f"obs_years_{rp}yr"] = ",".join(str(y) for y in ann.index[oe])
            row[f"model_years_{rp}yr"] = ",".join(str(y) for y in ann.index[qe])
            row[f"hits_{rp}yr"], row[f"false_alarms_{rp}yr"], row[f"misses_{rp}yr"] = tp, fp, fn
            row[f"f1_{rp}yr"] = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else float("nan")
        rows.append(row)
        print(
            f"{station:12s} {hid}  overlap {len(j)} d  daily rho {daily_rho:.3f}  years {len(years)}  peak rho {row['peak_rho']:.2f}  F1 3yr {row['f1_3yr']:.2f}  5yr {row['f1_5yr']:.2f}",
            flush=True,
        )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv(f"outputs/rescore_nga_{a.release}.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
