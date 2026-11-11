"""Mirror the GloFAS v4 consolidated reanalysis from EWDS into the team blob as one (cell, time) Zarr.

Why: EWDS serves the reanalysis one request at a time per account, caps a request at about one
year of days, and queues for hours, so every spoke that needs a GloFAS history re-fetches it
and most copies stop in 2022-2024. The cheapest EWDS shape is the whole globe for one year
(2.4 GB, ~10 min server time); 47 such requests cover 1979-2025 once, and this script turns them
into a store any point can be read from in one small fetch. Design and rejected layouts:
docs/decisions/0003-glofas-v4-mirror.md.

Layout, container `global` (dev stage):

    glofas/v4/reanalysis/bronze/glofas_v4_consolidated_<year>.nc   EWDS file as served (global, one year)
    glofas/v4/reanalysis/bronze/_jobs.json                         EWDS request ids per year (resume ledger)
    glofas/v4/reanalysis/q.zarr/_loaded/<year>.json                one marker per loaded year (the load ledger)
    glofas/v4/reanalysis/static/uparea_glofas_v4_0.nc              ECMWF auxiliary files as served
    glofas/v4/reanalysis/static/ldd_glofas_v4_0.nc
    glofas/v4/reanalysis/cells.parquet      one row per land cell: cell, row, col, lat, lon, uparea_km2, downstream_cell
    glofas/v4/reanalysis/q.zarr             zarr v3 group: q (cell, time) float32 m3/s; time; lat; lon; uparea_km2

Cells are every land cell of the GloFAS grid (6,221,926, where the upstream-area map is finite),
in row-major order of the 0.05 degree grid, so a latitude band is a contiguous cell range and the
yearly load writes each band once. `q` is sharded 4,096 cells x 1,826 days (five years) with inner
chunks of 64 cells x 1,826 days: one point's whole history is ten fetches of ~150 KB, and a new year
rewrites one shard column (~15 GB of blob traffic), never the store.

Time is stored exactly as EWDS stamps it: `valid_time` marks the END of the 24 h averaging window,
so a year's file runs 2 January to 1 January of the next year, and the value at T is the mean
discharge over [T-1d, T]. Three spokes shift this by -1 day in their copies (Somalia, Nepal, Chad);
Bangladesh keeps it. The convention is written into the array attributes.

Every invariant is enforced while loading and the result is recorded in the array attributes per
year: the discharge NaN mask equals the land mask on every day, the file's coordinates equal the
index coordinates, the days are consecutive and land inside the time axis. A violation raises
before anything of that year is written.

Commands (all state is in blob; nothing is written to local disk):

    uv run scripts/glofas_mirror.py static              # ECMWF auxiliary files -> blob; build cells.parquet
    uv run scripts/glofas_mirror.py init                # create the empty store (time 1979-01-02 .. 2026-01-01); no-op if present
    uv run scripts/glofas_mirror.py run 1979 ... 2025   # the pipeline: request, stream to bronze, load, mark; rerun to resume
    uv run scripts/glofas_mirror.py run 2000 --href URL # a result EWDS already holds (its cache link)
    uv run scripts/glofas_mirror.py status 1979 ... 2025
    uv run scripts/glofas_mirror.py fetch | load        # the two halves of `run`, for a rebuild from bronze

Three ledgers make `run` resumable at any step: bronze/_jobs.json (EWDS request id, time and attempt
count per year), the bronze file itself, and q.zarr/_loaded/<year>.json (the load record). A year
interrupted mid-load has no marker and is reloaded from bronze; the write is idempotent.

Azure Blob serves no suffix byte ranges, and adlfs passes them through, so the shards keep their
chunk index at the START (`index_location="start"`); with the zarr default (end) every partial
shard read from blob fails with "Required Content-Range response header is missing".

Needs DSCI_AZ_BLOB_DEV_SAS and DSCI_AZ_BLOB_DEV_SAS_WRITE (the single-node job policy injects both) and
CDSAPI_KEY or ~/.cdsapirc (fetch). Meant to run in Azure: from a laptop the uploads crawl (0.8 MB/s measured).
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import pathlib
import resource
import sys
import tempfile
import time

import netCDF4
import numpy as np
import pandas as pd
import requests
import zarr
from azure.storage.blob import BlobBlock, ContainerClient
from zarr.codecs import BloscCodec
from zarr.storage import FsspecStore

ACCOUNT = "imb0chd0dev"
CONTAINER = "global"
PREFIX = "glofas/v4/reanalysis"
STORE_PATH = f"{CONTAINER}/{PREFIX}/q.zarr"
EWDS_URL = "https://ewds.climate.copernicus.eu/api"
ECMWF_AUX = "https://confluence.ecmwf.int/download/attachments/242067380/"
AUX_FILES = ("uparea_glofas_v4_0.nc", "ldd_glofas_v4_0.nc")
EPOCH = pd.Timestamp("1979-01-01")
TIME_START, TIME_END = (
    pd.Timestamp("1979-01-02"),
    pd.Timestamp("2026-01-01"),
)  # EWDS stamps of 1979..2025
SHARD_CELLS, CHUNK_CELLS, CHUNK_DAYS = 4096, 64, 1826
BAND_ROWS = 231  # the EWDS netCDF chunk height; one band read = one row of its chunks
# PCRaster local drain direction codes -> (drow towards north, dcol towards east); 5 = pit/outlet
LDD = {1: (-1, -1), 2: (-1, 0), 3: (-1, 1), 4: (0, -1), 6: (0, 1), 7: (1, -1), 8: (1, 0), 9: (1, 1)}


# ---------------------------------------------------------------- blob helpers
def _container(write: bool = False):
    sas = os.environ.get("DSCI_AZ_BLOB_DEV_SAS_WRITE" if write else "DSCI_AZ_BLOB_DEV_SAS")
    if not sas:
        raise OSError(f"DSCI_AZ_BLOB_DEV_SAS{'_WRITE' if write else ''} is not set")
    return ContainerClient(
        f"https://{ACCOUNT}.blob.core.windows.net",
        CONTAINER,
        credential=sas,
        connection_timeout=300,
        read_timeout=600,
    )


def _blob_bytes(name: str) -> bytes:
    return (
        _container().get_blob_client(f"{PREFIX}/{name}").download_blob(max_concurrency=8).readall()
    )


def _blob_to_disk(name: str) -> pathlib.Path:
    """Download a blob to the node's local disk (Databricks: /local_disk0) and return the path."""
    base = pathlib.Path("/local_disk0/tmp") if pathlib.Path("/local_disk0").is_dir() else None
    if base is not None:
        base.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=pathlib.Path(name).suffix, dir=base)
    with os.fdopen(fd, "wb") as f:
        _container().get_blob_client(f"{PREFIX}/{name}").download_blob(max_concurrency=8).readinto(
            f
        )
    return pathlib.Path(path)


def _blob_exists(name: str) -> bool:
    return _container().get_blob_client(f"{PREFIX}/{name}").exists()


BLOCK = 32 * 2**20  # 32 MB blocks: a slow source never stalls an open Azure write


def _upload_stream(name: str, resp: requests.Response, length: int | None) -> int:
    """Stream an HTTP body into a block blob, one staged block per 32 MB read, so the Azure
    side only ever sees complete blocks (a single upload_blob from a slow stream timed out)."""
    bc = _container(write=True).get_blob_client(f"{PREFIX}/{name}")
    # an earlier aborted upload can leave uncommitted blocks with ids of another length, and the
    # service then rejects every new block (InvalidBlobOrBlock); an empty commit clears them
    bc.commit_block_list([])
    blocks, buf, n = [], bytearray(), 0
    for chunk in resp.iter_content(chunk_size=2**20):
        buf.extend(chunk)
        if len(buf) >= BLOCK:
            bid = f"{len(blocks):08d}"
            bc.stage_block(bid, bytes(buf), timeout=600)
            blocks.append(bid)
            n += len(buf)
            buf = bytearray()
    if buf:
        bid = f"{len(blocks):08d}"
        bc.stage_block(bid, bytes(buf), timeout=600)
        blocks.append(bid)
        n += len(buf)
    bc.commit_block_list([BlobBlock(b) for b in blocks])
    size = bc.get_blob_properties().size
    if size != n or (length and size != length):
        raise OSError(f"{name}: uploaded {size} bytes, read {n}, expected {length}")
    return size


def _store() -> FsspecStore:
    sas = os.environ.get("DSCI_AZ_BLOB_DEV_SAS_WRITE")
    if not sas:
        raise OSError(
            "DSCI_AZ_BLOB_DEV_SAS_WRITE is not set: the store is written with the write SAS"
        )
    return FsspecStore.from_url(
        f"abfs://{STORE_PATH}", storage_options={"account_name": ACCOUNT, "sas_token": sas}
    )


def read_store() -> FsspecStore:
    """Read-only handle on the store for consumers (uses the read SAS)."""
    sas = os.environ.get("DSCI_AZ_BLOB_DEV_SAS")
    if not sas:
        raise OSError("DSCI_AZ_BLOB_DEV_SAS is not set")
    return FsspecStore.from_url(
        f"abfs://{STORE_PATH}", storage_options={"account_name": ACCOUNT, "sas_token": sas}
    )


def _rss_gb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # bytes on macOS, kilobytes on Linux
    return rss / 1e9 if sys.platform == "darwin" else rss / 1e6


# ---------------------------------------------------------------- static: aux files + cell index
def _open_nc(buf: bytes) -> netCDF4.Dataset:
    return netCDF4.Dataset("in-memory", mode="r", memory=buf)


def cmd_static() -> None:
    for f in AUX_FILES:
        if _blob_exists(f"static/{f}"):
            print(f"static/{f} already in blob")
            continue
        with requests.get(ECMWF_AUX + f, stream=True, timeout=600) as r:
            r.raise_for_status()
            n = _upload_stream(f"static/{f}", r, int(r.headers.get("Content-Length", 0)) or None)
        print(f"static/{f}: {n / 1e6:.0f} MB to blob")
    up = _open_nc(_blob_bytes("static/uparea_glofas_v4_0.nc"))
    ld = _open_nc(_blob_bytes("static/ldd_glofas_v4_0.nc"))
    uv = next(v for v in up.variables if up[v].ndim == 2)
    lv = next(v for v in ld.variables if ld[v].ndim == 2)
    lat = np.asarray(up["lat"][:] if "lat" in up.variables else up["latitude"][:], dtype="float64")
    lon = np.asarray(up["lon"][:] if "lon" in up.variables else up["longitude"][:], dtype="float64")
    area = np.ma.filled(up[uv][:], np.nan).astype("float64")
    ldd = np.ma.filled(ld[lv][:], 0).astype("int16")
    if area.shape != (3000, 7200) or ldd.shape != area.shape:
        raise ValueError(f"unexpected grid shapes: uparea {area.shape}, ldd {ldd.shape}")
    land = np.isfinite(area)
    if not land[ldd > 0].all() or (ldd[land] == 0).any():
        raise ValueError("land mask differs between the upstream-area and drain-direction files")
    rows, cols = np.nonzero(land)  # row-major order
    n = len(rows)
    cell_of = np.full(area.shape, -1, dtype="int64")
    cell_of[rows, cols] = np.arange(n)
    north = -1 if lat[0] > lat[-1] else 1  # row step that moves north
    down = np.full(n, -1, dtype="int64")
    codes = ldd[rows, cols]
    for code, (dr, dc) in LDD.items():
        m = codes == code
        r2, c2 = rows[m] + dr * north, cols[m] + dc
        ok = (r2 >= 0) & (r2 < area.shape[0]) & (c2 >= 0) & (c2 < area.shape[1])
        d = np.full(m.sum(), -1, dtype="int64")
        d[ok] = cell_of[r2[ok], c2[ok]]
        down[m] = d
    if (down[codes == 5] != -1).any():
        raise AssertionError("pit cells must have no downstream cell")
    idx = pd.DataFrame(
        {
            "cell": np.arange(n, dtype="int64"),
            "row": rows.astype("int32"),
            "col": cols.astype("int32"),
            "lat": lat[rows],
            "lon": lon[cols],
            "uparea_km2": (area[rows, cols] / 1e6).astype("float32"),
            "downstream_cell": down,
            "ldd": codes,
        }
    )
    buf = io.BytesIO()
    idx.to_parquet(buf, index=False)
    _container(write=True).get_blob_client(f"{PREFIX}/cells.parquet").upload_blob(
        buf.getvalue(), overwrite=True
    )
    print(
        f"cells.parquet: {n:,} land cells; lat {lat[0]}..{lat[-1]} ({len(lat)}), lon {lon[0]}..{lon[-1]} ({len(lon)}); "
        f"downstream resolved for {(down >= 0).sum():,}, pits/outlets {(codes == 5).sum():,}"
    )


def load_index() -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(_blob_bytes("cells.parquet")))


# ---------------------------------------------------------------- init: the empty store
def cmd_init() -> None:
    idx = load_index()
    n = len(idx)
    times = pd.date_range(TIME_START, TIME_END, freq="D")
    store = _store()
    try:
        existing = zarr.open_group(store, mode="r")
        if existing["q"].shape == (n, len(times)):
            print(f"q.zarr already exists with q {existing['q'].shape}; nothing to do")
            return
        raise RuntimeError(
            f"q.zarr exists with a different shape {existing['q'].shape}; refusing to touch it"
        )
    except FileNotFoundError:
        pass
    root = zarr.open_group(store, mode="w-")  # refuses to overwrite an existing store
    comp = BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")
    q = root.create_array(
        "q",
        shape=(n, len(times)),
        shards={"shape": (SHARD_CELLS, CHUNK_DAYS), "index_location": "start"},
        chunks=(CHUNK_CELLS, CHUNK_DAYS),
        dtype="float32",
        fill_value=np.nan,
        compressors=comp,
        dimension_names=("cell", "time"),
    )
    q.attrs.update(
        {
            "long_name": "GloFAS v4 consolidated reanalysis, mean river discharge in the 24 h window ending at time",
            "units": "m3 s-1",
            "source": "EWDS cems-glofas-historical, system_version version_4_0, hydrological_model lisflood, product_type consolidated, timespan time_mean",
            "time_convention": "end of window: the value at T is the mean over [T-1d, T], as EWDS stamps it; a year's file runs 2 Jan to 1 Jan",
            "cell_order": "row-major over the 0.05 degree grid, land cells only (uparea finite); see cells.parquet",
            "years_loaded": {},
        }
    )
    root.create_array(
        "time", data=((times - EPOCH).days).values.astype("int32"), dimension_names=("time",)
    ).attrs.update({"units": "days since 1979-01-01", "calendar": "proleptic_gregorian"})
    root.create_array(
        "lat", data=idx.lat.values.astype("float64"), dimension_names=("cell",), chunks=(2**20,)
    )
    root.create_array(
        "lon", data=idx.lon.values.astype("float64"), dimension_names=("cell",), chunks=(2**20,)
    )
    root.create_array(
        "uparea_km2", data=idx.uparea_km2.values, dimension_names=("cell",), chunks=(2**20,)
    )
    print(
        f"q.zarr created: q {q.shape}, shards {q.shards}, chunks {q.chunks}, time {times[0].date()}..{times[-1].date()}"
    )


# ---------------------------------------------------------------- fetch: EWDS -> bronze
def _ewds_key() -> str:
    """The Copernicus key: CDSAPI_KEY in the environment (Databricks jobs), else ~/.cdsapirc."""
    if os.environ.get("CDSAPI_KEY"):
        return os.environ["CDSAPI_KEY"]
    rc = os.path.expanduser("~/.cdsapirc")
    if not os.path.exists(rc):
        raise FileNotFoundError(
            "neither CDSAPI_KEY nor ~/.cdsapirc: a Copernicus key is needed for EWDS"
        )
    return dict(line.strip().split(": ", 1) for line in open(rc) if ":" in line)["key"]


def _ewds_request(year: int) -> dict:
    return {
        "system_version": "version_4_0",
        "hydrological_model": "lisflood",
        "product_type": "consolidated",
        "variable": "average_river_discharge_in_the_last_24_hours",
        "timespan": "time_mean",
        "year": [str(year)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "data_format": "netcdf",
        "download_format": "unarchived",
    }  # no area: the whole globe; the request cost counts days, not area


def _jobs() -> dict:
    return json.loads(_blob_bytes("bronze/_jobs.json")) if _blob_exists("bronze/_jobs.json") else {}


def _save_jobs(j: dict) -> None:
    _container(write=True).get_blob_client(f"{PREFIX}/bronze/_jobs.json").upload_blob(
        json.dumps(j, indent=1), overwrite=True
    )


def _stream_to_bronze(year: int, href: str, attempts: int = 4) -> int:
    """EWDS drops long downloads now and then (2015 broke at 1.7 of 2.4 GB on 11 Nov 2026);
    a broken stream is restarted from scratch, the staged blocks of the failed try discarded."""
    for i in range(1, attempts + 1):
        try:
            with requests.get(href, stream=True, timeout=3600) as r:
                r.raise_for_status()
                return _upload_stream(
                    _bronze(year), r, int(r.headers.get("Content-Length", 0)) or None
                )
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError) as e:
            if i == attempts:
                raise OSError(f"{year}: download from EWDS broke {attempts} times") from e
            print(
                f"{year}: download broke on try {i} ({str(e)[:120]}); retrying in 60 s", flush=True
            )
            time.sleep(60)
    raise AssertionError("unreachable")


def _bronze(year: int) -> str:
    return f"bronze/glofas_v4_consolidated_{year}.nc"


def _in_bronze(year: int) -> bool:
    """A year counts as in bronze only with bytes behind it: clearing stale blocks before a
    staged upload leaves a zero-byte blob if the download then breaks before the commit."""
    bc = _container().get_blob_client(f"{PREFIX}/{_bronze(year)}")
    return bc.exists() and bc.get_blob_properties().size > 0


def _ledger_entry(jobs: dict, year: int) -> dict | None:
    """Ledger rows are {request_id, submitted, attempts}; rows written by the first version were bare ids."""
    e = jobs.get(str(year))
    if e is None:
        return None
    if isinstance(e, str):
        e = {"request_id": e, "submitted": None, "attempts": 1}
        jobs[str(year)] = e
    return e


def _submit(client, jobs: dict, year: int, why: str) -> dict:
    prev = _ledger_entry(jobs, year)
    rid = client.retrieve("cems-glofas-historical", _ewds_request(year)).request_id
    jobs[str(year)] = {
        "request_id": rid,
        "submitted": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "attempts": (prev["attempts"] + 1) if prev else 1,
    }
    _save_jobs(jobs)
    print(f"{year}: EWDS request {rid} ({why})", flush=True)
    return jobs[str(year)]


def cmd_run(
    years: list[int],
    poll_s: int = 60,
    href: str | None = None,
    do_load: bool = True,
    ewds_timeout_h: float = 6.0,
    allow_short_last: bool = False,
) -> None:
    """One pass per year, every step skipped when its ledger says it is done, so a stopped or
    frozen run is simply started again with the same years:

    1. loaded?   q.zarr/_loaded/<year>.json exists        -> nothing to do
    2. in bronze? bronze/glofas_v4_consolidated_<year>.nc  -> go to 4
    3. EWDS:     request id in bronze/_jobs.json; poll it; an id this key cannot see, a failed
                 job, or one older than --ewds-timeout-h is resubmitted (attempts counted);
                 on success the result is streamed straight into bronze
    4. load:     bronze -> q.zarr by latitude band, then the marker is written

    All years are requested up front, so EWDS works through its one-at-a-time queue while
    finished years are being loaded. --href streams a result link EWDS already holds (one year).
    """
    todo = [y for y in years if str(y) not in loaded_years()]
    for y in years:
        if y not in todo:
            print(f"{y}: already loaded, skipping")
    if href:
        if len(todo) != 1:
            raise ValueError("--href takes exactly one year that is not yet loaded")
        if _in_bronze(todo[0]):
            print(f"{todo[0]}: already in bronze")
        else:
            n = _stream_to_bronze(todo[0], href)
            print(f"{todo[0]}: {n / 1e9:.2f} GB streamed from the given link to bronze", flush=True)
        if do_load:
            cmd_load(todo, allow_short_last)
        return
    need = [y for y in todo if not _in_bronze(y)]
    for y in todo:
        if y not in need:
            print(f"{y}: already in bronze")
    pending: dict[int, dict] = {}
    if need:
        import cdsapi

        key = _ewds_key()
        H = {"PRIVATE-TOKEN": key}
        client = cdsapi.Client(url=EWDS_URL, key=key, wait_until_complete=False, quiet=True)
        jobs = _jobs()
        for y in need:
            e = _ledger_entry(jobs, y) or _submit(client, jobs, y, "new")
            pending[y] = e
        _save_jobs(jobs)
    while todo:
        progressed = False
        for y in list(todo):
            if y in pending:
                e = pending[y]
                r = requests.get(
                    f"{EWDS_URL}/retrieve/v1/jobs/{e['request_id']}", headers=H, timeout=60
                )
                if r.status_code in (403, 404):
                    pending[y] = _submit(client, jobs, y, "ledger id not visible to this key")
                    continue
                r.raise_for_status()
                j = r.json()
                st = j.get("status")
                age_h = (
                    (
                        dt.datetime.now(dt.UTC) - dt.datetime.fromisoformat(e["submitted"])
                    ).total_seconds()
                    / 3600
                    if e.get("submitted")
                    else 0.0
                )
                if st == "successful":
                    res = requests.get(
                        f"{EWDS_URL}/retrieve/v1/jobs/{e['request_id']}/results",
                        headers=H,
                        timeout=60,
                    ).json()
                    n = _stream_to_bronze(y, res["asset"]["value"]["href"])
                    print(
                        f"{y}: {n / 1e9:.2f} GB streamed to bronze at {dt.datetime.now(dt.UTC):%H:%MZ}",
                        flush=True,
                    )
                    del pending[y]
                    progressed = True
                elif st in ("failed", "dismissed", "rejected"):
                    if e["attempts"] >= 3:
                        raise RuntimeError(
                            f"{y}: EWDS job {e['request_id']} {st} after {e['attempts']} attempts: {str(j.get('metadata', ''))[:300]}"
                        )
                    pending[y] = _submit(client, jobs, y, f"previous job {st}")
                elif age_h > ewds_timeout_h:
                    if e["attempts"] >= 3:
                        raise RuntimeError(
                            f"{y}: EWDS job {e['request_id']} still {st} after {age_h:.1f} h and {e['attempts']} attempts"
                        )
                    pending[y] = _submit(client, jobs, y, f"job {st} for {age_h:.1f} h")
                else:
                    continue
            if y not in pending and _in_bronze(y):
                if do_load:
                    cmd_load([y], allow_short_last)
                todo.remove(y)
                progressed = True
        if todo and not progressed:
            print(
                f"{sorted(pending)} pending on EWDS at {dt.datetime.now(dt.UTC):%H:%MZ}", flush=True
            )
            time.sleep(poll_s)


def cmd_fetch(years: list[int], href: str | None, poll_s: int, then_load: bool = False) -> None:
    cmd_run(years, poll_s=poll_s, href=href, do_load=then_load)


def cmd_status(years: list[int]) -> None:
    """The registry: per year, the EWDS request, the bronze file and the load record."""
    jobs, loaded = _jobs(), loaded_years()
    cc = _container()
    sizes = {
        b.name.rsplit("/", 1)[1]: b.size
        for b in cc.list_blobs(name_starts_with=f"{PREFIX}/bronze/")
    }
    print(
        f"{'year':>5} {'ewds request':38} {'att':>3} {'bronze GB':>9} {'loaded at':20} {'days':>4} {'load s':>6} {'peak GB':>7}"
    )
    for y in years:
        e = _ledger_entry(jobs, y) or {}
        sz = sizes.get(f"glofas_v4_consolidated_{y}.nc")
        rec = loaded.get(str(y), {})
        print(
            f"{y:>5} {e.get('request_id', '-'):38} {e.get('attempts', 0):>3} "
            f"{(sz / 1e9) if sz else 0:>9.2f} {rec.get('loaded_at', '-'):20} {rec.get('days', '-')!s:>4} "
            f"{rec.get('seconds', '-')!s:>6} {rec.get('peak_rss_gb', '-')!s:>7}"
        )


# ---------------------------------------------------------------- load: bronze -> zarr
def loaded_years() -> dict:
    """The ledger of loaded years: one marker blob per year under q.zarr/_loaded/, written after the
    year's last band. One object per year, so concurrent loads of different years cannot overwrite
    each other's record; the array attribute `years_loaded` is derived from these."""
    cc = _container()
    out = {}
    for b in cc.list_blobs(name_starts_with=f"{PREFIX}/q.zarr/_loaded/"):
        y = b.name.rsplit("/", 1)[1].removesuffix(".json")
        out[y] = json.loads(cc.get_blob_client(b.name).download_blob().readall())
    return out


def _mark_loaded(year: int, rec: dict) -> None:
    _container(write=True).get_blob_client(f"{PREFIX}/q.zarr/_loaded/{year}.json").upload_blob(
        json.dumps(rec, indent=1), overwrite=True
    )


def cmd_load(years: list[int], allow_short_last: bool = False) -> None:
    idx = load_index()
    store = _store()
    root = zarr.open_group(store, mode="r+")
    q = root["q"]
    taxis = root["time"][:]
    t0_store = int(taxis[0])
    if not np.array_equal(taxis, np.arange(t0_store, t0_store + len(taxis))):
        raise AssertionError("store time axis is not consecutive days")
    land_rows = idx.row.values
    row_start = np.searchsorted(land_rows, np.arange(0, 3001))  # first cell of each grid row
    for y in years:
        t_wall = time.time()
        loaded = loaded_years()
        if str(y) in loaded:
            print(f"{y}: already loaded ({loaded[str(y)]['loaded_at']}), skipping")
            continue
        # from local disk, not memory: the 2.4 GB file held in RAM for the whole load was the
        # bulk of the 7.7 GB that hung the 14 GB driver on 11 Nov 2026 (run 586864369657320)
        nc_path = _blob_to_disk(f"bronze/glofas_v4_consolidated_{y}.nc")
        nc = netCDF4.Dataset(nc_path, mode="r")
        var = next(v for v in nc.variables if nc[v].ndim == 3)
        v = nc[var]
        tv = nc[v.dimensions[0]]
        times = pd.to_datetime(
            [
                t.isoformat()
                for t in netCDF4.num2date(tv[:], tv.units, only_use_cftime_datetimes=False)
            ]
        )
        days = (times - EPOCH).days.values
        if not np.array_equal(days, np.arange(days[0], days[0] + len(days))):
            raise AssertionError(f"{y}: file days are not consecutive")
        complete = times[-1] == pd.Timestamp(y + 1, 1, 1)
        # only the last year asked for may stop early: any other truncated file is still an error
        short_ok = allow_short_last and y == max(years) and times[-1] < pd.Timestamp(y + 1, 1, 1)
        if times[0] != pd.Timestamp(y, 1, 2) or not (complete or short_ok):
            raise AssertionError(
                f"{y}: expected stamps {y}-01-02 .. {y + 1}-01-01, got {times[0].date()} .. {times[-1].date()}"
                + (
                    ""
                    if allow_short_last
                    else "; the product may end here: --allow-short-last-year accepts a year that stops early"
                )
            )
        if not complete:
            print(
                f"{y}: file ends at {times[-1].date()}, {len(days)} days; accepted as the product's last year (incomplete, to be re-requested when the product extends)",
                flush=True,
            )
        t0 = int(days[0] - t0_store)
        if t0 < 0 or t0 + len(days) > len(taxis):
            raise AssertionError(f"{y}: days fall outside the store's time axis")
        flat = np.asarray(nc[v.dimensions[1]][:], dtype="float64")
        flon = np.asarray(nc[v.dimensions[2]][:], dtype="float64")
        if flat.shape != (3000,) or flon.shape != (7200,):
            raise AssertionError(f"{y}: file axes {flat.shape}, {flon.shape}")
        # every land cell's coordinates in the file must equal the index's (grid and orientation);
        # only 2,800 of the 3,000 latitude rows hold land, so the axes themselves are not compared
        if not (
            np.allclose(flat[idx.row.values], idx.lat.values, atol=1e-9)
            and np.allclose(flon[idx.col.values], idx.lon.values, atol=1e-9)
        ):
            raise AssertionError(
                f"{y}: file coordinates differ from the index coordinates at the land cells"
            )
        if v.shape[1:] != (3000, 7200):
            raise AssertionError(f"{y}: grid {v.shape[1:]}")
        v.set_auto_mask(False)
        nan_on_land = finite_off_land = 0
        for r0 in range(0, 3000, BAND_ROWS):
            r1 = min(r0 + BAND_ROWS, 3000)
            c0, c1 = int(row_start[r0]), int(row_start[r1])
            block = np.asarray(v[:, r0:r1, :], dtype="float32")  # (T, rows, 7200)
            fin = np.isfinite(block)
            band_land = np.zeros((r1 - r0, 7200), dtype=bool)
            band_land[idx.row.values[c0:c1] - r0, idx.col.values[c0:c1]] = True
            nan_on_land += int((~fin[:, band_land]).sum())
            finite_off_land += int(fin[:, ~band_land].sum())
            if nan_on_land or finite_off_land:
                raise AssertionError(
                    f"{y} rows {r0}-{r1}: discharge NaN mask differs from the land mask "
                    f"(NaN on land {nan_on_land}, finite off land {finite_off_land}); nothing written for this year"
                )
            if c1 > c0:
                # index the (rows, cols, T) view so the (cells, T) result is one copy, not two
                q[c0:c1, t0 : t0 + len(days)] = block.transpose(1, 2, 0)[band_land]
            print(
                f"  {y} rows {r0:4d}-{r1:4d}: cells {c0:,}-{c1:,} written; rss {_rss_gb():.1f} GB",
                flush=True,
            )
            del block, fin
        nc.close()
        nc_path.unlink()
        rec = {
            "days": len(days),
            "first": str(times[0].date()),
            "last": str(times[-1].date()),
            "complete": bool(complete),
            "nan_on_land": nan_on_land,
            "finite_off_land": finite_off_land,
            "coords_equal_index": True,
            "seconds": round(time.time() - t_wall),
            "peak_rss_gb": round(_rss_gb(), 2),
            "loaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        }
        _mark_loaded(y, rec)
        q.attrs["years_loaded"] = loaded_years()  # derived from the markers, never hand-merged
        print(f"{y}: loaded in {rec['seconds']} s, peak rss {rec['peak_rss_gb']} GB", flush=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("static")
    sub.add_parser("init")
    f = sub.add_parser("fetch")
    f.add_argument("years", type=int, nargs="+")
    f.add_argument("--href", help="stream an existing EWDS result link instead of requesting")
    f.add_argument("--poll", type=int, default=60, help="seconds between EWDS status polls")
    f.add_argument(
        "--then-load",
        action="store_true",
        help="load each year into the store once it is in bronze",
    )
    ld = sub.add_parser("load")
    ld.add_argument("years", type=int, nargs="+")
    r = sub.add_parser(
        "run", help="the one-pass pipeline: request, stream to bronze, load, mark; resumable"
    )
    r.add_argument("years", type=int, nargs="+")
    r.add_argument(
        "--href", help="stream a result link EWDS already holds (one year) instead of requesting"
    )
    r.add_argument("--poll", type=int, default=60)
    r.add_argument(
        "--ewds-timeout-h", type=float, default=6.0, help="resubmit a request older than this"
    )
    for sp in (ld, r):
        sp.add_argument(
            "--allow-short-last-year",
            action="store_true",
            help="accept a year whose file ends before the 1 Jan stamp (the product's last year); "
            "recorded as incomplete in its marker",
        )
    s = sub.add_parser("status", help="per year: EWDS request, bronze file, load record")
    s.add_argument("years", type=int, nargs="+")
    a = p.parse_args(argv)
    if a.cmd == "static":
        cmd_static()
    elif a.cmd == "init":
        cmd_init()
    elif a.cmd == "fetch":
        cmd_fetch(a.years, a.href, a.poll, a.then_load)
    elif a.cmd == "load":
        cmd_load(a.years, a.allow_short_last_year)
    elif a.cmd == "run":
        cmd_run(
            a.years,
            poll_s=a.poll,
            href=a.href,
            ewds_timeout_h=a.ewds_timeout_h,
            allow_short_last=a.allow_short_last_year,
        )
    elif a.cmd == "status":
        cmd_status(a.years)
    return 0


if __name__ == "__main__":
    # a plain return on success: Databricks runs the file in an IPython shell, where SystemExit(0) fails the task
    rc = main()
    if rc:
        sys.exit(rc)
