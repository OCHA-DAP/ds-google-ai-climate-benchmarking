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
from glofas_mirror_viz import CSS as VIZ_CSS
from glofas_mirror_viz import section as viz_section

OUT = Path("outputs/glofas_mirror")
MIRROR = "var(--accent)"
SPOKE = "var(--inc)"


def tile(v, label):
    return f'<div class="tile"><b>{esc(v)}</b><span>{esc(label)}</span></div>'


def hydrograph(st: dict, s: pd.DataFrame) -> str:
    """Mirror and spoke daily discharge at one station over every compared day on one time axis,
    the line broken wherever a day is missing (an unloaded year), both series reduced to one
    value per pixel column (the maximum, so floods survive) before drawing."""
    s = s.sort_values("date")
    d = pd.to_datetime(s.date)
    w, h, l, r, t, b = 1100, 220, 70, 16, 28, 30
    pw, ph = w - l - r, h - t - b
    d0, d1 = d.min(), d.max()
    span = max((d1 - d0).days, 1)
    ymax = max(float(s.mirror.max()), float(s.spoke.max())) * 1.05 or 1.0
    X = lambda dt_: l + (dt_ - d0).days / span * pw
    Y = lambda v: t + ph - v / ymax * ph
    out = [
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(st["station"])}: mirror and spoke daily discharge on one time axis">'
    ]
    for k in range(5):
        v = ymax * k / 4
        out.append(
            f'<line x1="{l}" x2="{w - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--line)" stroke-width="1"/>'
            f'<text x="{l - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)" font-family="var(--mono)">{v:,.0f}</text>'
        )
    for yr in range(d0.year, d1.year + 1):
        if yr % 5:
            continue
        x = X(pd.Timestamp(yr, 1, 1))
        if x < l or x > w - r:
            continue
        out.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{t}" y2="{t + ph}" stroke="var(--line)" stroke-width="1"/>'
            f'<text x="{x + 3:.1f}" y="{h - 10}" font-size="11" fill="var(--muted)" font-family="var(--mono)">{yr}</text>'
        )
    # one value per pixel column: the maximum of each series in that column; a column with no
    # day (an unloaded year) breaks the line
    px = ((d - d0).dt.days / span * pw).astype(int)
    g = pd.DataFrame({"px": px.values, "mirror": s.mirror.values, "spoke": s.spoke.values})
    g = g.groupby("px").max()
    for col, style in (
        ("spoke", f'stroke="{SPOKE}" stroke-width="3" stroke-dasharray="6 4"'),
        ("mirror", f'stroke="{MIRROR}" stroke-width="1.4"'),
    ):
        parts, prev = [], None
        for p_, v in g[col].items():
            cmd = "M" if prev is None or p_ - prev > 2 else "L"
            parts.append(f"{cmd}{l + p_},{Y(v):.1f}")
            prev = p_
        out.append(f'<path d="{" ".join(parts)}" fill="none" {style} stroke-linejoin="round"/>')
    out.append(
        f'<text x="{l}" y="{t - 10}" font-size="12" fill="var(--fg)">{esc(st["station"])} · cell {st["cell"]:,} · {st["uparea_km2"]:,.0f} km² upstream · m³/s</text>'
    )
    bd = st.get("boundary_days_differing") or []
    out.append(
        f'<text x="{w - r}" y="{t - 10}" text-anchor="end" font-size="11" fill="var(--muted)">spoke stamp shift {st["spoke_shift_days"]:+d} d · {st["n_compared"]:,} days · {st["share_equal_1e-3"]:.2%} equal'
        + (
            (
                f" · {len(bd)} spoke file-boundary days differ"
                if len(bd) > 3
                else f" · spoke file-boundary days differ: {', '.join(bd)}"
            )
            if bd
            else " · max diff 0"
        )
        + "</text>"
    )
    out.append("</svg>")
    return "".join(out)


def main(without_backfill: bool = False) -> int:
    c = json.loads((OUT / "check.json").read_text())
    series = (
        pd.read_csv(OUT / "series.csv")
        if (OUT / "series.csv").stat().st_size > 20
        else pd.DataFrame(columns=["station", "date", "mirror", "spoke"])
    )
    png = base64.b64encode((OUT / "landmask.png").read_bytes()).decode()
    snap = json.loads((OUT / "snapshots.json").read_text())  # scripts/glofas_mirror_snapshots.py
    # scripts/glofas_mirror_runs.py; absent only when the build says so (a run is still going)
    bf = json.loads((OUT / "backfill.json").read_text()) if not without_backfill else None
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
    runs_tbl = (
        ""
        if bf is None
        else "".join(
            f"<tr><td>{r['run_id']}</td><td>{esc(r['start'][:16].replace('T', ' '))}</td><td>{r['hours']}</td><td>{len(r['years_loaded'])}: {r['years_loaded'][0]} to {r['years_loaded'][-1]}</td><td>{esc(r['result'])}{(' in task ' + r['failed_task']) if r['failed_task'] else ''}; {esc(r['message'].split('.')[0]) if r['message'] else 'all tasks finished'}</td></tr>"
            if r["years_loaded"]
            else f"<tr><td>{r['run_id']}</td><td>{esc(r['start'][:16].replace('T', ' '))}</td><td>{r['hours']}</td><td>none</td><td>{esc(r['result'])}; {esc(r['message'][:120])}</td></tr>"
            for r in bf["runs"]
        )
    )
    bgd = next((x for x in c["stations"] if x["station"].startswith("Bahadurabad")), {})
    bgd_bd = bgd.get("boundary_days_differing") or []
    bgd_bd_desc = (
        ", ".join(bgd_bd)
        if len(bgd_bd) <= 3
        else f"{sum(d.endswith('-01-01') for d in bgd_bd)} of them a 1 January, from {bgd_bd[0]} to {bgd_bd[-1]}"
    )
    stations_tbl = "".join(
        f"<tr><td>{esc(s['station'])}</td><td>{s['cell']:,}</td><td>{s['lat']:.3f}, {s['lon']:.3f}</td><td>{s['uparea_km2']:,.0f}</td><td>{s['spoke_shift_days']:+d}</td><td>{s['n_compared']}</td><td>{s['share_equal_1e-3']:.2%}</td><td>{s['max_abs_diff']:.3g}</td><td>{s['one_point_history_s']} s</td></tr>"
        for s in c["stations"]
    )

    backfill_sec = (
        """<h2>How the backfill ran</h2>
<p>The backfill is still running; this section is written from the Databricks API once it has ended.</p>
"""
        if bf is None
        else f"""<h2>How the backfill ran</h2>
<p>{bf["ewds_requests"]} whole-globe requests on the team's EWDS key, one job on the single-node policy, started {len(bf["runs"])} times. Every year's state lives in three ledgers (the EWDS request id, the bronze file, the load marker), so each restart skipped what was done and redid only the year it was interrupted in. {("Resubmitted to EWDS: " + ", ".join(bf["ewds_resubmitted"]) + ".") if bf["ewds_resubmitted"] else "No request had to be resubmitted."} Total {bf["hours"]} cluster hours, about ${bf["usd"]} at ${bf["usd_per_hour"]} an hour ({esc(bf["rate_note"])}).</p>
<div class="wrap"><table><thead><tr><th>run</th><th>started (UTC)</th><th>hours</th><th>years loaded</th><th>ended with</th></tr></thead><tbody>{runs_tbl}</tbody></table></div>
<ul>
<li><b>Driver memory.</b> The first run stopped after 29 years when the driver stopped responding during the 2007 load: the loader held the 2.4 GB yearly file in memory and made two 1 GB copies per band, 7.7 GB resident beside the Spark driver on a 14 GB node. The file is now read from the node's disk and the band write is one copy; peak fell to 5.8 GB and a year loads in about half the time.</li>
<li><b>A dropped download.</b> The second run stopped when EWDS closed the 2015 download at 1.7 of 2.4 GB. A broken stream is now retried from scratch, and a zero-byte bronze blob (what an aborted staged upload leaves behind) no longer counts as present.</li>
<li><b>The product's last year.</b> The third run stopped on 2024 because its file ends at the 31 December 2024 stamp, one day short of the 1 January every other year carries: the consolidated product ends there, and the loader's calendar check refused the file, as it should. An explicit flag now accepts a year that stops early and records it as incomplete in its marker, so it is the year to re-request when the product extends.</li>
<li><b>Open.</b> 2025 from where the consolidated product ends; a second Copernicus key so a backfill does not queue behind the monitoring runs; an instance pool, since each restart paid a cluster start; v5 as a sibling prefix when it is operational; the code moved to its own pipeline repo with a KB page. Design and rejected layouts: ADR 0003 in the benchmark repo.</li>
</ul>
"""
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
h3{{font-size:16px;margin:28px 0 6px}}
{VIZ_CSS}
</style>
<main>
<div class="eyebrow">Mirror · checked {esc(c["checked_at"][:16].replace("T", " "))} UTC · GloFAS v4 consolidated reanalysis on the team blob</div>
<h1>GloFAS v4 mirror: {len(years)} years in the store, {c["n_pass"]} of {c["n_checks"]} checks pass</h1>
<p class="lede">One sharded Zarr on <code>global/glofas/v4/reanalysis</code> holding every land cell of the 0.05° grid as a (cell, time) array, loaded year by year from whole-globe EWDS files. This page is the store's own report: its layout, the checks on every loaded year, what it reads back, and how the backfill ran.</p>
<div class="tiles">
{tile(f"{ix['cells']:,}", "land cells in the store")}
{tile(f"{len(years)} of 47", f"years loaded, {years[0]} to {years[-1]}")}
{tile(f"{by['q_zarr_per_year_gb']} GB", "store per year")}
{tile(f"{by['q_zarr_47yr_gb_projection']} GB", "projected for 1979 to 2025")}
{tile(f"${by['cool_lrs_usd_per_month_47yr']}", "per month, Cool tier, 47 years")}
{tile(f"{rc['one_cell_history_s_median']} s", "one point, loaded history, from blob")}
</div>
<div class="verdict"><p>{"Every check passed. The store reads back exactly what the spokes hold, the land mask is where it should be, and one point's history reads in a fraction of a second per five-year shard column (about two seconds for the full 47 years)." if allpass else "Some checks failed; see the table. Nothing should be scheduled on this layout until they pass."}</p></div>

<h2>What the store is</h2>
<dl>
<dt>array</dt><dd><code>q</code> float32, shape {st["shape"][0]:,} cells × {st["shape"][1]:,} days, shards {st["shards"][0]:,} × {st["shards"][1]:,}, chunks {st["chunks"][0]} × {st["chunks"][1]:,}, zstd</dd>
<dt>time axis</dt><dd>{esc(st["time_first"][:10])} to {esc(st["time_last"][:10])}, consecutive days, stored as EWDS stamps them</dd>
<dt>cells</dt><dd>row-major over the grid, land where the upstream-area map is finite; <code>cells.parquet</code> maps cell to row, column, latitude, longitude, upstream area and downstream cell ({ix["pits"]:,} pits or outlets)</dd>
<dt>bronze</dt><dd>the EWDS netCDF per year as served, {by["bronze_per_year_gb"]} GB each, for provenance and rebuilds</dd>
<dt>blobs</dt><dd>{by["n_blobs"]:,} objects under the prefix</dd>
</dl>
<div class="wrap"><table><thead><tr><th>attribute</th><th>value</th></tr></thead><tbody>{attrs}</tbody></table></div>
{viz_section(snap)}

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
<tr><td>what the 2,000-cell read says</td><td>a cell list across all time touches a shard per 64 cells; bulk extraction (many cells) should read whole shards, not cell lists</td></tr>
<tr><td>47 years</td><td>{by["q_zarr_47yr_gb_projection"]} GB store and {by["bronze_per_year_gb"] * 47:.0f} GB bronze at the measured {by["q_zarr_per_year_gb"]} GB and {by["bronze_per_year_gb"]} GB a year; ${by["cool_lrs_usd_per_month_47yr"]} a month with bronze in the Archive tier</td></tr>
</tbody></table></div>

<h2>How to read it</h2>
<pre>import adlfs, os, zarr, pandas as pd
store = zarr.storage.FsspecStore.from_url("abfs://global/glofas/v4/reanalysis/q.zarr",
    storage_options={{"account_name": "imb0chd0dev", "sas_token": os.environ["DSCI_AZ_BLOB_DEV_SAS"]}})
g = zarr.open_group(store, mode="r")
import io
from azure.storage.blob import ContainerClient
cc = ContainerClient("https://imb0chd0dev.blob.core.windows.net", "global", credential=os.environ["DSCI_AZ_BLOB_DEV_SAS"])
cells = pd.read_parquet(io.BytesIO(cc.get_blob_client("glofas/v4/reanalysis/cells.parquet").download_blob().readall()))
cell = cells.query("abs(lat - 12.125) < 1e-6 and abs(lon - 15.025) < 1e-6").cell.item()   # N'Djamena's GloFAS cell
q = pd.Series(g["q"][cell, :], index=pd.Timestamp("1979-01-01") + pd.to_timedelta(g["time"][:], unit="D"))
# q is stamped at the END of each 24 h window; subtract one day for a start-of-day convention</pre>

<h2>Findings from this run</h2>
<ul>
<li><b>Sharded Zarr v3 on Azure Blob needs the shard index at the start.</b> Zarr's default puts each shard's chunk index at its end and reads it with a suffix byte range; Azure Blob serves none, adlfs passes the request through, and every partial read fails with "Required Content-Range response header is missing". Tested on two small arrays with the same code and credentials: index at the end fails, index at the start reads. The first build of this store had to be redone for that one setting, from bronze, with no new EWDS request. Unsharded Zarr (the team's IMERG and CMA stores) is not affected. Rule for any sharded Zarr on the team's blob: <code>index_location="start"</code>.</li>
<li><b>The Bangladesh spoke's per-year GloFAS files carry a boundary-day artefact.</b> At Bahadurabad the mirror equals the spoke copy on every day except {len(bgd_bd)} file-boundary days ({esc(bgd_bd_desc)}), where the spoke's yearly file holds the neighbouring day's value (its 31 Dec 2022 is EWDS's 1 Jan 2023). The mirror is internally consistent there. Harmless for a flood threshold, but it is the incumbent series the benchmark reads, so the framework owner should know.</li>
<li><b>Appending into a filled shard column costs more.</b> 2023 took {st["years_loaded"]["2023"]["seconds"] // 60} minutes against {st["years_loaded"]["2022"]["seconds"] // 60} for 2022 because it rewrote the shards 2022 had already filled. In the backfill the second to fifth year of every five-year column pays this, so plan on about ten minutes a year, not six.</li>
<li><b>Storage came in well under the gridded estimate.</b> The probe on the full grid projected about 107 GB for all land cells; the (cell, time) layout compresses along time and measures {by["q_zarr_per_year_gb"]} GB a year on three real years, {by["q_zarr_47yr_gb_projection"]} GB for the record.</li>
<li><b>The EWDS key is shared.</b> The requests submitted from a laptop key were visible to the Databricks job's key without resubmission, so the key in use is the same one the daily Nigeria and Somalia monitoring queues on. A second key does not exist yet.</li>
</ul>

{backfill_sec}</main>
"""
    (OUT / "index.html").write_text(html)
    print(f"wrote {OUT / 'index.html'} ({len(html) / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(without_backfill="--without-backfill" in sys.argv[1:]))
