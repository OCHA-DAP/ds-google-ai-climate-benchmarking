"""The "what the store looks like" section of the mirror page: an anatomy diagram drawn from the
store's own numbers, a basin map drawn cell by cell from the index and two read days, full point
histories, and one cell folded year by day. Data comes from outputs/glofas_mirror/snapshots.json
(scripts/glofas_mirror_snapshots.py); the drawing runs in the page, without libraries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charts import esc

CSS = """
.viz{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:10px 12px 8px;position:relative}
.viz canvas{width:100%;height:auto;display:block;touch-action:none} #map{max-width:620px}
.viz input[type=range]{width:150px;vertical-align:middle;accent-color:var(--accent)}
.viz .num{font-family:var(--mono);color:var(--fg)}
.viz .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--muted);margin:0 0 8px}
.viz button{font:inherit;font-size:13px;color:var(--fg);background:transparent;border:1px solid var(--line);border-radius:3px;padding:3px 10px;cursor:pointer}
.viz button[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.viz .ramp{display:inline-block;width:120px;height:10px;vertical-align:middle;border:1px solid var(--line);margin:0 6px}
.tip{position:absolute;pointer-events:none;background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:3px;padding:6px 9px;font-size:12px;font-family:var(--mono);white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.15);display:none;z-index:2}
.viz .sub{font-size:13px;color:var(--muted);margin:6px 0 0}
.diagram svg{max-width:100%;height:auto;display:block}
:root{--r0:#e3f1f5;--r1:#a9d4e2;--r2:#5fb0ca;--r3:#2a84a3;--r4:#0f4f66;--trace:#b2561a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--r0:#163a46;--r1:#1f5f74;--r2:#3a8ca6;--r3:#74bdd4;--r4:#c6e6ef;--trace:#e39a60}}
:root[data-theme="dark"]{--r0:#163a46;--r1:#1f5f74;--r2:#3a8ca6;--r3:#74bdd4;--r4:#c6e6ef;--trace:#e39a60}
"""


def anatomy_svg(an: dict, years_loaded: list[int]) -> str:
    """Grid -> land cells -> the (cell, time) array with its shard columns, and the two reads."""
    W, H = 1100, 330
    y0 = int(an["time_first"][:4])
    ncols = an["shard_cols"]
    years_per_col = round(an["shard"][1] / 365.25)
    # shading per column: share of its years that are loaded
    shade = []
    for k in range(ncols):
        ys = range(
            y0 + k * years_per_col, min(y0 + (k + 1) * years_per_col, int(an["time_last"][:4]) + 1)
        )
        ys = [
            y
            for y in ys
            if y <= int(an["time_last"][:4]) - (1 if an["time_last"][5:] == "01-01" else 0)
        ]
        shade.append(sum(y in years_loaded for y in ys) / max(len(ys), 1))
    o = [
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="The store: the 0.05 degree grid keeps only its land cells, laid row-major along one axis of a cell by time array sharded into five-year columns; a point history reads one chunk per column, a day map reads every shard row" font-family="var(--body)" font-size="12" fill="currentColor">',
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>',
        # the grid
        '<rect x="20" y="60" width="168" height="70" fill="none" stroke="currentColor" stroke-width="1.2"/>',
        '<text x="104" y="48" text-anchor="middle" font-weight="600">0.05° grid</text>',
        f'<text x="104" y="150" text-anchor="middle" fill="var(--muted)">{an["grid"][0]:,} × {an["grid"][1]:,} = {an["grid"][0] * an["grid"][1] / 1e6:.1f} M cells</text>',
        f'<text x="104" y="166" text-anchor="middle" fill="var(--muted)">{an["land_share"]:.1%} land</text>',
    ]
    # a few land blobs inside the grid
    for x, y, w, h in ((30, 70, 50, 30), (90, 66, 40, 22), (70, 100, 70, 24), (140, 80, 40, 40)):
        o.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="var(--accent)" opacity=".5"/>'
        )
    o += [
        '<line x1="196" y1="95" x2="256" y2="95" stroke="currentColor" stroke-width="1.2" marker-end="url(#ah)"/>',
        '<text x="226" y="84" text-anchor="middle" fill="var(--muted)">keep land</text>',
        '<text x="226" y="112" text-anchor="middle" fill="var(--muted)">row-major</text>',
        # the cell axis
        '<rect x="268" y="40" width="22" height="220" fill="var(--accent)" opacity=".5" stroke="currentColor" stroke-width="1.2"/>',
        '<text x="279" y="28" text-anchor="middle" font-weight="600">cell</text>',
        f'<text x="279" y="278" text-anchor="middle" fill="var(--muted)">{an["cells"]:,}</text>',
        '<text x="279" y="294" text-anchor="middle" fill="var(--muted)">cells.parquet:</text>',
        '<text x="279" y="308" text-anchor="middle" fill="var(--muted)">row col lat lon</text>',
        '<text x="279" y="322" text-anchor="middle" fill="var(--muted)">uparea downstream</text>',
        '<line x1="298" y1="150" x2="340" y2="150" stroke="currentColor" stroke-width="1.2" marker-end="url(#ah)"/>',
    ]
    # the array: AX..AX+AW by AY..AY+AH, columns = shard columns
    AX, AY, AW, AH = 350, 40, 600, 220
    cw = AW / ncols
    for k in range(ncols):
        o.append(
            f'<rect x="{AX + k * cw:.1f}" y="{AY}" width="{cw:.1f}" height="{AH}" fill="var(--accent)" opacity="{0.08 + 0.42 * shade[k]:.2f}" stroke="currentColor" stroke-width="1"/>'
        )
        o.append(
            f'<text x="{AX + k * cw + cw / 2:.1f}" y="{AY + AH + 16}" text-anchor="middle" fill="var(--muted)" font-family="var(--mono)" font-size="11">{y0 + k * years_per_col}</text>'
        )
    # shard rows: draw a few lines then a break
    for i in range(1, 6):
        yy = AY + i * 18
        o.append(
            f'<line x1="{AX}" y1="{yy}" x2="{AX + AW}" y2="{yy}" stroke="currentColor" stroke-width=".6" opacity=".6"/>'
        )
    o.append(
        f'<text x="{AX + AW / 2:.1f}" y="{AY + 140}" text-anchor="middle" fill="var(--muted)">⋮  {an["shard_rows"]:,} shard rows of {an["shard"][0]:,} cells</text>'
    )
    o.append(
        f'<text x="{AX + AW / 2:.1f}" y="{AY - 12}" text-anchor="middle" font-weight="600">q (cell, time) float32 · {an["shard_cols"]} shard columns of {an["shard"][1]:,} days</text>'
    )
    # one shard inset: inner chunks
    o.append(
        f'<rect x="{AX + 2 * cw + 8:.1f}" y="{AY + 160}" width="{cw - 16:.1f}" height="44" fill="var(--panel)" stroke="currentColor" stroke-width="1"/>'
    )
    for i in range(1, 8):
        yy = AY + 160 + i * 44 / 8
        o.append(
            f'<line x1="{AX + 2 * cw + 8:.1f}" y1="{yy:.1f}" x2="{AX + 3 * cw - 8:.1f}" y2="{yy:.1f}" stroke="currentColor" stroke-width=".5"/>'
        )
    o.append(
        f'<text x="{AX + 3 * cw + 4:.1f}" y="{AY + 178}" fill="var(--muted)">one shard = {an["chunks_per_shard"]} chunks of {an["chunk"][0]} cells × {an["chunk"][1]:,} days</text>'
    )
    o.append(
        f'<text x="{AX + 3 * cw + 4:.1f}" y="{AY + 194}" fill="var(--muted)">{an["chunk_raw_mb"]} MB raw per chunk; index at the shard\'s start</text>'
    )
    # the two reads
    ry = AY + 70
    o.append(
        f'<line x1="{AX - 4}" y1="{ry}" x2="{AX + AW + 4}" y2="{ry}" stroke="var(--accent)" stroke-width="3"/>'
    )
    o.append(
        f'<text x="{AX + AW + 8}" y="{ry + 4}" fill="var(--accent)" font-weight="600">one point\'s history</text>'
    )
    o.append(
        f'<text x="{AX + AW + 8}" y="{ry + 18}" fill="var(--muted)">{an["point_history_fetches"]} fetches, one per column</text>'
    )
    rx = AX + 8.5 * cw
    o.append(
        f'<line x1="{rx:.1f}" y1="{AY - 4}" x2="{rx:.1f}" y2="{AY + AH + 4}" stroke="var(--trace)" stroke-width="3"/>'
    )
    o.append(
        f'<text x="{rx + 6:.1f}" y="{AY + AH - 20}" fill="var(--trace)" font-weight="600">one day, everywhere</text>'
    )
    o.append(
        f'<text x="{rx + 6:.1f}" y="{AY + AH - 6}" fill="var(--muted)">{an["one_day_map_chunks"]:,} chunks, every shard row</text>'
    )
    o.append(
        f'<text x="{AX}" y="{AY + AH + 34}" fill="var(--muted)">time: {an["time_first"]} to {an["time_last"]}, {an["days"]:,} days, as EWDS stamps them · column shade = share of its years loaded</text>'
    )
    o.append("</svg>")
    return "".join(o)


def section(snap: dict) -> str:
    an, mp, hs, hm = snap["anatomy"], snap["map"], snap["hydrographs"], snap["heatmap"]
    nw, ca = snap["network"], snap["map"]["catchment"]
    yl = snap["years_loaded"]
    data = json.dumps(snap, separators=(",", ":")).replace("</", "<\\/")
    st_rows = "".join(
        f"<tr><td>{esc(s['name'])}</td><td>{s['cell']:,}</td><td>{s['uparea_km2']:,}</td></tr>"
        for s in mp["stations"]
    )
    hyd_divs = "".join(
        f'<div class="viz"><div class="bar"><b style="color:var(--fg)">{esc(h["station"])}</b> · cell {h["cell"]:,} · {h["uparea_km2"]:,} km² upstream · read in {h["read_s"]} s</div>'
        f'<canvas class="hyd" data-i="{i}" width="1100" height="200"></canvas><div class="tip"></div></div>'
        for i, h in enumerate(hs)
    )
    traces = "; ".join(f"{t['from']} to the outlet, {t['cells']:,} cells" for t in mp["traces"])
    return f"""
<h2>What the store looks like</h2>
<p>Five views drawn from the store itself, not from a figure made elsewhere. The diagram is the layout; the river network is the index; the map is the costly read; the hydrographs are the cheap one; the last grid is one row of the array.</p>

<figure class="viz diagram">{anatomy_svg(an, yl)}
<figcaption class="sub">The 0.05° grid keeps only its {an["cells"]:,} land cells, in row-major order, as one axis of a (cell, time) array. The array is cut into shards of {an["shard"][0]:,} cells × {an["shard"][1]:,} days ({an["shard_raw_mb"]} MB raw), each holding {an["chunks_per_shard"]} chunks of {an["chunk"][0]} cells. A point's full history is {an["point_history_fetches"]} small fetches; a day across the globe touches {an["one_day_map_chunks"]:,} chunks, which is why maps are made from bronze or from a bounded box, not from this store.</figcaption></figure>

<h3>Upstream area: a property of every cell, and the river network it defines</h3>
<p>Every land cell carries the area that drains into it, <code>uparea_km2</code> in the index, summed over the flow-direction map from that cell up to the ridges. It says nothing about any gauge: a cell on the Jamuna holds about a million km², a hillslope cell holds the cell's own 25 km². Keeping only the cells at or above a threshold keeps the rivers and drops the slopes; this is the subset a reforecast mirror would hold. Each {nw["coarse_deg"]}° square below is coloured by the largest upstream area among its {round(nw["coarse_deg"] / 0.05) ** 2} fine cells, and stays lit while any one of them clears the threshold, so the picture overstates what is kept and the count beside the slider is the exact figure from the index. Move the slider.</p>
<div class="viz" id="netviz"><div class="bar"><label>keep cells with upstream area ≥ <span class="num" id="netthr"></span> km² <input type="range" id="netrange" min="0" max="{len(nw["thresholds"]) - 1}" step="1" value="3"></label><span id="netout"></span></div>
<canvas id="net" width="{nw["cols"]}" height="{nw["rows"]}"></canvas><div class="tip"></div>
<p class="sub">Store sizes are for a reforecast store of every issue date, 11 members and leads 1 to 15 at the reanalysis store's measured compression, and for the reanalysis store as built.</p></div>

<h3>{esc(mp["name"])}: the cells, their upstream area, and two days of discharge</h3>
<p>{mp["rows"]} rows × {mp["cols"]} columns of the grid, {mp["land_cells"]:,} land cells, from latitude {mp["lat"][0]:.3f} to {mp["lat"][1]:.3f} and longitude {mp["lon"][0]:.3f} to {mp["lon"][1]:.3f}. The upstream-area layer is the index alone; the discharge layers are one read of the store for {mp["land_cells"]:,} cells on {mp["dates"][0]} and {mp["dates"][1]} ({mp["read_s"]} s, {mp["chunks_touched"]:,} chunks in {mp["shards_touched"]} shards). The lines trace <code>downstream_cell</code> from {esc(traces)}. The other meaning of upstream is the fourth layer: the {ca["cells"]:,} cells of the box whose downstream chain reaches {esc(ca["to"])}, its catchment as far as the box shows it; the Shabelle's head lies beyond the box in Ethiopia. The slider greys out cells below the threshold on the upstream-area layer. Hover or touch a cell.</p>
<div class="viz" id="mapviz"><div class="bar">
<button data-layer="up" aria-pressed="true">upstream area</button><button data-layer="q0">discharge {mp["dates"][0]}</button><button data-layer="q1">discharge {mp["dates"][1]}</button><button data-layer="catch">drains to {esc(ca["to"])}</button>
<label>≥ <span class="num" id="mapthr"></span> km² <input type="range" id="maprange" min="0" max="{len(nw["thresholds"]) - 1}" step="1" value="0"></label>
<span><i class="ramp" id="ramp"></i><span id="rampl"></span></span><span><i style="display:inline-block;width:22px;border-top:2px solid var(--trace);vertical-align:middle;margin-right:5px"></i>downstream trace</span><span><i style="display:inline-block;width:9px;height:9px;border:2px solid var(--fg);border-radius:50%;background:var(--panel);vertical-align:middle;margin-right:5px"></i>framework point</span>
</div><canvas id="map" width="{mp["cols"] * 4}" height="{mp["rows"] * 4}"></canvas><div class="tip"></div></div>
<div class="wrap"><table><thead><tr><th>framework point</th><th>cell</th><th>upstream km²</th></tr></thead><tbody>{st_rows}</tbody></table></div>

<h3>Full point histories, every loaded year</h3>
<p>One cell each, the whole time axis in one read: this is the query the layout exists for. Years without a load marker are left blank, not bridged. Hover for the day and value; the small marks are each year's maximum.</p>
{hyd_divs}

<h3>One cell as the array holds it</h3>
<p>{esc(hm["station"])}, cell {hm["cell"]:,}: its row of <code>q</code> folded into one line per year, day 1 on the left (2 January, as EWDS stamps the window end) to day 365 or 366 on the right. The monsoon is the dark band; the blank rows are the years not yet loaded{(" (" + ", ".join(str(y) for y in snap["years_missing"]) + ")") if snap["years_missing"] else ""}.</p>
<div class="viz" id="hmviz"><div class="bar"><span><i class="ramp" id="ramp2"></i><span id="ramp2l"></span></span></div><canvas id="hm" width="1146" height="{6 * len(hm["rows"])}"></canvas><div class="tip"></div></div>

<script id="snap" type="application/json">{data}</script>
<script>
(() => {{
const S = JSON.parse(document.getElementById('snap').textContent);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const ramp = () => ['--r0','--r1','--r2','--r3','--r4'].map(css);
const hex = h => [1,3,5].map(i => parseInt(h.slice(i, i+2), 16));
function colour(t, R) {{ // t in [0,1] along the five ramp stops
  const x = Math.min(Math.max(t, 0), 1) * 4, i = Math.min(Math.floor(x), 3), f = x - i;
  const a = hex(R[i]), b = hex(R[i+1]);
  return `rgb(${{a.map((v,k) => Math.round(v + (b[k]-v)*f)).join(',')}})`;
}}
function setRamp(el, label, lab, R) {{
  el.style.background = `linear-gradient(90deg,${{R.join(',')}})`; lab.textContent = label;
}}
function showTip(viz, tip, ev, html) {{
  const r = viz.getBoundingClientRect();
  tip.innerHTML = html; tip.style.display = 'block';
  let x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14;
  if (x + tip.offsetWidth > r.width - 8) x = ev.clientX - r.left - tip.offsetWidth - 14;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}}
const fmt = v => v == null ? 'no data' : (v >= 100 ? Math.round(v).toLocaleString() : v.toPrecision(3)) + ' m³/s';
const dayToDate = (t0, i) => {{ const d = new Date(t0 + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + i); return d.toISOString().slice(0,10); }};

// ---- river network by threshold (index only)
const N = S.network, TH = N.thresholds, nv = document.getElementById('netviz'), ncv = document.getElementById('net'), ntip = nv.querySelector('.tip');
const NB = Uint8Array.from(atob(N.max_log10_uparea_u8), ch => ch.charCodeAt(0));
const nLog = b => N.log_lo + b / N.log_per;   // byte -> log10 km²
const allCells = N.counts['0'], GB_RF = 1800, GB_RA = 53;   // reforecast leads 1-15 at the reanalysis ratio; the reanalysis store
const netRange = document.getElementById('netrange');
function drawNet() {{
  const R = ramp(), ctx = ncv.getContext('2d'), s = 1, thr = TH[+netRange.value], lthr = Math.log10(Math.max(thr, 1)), dim = css('--line');
  ctx.clearRect(0, 0, ncv.width, ncv.height);
  for (let r = 0; r < N.rows; r++) for (let c = 0; c < N.cols; c++) {{
    const b = NB[r * N.cols + c]; if (!b) continue;
    const l = nLog(b);
    ctx.fillStyle = (thr === 0 || l >= lthr) ? colour((l - 1) / 6, R) : dim; ctx.fillRect(c*s, r*s, s, s);
  }}
  const k = N.counts[String(thr)], share = k / allCells;
  document.getElementById('netthr').textContent = thr.toLocaleString();
  document.getElementById('netout').innerHTML = `<span class="num">${{k.toLocaleString()}}</span> cells, ${{(100*share).toFixed(share < 0.1 ? 1 : 0)}}% of land · reforecast store ≈ <span class="num">${{Math.round(GB_RF*share).toLocaleString()}} GB</span> · reanalysis store ≈ <span class="num">${{(GB_RA*share).toFixed(1)}} GB</span>`;
}}
netRange.addEventListener('input', drawNet);
ncv.addEventListener('pointermove', ev => {{
  const bx = ncv.getBoundingClientRect(), c = Math.floor((ev.clientX - bx.left) / bx.width * N.cols), r = Math.floor((ev.clientY - bx.top) / bx.height * N.rows);
  const b = (r >= 0 && c >= 0 && r < N.rows && c < N.cols) ? NB[r * N.cols + c] : 0;
  if (!b) {{ ntip.style.display = 'none'; return; }}
  showTip(nv, ntip, ev, `lat ${{(N.lat0 - (r + 0.5) * N.coarse_deg).toFixed(2)}} lon ${{(N.lon0 + (c + 0.5) * N.coarse_deg).toFixed(2)}}<br>largest upstream area in this ${{N.coarse_deg}}° square: ${{Math.round(10**nLog(b)).toLocaleString()}} km²`);
}});
ncv.addEventListener('pointerleave', () => ntip.style.display = 'none');

// ---- map
const M = S.map, mv = document.getElementById('mapviz'), mc = document.getElementById('map'), mtip = mv.querySelector('.tip');
let layer = 'up';
const mapRange = document.getElementById('maprange');
const CATCH = new Set(M.catchment.rc.map(([r, c]) => r * M.cols + c));
const q0 = M.q[0], q1 = M.q[1];
const lq = v => Math.log10(1 + v), qmaxL = lq(M.qmax);
function drawMap() {{
  const R = ramp(), ctx = mc.getContext('2d'), s = 4;
  ctx.clearRect(0, 0, mc.width, mc.height);
  const g = (layer === 'up' || layer === 'catch') ? M.log10_uparea : (layer === 'q0' ? q0 : q1);
  const scale = (layer === 'up' || layer === 'catch') ? (v => (v - 1) / (7 - 1)) : (v => lq(v) / qmaxL);
  const thr = TH[+mapRange.value], lthr = Math.log10(Math.max(thr, 1)), dim = css('--line'), acc = css('--accent');
  document.getElementById('mapthr').textContent = thr.toLocaleString();
  for (let r = 0; r < M.rows; r++) for (let c = 0; c < M.cols; c++) {{
    const v = g[r][c]; if (v == null) continue;
    let f = colour(scale(v), R);
    if (layer === 'up' && thr > 0 && v < lthr) f = dim;
    if (layer === 'catch') f = CATCH.has(r * M.cols + c) ? acc : dim;
    ctx.fillStyle = f; ctx.fillRect(c*s, r*s, s, s);
  }}
  ctx.strokeStyle = css('--trace'); ctx.lineWidth = 2.5; ctx.lineJoin = 'round';
  for (const t of M.traces) {{ ctx.beginPath(); t.path.forEach(([r,c],i) => ctx[i?'lineTo':'moveTo'](c*s+s/2, r*s+s/2)); ctx.stroke(); }}
  for (const p of M.stations) {{
    ctx.beginPath(); ctx.arc(p.c*s+s/2, p.r*s+s/2, 6, 0, 7); ctx.fillStyle = css('--panel'); ctx.fill(); ctx.strokeStyle = css('--fg'); ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = css('--fg'); ctx.font = '600 13px ' + css('--body'); ctx.fillText(p.name, p.c*s + 11, p.r*s + 5);
  }}
  setRamp(document.getElementById('ramp'), layer === 'catch' ? `${{M.catchment.cells.toLocaleString()}} cells drain to ${{M.catchment.to}} (accent); the rest of the box grey` : (layer === 'up' ? 'upstream area 10 to 10⁷ km², log' : 'discharge 0 to ' + Math.round(M.qmax).toLocaleString() + ' m³/s, log'), document.getElementById('rampl'), R);
}}
mv.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {{
  layer = b.dataset.layer; mv.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); drawMap();
}}));
mapRange.addEventListener('input', drawMap);
function cellId(r, c) {{ const f = M.row_cell0[r]; if (f == null) return null; let n = 0; for (let k = 0; k < c; k++) if (M.log10_uparea[r][k] != null) n++; return f + n; }}
mc.addEventListener('pointermove', ev => {{
  const b = mc.getBoundingClientRect(), c = Math.floor((ev.clientX - b.left) / b.width * M.cols), r = Math.floor((ev.clientY - b.top) / b.height * M.rows);
  if (r < 0 || c < 0 || r >= M.rows || c >= M.cols || M.log10_uparea[r][c] == null) {{ mtip.style.display = 'none'; return; }}
  const lat = (M.lat[0] - r * 0.05).toFixed(3), lon = (M.lon[0] + c * 0.05).toFixed(3);
  showTip(mv, mtip, ev, `cell ${{cellId(r,c).toLocaleString()}} · row ${{r}} col ${{c}} of the box<br>lat ${{lat}} lon ${{lon}}<br>upstream ${{Math.round(10**M.log10_uparea[r][c]).toLocaleString()}} km²${{CATCH.has(r * M.cols + c) ? ' · drains to ' + M.catchment.to : ''}}<br>${{M.dates[0]}}: ${{fmt(q0[r][c])}}<br>${{M.dates[1]}}: ${{fmt(q1[r][c])}}`);
}});
mc.addEventListener('pointerleave', () => mtip.style.display = 'none');

// ---- hydrographs
document.querySelectorAll('canvas.hyd').forEach(cv => {{
  const h = S.hydrographs[+cv.dataset.i], viz = cv.parentElement, tip = viz.querySelector('.tip');
  const W = cv.width, H = cv.height, L = 58, Rr = 12, T = 12, B = 24, pw = W - L - Rr, ph = H - T - B;
  const n = h.values.length, vmax = Math.max(...h.values.filter(v => v != null)) * 1.05;
  const X = i => L + i / (n - 1) * pw, Y = v => T + ph - v / vmax * ph;
  const y0 = +h.t0.slice(0,4);
  function draw(hi) {{
    const ctx = cv.getContext('2d'); ctx.clearRect(0,0,W,H);
    ctx.font = '11px ' + css('--mono'); ctx.fillStyle = css('--muted'); ctx.strokeStyle = css('--line'); ctx.lineWidth = 1;
    for (let k = 0; k <= 4; k++) {{ const v = vmax * k / 4, y = Y(v); ctx.beginPath(); ctx.moveTo(L, y); ctx.lineTo(W - Rr, y); ctx.stroke(); ctx.textAlign = 'right'; ctx.fillText(Math.round(v).toLocaleString(), L - 6, y + 4); }}
    ctx.textAlign = 'left';
    for (let y = y0; y <= y0 + 47; y += 5) {{ const i = Math.round((Date.UTC(y,0,1) - Date.UTC(y0,0,1)) / 864e5) - 1; if (i < 0 || i >= n) continue; const x = X(i); ctx.beginPath(); ctx.moveTo(x, T); ctx.lineTo(x, T + ph); ctx.stroke(); ctx.fillText(y, x + 3, H - 8); }}
    ctx.strokeStyle = css('--accent'); ctx.lineWidth = 1.2; ctx.beginPath(); let pen = false;
    for (let i = 0; i < n; i++) {{ const v = h.values[i]; if (v == null) {{ pen = false; continue; }} const x = X(i), y = Y(v); if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y); pen = true; }}
    ctx.stroke();
    ctx.fillStyle = css('--trace');
    for (const [y, v] of Object.entries(h.annual_max)) {{ if (v == null) continue; const i = Math.round((Date.UTC(+y,6,1) - Date.UTC(y0,0,1)) / 864e5); ctx.beginPath(); ctx.arc(X(i), Y(v), 2.5, 0, 7); ctx.fill(); }}
    if (hi != null) {{ ctx.strokeStyle = css('--fg'); ctx.lineWidth = 1; ctx.setLineDash([3,3]); ctx.beginPath(); ctx.moveTo(X(hi), T); ctx.lineTo(X(hi), T + ph); ctx.stroke(); ctx.setLineDash([]); if (h.values[hi] != null) {{ ctx.beginPath(); ctx.arc(X(hi), Y(h.values[hi]), 4, 0, 7); ctx.fillStyle = css('--accent'); ctx.fill(); }} }}
  }}
  draw(null);
  cv.addEventListener('pointermove', ev => {{ const b = cv.getBoundingClientRect(); const i = Math.round(((ev.clientX - b.left) / b.width * W - L) / pw * (n - 1)); if (i < 0 || i >= n) {{ tip.style.display = 'none'; draw(null); return; }} draw(i); showTip(viz, tip, ev, `${{dayToDate(h.t0, i)}}<br>${{fmt(h.values[i])}}`); }});
  cv.addEventListener('pointerleave', () => {{ tip.style.display = 'none'; draw(null); }});
  cv._redraw = () => draw(null);
}});

// ---- heatmap
const HM = S.heatmap, hv = document.getElementById('hmviz'), hc = document.getElementById('hm'), htip = hv.querySelector('.tip');
function drawHm() {{
  const R = ramp(), ctx = hc.getContext('2d'), G = 48, sx = 3, sy = 6, lmax = lq(HM.vmax); ctx.clearRect(0,0,hc.width,hc.height);
  HM.rows.forEach((row, r) => row.forEach((v, d) => {{ if (v == null) return; ctx.fillStyle = colour(lq(v) / lmax, R); ctx.fillRect(G + d*sx, r*sy, sx, sy); }}));
  ctx.fillStyle = css('--muted'); ctx.font = '11px ' + css('--mono'); ctx.textAlign = 'right';
  HM.rows.forEach((row, r) => {{ const y = HM.year_first + r; if (y % 5 === 0) ctx.fillText(y, G - 6, r*sy + sy - 1); }});
  setRamp(document.getElementById('ramp2'), 'discharge 0 to ' + Math.round(HM.vmax).toLocaleString() + ' m³/s, log', document.getElementById('ramp2l'), R);
}}
hc.addEventListener('pointermove', ev => {{
  const b = hc.getBoundingClientRect(), d = Math.floor(((ev.clientX - b.left) / b.width * hc.width - 48) / 3), r = Math.floor((ev.clientY - b.top) / b.height * HM.rows.length);
  if (r < 0 || d < 0 || r >= HM.rows.length || d >= 366) {{ htip.style.display = 'none'; return; }}
  const y = HM.year_first + r, v = HM.rows[r][d];
  showTip(hv, htip, ev, `${{y}} · day ${{d+1}} · ${{dayToDate(y + '-01-02', d)}}<br>${{fmt(v)}}`);
}});
hc.addEventListener('pointerleave', () => htip.style.display = 'none');

function all() {{ drawNet(); drawMap(); drawHm(); document.querySelectorAll('canvas.hyd').forEach(c => c._redraw()); }}
all();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', all);
new MutationObserver(all).observe(document.documentElement, {{ attributes: true, attributeFilter: ['data-theme'] }});
}})();
</script>
"""
