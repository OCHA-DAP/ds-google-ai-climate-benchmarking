"""Extend each incumbent GloFAS series to the present from the Copernicus Early Warning Data Store.

The spokes' GloFAS reanalysis copies stop where their last download stopped (Somalia v5 and
Nepal v4 at 2023, Bangladesh v4 at 2022, Chad v4 at 2024), so the year ledger's incumbent
column is blank after that. This script fetches the consolidated reanalysis
(`cems-glofas-historical`) for the missing years at each incumbent's GloFAS cell, the same
version the framework runs on, and writes one tidy parquet that `incumbents.py` appends to the
spoke series:

    outputs/glofas_recent.parquet   columns: framework, station, version, date, q

Cells are the ones the spokes use: Somali stations from `ds-aa-som-floods` constants (v5),
Chatara from the Nepal spoke's GloFAS station list, N'Djamena from the Chad spoke constants,
Bahadurabad from the Bangladesh spoke config (v4). Each request is a small box around the cell
(0.3 degrees), one per station and year; the nearest grid cell is taken.

Needs a Copernicus key in ~/.cdsapirc (the EWDS endpoint accepts the CDS key). Requests queue
on the EWDS side; a year typically takes a few minutes. Raw boxes are kept under
outputs/glofas_recent/ so a rerun only fetches what is missing.

Usage:
    uv run scripts/fetch_glofas_recent.py                 # all missing years to the current year
    uv run scripts/fetch_glofas_recent.py --years 2024 2025 --frameworks Somalia
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import cdsapi
import pandas as pd
import xarray as xr

EWDS_URL = "https://ewds.climate.copernicus.eu/api"
RAW = Path("outputs/glofas_recent")
OUT = Path("outputs/glofas_recent.parquet")

# framework -> (version, first missing year, {station: (lat, lon)})
POINTS = {
    "Somalia": (
        "version_5_0",
        2024,
        {
            "belet_weyne": (4.725, 45.225),
            "bulo_burti": (3.825, 45.575),
            "jowhar": (2.775, 45.525),
            "luuq": (3.725, 42.525),
            "bardheere": (2.325, 42.225),
            "bualle": (1.225, 42.575),
            "dollow": (4.175, 42.075),
        },
    ),
    "Nepal 2025 (Chatara)": ("version_4_0", 2024, {"Chatara": (26.95, 87.15)}),
    "Chad 2025": ("version_4_0", 2025, {"ndjamena": (12.125, 15.025)}),
    "Bangladesh 2025 (Bahadurabad)": ("version_4_0", 2023, {"Bahadurabad": (25.15, 89.65)}),
}
BOX = 0.15  # half-width of the request box in degrees


def _client() -> cdsapi.Client:
    rc = Path.home() / ".cdsapirc"
    if not rc.exists():
        raise FileNotFoundError("~/.cdsapirc missing: a Copernicus key is needed for EWDS")
    lines = dict(line.strip().split(": ", 1) for line in rc.read_text().splitlines() if ":" in line)
    return cdsapi.Client(url=EWDS_URL, key=lines["key"], wait_until_complete=True, quiet=True)


def fetch_box(client, version: str, year: int, lat: float, lon: float, target: Path) -> Path:
    if target.exists():
        return target
    query = {
        "system_version": version,
        "hydrological_model": "lisflood",
        "product_type": "consolidated",
        "variable": "average_river_discharge_in_the_last_24_hours",
        "timespan": "time_mean",
        "year": str(year),
        "month": [f"{m:02d}" for m in range(1, 13)],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [lat + BOX, lon - BOX, lat - BOX, lon + BOX],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    client.retrieve("cems-glofas-historical", query, str(target))
    return target


def cell_series(path: Path, lat: float, lon: float) -> pd.Series:
    ds = xr.open_dataset(path)
    var = "dis24" if "dis24" in ds else next(iter(ds.data_vars))
    da = ds[var]
    tdim = "valid_time" if "valid_time" in da.dims else "time"
    s = da.sel(latitude=lat, longitude=lon, method="nearest").to_series()
    s.index = pd.to_datetime(s.index.get_level_values(tdim) if s.index.nlevels > 1 else s.index)
    s = s.dropna()
    if s.empty:
        raise ValueError(f"{path}: no values at the nearest cell to ({lat}, {lon})")
    return s.rename("q")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--years",
        type=int,
        nargs="*",
        help="years to fetch (default: each framework's missing years to now)",
    )
    p.add_argument("--frameworks", nargs="*", default=list(POINTS))
    a = p.parse_args(argv)
    client = _client()
    this_year = dt.date.today().year
    frames = []
    for fw in a.frameworks:
        version, first, stations = POINTS[fw]
        years = a.years or list(range(first, this_year + 1))
        for st, (lat, lon) in stations.items():
            for y in years:
                target = RAW / f"{fw.split()[0].lower()}_{st}_{version}_{y}.nc"
                try:
                    fetch_box(client, version, y, lat, lon, target)
                except Exception as e:  # the EWDS error says whether the year is not yet served
                    print(
                        f"{fw} {st} {version} {y}: FAILED: {type(e).__name__}: {str(e)[:200]}",
                        file=sys.stderr,
                    )
                    raise
                s = cell_series(target, lat, lon)
                print(
                    f"{fw} {st} {version} {y}: {s.index.min().date()} to {s.index.max().date()}, {len(s)} days"
                )
                frames.append(
                    pd.DataFrame(
                        {
                            "framework": fw,
                            "station": st,
                            "version": version,
                            "date": s.index,
                            "q": s.values,
                        }
                    )
                )
    if not frames:
        raise SystemExit("nothing fetched")
    new = pd.concat(frames, ignore_index=True)
    if OUT.exists():
        old = pd.read_parquet(OUT)
        key = ["framework", "station", "date"]
        old = old.merge(new[key].drop_duplicates(), on=key, how="left", indicator=True)
        old = old[old["_merge"] == "left_only"].drop(columns="_merge")
        new = pd.concat([old, new], ignore_index=True)
    new.sort_values(["framework", "station", "date"]).to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(new)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
