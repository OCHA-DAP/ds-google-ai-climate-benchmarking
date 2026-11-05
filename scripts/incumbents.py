"""The model each framework actually ran on (the incumbent), as daily reanalysis series.

The benchmark's headline comparison is incumbent vs GRRR November 2026. GRRR 2023 (the Flood
Hub bucket) is the incumbent for Nigeria 2026 and one leg of the Somalia proposal; every other
flood framework in the portfolio ran on GloFAS, and Niger on the ABN gauge alone. Sources, all
read from the team's own copies (frameworks/ pages in the KB give the trigger detail):

- Bangladesh 2025: GloFAS v4 reanalysis at Bahadurabad, the spoke's station-extracted per-year
  files on the shared drive (`public/processed/bgd/glofas/bgd_cems-glofas-historical_v4_<year>_*
  _processed.nc`, 1979-2022). The framework was calibrated on v3.1 and runs on v4; a v3 file
  (`bgd_cems-glofas-historical_v3.nc`) is also there and not used here.
- Nepal 2025: GloFAS v4 reanalysis at Chatara / Chisapani
  (`public/processed/npl/glofas/npl_cems-glofas-historical_v4.nc`, 1979-2023).
- Chad 2025: GloFAS v4 reanalysis at N'Djamena, dev blob
  `pa-aa-tcd-flooding/processed/glofas/glofas_reanalysis_ndjamena.parquet` (1979-2024).
- Somalia: GloFAS v5 reanalysis per SWALIM station, dev blob
  `ds-aa-som-floods/processed/discharge_daily_glofas_v5.parquet` (1999-2023).

Every loader raises when the file, variable or station is missing; none returns a partial series.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import ocha_stratus as stratus
import pandas as pd
import xarray as xr

# framework -> label used in tables and figures for the incumbent column
INCUMBENT = {
    "Nigeria 2026": "GRRR 2023",
    "Somalia": "GloFAS v5",
    "Nepal 2025 (Chatara)": "GloFAS v4",
    "Chad 2025": "GloFAS v4",
    "Bangladesh 2025 (Bahadurabad)": "GloFAS v4",
    "Niger 2025": "ABN gauge",
}

# what the framework's own trigger ran on, for the year-by-year panels
TRIGGER_SOURCE = {
    "Nigeria 2026": "Trigger: GRRR 2023 bucket, 10 Benue gauges, 6 of 10 over 4-yr levels; GloFAS readiness. Backtest years: framework doc.",
    "Somalia": "Proposed trigger: GloFAS v5 + GRRR 2023 + GEOGloWS vote at SWALIM gauges. Backtest years: spoke analysis.",
    "Nepal 2025 (Chatara)": "Trigger: GloFAS 7-day readiness at Chatara, RP5 at 50%; DHM bulletin action. No backtest years published; DHM record to 2012.",
    "Chad 2025": "Trigger: GloFAS v4 ensemble mean at N'Djamena, 4,542 m³/s (~RP4). Backtest years: framework doc annex.",
    "Bangladesh 2025 (Bahadurabad)": "Trigger: GloFAS v3.1-calibrated, run on v4, with FFWC danger level + 0.85 m for 3 days (the gauge column's rule). No backtest years published.",
    "Niger 2025": "Trigger: ABN gauge at Niamey, 604 cm, no model. Backtest years: framework doc.",
}


def _root() -> Path:
    return Path(os.environ["AA_DATA_DIR"])


def glofas_bgd_bahadurabad() -> pd.Series:
    files = sorted(
        glob.glob(
            str(
                _root()
                / "public/processed/bgd/glofas/bgd_cems-glofas-historical_v4_[0-9]*_processed.nc"
            )
        )
    )
    if len(files) < 40:
        raise FileNotFoundError(
            f"expected ~44 yearly GloFAS v4 files for Bangladesh, found {len(files)}"
        )
    parts = []
    for f in files:
        ds = xr.open_dataset(f)
        if "Bahadurabad" not in ds.data_vars:
            raise KeyError(f"{f}: no Bahadurabad variable")
        parts.append(ds["Bahadurabad"].to_series())
    s = pd.concat(parts).sort_index()
    s.index = pd.to_datetime(s.index).normalize()
    if s.index.duplicated().any() or s.isna().any():
        raise ValueError("Bangladesh GloFAS v4: duplicated days or NaN in the concatenated series")
    return s.rename("q")


def glofas_npl(station: str) -> pd.Series:
    ds = xr.open_dataset(_root() / "public/processed/npl/glofas/npl_cems-glofas-historical_v4.nc")
    if station not in ds.data_vars:
        raise KeyError(f"Nepal GloFAS v4 file has {list(ds.data_vars)}, not {station}")
    s = ds[station].to_series().dropna()
    s.index = pd.to_datetime(s.index).normalize()
    return s[~s.index.duplicated()].sort_index().rename("q")


def glofas_tcd_ndjamena() -> pd.Series:
    df = stratus.load_parquet_from_blob(
        "pa-aa-tcd-flooding/processed/glofas/glofas_reanalysis_ndjamena.parquet", stage="dev"
    )
    tcol = "time" if "time" in df.columns else "valid_time"
    s = df.set_index(pd.to_datetime(df[tcol]).dt.normalize())["dis24"].sort_index()
    return s[~s.index.duplicated()].rename("q")


def glofas_som(station: str) -> pd.Series:
    df = stratus.load_parquet_from_blob(
        "ds-aa-som-floods/processed/discharge_daily_glofas_v5.parquet", stage="dev"
    )
    sub = df[df.station == station]
    if sub.empty:
        raise KeyError(f"Somalia GloFAS v5 parquet has no station {station!r}")
    s = sub.set_index(pd.to_datetime(sub["date"]).dt.normalize())["discharge"].sort_index()
    return s[~s.index.duplicated()].dropna().rename("q")
