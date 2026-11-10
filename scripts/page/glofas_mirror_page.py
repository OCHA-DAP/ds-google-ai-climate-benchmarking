"""Build outputs/glofas_mirror/index.html, the page that shows the GloFAS v4 mirror experiment.

Every number on the page comes from outputs/glofas_mirror/check.json, series.csv and
landmask.png, written by scripts/glofas_mirror_check.py; nothing is typed into the template.
Uses the benchmark page's tokens (scripts/page/build.py) so the two pages read as one set.

    uv run scripts/page/glofas_mirror_page.py
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from charts import esc

OUT = Path("outputs/glofas_mirror")
MIRROR = "var(--accent)"
SPOKE = "var(--inc)"


def tile(v, label):
    return f'<div class="tile"><b>{esc(v)}</b><span>{esc(label)}</span></div>'


def hydrograph(st: dict, s: pd.DataFrame) -> str:
    """Mirror and spoke daily discharge at one station: one panel per loaded year, one shared
    y scale, so the gap between years is not drawn as a line."""
    s = s.sort_values("date")
    d = pd.to_datetime(s.date)
    years = sorted(
        set(d.dt.year[(d.dt.month > 1) | (d.dt.day > 1)])
    )  # a 1 Jan stamp belongs to the year before
    w, h, l, r, t, b, gap = 1100, 240, 70, 16, 28, 34, 24
    n = max(len(years), 1)
    pw = (w - l - r - gap * (n - 1)) / n
    ph = h - t - b
    ymax = max(float(s.mirror.max()), float(s.spoke.max())) * 1.05 or 1.0
    Y = lambda v: t + ph - v / ymax * ph
    out = [
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(st["station"])}: mirror and spoke daily discharge, one panel per loaded year">'
    ]
    for k in range(5):
        v = ymax * k / 4
        out.append(
            f'<text x="{l - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)" font-family="var(--mono)">{v:,.0f}</text>'
        )
    for i, yr in enumerate(years):
        x0 = l + i * (pw + gap)
        a, bnd = pd.Timestamp(yr, 1, 2), pd.Timestamp(yr + 1, 1, 1)
        sel = (d >= a) & (d <= bnd)
        X = lambda dt, x0=x0, a=a, bnd=bnd: x0 + (dt - a).days / max((bnd - a).days, 1) * pw
        for k in range(5):
            v = ymax * k / 4
            out.append(
                f'<line x1="{x0:.1f}" x2="{x0 + pw:.1f}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--line)" stroke-width="1"/>'
            )
        for m in (4, 7, 10):
            dm = pd.Timestamp(yr, m, 1)
            out.append(
                f'<line x1="{X(dm):.1f}" x2="{X(dm):.1f}" y1="{t}" y2="{t + ph}" stroke="var(--line)" stroke-width="1"/>'
            )
            out.append(
                f'<text x="{X(dm) + 3:.1f}" y="{h - 12}" font-size="10" fill="var(--muted)" font-family="var(--mono)">{dm:%b}</text>'
            )
        out.append(
            f'<text x="{x0:.1f}" y="{h - 12}" font-size="11" fill="var(--fg)" font-family="var(--mono)">{yr}</text>'
        )
        ds_, sp, mi = d[sel], s.spoke[sel], s.mirror[sel]
        if len(ds_):

            def path(vals, X=X, ds_=ds_):
                return "M" + " L".join(
                    f"{X(dd):.1f},{Y(v):.1f}" for dd, v in zip(ds_, vals, strict=True)
                )

            out.append(
                f'<path d="{path(sp)}" fill="none" stroke="{SPOKE}" stroke-width="3.5" stroke-dasharray="7 5" stroke-linejoin="round"/>'
            )
            out.append(
                f'<path d="{path(mi)}" fill="none" stroke="{MIRROR}" stroke-width="1.6" stroke-linejoin="round"/>'
            )
    out.append(
        f'<text x="{l}" y="{t - 10}" font-size="12" fill="var(--fg)">{esc(st["station"])} · cell {st["cell"]:,} · {st["uparea_km2"]:,.0f} km² upstream · m³/s, shared scale</text>'
    )
    bd = st.get("boundary_days_differing") or []
    out.append(
        f'<text x="{w - r}" y="{t - 10}" text-anchor="end" font-size="11" fill="var(--muted)">spoke stamp shift {st["spoke_shift_days"]:+d} d · {st["n_compared"]} days · {st["share_equal_1e-3"]:.2%} equal'
        + (f" · spoke file-boundary days differ: {', '.join(bd)}" if bd else " · max diff 0")
        + "</text>"
    )
    out.append("</svg>")
    return "".join(out)


def main() -> int:
    c = json.loads((OUT / "check.json").read_text())
    series = (
        pd.read_csv(OUT / "series.csv")
        if (OUT / "series.csv").stat().st_size > 20
        else pd.DataFrame(columns=["station", "date", "mirror", "spoke"])
    )
    png = base64.b64encode((OUT / "landmask.png").read_bytes()).decode()
    st, by, rc, ix = c["store"], c["bytes"], c["read_cost"], c["index"]
    years = sorted(st["years_loaded"])
    allpass = c["n_pass"] == c["n_checks"]

    checks = "".join(
        f'<tr class="{"ok" if k["pass"] else "bad"}"><td><span class="pill">{"pass" if k["pass"] else "FAIL"}</span></td><td>{esc(k["name"])}</td><td>{esc(k["evidence"])}</td></tr>'
        for k in c["checks"]
    )
    loads = "".join(
        f"<tr><td>{y}</td><td>{r['days']}</td><td>{r['first']} to {r['last']}</td><td>{r['nan_on_land']}</td><td>{r['finite_off_land']}</td><td>{r['seconds'] // 60} min {r['seconds'] % 60} s</td><td>{r['peak_rss_gb']} GB</td></tr>"
        for y, r in sorted(st["years_loaded"].items())
    )
    figs = "".join(
        f"<figure>{hydrograph(s, series[series.station == s['station']])}</figure>"
        for s in c["stations"]
        if (series.station == s["station"]).any()
    )
    attrs = "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(str(v))}</td></tr>" for k, v in st["attrs"].items()
    )
    stations_tbl = "".join(
        f"<tr><td>{esc(s['station'])}</td><td>{s['cell']:,}</td><td>{s['lat']:.3f}, {s['lon']:.3f}</td><td>{s['uparea_km2']:,.0f}</td><td>{s['spoke_shift_days']:+d}</td><td>{s['n_compared']}</td><td>{s['share_equal_1e-3']:.2%}</td><td>{s['max_abs_diff']:.3g}</td><td>{s['one_point_history_s']} s</td></tr>"
        for s in c["stations"]
    )

    html = f"""<title>GloFAS v4 Mirror</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: one reading column; the store's own numbers first, then the proof, then the cost */
:root{{--bg:#f7f8f8;--panel:#ffffff;--fg:#182026;--muted:#5b6770;--line:#d9dfe3;--accent:#0f6e8c;--accent-soft:#d6ecf2;--ok:#2a7a3b;--warn:#b2561a;--inc:#7b4fa0;
--body:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#13191d;--panel:#1b2329;--fg:#e6ebee;--muted:#9aa7b0;--line:#2e3a42;--accent:#5fb6d1;--accent-soft:#163a46;--ok:#6cc47f;--warn:#e39a60;--inc:#b995dc;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#13191d;--panel:#1b2329;--fg:#e6ebee;--muted:#9aa7b0;--line:#2e3a42;--accent:#5fb6d1;--accent-soft:#163a46;--ok:#6cc47f;--warn:#e39a60;--inc:#b995dc;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:15px;line-height:1.5;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:32px 64px}}
main{{max-width:1100px;margin:0 auto}}
h1{{font-size:28px;line-height:1.2;margin:0 0 6px;text-wrap:balance}} h2{{font-size:19px;margin:40px 0 10px;text-wrap:balance}}
p{{max-width:68ch}} .eyebrow{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
.lede{{color:var(--muted);font-size:16px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:12px 14px;min-width:0}}
.tile b{{display:block;font-family:var(--mono);font-size:22px;font-weight:500;font-variant-numeric:tabular-nums;color:var(--accent)}} .tile span{{font-size:13px;color:var(--muted)}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}}
th{{text-align:left;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:500;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}} td:first-child{{white-space:nowrap}}
.pill{{display:inline-block;font-size:11px;letter-spacing:.05em;text-transform:uppercase;padding:1px 7px;border-radius:3px;background:var(--accent-soft);color:var(--ok)}}
tr.bad .pill{{color:var(--warn);background:transparent;border:1px solid var(--warn)}}
.verdict{{border-left:3px solid {"var(--ok)" if allpass else "var(--warn)"};padding:4px 14px;margin:18px 0;background:var(--panel)}}
figure{{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:8px}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:4px 0 8px}} .legend i{{display:inline-block;width:26px;height:0;border-top:3px solid;vertical-align:middle;margin-right:6px}}
img.mask{{width:100%;max-width:100%;border:1px solid var(--line);image-rendering:auto}}
code,pre{{font-family:var(--mono);font-size:13px}} pre{{background:var(--panel);border:1px solid var(--line);padding:12px;overflow-x:auto;border-radius:4px}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font-size:14px}} dt{{color:var(--muted)}} dd{{margin:0;min-width:0}}
</style>
<main>
<div class="eyebrow">Experiment · checked {esc(c["checked_at"][:16].replace("T", " "))} UTC · GloFAS v4 consolidated reanalysis on the team blob</div>
<h1>GloFAS v4 mirror: {len(years)} years in the store, {c["n_pass"]} of {c["n_checks"]} checks pass</h1>
<p class="lede">One sharded Zarr on <code>global/glofas/v4/reanalysis</code> holding every land cell of the 0.05° grid as a (cell, time) array, loaded year by year from whole-globe EWDS files. This page is the small-scale run that has to be right before the 47-year backfill is scheduled.</p>
<div class="tiles">
{tile(f"{ix['cells']:,}", "land cells in the store")}
{tile(", ".join(years), "years loaded")}
{tile(f"{by['q_zarr_per_year_gb']} GB", "store per year")}
{tile(f"{by['q_zarr_47yr_gb_projection']} GB", "projected for 1979 to 2025")}
{tile(f"${by['cool_lrs_usd_per_month_47yr']}", "per month, Cool tier, 47 years")}
{tile(f"{rc['one_cell_history_s_median']} s", "one point, loaded history, from blob")}
</div>
<div class="verdict"><p>{"Every check passed. The store reads back exactly what the spokes hold, the land mask is where it should be, and a point history is a sub-second read." if allpass else "Some checks failed; see the table. Nothing should be scheduled on this layout until they pass."}</p></div>

<h2>What the store is</h2>
<dl>
<dt>array</dt><dd><code>q</code> float32, shape {st["shape"][0]:,} cells × {st["shape"][1]:,} days, shards {st["shards"][0]:,} × {st["shards"][1]:,}, chunks {st["chunks"][0]} × {st["chunks"][1]:,}, zstd</dd>
<dt>time axis</dt><dd>{esc(st["time_first"][:10])} to {esc(st["time_last"][:10])}, consecutive days, stored as EWDS stamps them</dd>
<dt>cells</dt><dd>row-major over the grid, land where the upstream-area map is finite; <code>cells.parquet</code> maps cell to row, column, latitude, longitude, upstream area and downstream cell ({ix["pits"]:,} pits or outlets)</dd>
<dt>bronze</dt><dd>the EWDS netCDF per year as served, {by["bronze_per_year_gb"]} GB each, for provenance and rebuilds</dd>
<dt>blobs</dt><dd>{by["n_blobs"]:,} objects under the prefix</dd>
</dl>
<div class="wrap"><table><thead><tr><th>attribute</th><th>value</th></tr></thead><tbody>{attrs}</tbody></table></div>

<h2>Checks</h2>
<div class="wrap"><table><thead><tr><th></th><th>check</th><th>evidence</th></tr></thead><tbody>{checks}</tbody></table></div>

<h2>Each year's load</h2>
<p>Recorded in the array attributes by the loader at the time of the write. A year with a mask or calendar fault is never written.</p>
<div class="wrap"><table><thead><tr><th>year</th><th>days</th><th>stamps</th><th>NaN on land</th><th>finite off land</th><th>load time</th><th>peak memory</th></tr></thead><tbody>{loads}</tbody></table></div>

<h2>Read back against the spokes' own copies</h2>
<p>The frameworks' GloFAS v4 series at their trigger cells, as the spokes hold them on the shared drive and in their blob, against the mirror at the same cell found through the index. The spokes stamp a day at its start, EWDS at its end; the shift is undone before comparing. Equality here proves the orientation of the grid, the cell order and the values in one go.</p>
<div class="legend"><span><i style="border-color:{MIRROR}"></i>mirror (this store)</span><span><i style="border-color:{SPOKE};border-top-style:dashed"></i>spoke copy</span></div>
{figs}
<div class="wrap"><table><thead><tr><th>station</th><th>cell</th><th>lat, lon</th><th>upstream km²</th><th>shift</th><th>days</th><th>equal within 0.1%</th><th>max abs diff m³/s</th><th>one history read</th></tr></thead><tbody>{stations_tbl}</tbody></table></div>

<h2>The land mask as stored</h2>
<p>Every stored cell drawn from the index at one tenth of the grid's resolution, north up; latitude {ix["lat_range"][0]:.3f} to {ix["lat_range"][1]:.3f}, longitude {ix["lon_range"][0]:.3f} to {ix["lon_range"][1]:.3f}. A flipped or shifted grid shows here before any number does.</p>
<img class="mask" alt="land cells of the GloFAS grid held in the store, drawn north up" src="data:image/png;base64,{png}">

<h2>Read cost and bytes</h2>
<div class="wrap"><table><thead><tr><th>measure</th><th>value</th></tr></thead><tbody>
<tr><td>one cell, whole loaded history, median of 3</td><td>{rc["one_cell_history_s_median"]} s</td></tr>
<tr><td>50 scattered cells, whole loaded history, median of 3</td><td>{rc["fifty_cells_history_s_median"]} s</td></tr>
<tr><td>2,000 random cells, whole axis (the join check)</td><td>{c["read_2000_cells_all_time_s"]} s</td></tr>
<tr><td>q.zarr on blob</td><td>{by["q.zarr"] / 1e9:.2f} GB for {len(years)} years</td></tr>
<tr><td>bronze on blob</td><td>{by["bronze"] / 1e9:.2f} GB</td></tr>
<tr><td>static (ECMWF upstream area, drain direction) and index</td><td>{(by["static"] + by["cells.parquet"]) / 1e6:.0f} MB</td></tr>
<tr><td>47 years, projected</td><td>{by["q_zarr_47yr_gb_projection"]} GB store, {by["bronze_per_year_gb"] * 47:.0f} GB bronze; ${by["cool_lrs_usd_per_month_47yr"]} a month with bronze in the Archive tier</td></tr>
</tbody></table></div>

<h2>How to read it</h2>
<pre>import adlfs, os, zarr, pandas as pd
store = zarr.storage.FsspecStore.from_url("abfs://global/glofas/v4/reanalysis/q.zarr",
    storage_options={{"account_name": "imb0chd0dev", "sas_token": os.environ["DSCI_AZ_BLOB_DEV_SAS"]}})
g = zarr.open_group(store, mode="r")
cells = pd.read_parquet("cells.parquet")              # from the same prefix: cell, lat, lon, uparea_km2, downstream_cell
cell = cells.query("abs(lat - 12.125) < 1e-6 and abs(lon - 15.025) < 1e-6").cell.item()   # N'Djamena's GloFAS cell
q = pd.Series(g["q"][cell, :], index=pd.Timestamp("1979-01-01") + pd.to_timedelta(g["time"][:], unit="D"))
# q is stamped at the END of each 24 h window; subtract one day for a start-of-day convention</pre>

<h2>Before the full run</h2>
<p>The backfill is 47 whole-globe requests, about {by["bronze_per_year_gb"] * 47:.0f} GB through EWDS, loaded one year at a time on the single-node job policy. Open before scheduling it: the EWDS requests share the team key's queue with the daily Nigeria and Somalia runs, so the run belongs off-season or on a second key; 2025 comes from the intermediate product where the consolidated one ends; v5 is a sibling prefix when it goes operational; and the code should move from the benchmark repo to its own pipeline with a KB page. Design and rejected layouts: ADR 0003 in the benchmark repo.</p>
</main>
"""
    (OUT / "index.html").write_text(html)
    print(f"wrote {OUT / 'index.html'} ({len(html) / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
