"""One loader for both public GRRR releases, so a re-score can run the same code on each.

- 2023: `model_id_8583a5c2_v0`, gauge-keyed `hybas_<id>`, reanalysis 1980-01-01 to 2023-12-23,
  return periods in `return_periods.zarr`.
- 2026: `distributed_model_2026_11`, basin-keyed `subhybas_<id>`, reanalysis 1980-12-31 to
  2025-12-30, return periods in `return_periods.parquet`.

The HydroBASINS number is the same in both, so one `hybas_<id>` addresses both releases.
Every function raises if the id is absent or the series has missing values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

ANON = {"token": "anon"}
BASES = {
    "2023": "gs://flood-forecasting/hydrologic_predictions/model_id_8583a5c2_v0/",
    "2026": "gs://flood-forecasting/hydrologic_predictions/distributed_model_2026_11/",
}
_stores: dict[tuple[str, str], xr.Dataset] = {}


def _open(release: str, name: str) -> xr.Dataset:
    key = (release, name)
    if key not in _stores:
        _stores[key] = xr.open_zarr(BASES[release] + name, chunks=None, storage_options=ANON)
    return _stores[key]


def gauge_key(release: str, hybas_id: str) -> str:
    if not hybas_id.startswith("hybas_"):
        raise ValueError(f"expected a hybas_ id, got {hybas_id}")
    return hybas_id if release == "2023" else "sub" + hybas_id


def reanalysis(release: str, hybas_id: str) -> pd.Series:
    """Daily reanalysis discharge as a Series indexed by day (left-labelled)."""
    ds = _open(release, "reanalysis/streamflow.zarr/")
    gid = gauge_key(release, hybas_id)
    if gid not in ds.gauge_id.values:
        raise KeyError(f"{gid} not in the {release} reanalysis")
    s = ds.streamflow.sel(gauge_id=gid).compute().to_series()
    s.index = pd.to_datetime(s.index).normalize()
    s.index.name = "date"
    if s.isna().any():
        raise ValueError(f"{gid}: {int(s.isna().sum())} NaN days in the {release} reanalysis")
    return s.rename("q")


def shipped_return_periods(release: str, hybas_id: str) -> dict[float, float]:
    """The return-period discharges each release ships, keyed by years."""
    gid = gauge_key(release, hybas_id)
    if release == "2026":
        rp = pd.read_parquet(BASES[release] + "return_periods.parquet", storage_options=ANON)
        if gid not in rp.index:
            raise KeyError(f"{gid} not in the 2026 return-period table")
        return {float(c): float(rp.loc[gid, c]) for c in rp.columns}
    ds = _open(release, "return_periods.zarr/")
    if gid not in ds.gauge_id.values:
        raise KeyError(f"{gid} not in the 2023 return_periods.zarr")
    sub = ds.sel(gauge_id=gid).compute()
    out = {}
    for name in sub.data_vars:
        val = float(np.asarray(sub[name].values).ravel()[0])
        yrs = "".join(ch for ch in str(name) if ch.isdigit() or ch == ".")
        if yrs:
            out[float(yrs)] = val
    if not out:
        raise ValueError(
            f"could not read return periods for {gid}: variables {list(sub.data_vars)}"
        )
    return out


def weibull_threshold(annual_max: np.ndarray, target_rp: float) -> float:
    """Discharge at `target_rp` by Weibull plotting position, log-log interpolation.

    Same estimator as ds-aa-som-floods `src/utils.weibull_threshold`. NaN when the target
    exceeds the record length (no extrapolation).
    """
    am = np.sort(np.asarray(annual_max, dtype=float))[::-1]
    n = len(am)
    rps = (n + 1) / np.arange(1, n + 1)
    if target_rp > rps[0]:
        return float("nan")
    lo = np.log(np.maximum(am[::-1], 1e-3))
    return float(np.exp(np.interp(np.log(target_rp), np.log(rps[::-1]), lo)))


def empirical_quantile_threshold(annual_max: pd.Series, rp: float) -> float:
    """ds-aa-npl-flooding notebook 02.0 convention: quantile 1 - 1/rp of the annual maxima."""
    return float(annual_max.quantile(1 - 1 / rp))
