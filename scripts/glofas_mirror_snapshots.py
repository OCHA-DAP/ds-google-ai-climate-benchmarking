"""Small snapshots of the GloFAS v4 mirror, read straight from the Zarr on blob, for the page's
"what the store looks like" views: one basin's cells on two days (a map, the costly read), full
point histories at three stations (the cheap read), one cell as a year x day grid, the
numbers the anatomy diagram is drawn from, and the river network by upstream-area threshold
(a coarse global grid, the exact cell count per threshold, and the box cells draining to one
framework point), from the index alone. Writes outputs/glofas_mirror/snapshots.json.

Only dates inside years with a load marker are read; a requested map date in a year without a
marker is an error, never a blank map.

    uv run scripts/glofas_mirror_snapshots.py [--dates 2023-09-01 2023-11-20]
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import zarr

sys.path.insert(0, str(Path(__file__).parent))
import glofas_mirror as gm
from fetch_glofas_recent import POINTS

OUT = Path("outputs/glofas_mirror")
STATIONS = [  # label, framework key in POINTS, station key
    ("Chatara (Koshi)", "Nepal 2025 (Chatara)", "Chatara"),
    ("N'Djamena (Chari)", "Chad 2025", "ndjamena"),
    ("Bahadurabad (Jamuna)", "Bangladesh 2025 (Bahadurabad)", "Bahadurabad"),
]
HEATMAP_STATION = "Bahadurabad (Jamuna)"
MAP = {  # the Somalia framework's basins: Juba and Shabelle from the Ethiopian highlands to the sea
    "name": "Juba and Shabelle basins (Somalia framework)",
    "lat": (-2.0, 10.0),
    "lon": (40.0, 49.0),
    "framework": "Somalia",
    "traces": ["belet_weyne", "luuq"],  # drawn downstream to the outlet, cell by cell
    "catchment": "belet_weyne",  # the box cells whose downstream chain reaches this point
}
THRESHOLDS = [0, 100, 500, 1000, 5000, 10000, 50000]  # km² upstream; 0 is every land cell
COARSE = 5  # 0.05° cells per side of a coarse cell in the global network panel (0.25°)
LOG_LO, LOG_PER = 1.0, 36.0  # uint8 encoding of log10 upstream area: (log10 - 1) * 36


def network(idx: pd.DataFrame) -> dict:
    """The river network by threshold: exact counts, and a coarse global grid holding each
    coarse cell's largest upstream area, encoded to one byte (0 is no land)."""
    up = idx.uparea_km2.values
    if not np.all(np.isfinite(up)) or up.min() <= 0:
        raise ValueError("upstream area must be finite and positive on every land cell")
    counts = {str(t): int((up >= t).sum()) for t in THRESHOLDS}
    nr, nc = int(idx.row.max()) // COARSE + 1, int(idx.col.max()) // COARSE + 1
    g = np.zeros((nr, nc), dtype=np.float64)
    np.maximum.at(g, (idx.row.values // COARSE, idx.col.values // COARSE), up)
    enc = np.zeros(g.shape, dtype=np.uint8)
    land = g > 0
    enc[land] = np.clip(np.round((np.log10(g[land]) - LOG_LO) * LOG_PER), 1, 255)
    return {
        "thresholds": THRESHOLDS,
        "counts": counts,
        "coarse_deg": COARSE * 0.05,
        "rows": nr,
        "cols": nc,
        "lat0": float(idx.lat.max()) + 0.025,
        "lon0": float(idx.lon.min()) - 0.025,
        "log_lo": LOG_LO,
        "log_per": LOG_PER,
        "max_log10_uparea_u8": base64.b64encode(enc.tobytes()).decode(),
    }


def catchment_in_box(idx: pd.DataFrame, cells: np.ndarray, target: int) -> list[int]:
    """Cells among `cells` whose downstream chain reaches `target`, following the index's
    downstream_cell links (the chain stops at the sea, -1)."""
    down = idx.downstream_cell.values
    reaches: dict[int, bool] = {target: True}
    out = []
    for c0 in cells:
        c, path = int(c0), []
        while c not in reaches:
            path.append(c)
            c = int(down[c])
            if c < 0:
                reaches[c] = False
                break
        hit = reaches[c]
        for p_ in path:
            reaches[p_] = hit
        if hit:
            out.append(int(c0))
    return out


def sig(x: float, n: int = 3) -> float | None:
    if not np.isfinite(x):
        return None
    if x == 0:
        return 0.0
    return round(float(x), -math.floor(math.log10(abs(x))) + n - 1)


def year_of_stamp(d: pd.Timestamp) -> int:
    """EWDS stamps a year 2 Jan .. 1 Jan: a 1 Jan stamp belongs to the year before."""
    return d.year - 1 if (d.month == 1 and d.day == 1) else d.year


def find_cell(idx: pd.DataFrame, lat: float, lon: float) -> pd.Series:
    hit = idx[(np.abs(idx.lat - lat) < 1e-6) & (np.abs(idx.lon - lon) < 1e-6)]
    if len(hit) != 1:
        raise LookupError(f"{len(hit)} index rows at ({lat}, {lon})")
    return hit.iloc[0]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dates", nargs=2, default=["2023-09-01", "2023-11-20"], help="map days")
    a = p.parse_args(argv)

    root = zarr.open_group(gm.read_store(), mode="r")
    q = root["q"]
    dates = gm.EPOCH + pd.to_timedelta(root["time"][:], unit="D")
    loaded = gm.loaded_years()
    years_loaded = sorted(int(y) for y in loaded)
    idx = gm.load_index()
    stamp_year = np.array([year_of_stamp(d) for d in dates])
    out_network = network(idx)
    print(
        "network: " + ", ".join(f"≥{t:,} km² {out_network['counts'][str(t)]:,}" for t in THRESHOLDS)
    )
    in_loaded = np.isin(stamp_year, years_loaded)
    print(f"store {q.shape}, {len(years_loaded)} years loaded, {in_loaded.sum():,} days readable")

    out: dict = {
        "made_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "years_loaded": years_loaded,
        "years_missing": sorted(set(range(dates[0].year, dates[-1].year)) - set(years_loaded)),
    }

    # anatomy: the numbers the diagram is drawn from, derived from the store itself
    ncell, nday = q.shape
    sc, st = q.shards
    cc, ct = q.chunks
    out["anatomy"] = {
        "cells": int(ncell),
        "days": int(nday),
        "time_first": str(dates[0].date()),
        "time_last": str(dates[-1].date()),
        "shard": [int(sc), int(st)],
        "chunk": [int(cc), int(ct)],
        "shard_rows": math.ceil(ncell / sc),
        "shard_cols": math.ceil(nday / st),
        "chunks_per_shard": (sc // cc) * (st // ct),
        "chunk_raw_mb": round(cc * ct * 4 / 1e6, 2),
        "shard_raw_mb": round(sc * st * 4 / 1e6, 1),
        "point_history_fetches": math.ceil(nday / st),
        "one_day_map_chunks": math.ceil(ncell / cc),
        "grid": [3000, 7200],
        "grid_res_deg": 0.05,
        "land_share": round(ncell / (3000 * 7200), 4),
    }

    # full point histories: the read the layout is for
    out["hydrographs"] = []
    for label, fw, key in STATIONS:
        lat, lon = POINTS[fw][2][key]
        row = find_cell(idx, lat, lon)
        t = time.time()
        v = q[int(row.cell), :]
        sec = time.time() - t
        v = np.where(in_loaded, v, np.nan)
        out["hydrographs"].append(
            {
                "station": label,
                "cell": int(row.cell),
                "lat": lat,
                "lon": lon,
                "uparea_km2": round(float(row.uparea_km2)),
                "read_s": round(sec, 2),
                "t0": str(dates[0].date()),
                "values": [sig(x) for x in v],
                "annual_max": {int(y): sig(np.nanmax(v[stamp_year == y])) for y in years_loaded},
            }
        )
        print(f"{label}: cell {int(row.cell):,}, history in {sec:.2f} s")

    # one cell as the store holds it: a row of the array folded year by year
    h = next(x for x in out["hydrographs"] if x["station"] == HEATMAP_STATION)
    vals = np.array([np.nan if x is None else x for x in h["values"]])
    rows = []
    for y in range(dates[0].year, dates[-1].year):
        m = stamp_year == y
        r = [sig(x) for x in vals[m]]
        rows.append(r + [None] * (366 - len(r)))
    out["heatmap"] = {
        "station": h["station"],
        "cell": h["cell"],
        "year_first": int(dates[0].year),
        "rows": rows,
        "vmax": sig(np.nanmax(vals)),
    }

    # one basin on two days: the costly read, timed and counted
    d1, d2 = (pd.Timestamp(x) for x in a.dates)
    for d in (d1, d2):
        if year_of_stamp(d) not in years_loaded:
            raise LookupError(
                f"map date {d.date()} is in year {year_of_stamp(d)}, which has no load marker"
            )
    (la0, la1), (lo0, lo1) = MAP["lat"], MAP["lon"]
    sub = idx[(idx.lat >= la0) & (idx.lat <= la1) & (idx.lon >= lo0) & (idx.lon <= lo1)]
    r0, r1 = int(sub.row.min()), int(sub.row.max())
    c0, c1 = int(sub.col.min()), int(sub.col.max())
    nr, nc = r1 - r0 + 1, c1 - c0 + 1
    cells = sub.cell.values
    ti = [int(np.searchsorted(dates, d)) for d in (d1, d2)]
    if dates[ti[0]] != d1 or dates[ti[1]] != d2:
        raise LookupError("map dates are not on the time axis")
    t = time.time()
    block = q.get_orthogonal_selection((cells, np.array(ti)))
    sec = time.time() - t
    time_chunks = {i // ct for i in ti}
    grid = lambda v: [  # dense (nr, nc) with null off land
        [None] * nc for _ in range(nr)
    ]
    g_up, g1, g2 = grid(None), grid(None), grid(None)
    for (rr, cc_, up), v1, v2 in zip(
        sub[["row", "col", "uparea_km2"]].itertuples(index=False),
        block[:, 0],
        block[:, 1],
        strict=True,
    ):
        g_up[rr - r0][cc_ - c0] = round(float(np.log10(up)), 2)
        g1[rr - r0][cc_ - c0] = sig(v1)
        g2[rr - r0][cc_ - c0] = sig(v2)
    # the global id of each map row's first land cell inside the box: with the land flags this
    # gives any map cell's id in the reader (cells are row-major, so id = first + land cells left)
    first_land = sub.groupby("row").cell.min()
    row_cell0 = [
        int(first_land[rr]) if rr in first_land.index else None for rr in range(r0, r1 + 1)
    ]
    lat_of = lambda rr: float(sub.lat[sub.row == rr].iloc[0])
    lon_of = lambda cc_: float(sub.lon[sub.col == cc_].iloc[0])
    stations = []
    for key, (lat, lon) in POINTS[MAP["framework"]][2].items():
        row = find_cell(idx, lat, lon)
        stations.append(
            {
                "name": key.replace("_", " ").title(),
                "r": int(row.row) - r0,
                "c": int(row.col) - c0,
                "cell": int(row.cell),
                "uparea_km2": round(float(row.uparea_km2)),
            }
        )
    down = idx.downstream_cell.values
    traces = []
    for key in MAP["traces"]:
        lat, lon = POINTS[MAP["framework"]][2][key]
        c = int(find_cell(idx, lat, lon).cell)
        path, steps = [], 0
        while c >= 0 and steps < 20000:
            rr, cc_ = int(idx.row.values[c]), int(idx.col.values[c])
            if not (r0 <= rr <= r1 and c0 <= cc_ <= c1):
                break
            path.append([rr - r0, cc_ - c0])
            c = int(down[c])
            steps += 1
        traces.append({"from": key.replace("_", " ").title(), "cells": len(path), "path": path})
    ckey = MAP["catchment"]
    target = int(find_cell(idx, *POINTS[MAP["framework"]][2][ckey]).cell)
    drains = catchment_in_box(idx, cells, target)
    rows_, cols_ = idx.row.values[drains] - r0, idx.col.values[drains] - c0
    catchment = {
        "to": ckey.replace("_", " ").title(),
        "cells": len(drains),
        "rc": [[int(a), int(b)] for a, b in zip(rows_, cols_, strict=True)],
    }
    print(f"catchment of {catchment['to']} inside the box: {len(drains):,} cells")
    out["map"] = {
        "name": MAP["name"],
        "lat": [lat_of(r0), lat_of(r1)],
        "lon": [lon_of(c0), lon_of(c1)],
        "rows": nr,
        "cols": nc,
        "land_cells": len(cells),
        "dates": [str(d1.date()), str(d2.date())],
        "read_s": round(sec, 1),
        "chunks_touched": int(len(np.unique(cells // cc)) * len(time_chunks)),
        "shards_touched": int(len(np.unique(cells // sc)) * len(time_chunks)),
        "row_cell0": row_cell0,
        "log10_uparea": g_up,
        "q": [g1, g2],
        "qmax": sig(np.nanmax(block)),
        "stations": stations,
        "traces": traces,
        "catchment": catchment,
    }
    out["network"] = out_network
    print(
        f"map {nr}x{nc}, {len(cells):,} land cells, 2 days in {sec:.1f} s "
        f"({out['map']['chunks_touched']} chunks in {out['map']['shards_touched']} shards)"
    )
    OUT.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(out, separators=(",", ":"))
    (OUT / "snapshots.json").write_text(txt)
    print(f"wrote {OUT / 'snapshots.json'} ({len(txt) / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
