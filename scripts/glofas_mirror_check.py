"""Check the GloFAS v4 mirror on blob and write what the page shows: outputs/glofas_mirror/check.json.

Reads the store the way a consumer would (read SAS, FsspecStore over the network) and verifies:

- the index: 6,221,926 land cells, row-major, every upstream area finite, every downstream link
  valid, and water flows to larger upstream area (the drain-direction orientation check)
- the store: shape equals (cells, days 1979-01-02..2026-01-01), sharding and chunking as designed,
  the time axis consecutive, the per-year load records in the attributes clean (no NaN on land,
  nothing finite off land, coordinates equal to the index, 365 or 366 days)
- the year join: for 2,000 random cells, every day of the loaded years is finite and every day
  outside them is NaN (the fill value), so "not loaded" and "no data" cannot be confused
- orientation and values: the mirror equals the spokes' own GloFAS v4 copies at Chatara,
  N'Djamena and Bahadurabad once the spoke's day-stamp shift is undone (fetch_glofas_recent.py
  STAMP_SHIFT_DAYS), resolved through the index by the spokes' cell coordinates
- read cost from blob: one point's loaded history, 50 scattered points, each the median of 3
- bytes on blob: the store, bronze and static, and the projection to 47 years

Also writes series.csv (mirror and spoke daily values at the three stations) and landmask.png
(the index drawn on the grid at 1/10 resolution). Every check is a pass/fail with its evidence;
a failing check is recorded, not raised, so the page can show it.
"""

from __future__ import annotations

import itertools
import json
import struct
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import zarr

sys.path.insert(0, str(Path(__file__).parent))
import glofas_mirror as gm
import incumbents as inc
from fetch_glofas_recent import POINTS, STAMP_SHIFT_DAYS

OUT = Path("outputs/glofas_mirror")
N_CELLS = 6_221_926
STATIONS = [  # (label, framework key in POINTS, station key, spoke loader)
    ("Chatara (Koshi)", "Nepal 2025 (Chatara)", "Chatara", lambda: inc.glofas_npl("Chatara")),
    ("N'Djamena (Chari)", "Chad 2025", "ndjamena", inc.glofas_tcd_ndjamena),
    (
        "Bahadurabad (Jamuna)",
        "Bangladesh 2025 (Bahadurabad)",
        "Bahadurabad",
        inc.glofas_bgd_bahadurabad,
    ),
]


def check(name: str, ok: bool, evidence: str) -> dict:
    print(("PASS " if ok else "FAIL ") + name + ": " + evidence, flush=True)
    return {"name": name, "pass": bool(ok), "evidence": evidence}


def png_gray(img: np.ndarray) -> bytes:
    """Minimal 8-bit greyscale PNG encoder (no PIL dependency)."""
    h, w = img.shape
    raw = b"".join(b"\x00" + img[r].astype("uint8").tobytes() for r in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    checks, res = [], {}
    idx = gm.load_index()
    res["index"] = {"cells": len(idx), "columns": idx.columns.tolist()}
    checks.append(
        check(
            "index: cell count",
            len(idx) == N_CELLS,
            f"{len(idx):,} land cells (expected {N_CELLS:,})",
        )
    )
    rm = np.lexsort((idx.col.values, idx.row.values))
    checks.append(
        check(
            "index: row-major order",
            np.array_equal(rm, np.arange(len(idx))),
            "rows then columns ascending",
        )
    )
    checks.append(
        check(
            "index: upstream area finite",
            bool(np.isfinite(idx.uparea_km2.values).all()),
            f"min {idx.uparea_km2.min():.1f} km2, max {idx.uparea_km2.max():,.0f} km2",
        )
    )
    d = idx.downstream_cell.values
    valid = (d == -1) | ((d >= 0) & (d < len(idx)))
    has = d >= 0
    grows = idx.uparea_km2.values[d[has]] >= idx.uparea_km2.values[has] * 0.999
    checks.append(
        check(
            "index: downstream links valid",
            bool(valid.all()),
            f"{has.sum():,} linked, {(d == -1).sum():,} pits or outlets",
        )
    )
    checks.append(
        check(
            "index: water flows to larger upstream area",
            grows.mean() > 0.999,
            f"{grows.mean():.5%} of linked cells drain to a cell with upstream area >= their own",
        )
    )
    res["index"]["pits"] = int((d == -1).sum())
    res["index"]["lat_range"] = [float(idx.lat.min()), float(idx.lat.max())]
    res["index"]["lon_range"] = [float(idx.lon.min()), float(idx.lon.max())]

    # land-mask thumbnail from the index alone (what a reader sees), 1/10 of the grid
    grid = np.zeros((3000, 7200), dtype=bool)
    grid[idx.row.values, idx.col.values] = True
    thumb = grid.reshape(300, 10, 720, 10).mean(axis=(1, 3))
    img = (255 - (thumb * 200)).astype("uint8")  # land dark, water white
    if idx.lat.values[0] < idx.lat.values[-1]:
        img = img[::-1]  # draw north up
    (OUT / "landmask.png").write_bytes(png_gray(img))
    res["index"]["north_up"] = bool(idx.lat.values[0] > idx.lat.values[-1])

    store = gm.read_store()
    root = zarr.open_group(store, mode="r")
    q, taxis = root["q"], root["time"][:]
    attrs = dict(q.attrs)
    loaded = gm.loaded_years()
    res["store"] = {
        "shape": list(q.shape),
        "shards": list(q.shards),
        "chunks": list(q.chunks),
        "dtype": str(q.dtype),
        "time_first": str(gm.EPOCH + pd.Timedelta(days=int(taxis[0]))),
        "time_last": str(gm.EPOCH + pd.Timedelta(days=int(taxis[-1]))),
        "attrs": {k: v for k, v in attrs.items() if k != "years_loaded"},
        "years_loaded": loaded,
    }
    checks.append(
        check(
            "store: shape",
            q.shape == (len(idx), len(taxis)) and len(taxis) == 17167,
            f"q {q.shape}, time {len(taxis)} days",
        )
    )
    checks.append(
        check(
            "store: layout as designed",
            tuple(q.shards) == (gm.SHARD_CELLS, gm.CHUNK_DAYS)
            and tuple(q.chunks) == (gm.CHUNK_CELLS, gm.CHUNK_DAYS),
            f"shards {q.shards}, chunks {q.chunks}",
        )
    )
    checks.append(
        check(
            "store: time axis consecutive",
            np.array_equal(taxis, np.arange(taxis[0], taxis[0] + len(taxis))),
            f"{res['store']['time_first'][:10]} .. {res['store']['time_last'][:10]}",
        )
    )
    for y, rec in sorted(loaded.items()):
        ok = (
            rec["nan_on_land"] == 0
            and rec["finite_off_land"] == 0
            and rec["coords_equal_index"]
            and rec["days"] in (365, 366)
        )
        checks.append(
            check(
                f"load {y}: masks, coordinates, calendar",
                ok,
                f"{rec['days']} days {rec['first']}..{rec['last']}, NaN on land {rec['nan_on_land']}, finite off land {rec['finite_off_land']}, {rec['seconds']} s, peak RSS {rec['peak_rss_gb']} GB",
            )
        )

    # year join and the fill value outside loaded years, on 2,000 random cells
    rng = np.random.default_rng(0)
    cells = np.sort(rng.choice(len(idx), 2000, replace=False))
    t = time.time()
    block = q.get_orthogonal_selection((cells, slice(None)))  # (2000, all days)
    res["read_2000_cells_all_time_s"] = round(time.time() - t, 1)
    dates = gm.EPOCH + pd.to_timedelta(taxis, unit="D")
    in_loaded = in_loaded_dates(dates, loaded, 0)
    fin = np.isfinite(block)
    checks.append(
        check(
            "values: finite on every loaded day",
            bool(fin[:, in_loaded].all()),
            f"2,000 random cells x {in_loaded.sum()} loaded days, {(~fin[:, in_loaded]).sum()} NaN",
        )
    )
    checks.append(
        check(
            "values: NaN (fill) outside loaded years",
            bool((~fin[:, ~in_loaded]).all()),
            f"{fin[:, ~in_loaded].sum()} finite values among {(~in_loaded).sum()} unloaded days",
        )
    )
    years = sorted(int(y) for y in loaded)
    joins = [(a, b) for a, b in itertools.pairwise(years) if b == a + 1]
    for a, b in joins:
        j = pd.Timestamp(b, 1, 1)
        w = (dates >= j - pd.Timedelta(days=3)) & (dates <= j + pd.Timedelta(days=3))
        checks.append(
            check(
                f"join {a}/{b}: no gap, no double day",
                bool(fin[:, w].all()) and w.sum() == 7,
                f"7 consecutive days around {j.date()} all finite",
            )
        )
    res["value_range"] = {
        "min": float(np.nanmin(block)),
        "max": float(np.nanmax(block)),
        "negative": int((block[fin] < 0).sum()),
    }
    checks.append(
        check(
            "values: no negative discharge",
            res["value_range"]["negative"] == 0,
            f"min {res['value_range']['min']:.3f}, max {res['value_range']['max']:,.0f} m3/s",
        )
    )

    # the spokes' own copies, at their cells, through the index
    series_rows, res["stations"] = [], []
    for label, fw, st, loader in STATIONS:
        lat, lon = POINTS[fw][2][st]
        hit = idx[(np.abs(idx.lat - lat) < 1e-6) & (np.abs(idx.lon - lon) < 1e-6)]
        if len(hit) != 1:
            checks.append(
                check(f"{label}: cell found", False, f"{len(hit)} index rows at ({lat}, {lon})")
            )
            continue
        cell = int(hit.cell.iloc[0])
        t = time.time()
        m = pd.Series(q[cell, :], index=dates, name="mirror")
        one_s = time.time() - t
        spoke = loader()
        shift = STAMP_SHIFT_DAYS[fw]
        m_sp = m.copy()
        m_sp.index = m_sp.index + pd.Timedelta(days=shift)  # mirror stamp -> spoke stamp
        both = pd.concat([m_sp.rename("mirror"), spoke.rename("spoke")], axis=1)
        both = both[in_loaded_dates(both.index, loaded, shift)].dropna()
        diff = (both.mirror - both.spoke).abs()
        equal = diff <= 1e-3 * both.spoke.abs().clip(lower=1)
        eq = equal.mean() if len(both) else float("nan")
        # the spokes' per-year files can carry a boundary-day artefact (the last or first day of a
        # yearly file holding the neighbouring day's value); those days are reported, not scored
        boundary = (both.index.month == 1) & (both.index.day == 1) | (both.index.month == 12) & (
            both.index.day == 31
        )
        off_boundary_equal = bool(equal[~boundary].all()) if (~boundary).any() else False
        boundary_bad = [str(d.date()) for d in both.index[boundary & ~equal]]
        row = {
            "station": label,
            "framework": fw,
            "cell": cell,
            "lat": lat,
            "lon": lon,
            "uparea_km2": float(hit.uparea_km2.iloc[0]),
            "spoke_shift_days": shift,
            "n_compared": len(both),
            "share_equal_1e-3": round(float(eq), 5),
            "max_abs_diff": float(diff.max()) if len(both) else None,
            "boundary_days_differing": boundary_bad,
            "spoke_range": [str(spoke.index.min().date()), str(spoke.index.max().date())],
            "one_point_history_s": round(one_s, 2),
        }
        res["stations"].append(row)
        checks.append(
            check(
                f"{label}: mirror equals the spoke copy",
                len(both) > 300 and off_boundary_equal,
                f"{len(both)} days compared, {eq:.3%} equal within 0.1%, every day off the 1 Jan / 31 Dec file boundaries equal"
                + (
                    f"; spoke file-boundary days differing: {', '.join(boundary_bad)}"
                    if boundary_bad
                    else ""
                )
                + f", max abs diff {row['max_abs_diff']:.4g} m3/s, spoke shift {shift} d",
            )
        )
        for d_, r_ in both.iterrows():
            series_rows.append(
                {
                    "station": label,
                    "date": d_.date().isoformat(),
                    "mirror": round(float(r_.mirror), 3),
                    "spoke": round(float(r_.spoke), 3),
                }
            )
    pd.DataFrame(series_rows).to_csv(OUT / "series.csv", index=False)

    # read cost from blob
    lat = []
    for _ in range(3):
        t = time.time()
        q[int(cells[0]), :]
        lat.append(time.time() - t)
    lat50 = []
    c50 = np.sort(rng.choice(len(idx), 50, replace=False))
    for _ in range(3):
        t = time.time()
        q.get_orthogonal_selection((c50, slice(None)))
        lat50.append(time.time() - t)
    res["read_cost"] = {
        "one_cell_history_s_median": round(float(np.median(lat)), 2),
        "fifty_cells_history_s_median": round(float(np.median(lat50)), 2),
    }

    # bytes on blob
    cc = gm._container()
    sizes = {"q.zarr": 0, "bronze": 0, "static": 0, "cells.parquet": 0}
    nblobs = 0
    for b in cc.list_blobs(name_starts_with=gm.PREFIX + "/"):
        k = b.name[len(gm.PREFIX) + 1 :]
        for key in sizes:
            if k.startswith(key):
                sizes[key] += b.size
                nblobs += 1
    res["bytes"] = {k: v for k, v in sizes.items()}
    ny = max(len(loaded), 1)
    res["bytes"]["q_zarr_per_year_gb"] = round(sizes["q.zarr"] / ny / 1e9, 2)
    res["bytes"]["q_zarr_47yr_gb_projection"] = round(sizes["q.zarr"] / ny / 1e9 * 47, 1)
    res["bytes"]["bronze_per_year_gb"] = round(sizes["bronze"] / ny / 1e9, 2)
    res["bytes"]["n_blobs"] = nblobs
    res["bytes"]["cool_lrs_usd_per_month_47yr"] = round(
        (sizes["q.zarr"] / ny * 47) / 1e9 * 0.01 + (sizes["bronze"] / ny * 47) / 1e9 * 0.002, 2
    )
    checks.append(
        check(
            "bytes: store per year within the measured projection",
            sizes["q.zarr"] / ny / 1e9 < 2.6,
            f"{res['bytes']['q_zarr_per_year_gb']} GB per loaded year in q.zarr ({nblobs:,} blobs), bronze {res['bytes']['bronze_per_year_gb']} GB per year",
        )
    )

    res["checks"] = checks
    res["n_pass"] = sum(c["pass"] for c in checks)
    res["n_checks"] = len(checks)
    res["checked_at"] = pd.Timestamp.now("UTC").isoformat(timespec="seconds")
    (OUT / "check.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\n{res['n_pass']} of {res['n_checks']} checks pass; wrote {OUT / 'check.json'}")
    return 0 if res["n_pass"] == res["n_checks"] else 1


def in_loaded_dates(index: pd.DatetimeIndex, loaded: dict, shift: int) -> np.ndarray:
    """Days the markers say are written: each year's recorded first and last stamp (the product's
    last year ends early), shifted to the spoke's convention."""
    m = np.zeros(len(index), dtype=bool)
    for rec in loaded.values():
        a = pd.Timestamp(rec["first"]) + pd.Timedelta(days=shift)
        b = pd.Timestamp(rec["last"]) + pd.Timedelta(days=shift)
        m |= (index >= a) & (index <= b)
    return m


if __name__ == "__main__":
    sys.exit(main())
