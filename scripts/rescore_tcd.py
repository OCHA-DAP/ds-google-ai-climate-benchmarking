"""Chad: model annual peaks at N'Djamena against the DRE observed river level, same code on both releases.

Reproduces `pa-aa-tcd-flooding/exploration/dre_glofas.md` and the 2025 framework document's
annex ("Performance historique de la station GloFAS N'Djamena"): per year from 2003, the annual
peak of the observed level (DRE station TP, N'Djamena) and the annual peak of the model; years
2006, 2008, 2023 and 2024 dropped for incomplete observations; the 4-yr level on each side as the
quantile 1 - 1/4 of the annual peaks; years each side flags; false negatives (observed over its
4-yr level, model under its own) and false positives; Spearman of the peaks; and the mean number
of days the model peak comes before the observed peak.

The document reports, for the GloFAS reanalysis: false negatives 2019 and 2020, false positives
2003 and 2005, 18 years, model peak 31 days early on average. GloFAS v4 reanalysis from the repo's
processed blob is run through the same code as the published-reproduction column.

Observed data: dev blob `pa-aa-tcd-flooding/raw/dre/tp.xls` (DRE, Direction des ressources en
eau). GRRR basin: `hybas_1120734190`, the largest river within 10 km of the GloFAS cell, not yet
confirmed by a human (`outputs/stations_mapped.csv`).

Usage:
    uv run scripts/rescore_tcd.py --release 2026
Writes outputs/rescore_tcd_<release>.csv.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from grrr_releases import reanalysis

HYBAS = "hybas_1120734190"
MIN_YEAR = 2003
DROP_YEARS = [2006, 2008, 2023, 2024]
RP = 4


def load_dre_tp() -> pd.Series:
    raw = stratus.load_blob_data("pa-aa-tcd-flooding/raw/dre/tp.xls", stage="dev")
    df = pd.read_excel(io.BytesIO(raw), sheet_name="Sheet1", skiprows=1)
    df = df.iloc[:-1]
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    col = "Hauteur écoulement (cm REFERENTIEL HYDROM)"
    if col not in df.columns:
        raise KeyError(f"DRE file columns changed: {list(df.columns)}")
    s = df.set_index("Date")[col].replace(-999999, np.nan).dropna()
    s = s[~s.index.duplicated()].sort_index().astype(float)
    s = s[(s.index.year >= MIN_YEAR) & ~s.index.year.isin(DROP_YEARS)]
    return s.rename("level_cm")


def load_glofas_ndjamena() -> pd.Series:
    df = stratus.load_parquet_from_blob(
        "pa-aa-tcd-flooding/processed/glofas/glofas_reanalysis_ndjamena.parquet", stage="dev"
    )
    tcol = "time" if "time" in df.columns else "valid_time"
    s = df.set_index(pd.to_datetime(df[tcol]).dt.normalize())["dis24"].sort_index()
    return s[~s.index.duplicated()].rename("q")


def score(obs: pd.Series, model: pd.Series, label: str) -> dict:
    years = sorted(set(obs.index.year) & set(model.index.year))
    o = obs[obs.index.year.isin(years)]
    m = model[model.index.year.isin(years)]
    po = o.groupby(o.index.year).agg(["max", "idxmax"])
    pm = m.groupby(m.index.year).agg(["max", "idxmax"])
    j = po.join(pm, lsuffix="_obs", rsuffix="_mod").dropna()
    to, tm = j["max_obs"].quantile(1 - 1 / RP), j["max_mod"].quantile(1 - 1 / RP)
    oe, me = j["max_obs"] >= to, j["max_mod"] >= tm
    days_early = j["idxmax_obs"].dt.dayofyear - j["idxmax_mod"].dt.dayofyear
    return {
        "model": label,
        "n_years": len(j),
        "years": ",".join(str(y) for y in j.index),
        "obs_4yr_level_cm": to,
        "model_4yr_m3s": tm,
        "obs_years_over": ",".join(str(y) for y in j.index[oe]),
        "model_years_over": ",".join(str(y) for y in j.index[me]),
        "hits": int((oe & me).sum()),
        "false_negatives": ",".join(str(y) for y in j.index[oe & ~me]) or "none",
        "false_positives": ",".join(str(y) for y in j.index[~oe & me]) or "none",
        "peak_rho": float(stats.spearmanr(j["max_obs"], j["max_mod"])[0]),
        "mean_days_early": float(days_early.mean()),
        "median_days_early": float(days_early.median()),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--release", choices=["2023", "2026"], required=True)
    a = p.parse_args(argv)
    obs = load_dre_tp()
    print(
        f"DRE TP: {obs.index.min().date()} to {obs.index.max().date()}, {obs.index.year.nunique()} years kept"
    )
    rows = [score(obs, reanalysis(a.release, HYBAS), f"GRRR {a.release}")]
    rows.append(score(obs, load_glofas_ndjamena(), "GloFAS v4 reanalysis"))
    df = pd.DataFrame(rows)
    df.insert(0, "release", a.release)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv(f"outputs/rescore_tcd_{a.release}.csv", index=False)
    pd.set_option("display.width", 250)
    print(
        df[
            [
                "model",
                "n_years",
                "hits",
                "false_negatives",
                "false_positives",
                "peak_rho",
                "mean_days_early",
            ]
        ]
        .round(2)
        .to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
