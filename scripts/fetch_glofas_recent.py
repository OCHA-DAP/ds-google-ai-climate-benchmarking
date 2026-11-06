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
on the EWDS side for hours, so all requests are submitted first and then polled together; the
request ids are kept in outputs/glofas_recent/jobs.json and a rerun resumes from them. Raw boxes
are kept under outputs/glofas_recent/ so a rerun only fetches what is missing. A request the
store rejects (a year or version it does not serve) is reported and left out, not retried.

Usage:
    uv run scripts/fetch_glofas_recent.py                 # all missing years to the current year
    uv run scripts/fetch_glofas_recent.py --years 2024 2025 --frameworks Somalia
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import cdsapi
import pandas as pd
import requests
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
    # the cell whose 2023 values equal the spoke's Chatara series to the decimal (the gauge itself
    # sits at about 26.95, 87.15; the GloFAS cell for it is one row south)
    "Nepal 2025 (Chatara)": ("version_4_0", 2024, {"Chatara": (26.825, 87.125)}),
    "Chad 2025": ("version_4_0", 2025, {"ndjamena": (12.125, 15.025)}),
    # the cell whose 2022 peak equals the spoke's Bahadurabad series; starts at 2022 because the
    # spoke copy keeps the end-of-window stamp, so its last day (31 Dec 2022) is followed by the
    # 1 Jan 2023 stamp that the store serves inside the 2022 request
    "Bangladesh 2025 (Bahadurabad)": ("version_4_0", 2022, {"Bahadurabad": (25.175, 89.675)}),
}
BOX = 0.15  # half-width of the request box in degrees

# EWDS stamps each daily mean at the end of its 24-hour window (a year runs 2 Jan to 1 Jan). The
# spokes' copies differ: Chad, Nepal and Somalia stamp it at the start of the day (1 Jan to
# 31 Dec), Bangladesh keeps the end-of-window stamp. Days shifted to each spoke's convention so
# the series join without a gap or a double day; established on overlap years the spokes already
# hold (outputs/glofas_recent/verify/, docs/rescore-2026-11.md), where the fetched cell equals the
# spoke copy to the decimal once shifted.
STAMP_SHIFT_DAYS = {
    "Somalia": -1,
    "Nepal 2025 (Chatara)": -1,
    "Chad 2025": -1,
    "Bangladesh 2025 (Bahadurabad)": 0,
}


JOBS = RAW / "jobs.json"


def _client() -> cdsapi.Client:
    rc = Path.home() / ".cdsapirc"
    if not rc.exists():
        raise FileNotFoundError("~/.cdsapirc missing: a Copernicus key is needed for EWDS")
    lines = dict(line.strip().split(": ", 1) for line in rc.read_text().splitlines() if ":" in line)
    return cdsapi.Client(url=EWDS_URL, key=lines["key"], wait_until_complete=False, quiet=True)


def query_for(version: str, year: int, lat: float, lon: float) -> dict:
    return {
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


def submit_all(client, wanted: list[tuple[str, str, str, int, float, float, Path]]) -> dict:
    """Submit every missing request; returns {target name: request id}, persisted to JOBS."""
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(JOBS.read_text()) if JOBS.exists() else {}
    for fw, st, version, year, lat, lon, target in wanted:
        if target.exists() or target.name in jobs:
            continue
        try:
            res = client.retrieve("cems-glofas-historical", query_for(version, year, lat, lon))
            jobs[target.name] = res.request_id
            print(f"submitted {fw} {st} {version} {year}: {res.request_id}", flush=True)
        except Exception as e:  # noqa: BLE001 - cdsapi raises a bare Exception on a 4xx
            print(
                f"{fw} {st} {version} {year}: REJECTED at submission: {type(e).__name__}: {str(e)[:200]}",
                file=sys.stderr,
                flush=True,
            )
            jobs[target.name] = f"rejected: {type(e).__name__}"
        JOBS.write_text(json.dumps(jobs, indent=1))
    return jobs


def _headers() -> dict:
    rc = Path.home() / ".cdsapirc"
    lines = dict(line.strip().split(": ", 1) for line in rc.read_text().splitlines() if ":" in line)
    return {"PRIVATE-TOKEN": lines["key"]}


def poll_and_download(jobs: dict, poll_s: int = 300) -> dict:
    """Poll the submitted requests on the EWDS jobs API until each is downloaded or failed."""
    outcome = {}
    pending = {}
    for n, rid in jobs.items():
        if rid.startswith("rejected"):
            outcome[n] = rid
        elif (RAW / n).exists():
            outcome[n] = "downloaded"
        else:
            pending[n] = rid
    while pending:
        for n, rid in list(pending.items()):
            r = requests.get(f"{EWDS_URL}/retrieve/v1/jobs/{rid}", headers=_headers(), timeout=60)
            if r.status_code != 200:
                print(f"{n}: status query {r.status_code}", file=sys.stderr, flush=True)
                continue
            status = r.json().get("status")
            if status == "successful":
                res = requests.get(
                    f"{EWDS_URL}/retrieve/v1/jobs/{rid}/results", headers=_headers(), timeout=60
                )
                res.raise_for_status()
                href = res.json()["asset"]["value"]["href"]
                with requests.get(href, stream=True, timeout=600) as dl:
                    dl.raise_for_status()
                    with open(RAW / n, "wb") as f:
                        f.writelines(dl.iter_content(1 << 20))
                outcome[n] = "downloaded"
                print(f"downloaded {n}", flush=True)
                del pending[n]
            elif status in ("failed", "dismissed", "rejected"):
                detail = str(r.json().get("metadata", {}))[:200]
                outcome[n] = f"{status}: {detail}"
                print(f"{n}: {outcome[n]}", file=sys.stderr, flush=True)
                del pending[n]
        if pending:
            print(f"{len(pending)} pending at {dt.datetime.now(dt.UTC):%H:%MZ}", flush=True)
            time.sleep(poll_s)
    return outcome


def cell_series(path: Path, lat: float, lon: float, shift_days: int) -> pd.Series:
    ds = xr.open_dataset(path)
    var = "dis24" if "dis24" in ds else next(iter(ds.data_vars))
    da = ds[var]
    tdim = "valid_time" if "valid_time" in da.dims else "time"
    s = da.sel(latitude=lat, longitude=lon, method="nearest").to_series()
    s.index = pd.to_datetime(s.index.get_level_values(tdim) if s.index.nlevels > 1 else s.index)
    s = s.dropna()
    if s.empty:
        raise ValueError(f"{path}: no values at the nearest cell to ({lat}, {lon})")
    if s.index.min().dayofyear != 2:
        raise ValueError(
            f"{path}: expected an end-of-window stamp starting 2 January, got {s.index.min().date()}"
        )
    s.index = s.index + pd.Timedelta(days=shift_days)  # see STAMP_SHIFT_DAYS
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
    wanted = []
    for fw in a.frameworks:
        version, first, stations = POINTS[fw]
        years = a.years or list(range(first, this_year + 1))
        for st, (lat, lon) in stations.items():
            for y in years:
                wanted.append(
                    (
                        fw,
                        st,
                        version,
                        y,
                        lat,
                        lon,
                        RAW / f"{fw.split()[0].lower()}_{st}_{version}_{y}.nc",
                    )
                )
    jobs = submit_all(client, wanted)
    outcome = poll_and_download(jobs)
    frames = []
    for fw, st, version, y, lat, lon, target in wanted:
        if outcome.get(target.name) != "downloaded":
            print(
                f"{fw} {st} {version} {y}: not fetched ({outcome.get(target.name)})",
                file=sys.stderr,
            )
            continue
        s = cell_series(target, lat, lon, STAMP_SHIFT_DAYS[fw])
        print(
            f"{fw} {st} {version} {y}: {s.index.min().date()} to {s.index.max().date()}, {len(s)} days"
        )
        frames.append(
            pd.DataFrame(
                {"framework": fw, "station": st, "version": version, "date": s.index, "q": s.values}
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
