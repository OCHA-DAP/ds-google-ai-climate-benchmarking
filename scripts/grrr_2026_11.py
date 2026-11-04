"""Open Google's November 2026 GRRR release and fetch one basin.

GRRR = Google Runoff Reanalysis & Reforecast. The release is public (CC-BY-4.0) and read
anonymously from a Google Cloud Storage bucket. Three stores and one table:

- reanalysis/streamflow.zarr     (gauge_id, time)                  daily, 1980-12-31 to 2025-12-30
- reforecast/streamflow.zarr     (gauge_id, issue_time, lead_time) issues 2016-01-01 to 2025-12-31, leads 0..10 d
- return_periods.parquet         one row per gauge_id, columns 1.01, 2, 5, 10, 20, 25, 50, 100 (years)
- subhybas_outlet_locations_UNOFFICIAL.zarr  (gauge_id) lat, lon of each basin outlet

`gauge_id` is a HydroBasins sub-basin, "subhybas_<hybas id>", not a Flood Hub gauge. The
value is the discharge at the sub-basin outlet, draining everything upstream.

Labelling, from Google's reading notebook: reanalysis time T covers [T, T+1d] ("left
labelled"); reforecast lead L at issue T covers [T+L-1d, T+L] ("right labelled"). Hence
    Reanalysis[time=T] == Reforecast[issue_time=T+1d, lead_time=0]
which `verify_identity` checks exactly. Lead 0 is therefore not a forecast at all.

Usage:
    uv run scripts/grrr_2026_11.py subhybas_1121902040
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
import xarray as xr

RELEASE = "distributed_model_2026_11"
BASE = f"gs://flood-forecasting/hydrologic_predictions/{RELEASE}/"
REANALYSIS = BASE + "reanalysis/streamflow.zarr/"
REFORECAST = BASE + "reforecast/streamflow.zarr/"
RETURN_PERIODS = BASE + "return_periods.parquet"
OUTLETS = BASE + "subhybas_outlet_locations_UNOFFICIAL.zarr/"

ANON = {"token": "anon"}


def open_store(path: str) -> xr.Dataset:
    """Open one zarr store lazily. Chunks are 128 basins wide; reading one basin reads its chunk."""
    return xr.open_zarr(path, chunks=None, storage_options=ANON)


def open_release() -> tuple[xr.Dataset, xr.Dataset, pd.DataFrame, xr.Dataset]:
    reanalysis = open_store(REANALYSIS)
    reforecast = open_store(REFORECAST)
    return_periods = pd.read_parquet(RETURN_PERIODS, storage_options=ANON)
    outlets = open_store(OUTLETS)
    if not np.array_equal(reanalysis.gauge_id.values, reforecast.gauge_id.values):
        raise RuntimeError("reanalysis and reforecast stores list different gauge_ids")
    return reanalysis, reforecast, return_periods, outlets


def fetch_basin(gauge_id: str) -> dict:
    """Return the reanalysis series, reforecast array, return periods and outlet for one basin."""
    reanalysis, reforecast, return_periods, outlets = open_release()
    if gauge_id not in return_periods.index:
        raise KeyError(
            f"{gauge_id} is not in the {RELEASE} release (970,005 basins have predictions)"
        )
    out = {
        "reanalysis": reanalysis.streamflow.sel(gauge_id=gauge_id).compute(),
        "reforecast": reforecast.streamflow.sel(gauge_id=gauge_id).compute(),
        "return_periods": return_periods.loc[gauge_id],
    }
    if gauge_id in outlets.gauge_id.values:
        o = outlets.sel(gauge_id=gauge_id).compute()
        out["outlet"] = (float(o.latitude), float(o.longitude))
    else:
        out["outlet"] = None  # the outlet file is unofficial and does not cover every basin
    return out


def verify_identity(reanalysis: xr.DataArray, reforecast: xr.DataArray) -> int:
    """Check Reanalysis[T] == Reforecast[T+1d, lead 0] on every issue day. Returns the count checked."""
    issues = reforecast.issue_time.values
    valid = issues - np.timedelta64(1, "D")
    ra = reanalysis.sel(time=valid).values
    rf = reforecast.sel(lead_time=np.timedelta64(0, "D")).values
    mismatch = ~np.isclose(ra, rf, rtol=0, atol=0, equal_nan=True)
    if mismatch.any():
        i = int(np.argmax(mismatch))
        raise AssertionError(
            f"lead-0 identity fails on {mismatch.sum()} of {len(ra)} days; first at issue "
            f"{issues[i]}: reanalysis {ra[i]} vs reforecast {rf[i]}"
        )
    return len(ra)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("gauge_id", help="HydroBasins id, e.g. subhybas_1121902040")
    a = p.parse_args(argv)

    b = fetch_basin(a.gauge_id)
    ra, rf = b["reanalysis"], b["reforecast"]
    print(f"release   {RELEASE}")
    print(f"basin     {a.gauge_id}  outlet {b['outlet']}")
    print(f"reanalysis {ra.sizes}  {str(ra.time.values[0])[:10]} to {str(ra.time.values[-1])[:10]}")
    print(
        f"reforecast {rf.sizes}  issues {str(rf.issue_time.values[0])[:10]} to {str(rf.issue_time.values[-1])[:10]}"
    )
    print(f"NaN        reanalysis {int(ra.isnull().sum())}, reforecast {int(rf.isnull().sum())}")
    print("return periods (m3/s):")
    print(b["return_periods"].round(2).to_string())
    n = verify_identity(ra, rf)
    print(
        f"identity   Reanalysis[T] == Reforecast[T+1d, lead 0] holds exactly on all {n} issue days"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
