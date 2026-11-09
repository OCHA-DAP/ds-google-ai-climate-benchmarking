"""Inline SVG figures for the benchmark page, built from the repo's outputs.

Every figure is a function returning an SVG string. Colours come from the page's CSS tokens
(var(--…)) so they follow the theme. No library: the page loads nothing external.
"""

import csv
import json
import math
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[2] / "outputs") + "/"
INK, QUIET, LINE = "var(--fg)", "var(--muted)", "var(--line)"
C23, C26, PUB = "var(--muted)", "var(--accent)", "var(--fg)"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fnum(x, nd=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    return round(v, nd)


def tone(v, good=0.95, mid=0.9, bad=0.5):
    """Fill for a correlation cell."""
    if v is None:
        return "var(--line)"
    if v >= good:
        return "var(--ok)"
    if v >= mid:
        return "#c9a227"  # amber, used in both themes at 0.85 opacity
    if v >= bad:
        return "var(--warn)"
    return "#b23a3a"


# ----------------------------------------------------------------------------- step 1 heatmap
def fig_proxy_heatmap():
    rows = list(csv.DictReader(open(REPO + "proxy_check.csv")))
    stations = list(dict.fromkeys(r["station"] for r in rows))
    by = {(r["station"], int(r["lead"])): r for r in rows}
    leads = list(range(1, 11))
    x0, y0, cw, rh = 232, 54, 42, 19
    w, h = x0 + cw * len(leads) + 130, y0 + rh * len(stations) + 60
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Seasonal-peak rank correlation of reforecast against reanalysis by station and lead' font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Reforecast tracks reanalysis to a week ahead at 29 of 32 station-seasons</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>Cell = Spearman ρ of seasonal peaks, reforecast vs reanalysis on the same day, 2016–2025. Right: reforecast ÷ reanalysis above the 2-yr level at lead 7.</text>"
    )
    for j, L in enumerate(leads):
        out.append(
            f"<text x='{x0 + j * cw + cw / 2}' y='{y0 - 6}' text-anchor='middle' fill='{QUIET}'>lead {L}</text>"
        )
    out.append(
        f"<text x='{x0 + cw * len(leads) + 12}' y='{y0 - 6}' fill='{QUIET}'>ratio, lead 7</text>"
    )
    prev_fw = None
    for i, st in enumerate(stations):
        y = y0 + i * rh
        fw = by[(st, 1)]["framework"]
        if fw != prev_fw and prev_fw is not None:
            out.append(f"<line x1='8' x2='{w - 8}' y1='{y - 1}' y2='{y - 1}' stroke='{LINE}'/>")
        prev_fw = fw
        label = (
            st.replace("NGA ", "Benue ")
            .replace(" (tributary outlier)", " (tributary)")
            .replace("Benue 1120842550 (Wuroboki)", "Benue Wuroboki 1120842550")
        )
        flag = " *" if by[(st, 1)]["needs_check"] == "True" else ""
        out.append(
            f"<text x='{x0 - 8}' y='{y + 13}' text-anchor='end' fill='{INK}'>{esc(label[:30] + flag)}</text>"
        )
        for j, L in enumerate(leads):
            v = fnum(by[(st, L)]["peak_rho"])
            x = x0 + j * cw
            out.append(
                f"<rect x='{x + 1}' y='{y + 1}' width='{cw - 2}' height='{rh - 2}' rx='2' fill='{tone(v)}' fill-opacity='0.85'/>"
            )
            if v is not None:
                out.append(
                    f"<text x='{x + cw / 2}' y='{y + 13}' text-anchor='middle' fill='#fff' font-size='10'>{v:.2f}</text>"
                )
        r7 = fnum(by[(st, 7)]["ratio_above_rp2"])
        bx = x0 + cw * len(leads) + 12
        if r7 is not None:
            bw = min(r7, 1.2) / 1.2 * 90
            out.append(
                f"<rect x='{bx}' y='{y + 5}' width='{bw:.1f}' height='{rh - 10}' fill='{C26}' fill-opacity='0.7'/>"
            )
            out.append(
                f"<text x='{bx + bw + 4:.1f}' y='{y + 13}' fill='{INK}' font-size='10'>{r7:.2f}</text>"
            )
        else:
            out.append(
                f"<text x='{bx}' y='{y + 13}' fill='{QUIET}' font-size='10'>no days above 2-yr</text>"
            )
    one = x0 + cw * len(leads) + 12 + 1 / 1.2 * 90
    out.append(
        f"<line x1='{one:.1f}' x2='{one:.1f}' y1='{y0}' y2='{y0 + rh * len(stations)}' stroke='{INK}' stroke-dasharray='3 3' stroke-opacity='0.5'/>"
    )
    ly = y0 + rh * len(stations) + 22
    for k, (c, t) in enumerate(
        [
            ("var(--ok)", "ρ ≥ 0.95"),
            ("#c9a227", "0.90 to 0.95"),
            ("var(--warn)", "0.50 to 0.90"),
            ("#b23a3a", "below 0.50"),
        ]
    ):
        out.append(
            f"<rect x='{8 + k * 150}' y='{ly - 10}' width='14' height='12' rx='2' fill='{c}' fill-opacity='0.85'/><text x='{26 + k * 150}' y='{ly}' fill='{QUIET}'>{t}</text>"
        )
    out.append(
        f"<text x='{8}' y='{ly + 18}' fill='{QUIET}'>* basin chosen as the largest river within 10 km, not yet confirmed. Dashed line: ratio 1.0.</text>"
    )
    out.append("</svg>")
    return "".join(out)


# ----------------------------------------------------------------------------- dumbbell helper
INC = "var(--inc)"


def wrap(text, n):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + 1 > n and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = (cur + " " + w_).strip()
    if cur:
        lines.append(cur)
    return lines


def dumbbell(
    title,
    subtitle,
    rows,
    inc_label,
    xmin=0.0,
    xmax=1.0,
    ticks=(0, 0.25, 0.5, 0.75, 1.0),
    label_w=190,
    width=760,
    note=None,
    pub_label="published",
    fmt="{:.2f}",
    inc_color=INC,
    show23=True,
):
    """rows: list of (label, v_incumbent, v26, vpub or None, v23 or None, group_break:bool).

    The segment joins the incumbent (the model the framework ran on) to GRRR 2026: that is the
    comparison. GRRR 2023 is a small grey dot where it is not the incumbent; published values a ring.
    """
    rh = 22
    x0, x1 = label_w + 10, width - 70
    y0 = 58
    h = y0 + rh * len(rows) + (56 if note else 40)
    sx = lambda v: x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)
    out = [
        f"<svg viewBox='0 0 {width} {h}' role='img' aria-label='{esc(title)}' font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>{esc(title)}</text>"
    )
    out.append(f"<text x='8' y='36' fill='{QUIET}'>{esc(subtitle)}</text>")
    for t in ticks:
        out.append(
            f"<line x1='{sx(t):.1f}' x2='{sx(t):.1f}' y1='{y0 - 6}' y2='{y0 + rh * len(rows)}' stroke='{LINE}'/>"
        )
        out.append(
            f"<text x='{sx(t):.1f}' y='{y0 - 10}' text-anchor='middle' fill='{QUIET}' font-size='10'>{t:g}</text>"
        )
    for i, (label, vinc, v26, vpub, v23, brk) in enumerate(rows):
        y = y0 + i * rh + rh / 2
        if brk:
            out.append(
                f"<line x1='8' x2='{width - 8}' y1='{y - rh / 2:.1f}' y2='{y - rh / 2:.1f}' stroke='{LINE}'/>"
            )
        out.append(
            f"<text x='{x0 - 10}' y='{y + 4:.1f}' text-anchor='end' fill='{INK}'>{esc(label)}</text>"
        )
        if vinc is not None and v26 is not None:
            out.append(
                f"<line x1='{sx(vinc):.1f}' x2='{sx(v26):.1f}' y1='{y:.1f}' y2='{y:.1f}' stroke='{QUIET}' stroke-width='2' stroke-opacity='0.6'/>"
            )
        if vpub is not None:
            out.append(
                f"<circle cx='{sx(vpub):.1f}' cy='{y:.1f}' r='7' fill='none' stroke='{PUB}' stroke-width='1.5'/>"
            )
        if show23 and v23 is not None:
            out.append(f"<circle cx='{sx(v23):.1f}' cy='{y:.1f}' r='3.5' fill='{C23}'/>")
        if vinc is not None:
            out.append(f"<circle cx='{sx(vinc):.1f}' cy='{y:.1f}' r='5' fill='{inc_color}'/>")
        if v26 is not None:
            out.append(f"<circle cx='{sx(v26):.1f}' cy='{y:.1f}' r='5' fill='{C26}'/>")
            out.append(
                f"<text x='{x1 + 10}' y='{y + 4:.1f}' fill='{INK}' font-size='10'>{fmt.format(v26)}</text>"
            )
    ly = y0 + rh * len(rows) + 22
    lx = 16
    out.append(
        f"<circle cx='{lx}' cy='{ly - 4}' r='5' fill='{inc_color}'/><text x='{lx + 10}' y='{ly}' fill='{QUIET}'>ran on: {esc(inc_label)}</text>"
    )
    lx += 24 + 6.2 * len(inc_label) + 60
    out.append(
        f"<circle cx='{lx}' cy='{ly - 4}' r='5' fill='{C26}'/><text x='{lx + 10}' y='{ly}' fill='{QUIET}'>GRRR November 2026</text>"
    )
    lx += 150
    if show23:
        out.append(
            f"<circle cx='{lx}' cy='{ly - 4}' r='3.5' fill='{C23}'/><text x='{lx + 10}' y='{ly}' fill='{QUIET}'>GRRR 2023 bucket</text>"
        )
        lx += 130
    out.append(
        f"<circle cx='{lx}' cy='{ly - 4}' r='7' fill='none' stroke='{PUB}' stroke-width='1.5'/><text x='{lx + 12}' y='{ly}' fill='{QUIET}'>{esc(pub_label)}</text>"
    )
    if note:
        out.append(f"<text x='8' y='{ly + 18}' fill='{QUIET}'>{esc(note)}</text>")
    out.append("</svg>")
    return "".join(out)


def _summary():
    return json.load(open(REPO + "rescore_summary.json"))


def fig_som_corr():
    s = _summary()["som_corr"]
    rows = []
    last_river = None
    for r in s:
        river = "Juba" if r["station"] in ("Dollow", "Luuq", "Bardheere", "Bualle") else "Shabelle"
        rows.append(
            (
                f"{r['station']} {r['season']}",
                fnum(r["cinc"]),
                fnum(r["c26"]),
                fnum(r["pub"]),
                fnum(r["c23"]),
                river != last_river and last_river is not None,
            )
        )
        last_river = river
    return dumbbell(
        "Somalia: GRRR 2026 tracks the gauges more closely than the GloFAS v5 leg it would sit beside",
        "Best-lag Spearman ρ of daily reanalysis against the river's reference gauge level, 1998–2023. Juba rows first, then Shabelle.",
        rows,
        "GloFAS v5 (proposal leg)",
        xmin=0.3,
        xmax=1.0,
        ticks=(0.3, 0.5, 0.7, 0.9, 1.0),
        label_w=150,
        note="The proposal votes GloFAS v5, GRRR 2023 and GEOGloWS. Published rings are the spoke's GRRR 2023 table; the grey dot reproduces them.",
    )


def fig_som_pod():
    s = _summary()["som_ep"]
    rows = [
        (
            r["station"],
            fnum(r["podinc"]),
            fnum(r["pod26"]),
            fnum(r["pub_pod"]),
            fnum(r["pod23"]),
            False,
        )
        for r in s
    ]
    a = dumbbell(
        "Somalia: RP3 episodes caught (POD), per gauge",
        "Model episodes at its own RP3 against gauge episodes at the post-2000 RP3 level, 2002–2023, 14-day recession, 7-day tolerance.",
        rows,
        "GloFAS v5 (proposal leg)",
        label_w=110,
        width=760,
    )
    rows = [
        (
            r["station"],
            fnum(r["farinc"]),
            fnum(r["far26"]),
            fnum(r["pub_far"]),
            fnum(r["far23"]),
            False,
        )
        for r in s
    ]
    b = dumbbell(
        "Somalia: false-alarm ratio (FAR), lower is better",
        "Share of model episodes with no gauge episode within 7 days.",
        rows,
        "GloFAS v5 (proposal leg)",
        label_w=110,
        width=760,
    )
    return a + b


def fig_npl():
    s = [r for r in _summary()["npl"] if r["conv"] in ("quantile_full", "dashboard")]
    groups = [("Chatara", "RP2"), ("Chatara", "RP5"), ("Chisapani", "RP2"), ("Chisapani", "RP5")]
    w, h = 760, 318
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Nepal: DHM danger-level crossings matched by each model' font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Nepal: against GloFAS v4, the model the framework runs on, GRRR 2026 matches the same or fewer crossings</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>Bars: share of DHM danger-level crossings matched within 7 days (Chatara 9 crossings to 2012, Chisapani 7 to 2015).</text>"
    )
    out.append(
        f"<text x='8' y='50' fill='{QUIET}'>Number under each bar: false alarms (model events with no crossing within 7 days). Chatara is the live trigger station.</text>"
    )
    gx0, gw, bw, gap = 60, 160, 40, 12
    base, top = 236, 80
    for gi, (st, rp) in enumerate(groups):
        x = gx0 + gi * (gw + 20)
        out.append(
            f"<text x='{x + gw / 2}' y='{base + 48}' text-anchor='middle' fill='{INK}' font-weight='600'>{st} {rp}</text>"
        )
        bars = [
            ("GloFAS v4", INC, "GloFAS v4", None),
            ("GRRR 2026", C26, "GRRR", "2026"),
            ("GRRR 2023", C23, "GRRR", "2023"),
        ]
        for bi, (lab, col, src, rel) in enumerate(bars):
            r = next(q for q in s if q["station"] == st and q["rp"] == rp and q["source"] == src)
            m, n = (r["m26"] if rel == "2026" else r["m23"]).split(" of ")
            fa = r["fa26"] if rel == "2026" else r["fa23"]
            frac = int(m) / int(n)
            bx = x + bi * (bw + gap)
            bh = (base - top) * frac
            out.append(
                f"<rect x='{bx}' y='{base - bh:.1f}' width='{bw}' height='{bh:.1f}' fill='{col}' fill-opacity='{0.6 if rel == '2023' else 0.85}'/>"
            )
            out.append(
                f"<text x='{bx + bw / 2}' y='{base - bh - 4:.1f}' text-anchor='middle' fill='{INK}' font-size='10'>{m} of {n}</text>"
            )
            out.append(
                f"<text x='{bx + bw / 2}' y='{base + 14}' text-anchor='middle' fill='{QUIET}' font-size='10'>{fa} FA</text>"
            )
            out.append(
                f"<text x='{bx + bw / 2}' y='{base + 28}' text-anchor='middle' fill='{QUIET}' font-size='9'>{lab.replace('GRRR ', '').replace('GloFAS v4', 'GloFAS')}</text>"
            )
    out.append(f"<line x1='{gx0 - 10}' x2='{w - 20}' y1='{base}' y2='{base}' stroke='{LINE}'/>")
    out.append(
        f"<text x='8' y='{h - 20}' fill='{QUIET}'>GloFAS v4 at the Copernicus dashboard values the framework uses.</text>"
    )
    out.append(
        f"<text x='8' y='{h - 7}' fill='{QUIET}'>GRRR thresholds: quantile 1 − 1/RP of annual maxima over the full reanalysis (the book's convention).</text>"
    )
    out.append("</svg>")
    return "".join(out)


def fig_nga():
    s = [r for r in _summary()["nga"] if not r["excluded"]]
    lab = lambda r: (
        f"{r['station']} ({r['hybas'].replace('hybas_', '')[-4:]})" if r["note"] else r["station"]
    )
    rows = [
        (
            lab(r),
            fnum(r["peak23"]),
            fnum(r["peak26"]),
            0.76 if r["station"] == "Yidere Bode" else None,
            None,
            False,
        )
        for r in s
    ]
    a = dumbbell(
        "Nigeria: annual-peak rank correlation against GRDC, mixed",
        "Spearman ρ of wet-season (Jul–Nov) annual maxima, reanalysis vs observed discharge; years passing the notebook's completeness filters.",
        rows,
        "GRRR 2023 bucket",
        label_w=150,
        note="The 2026 framework runs on the 2023 bucket, so here the grey is the incumbent. Published: 0.76 at Yidere Bode. Lokoja has two candidate basins, both shown.",
        inc_color=C23,
        show23=False,
    )
    rows = [(lab(r), fnum(r["f1_3_23"]), fnum(r["f1_3_26"]), None, None, False) for r in s]
    b = dumbbell(
        "Nigeria: agreement on 3-yr exceedance years (F1)",
        "Each side flags years above its own empirical 3-yr level; F1 of the two flag sets.",
        rows,
        "GRRR 2023 bucket",
        label_w=150,
        pub_label="(no published figure)",
        inc_color=C23,
        show23=False,
    )
    return a + b


def fig_tcd():
    s = {r["model"].split()[0]: r for r in _summary()["tcd"] if r["kind"] == "hits"}
    g, r = s["GloFAS"], s["GRRR"]
    panels = [
        (
            "Observed 4-yr flood years flagged, of 5",
            0,
            5,
            (0, 1, 2, 3, 4, 5),
            g["hits26"],
            r["hits26"],
            r["hits23"],
            g["pub"],
            "{:.0f}",
        ),
        (
            "Rank correlation of annual peaks (ρ)",
            0.4,
            1.0,
            (0.4, 0.6, 0.8, 1.0),
            g["rho26"],
            r["rho26"],
            r["rho23"],
            None,
            "{:.2f}",
        ),
        (
            "Days the model peak comes before the observed peak",
            0,
            40,
            (0, 10, 20, 30, 40),
            g["early26"],
            r["early26"],
            r["early23"],
            31.4,
            "{:.0f}",
        ),
    ]
    w, rh, y0 = 760, 46, 58
    h = y0 + rh * len(panels) + 60
    x0, x1 = 300, w - 70
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label=\"Chad: N'Djamena, GloFAS v4 against GRRR 2026 on the framework's annex test\" font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Chad: on the framework's annex test, GRRR 2026 flags more of the observed years than GloFAS v4</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>DRE observed level vs model annual peak at N'Djamena, 18 years 2003–2022, each side at its own 4-yr quantile.</text>"
    )
    for i, (label, xmin, xmax, ticks, vinc, v26, v23, vpub, fmt) in enumerate(panels):
        y = y0 + i * rh + rh / 2
        sx = lambda v, xmin=xmin, xmax=xmax: x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)
        out.append(
            f"<text x='{x0 - 12}' y='{y + 4}' text-anchor='end' fill='{INK}'>{esc(label)}</text>"
        )
        out.append(f"<line x1='{x0}' x2='{x1}' y1='{y}' y2='{y}' stroke='{LINE}'/>")
        for t in ticks:
            out.append(
                f"<line x1='{sx(t):.1f}' x2='{sx(t):.1f}' y1='{y - 4}' y2='{y + 4}' stroke='{LINE}'/>"
            )
            out.append(
                f"<text x='{sx(t):.1f}' y='{y + 17}' text-anchor='middle' fill='{QUIET}' font-size='9'>{t:g}</text>"
            )
        out.append(
            f"<line x1='{sx(vinc):.1f}' x2='{sx(v26):.1f}' y1='{y}' y2='{y}' stroke='{QUIET}' stroke-width='2' stroke-opacity='0.6'/>"
        )
        if vpub is not None:
            out.append(
                f"<circle cx='{sx(vpub):.1f}' cy='{y}' r='7' fill='none' stroke='{PUB}' stroke-width='1.5'/>"
            )
        out.append(f"<circle cx='{sx(v23):.1f}' cy='{y}' r='3.5' fill='{C23}'/>")
        out.append(f"<circle cx='{sx(vinc):.1f}' cy='{y}' r='5' fill='{INC}'/>")
        out.append(f"<circle cx='{sx(v26):.1f}' cy='{y}' r='5' fill='{C26}'/>")
        out.append(
            f"<text x='{x1 + 10}' y='{y + 4}' fill='{INK}' font-size='10'>{fmt.format(v26)}</text>"
        )
    ly = y0 + rh * len(panels) + 18
    out.append(
        f"<circle cx='16' cy='{ly - 4}' r='5' fill='{INC}'/><text x='26' y='{ly}' fill='{QUIET}'>ran on: GloFAS v4</text>"
    )
    out.append(
        f"<circle cx='150' cy='{ly - 4}' r='5' fill='{C26}'/><text x='160' y='{ly}' fill='{QUIET}'>GRRR November 2026</text>"
    )
    out.append(
        f"<circle cx='300' cy='{ly - 4}' r='3.5' fill='{C23}'/><text x='310' y='{ly}' fill='{QUIET}'>GRRR 2023 bucket</text>"
    )
    out.append(
        f"<circle cx='430' cy='{ly - 4}' r='7' fill='none' stroke='{PUB}' stroke-width='1.5'/><text x='442' y='{ly}' fill='{QUIET}'>published (document annex)</text>"
    )
    out.append(
        f"<text x='8' y='{ly + 18}' fill='{QUIET}'>GloFAS v4 through this code reproduces the annex exactly (3 of 5, 31 days early). The 2023 bucket flagged all five, 20 days early;</text>"
    )
    out.append(
        f"<text x='8' y='{ly + 32}' fill='{QUIET}'>the 2026 release misses 2010 and adds 2018.</text>"
    )
    out.append("</svg>")
    return "".join(out)


def fig_bgd():
    s = _summary()["bgd"]
    w, h = 760, 272
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Bangladesh: FFWC severe floods matched by GloFAS v4 and GRRR' font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Bangladesh: GloFAS v4 and GRRR match the same 3 of 7 FFWC severe floods; GRRR 2026 adds false alarms</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>Observed events: water level at or above danger level + 0.85 m for 3 days: 1988, 2012, 2016, 2017, 2019, 2020 twice.</text>"
    )
    out.append(
        f"<text x='8' y='50' fill='{QUIET}'>Model events: reanalysis above its RP5, 7-day gap, matched within 7 days. The framework runs on GloFAS (v3.1-calibrated, v4 live).</text>"
    )
    gx0, bw, gap = 90, 56, 22
    base, top = 196, 82
    groups = [
        (
            "RP5 as quantile of own annual maxima",
            [
                ("glofas_v4", "GloFAS v4", INC),
                ("2026", "GRRR 2026", C26),
                ("2023", "GRRR 2023", C23),
            ],
            "quantile_full",
        ),
        (
            "RP5 from the release table",
            [("2026", "GRRR 2026", C26), ("2023", "GRRR 2023", C23)],
            "shipped",
        ),
    ]
    x = gx0
    for title, bars, conv in groups:
        gw = len(bars) * (bw + gap) - gap
        out.append(
            f"<text x='{x + gw / 2}' y='{base + 44}' text-anchor='middle' fill='{INK}' font-weight='600'>{title}</text>"
        )
        for bi, (rel, lab, col) in enumerate(bars):
            r = next(q for q in s if q["conv"] == conv and q["release"] == rel)
            frac = int(r["matched"]) / int(r["n_ref"])
            bx = x + bi * (bw + gap)
            bh = (base - top) * frac
            out.append(
                f"<rect x='{bx}' y='{base - bh:.1f}' width='{bw}' height='{bh:.1f}' fill='{col}' fill-opacity='{0.6 if rel == '2023' else 0.85}'/>"
            )
            out.append(
                f"<text x='{bx + bw / 2}' y='{base - bh - 4:.1f}' text-anchor='middle' fill='{INK}' font-size='10'>{r['matched']} of {r['n_ref']}</text>"
            )
            out.append(
                f"<text x='{bx + bw / 2}' y='{base + 14}' text-anchor='middle' fill='{QUIET}' font-size='10'>{r['fa']} FA</text>"
            )
            out.append(
                f"<text x='{bx + bw / 2}' y='{base + 28}' text-anchor='middle' fill='{QUIET}' font-size='9'>{lab.replace('GRRR ', '').replace('GloFAS v4', 'GloFAS')}</text>"
            )
        x += gw + 90
    out.append(f"<line x1='{gx0 - 10}' x2='{w - 20}' y1='{base}' y2='{base}' stroke='{LINE}'/>")
    out.append(
        f"<text x='8' y='{h - 8}' fill='{QUIET}'>No published detection figure for this station. GloFAS v4 from the spoke's station files on the shared drive, 1979–2022.</text>"
    )
    out.append("</svg>")
    return "".join(out)


FRAMEWORK_LEADS = [  # framework, station prefixes in proxy_check.csv, action lead, readiness lead, note
    ("Nigeria 2026", ["NGA "], 5, 12, "GRRR action, GloFAS readiness"),
    (
        "Somalia",
        ["Dollow", "Luuq", "Bardheere", "Bualle", "Belet Weyne", "Bulo Burti", "Jowhar"],
        6,
        12,
        "GRRR Gu, GloFAS Deyr and readiness",
    ),
    ("Nepal 2025", ["Chatara"], None, 7, "GloFAS readiness, DHM action"),
    ("Chad 2025", ["N'Djamena"], 10, 14, "GloFAS, both windows"),
    ("Bangladesh 2025", ["Bahadurabad", "Mawa"], 5, 15, "GloFAS readiness, FFWC action"),
    ("Niger 2025", ["Niamey"], 0, None, "observed gauge, no forecast"),
    ("Uganda (dev)", ["Akokoro"], 5, None, "GloFAS, Teso zone"),
]
SHORT = {
    "NGA 1120840690 (tributary outlier)": "Benue tributary gauge",
    "Chisapani (Karnali)": "Chisapani",
    "Chatara (Koshi)": "Chatara",
}


def fig_proxy_summary():
    rows = list(csv.DictReader(open(REPO + "proxy_check.csv")))
    stations = list(dict.fromkeys(r["station"] for r in rows))
    by = {(r["station"], int(r["lead"])): r for r in rows}

    def usable(st):
        k = 0
        for L in range(1, 11):
            if (fnum(by[(st, L)]["peak_rho"]) or 0) >= 0.95:
                k = L
            else:
                break
        return k

    LMAX = 16
    x0, x1, y0, rh = 200, 560, 88, 46
    w = 760
    h = y0 + rh * len(FRAMEWORK_LEADS) + 74
    sx = lambda L: x0 + L / LMAX * (x1 - x0)
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Where the reanalysis can stand in for the reforecast, against each framework lead time' font-family='var(--body)' font-size='11.5'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Does the reanalysis stand in for the reforecast at the lead each framework needs?</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>Green bar: leads where every trigger station of the framework keeps seasonal-peak ρ ≥ 0.95; lighter: some stations only.</text>"
    )
    out.append(
        f"<text x='8' y='50' fill='{QUIET}'>Markers: the framework's action lead (filled) and readiness lead (hollow). Grey: beyond the Google reforecast's 10 days.</text>"
    )
    out.append(
        f"<rect x='{sx(10):.1f}' y='{y0 - 8}' width='{sx(LMAX) - sx(10):.1f}' height='{rh * len(FRAMEWORK_LEADS) + 8}' fill='{LINE}' fill-opacity='0.35'/>"
    )
    for L in range(0, LMAX + 1, 2):
        out.append(
            f"<line x1='{sx(L):.1f}' x2='{sx(L):.1f}' y1='{y0 - 8}' y2='{y0 + rh * len(FRAMEWORK_LEADS)}' stroke='{LINE}'/>"
        )
        out.append(
            f"<text x='{sx(L):.1f}' y='{y0 - 12}' text-anchor='middle' fill='{QUIET}' font-size='10'>{L} d</text>"
        )
    for i, (fw, prefixes, act, ready, note) in enumerate(FRAMEWORK_LEADS):
        sts = [s for s in stations if any(s.startswith(p) for p in prefixes)]
        us = {s: usable(s) for s in sts}
        lo, hi = min(us.values()), max(us.values())
        y = y0 + i * rh + rh / 2
        out.append(
            f"<text x='{x0 - 10}' y='{y - 2:.1f}' text-anchor='end' fill='{INK}' font-weight='600'>{esc(fw)}</text>"
        )
        out.append(
            f"<text x='{x0 - 10}' y='{y + 12:.1f}' text-anchor='end' fill='{QUIET}' font-size='9.5'>{esc(note)}</text>"
        )
        out.append(
            f"<rect x='{sx(0):.1f}' y='{y - 9:.1f}' width='{max(sx(hi) - sx(0), 2):.1f}' height='18' rx='3' fill='var(--ok)' fill-opacity='0.25'/>"
        )
        out.append(
            f"<rect x='{sx(0):.1f}' y='{y - 9:.1f}' width='{max(sx(lo) - sx(0), 2):.1f}' height='18' rx='3' fill='var(--ok)' fill-opacity='0.75'/>"
        )
        weakest = min(us, key=us.get)
        lab = (
            f"{len(sts)} station{'s' if len(sts) > 1 else ''} to {lo} d"
            if lo == hi
            else f"{lo} to {hi} d, weakest {SHORT.get(weakest, weakest.split(' (')[0])}"
        )
        out.append(
            f"<text x='{sx(hi) + 8:.1f}' y='{y + 4:.1f}' fill='{INK}' font-size='10'>{esc(lab)}</text>"
        )
        for lead, filled in [(act, True), (ready, False)]:
            if lead is None:
                continue
            col = "var(--ok)" if lead <= lo else ("#c9a227" if lead <= hi else "var(--warn)")
            px = sx(lead)
            tri = f"{px:.1f},{y - 12:.1f} {px - 6:.1f},{y - 22:.1f} {px + 6:.1f},{y - 22:.1f}"
            out.append(
                f"<polygon points='{tri}' fill='{col if filled else 'var(--panel)'}' stroke='{col}' stroke-width='1.5'/>"
            )
    ly = y0 + rh * len(FRAMEWORK_LEADS) + 18
    out.append(
        f"<text x='8' y='{ly}' fill='{QUIET}'>Marker colour: green inside the range for every station, amber for some, orange outside it. Niger's trigger is the gauge itself (lead 0).</text>"
    )
    out.append(
        f"<text x='8' y='{ly + 16}' fill='{QUIET}'>Readiness legs past 10 days run on GloFAS, whose own reforecast covers them. Nepal ends at 2 d because of Chatara; Nigeria's lower bound is one tributary gauge.</text>"
    )
    out.append("</svg>")
    return "".join(out)


LEDGER_COLS = [
    ("framework_fired", "framework\nbacktest", "flag"),
    ("incumbent", "ran on\n{inc}", "flag"),
    ("grrr_2026", "GRRR\n2026", "flag"),
    ("observed", "gauge\n{obs}", "flag"),
    ("grrr_2023", "GRRR 2023\n{g23}", "flag"),
    ("emdat_basin", "EM-DAT basin\naffected", "num"),
    ("cerf_total_usd", "CERF flood\nUS$", "cerf"),
]
RATE_KEY = {
    "framework_fired": ("fired_n", "baseline_years"),
    "incumbent": ("incumbent_n", "incumbent_years"),
    "grrr_2023": ("grrr_2023_n", "grrr_2023_years"),
    "grrr_2026": ("grrr_2026_n", "baseline_years"),
    "observed": ("observed_n", "observed_years"),
}


def fmt_big(v):
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.0f}k"
    return f"{v:.0f}"


def fig_ledger():
    rows = list(csv.DictReader(open(REPO + "year_ledger.csv")))
    rates = {r["framework"]: r for r in csv.DictReader(open(REPO + "year_ledger_rates.csv"))}
    corr = {i: r for i, r in enumerate(csv.DictReader(open(REPO + "year_ledger_impact_corr.csv")))}
    CORR_ROWS = [
        ("emdat_basin", "rho", "ρ vs EM-DAT basin"),
        ("cerf_flood_usd", "rho", "ρ vs CERF RR US$"),
        ("emdat_basin", "hmf", "EM-DAT hit/miss/FA"),
        ("cerf_flood_usd", "hmf", "CERF RR hit/miss/FA"),
    ]
    corr = {(r["framework"], r["column"], r["impact"]): r for r in corr.values()}
    fws = list(dict.fromkeys(r["framework"] for r in rows))
    years = sorted({int(r["year"]) for r in rows})
    cw, rh = 80, 15
    head = 130  # title, trigger line (2 rows), column headers, rates
    panel_w = 70 + cw * len(LEDGER_COLS)
    cols_per_row = 2
    panel_h = head + rh * len(years) + 10 + 4 * rh + 14 + 26
    w = 24 + cols_per_row * (panel_w + 24)
    nrows = (len(fws) + cols_per_row - 1) // cols_per_row
    h = 112 + nrows * (panel_h + 16)
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Year by year: framework trigger, the model it ran on, Google 2026, observed record, impact and CERF funding' font-family='var(--body)' font-size='10.5'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Year by year: who said flood, and what followed</text>"
    )
    out.append(
        f"<text x='8' y='34' fill='{QUIET}'>Key pair bracketed: the model each framework ran on against GRRR 2026. One rule for every model and gauge column: Weibull level at the framework's return period on the same baseline years.</text>"
    )
    out.append(
        f"<text x='8' y='47' fill='{QUIET}'>Under each header: flags in the baseline and the implied return period. Each panel's second line: what the trigger ran on and where the backtest years come from.</text>"
    )
    out.append(
        f"<text x='8' y='60' fill='{QUIET}'>Bottom rows: each column's yearly flags against two impact measures independent of the models: EM-DAT people affected in events touching the basin, and CERF rapid-response flood US$.</text>"
    )
    out.append(
        f"<text x='8' y='73' fill='{QUIET}'>Spearman with a bootstrap interval, then hits / misses / false alarms against the impact years (the years whose amount reaches the framework's RP level). Anticipatory years are out of the statistics; CERF cells: orange RR, green AA, label the total.</text>"
    )
    out.append(
        f"<text x='8' y='86' fill='{QUIET}'>Dashed cell: no record for that year. Outlined box: the baseline years the levels were fitted on.</text>"
    )
    for fi, fw in enumerate(fws):
        px = 24 + (fi % cols_per_row) * (panel_w + 24)
        py = 112 + (fi // cols_per_row) * (panel_h + 16)
        d = {int(r["year"]): r for r in rows if r["framework"] == fw}
        rt = rates[fw]
        inc = rt["incumbent_label"]
        same23 = inc == "GRRR 2023"
        out.append(
            f"<text x='{px}' y='{py + 14}' font-size='12.5' font-weight='600' fill='{INK}'>{esc(fw)}</text>"
        )
        out.append(
            f"<text x='{px + panel_w - 4}' y='{py + 14}' text-anchor='end' fill='{QUIET}' font-size='9.5'>Weibull RP{float(rt['rp']):g} on {rt['baseline_start']}–{rt['baseline_end']}</text>"
        )
        for li, line in enumerate(wrap(rt["trigger_source"], 150)[:1]):
            out.append(
                f"<text x='{px}' y='{py + 29 + li * 11}' fill='{INK}' font-size='9'>{esc(line)}</text>"
            )
        for li, line in enumerate(wrap("Taint: " + rt["taint"], 150)[:2]):
            out.append(
                f"<text x='{px}' y='{py + 41 + li * 11}' fill='{QUIET}' font-size='8.5'>{esc(line)}</text>"
            )
        hy = py + 74  # header baseline
        # bracket over the key pair
        bx0, bx1 = px + 70 + 1 * cw + 3, px + 70 + 3 * cw - 3
        out.append(
            f"<path d='M{bx0} {hy - 4} v-4 H{bx1} v4' fill='none' stroke='var(--accent)' stroke-width='1.2'/>"
        )
        out.append(
            f"<text x='{(bx0 + bx1) / 2}' y='{hy - 11}' text-anchor='middle' fill='var(--accent)' font-size='8.5' font-weight='600'>key comparison</text>"
        )
        nums = {}
        for key, _lab, kind in LEDGER_COLS:
            if kind == "num":
                vals = [fnum(d[y][key], 0) for y in years]
                nums[key] = max([v for v in vals if v is not None] or [1])
        for ci, (key, lab, _kind) in enumerate(LEDGER_COLS):
            cx = px + 70 + ci * cw + cw / 2
            lab = lab.format(
                inc=inc, g23="(= ran on)" if same23 else "secondary", obs=rt["observed_label"]
            )
            for li, line in enumerate(lab.split("\n")):
                out.append(
                    f"<text x='{cx}' y='{hy + li * 11}' text-anchor='middle' fill='{INK if key in ('incumbent', 'grrr_2026') else QUIET}' font-size='9.5' font-weight='{600 if key in ('incumbent', 'grrr_2026') and li == 1 else 400}'>{esc(line)}</text>"
                )
            if (
                key in RATE_KEY
                and not (key == "grrr_2023" and same23)
                and rt.get(RATE_KEY[key][0]) not in (None, "")
            ):
                n, N = fnum(rt[RATE_KEY[key][0]], 0), fnum(rt[RATE_KEY[key][1]], 0)
                if n is not None and N:
                    out.append(
                        f"<text x='{cx}' y='{hy + 22}' text-anchor='middle' fill='{INK}' font-size='8.5' font-weight='600'>{n:.0f} of {N:.0f}</text>"
                    )
                    out.append(
                        f"<text x='{cx}' y='{hy + 32}' text-anchor='middle' fill='{INK}' font-size='8.5'>1-in-{N / n if n else 0:.1f}</text>"
                    )
        b0, b1 = int(rt["baseline_start"]), int(rt["baseline_end"])
        nflag = sum(
            1 for k, _l, kd in LEDGER_COLS if kd == "flag" and not (k == "grrr_2023" and same23)
        )
        by0 = py + head - 12 + years.index(b0) * rh
        out.append(
            f"<rect x='{px + 70 - 1}' y='{by0 - 1}' width='{cw * nflag + 2}' height='{rh * (b1 - b0 + 1) + 2}' rx='3' fill='var(--fg)' fill-opacity='0.035' stroke='var(--fg)' stroke-opacity='0.35' stroke-width='1'/>"
        )
        for yi, y in enumerate(years):
            ry = py + head - 12 + yi * rh
            out.append(
                f"<text x='{px + 62}' y='{ry + 11}' text-anchor='end' fill='{INK}' font-size='9.5'>{y}</text>"
            )
            for ci, (key, _lab, kind) in enumerate(LEDGER_COLS):
                cx = px + 70 + ci * cw
                if key == "grrr_2023" and same23:
                    continue
                v = fnum(d[y][key], 0)
                if v is None:
                    out.append(
                        f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' fill='none' stroke='{LINE}' stroke-dasharray='2 2'/>"
                    )
                    continue
                if kind == "cerf":
                    rr, aa = fnum(d[y]["cerf_flood_usd"], 0) or 0, fnum(d[y]["cerf_aa_usd"], 0) or 0
                    if rr and aa:
                        out.append(
                            f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw / 2 - 1}' height='{rh - 2}' rx='2' fill='var(--warn)' fill-opacity='0.75'/>"
                        )
                        out.append(
                            f"<rect x='{cx + cw / 2}' y='{ry + 1}' width='{cw / 2 - 1}' height='{rh - 2}' rx='2' fill='var(--ok)' fill-opacity='0.75'/>"
                        )
                    else:
                        out.append(
                            f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' rx='2' fill='{'var(--ok)' if aa else 'var(--warn)'}' fill-opacity='0.75'/>"
                        )
                    out.append(
                        f"<text x='{cx + cw / 2}' y='{ry + 11}' text-anchor='middle' fill='{INK}' font-size='9' font-weight='600'>{fmt_big(v)}</text>"
                    )
                elif kind == "flag":
                    fill = "var(--accent)" if v >= 1 else "var(--line)"
                    op = (0.9 if v >= 1 else 0.5) * (0.55 if key == "grrr_2023" else 1)
                    out.append(
                        f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' rx='2' fill='{fill}' fill-opacity='{op:.2f}'/>"
                    )
                else:
                    frac = v / nums[key] if nums[key] else 0
                    out.append(
                        f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' rx='2' fill='var(--warn)' fill-opacity='{0.12 + 0.75 * frac:.2f}'/>"
                    )
                    out.append(
                        f"<text x='{cx + cw / 2}' y='{ry + 11}' text-anchor='middle' fill='{INK}' font-size='9'>{fmt_big(v)}</text>"
                    )
        # impact rows: rho with bootstrap half-width, then hits/misses/false alarms against impact years
        cy0 = py + head - 12 + len(years) * rh + 10
        out.append(
            f"<line x1='{px}' x2='{px + panel_w - 4}' y1='{cy0 - 4}' y2='{cy0 - 4}' stroke='{LINE}'/>"
        )
        for ri, (imp, stat, lab) in enumerate(CORR_ROWS):
            ry = cy0 + ri * rh
            out.append(
                f"<text x='{px + 62}' y='{ry + 11}' text-anchor='end' fill='{INK}' font-size='8.5'>{esc(lab)}</text>"
            )
            n_shown = max(
                (
                    int(c["n"]) if stat == "rho" else int(c["n_scored"])
                    for (f_, _k, i_), c in corr.items()
                    if f_ == fw and i_ == imp
                ),
                default=None,
            )
            for ci, (key, _lab, kind) in enumerate(LEDGER_COLS):
                cx = px + 70 + ci * cw
                if kind != "flag" or (key == "grrr_2023" and same23):
                    if (
                        key in (imp, "cerf_total_usd" if imp == "cerf_flood_usd" else imp)
                        and n_shown
                    ):
                        out.append(
                            f"<text x='{cx + cw / 2}' y='{ry + 11}' text-anchor='middle' fill='{QUIET}' font-size='8.5'>n = {n_shown}</text>"
                        )
                    continue
                c = corr.get((fw, key, imp))
                if stat == "rho":
                    r = fnum(c["r"], 2) if c else None
                    if r is None:
                        out.append(
                            f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' fill='none' stroke='{LINE}' stroke-dasharray='2 2'/>"
                        )
                        continue
                    lo, hi = fnum(c["r_lo"], 2), fnum(c["r_hi"], 2)
                    half = (hi - lo) / 2 if lo is not None and hi is not None else None
                    fill = "var(--accent)" if r >= 0 else "var(--warn)"
                    out.append(
                        f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' rx='2' fill='{fill}' fill-opacity='{0.08 + 0.7 * min(abs(r), 1):.2f}'/>"
                    )
                    txt = f"{r:+.2f}" + (f" ±{half:.2f}" if half is not None else "")
                    out.append(
                        f"<text x='{cx + cw / 2}' y='{ry + 11}' text-anchor='middle' fill='{INK}' font-size='8.5' font-weight='{600 if key in ('incumbent', 'grrr_2026') else 400}'>{txt}</text>"
                    )
                else:
                    if not c or not int(c["n_scored"]):
                        out.append(
                            f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' fill='none' stroke='{LINE}' stroke-dasharray='2 2'/>"
                        )
                        continue
                    h, m, f = int(c["hits"]), int(c["misses"]), int(c["false_alarms"])
                    score = h / (h + m) if h + m else 0
                    out.append(
                        f"<rect x='{cx + 1}' y='{ry + 1}' width='{cw - 2}' height='{rh - 2}' rx='2' fill='var(--accent)' fill-opacity='{0.08 + 0.6 * score:.2f}'/>"
                    )
                    out.append(
                        f"<text x='{cx + cw / 2}' y='{ry + 11}' text-anchor='middle' fill='{INK}' font-size='9' font-weight='{600 if key in ('incumbent', 'grrr_2026') else 400}'>{h} / {m} / {f}</text>"
                    )
        fy = cy0 + len(CORR_ROWS) * rh + 12
        ce = corr.get((fw, "grrr_2026", "emdat_basin")) or {}
        cc = corr.get((fw, "grrr_2026", "cerf_flood_usd")) or {}
        aa = (ce.get("aa_years_excluded") or "").replace(",", ", ") or "none"
        out.append(
            f"<text x='{px}' y='{fy}' fill='{QUIET}' font-size='8.5'>Impact years at Weibull RP{float(rt['rp']):g} on the baseline: EM-DAT basin {(ce.get('impact_years') or 'none').replace(',', ', ')}; CERF RR {(cc.get('impact_years') or 'none').replace(',', ', ')}.</text>"
        )
        out.append(
            f"<text x='{px}' y='{fy + 12}' fill='{QUIET}' font-size='8.5'>AA years out of every statistic: {esc(aa)}. ± is half the bootstrap 90% interval; columns closer than that are not distinguishable.</text>"
        )
    out.append("</svg>")
    return "".join(out)


def fig_paired():
    """GRRR 2026 against the incumbent on the framework-years of each window: impact years caught,
    false alarms, and the critical success index, each as a difference with a 90% interval."""
    rows = list(csv.DictReader(open(REPO + "year_ledger_paired.csv")))
    fws = list(dict.fromkeys(r["framework"] for r in rows))
    measures = [
        ("emdat_basin", "EM-DAT basin, people affected"),
        ("cerf_flood_usd", "CERF rapid response, US$"),
    ]
    panels = [
        ("diff", "impact years caught", -10, 6, 2),
        ("fa_diff", "false alarms", -10, 6, 2),
        ("csi_diff", "CSI, hits / (hits + misses + false alarms)", -0.75, 0.5, 0.25),
    ]
    w, rh, label_w, pw, gap = 1250, 20, 170, 240, 22
    y0 = 84
    h = y0 + (len(fws) * rh + 44) * len(measures) + 40
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='GRRR 2026 against the incumbent: impact years caught, false alarms and CSI, per framework and pooled' font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>Would the 2026 model have served the frameworks better than the model each runs on?</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>GRRR 2026 minus incumbent on each framework's comparison window, over all its framework-years: impact years caught, false alarms (years flagged that were not impact years),</text>"
    )
    out.append(
        f"<text x='8' y='50' fill='{QUIET}'>and the critical success index. Bar: bootstrap 90% interval over the window years; the pooled row sums the same resamples across frameworks. Left of zero: fewer with the 2026 model.</text>"
    )
    out.append(
        f"<text x='8' y='64' fill='{QUIET}'>Fewer impact years caught is bad, fewer false alarms is good, lower CSI is bad. Right: CSI 2026 v incumbent, impact years caught of N, false alarms, framework-years. Anticipatory years are out.</text>"
    )
    y = y0
    for key, title in measures:
        out.append(f"<text x='8' y='{y}' font-weight='600' fill='{INK}'>{esc(title)}</text>")
        y += 10
        for p, (dk, ptitle, xmin, xmax, step) in enumerate(panels):
            x0 = label_w + 10 + p * (pw + gap)
            x1 = x0 + pw
            sx = lambda v, x0=x0, x1=x1, xmin=xmin, xmax=xmax: (
                x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)
            )
            out.append(
                f"<text x='{x0}' y='{y - 2}' fill='{QUIET}' font-size='10'>{esc(ptitle)}</text>"
            )
            tick = xmin
            while tick <= xmax + 1e-9:
                out.append(
                    f"<line x1='{sx(tick):.1f}' x2='{sx(tick):.1f}' y1='{y + 4}' y2='{y + 4 + rh * len(fws)}' stroke='{LINE}' stroke-opacity='{1 if abs(tick) < 1e-9 else 0.5}'/>"
                )
                lab = f"{tick:+.2f}".rstrip("0").rstrip(".") if step < 1 else f"{int(tick):+d}"
                out.append(
                    f"<text x='{sx(tick):.1f}' y='{y + rh * len(fws) + 16}' text-anchor='middle' fill='{QUIET}' font-size='9'>{lab if abs(tick) > 1e-9 else '0'}</text>"
                )
                tick += step
            for i, fw in enumerate(fws):
                r = next(q for q in rows if q["framework"] == fw and q["impact"] == key)
                cy = y + 4 + i * rh + rh / 2
                pooled = fw.startswith("All")
                if p == 0:
                    out.append(
                        f"<text x='{x0 - 10}' y='{cy + 4:.1f}' text-anchor='end' fill='{INK}' font-weight='{600 if pooled else 400}'>{esc(fw.replace(' (Chatara)', '').replace(' (Bahadurabad)', ''))}</text>"
                    )
                lo, hi, d = (float(r[dk + s]) for s in ("_lo", "_hi", ""))
                lo, hi = max(lo, xmin), min(hi, xmax)
                out.append(
                    f"<line x1='{sx(lo):.1f}' x2='{sx(hi):.1f}' y1='{cy:.1f}' y2='{cy:.1f}' stroke='{C26}' stroke-width='{5 if pooled else 3}' stroke-opacity='0.45' stroke-linecap='round'/>"
                )
                out.append(
                    f"<circle cx='{sx(max(min(d, xmax), xmin)):.1f}' cy='{cy:.1f}' r='{5 if pooled else 4}' fill='{C26}'/>"
                )
                if p == 2:
                    out.append(
                        f"<text x='{x1 + 10}' y='{cy + 4:.1f}' fill='{INK}' font-size='10'>CSI {float(r['csi_grrr_2026']):.2f} v {float(r['csi_incumbent']):.2f} · {r['hits_grrr_2026']} v {r['hits_incumbent']} of {r['n_impact_years']} · FA {r['fa_grrr_2026']} v {r['fa_incumbent']} · {r['n_years']} yrs</text>"
                    )
        y += rh * len(fws) + 44
    out.append(
        f"<text x='8' y='{h - 8}' fill='{QUIET}'>Nigeria is exactly zero on every panel: its incumbent is the 2023 bucket and both flag the same years. A CSI interval is from resamples with at least one impact year or flag.</text>"
    )
    out.append("</svg>")
    return "".join(out)


def fig_gauge():
    """GRRR 2026 against the incumbent on each framework's own gauge test (section 3), reduced to
    the same four numbers as the impact side: rank correlation with the observed record, share of
    observed events caught, false-alarm ratio and CSI, per trigger station. Absolute values as
    dumbbells; no intervals (point results of the rescores) and no pooled row (the event units
    differ). Reads outputs/rescore_gauge_2x2.csv."""
    rows = list(csv.DictReader(open(REPO + "rescore_gauge_2x2.csv")))
    f = lambda v: None if v in ("", None) else float(v)
    panels = [
        ("rho", "rank ρ with the observed record"),
        ("pod", "observed events caught, share of N"),
        ("far", "false-alarm ratio, FA / (hits + FA)"),
        ("csi", "CSI, hits / (hits + misses + FA)"),
    ]

    def vals(r):
        n, h_i, fa_i, h6, fa6 = (
            f(r[k])
            for k in ("n_obs", "hits_incumbent", "fa_incumbent", "hits_grrr_2026", "fa_grrr_2026")
        )
        if n is None:
            return None
        return {
            "rho": (f(r["rho_incumbent"]), f(r["rho_grrr_2026"])),
            "pod": (h_i / n, h6 / n),
            "far": (
                fa_i / (h_i + fa_i) if h_i + fa_i else None,
                fa6 / (h6 + fa6) if h6 + fa6 else None,
            ),
            "csi": (f(r["csi_incumbent"]), f(r["csi_grrr_2026"])),
        }

    w, rh, label_w, pw, gap = 1250, 20, 215, 185, 18
    y0 = 96
    h = y0 + rh * len(rows) + 92
    out = [
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='GRRR 2026 against the incumbent on each framework&#39;s own gauge test: correlation, events caught, false-alarm ratio and CSI per station' font-family='var(--body)' font-size='11'>"
    ]
    out.append(
        f"<text x='8' y='18' font-size='14' font-weight='600' fill='{INK}'>On the frameworks' own gauge tests, scored the same way: the 2026 model against the model each framework runs on</text>"
    )
    out.append(
        f"<text x='8' y='36' fill='{QUIET}'>Each framework's section-3 test reduced to the impact side's four numbers, per trigger station: rank correlation with the observed record where the test reports one, observed events caught</text>"
    )
    out.append(
        f"<text x='8' y='50' fill='{QUIET}'>(RP3 episodes, 3-yr or 4-yr peak years, DHM danger-level crossings, FFWC severe floods), false alarms (model events matching none) and the critical success index. Segment joins the</text>"
    )
    out.append(
        f"<text x='8' y='64' fill='{QUIET}'>incumbent to GRRR 2026; right of the incumbent is better except for the false-alarm ratio. Both models of a pair on one threshold convention (own quantile; published levels in Nepal). Point results, no intervals.</text>"
    )
    out.append(
        f"<text x='8' y='78' fill='{QUIET}'>Right: CSI 2026 v incumbent, events caught of N, false alarms. No pooled row: episodes, crossings, severe floods and peak years are different units and do not add.</text>"
    )
    y = y0
    for p, (_dk, ptitle) in enumerate(panels):
        x0 = label_w + 10 + p * (pw + gap)
        x1 = x0 + pw
        out.append(f"<text x='{x0}' y='{y - 4}' fill='{QUIET}' font-size='10'>{esc(ptitle)}</text>")
        for t in (0, 0.25, 0.5, 0.75, 1):
            tx = x0 + t * (x1 - x0)
            out.append(
                f"<line x1='{tx:.1f}' x2='{tx:.1f}' y1='{y + 2}' y2='{y + 2 + rh * len(rows)}' stroke='{LINE}' stroke-opacity='{1 if t in (0, 1) else 0.5}'/>"
            )
            out.append(
                f"<text x='{tx:.1f}' y='{y + rh * len(rows) + 14}' text-anchor='middle' fill='{QUIET}' font-size='9'>{t:g}</text>"
            )
    xr = label_w + 10 + len(panels) * (pw + gap) - gap + 12
    prev = None
    for i, r in enumerate(rows):
        cy = y + 2 + i * rh + rh / 2
        fw = r["framework"]
        if fw != prev:
            if i:
                out.append(
                    f"<line x1='8' x2='{w - 8}' y1='{cy - rh / 2:.1f}' y2='{cy - rh / 2:.1f}' stroke='{LINE}'/>"
                )
            out.append(
                f"<text x='8' y='{cy + 4:.1f}' fill='{INK}' font-weight='600'>{esc(fw.replace(' (Chatara)', '').replace(' (Bahadurabad)', ''))}</text>"
            )
            prev = fw
        out.append(
            f"<text x='{label_w}' y='{cy + 4:.1f}' text-anchor='end' fill='{INK}'>{esc(r['station'])}</text>"
        )
        v = vals(r)
        if v is None:
            out.append(
                f"<text x='{label_w + 10}' y='{cy + 4:.1f}' fill='{QUIET}'>{esc(r['test'])}: no model to compare. {esc(r['incumbent'])}.</text>"
            )
            continue
        inc_col = C23 if r["incumbent"].startswith("GRRR") else INC
        for p, (dk, _) in enumerate(panels):
            x0 = label_w + 10 + p * (pw + gap)
            sx = lambda t, x0=x0: x0 + t * pw
            vi, v6 = v[dk]
            if vi is None and v6 is None:
                if fw != rows[i - 1]["framework"] if i else True:
                    out.append(
                        f"<text x='{x0 + pw / 2:.1f}' y='{cy + 4:.1f}' text-anchor='middle' fill='{QUIET}' font-size='9'>not in this test</text>"
                    )
                continue
            if vi is not None and v6 is not None:
                out.append(
                    f"<line x1='{sx(vi):.1f}' x2='{sx(v6):.1f}' y1='{cy:.1f}' y2='{cy:.1f}' stroke='{QUIET}' stroke-width='2' stroke-opacity='0.6'/>"
                )
            if vi is not None:
                out.append(f"<circle cx='{sx(vi):.1f}' cy='{cy:.1f}' r='4.5' fill='{inc_col}'/>")
            if v6 is not None:
                out.append(f"<circle cx='{sx(v6):.1f}' cy='{cy:.1f}' r='4.5' fill='{C26}'/>")
        out.append(
            f"<text x='{xr}' y='{cy + 4:.1f}' fill='{INK}' font-size='10'>CSI {float(r['csi_grrr_2026']):.2f} v {float(r['csi_incumbent']):.2f} · {int(float(r['hits_grrr_2026']))} v {int(float(r['hits_incumbent']))} of {int(float(r['n_obs']))} · FA {int(float(r['fa_grrr_2026']))} v {int(float(r['fa_incumbent']))}</text>"
        )
    ly = y + 2 + rh * len(rows) + 40
    out.append(
        f"<circle cx='16' cy='{ly - 4}' r='4.5' fill='{INC}'/><text x='26' y='{ly}' fill='{QUIET}'>ran on: GloFAS v4 or v5</text>"
    )
    out.append(
        f"<circle cx='190' cy='{ly - 4}' r='4.5' fill='{C23}'/><text x='200' y='{ly}' fill='{QUIET}'>ran on: GRRR 2023 bucket (Nigeria)</text>"
    )
    out.append(
        f"<circle cx='420' cy='{ly - 4}' r='4.5' fill='{C26}'/><text x='430' y='{ly}' fill='{QUIET}'>GRRR November 2026</text>"
    )
    out.append(
        f"<text x='8' y='{ly + 18}' fill='{QUIET}'>Tests: Somalia RP3 episodes at each SWALIM gauge 2002–2023, ρ the mean of Gu and Deyr daily ρ against the river's reference gauge; Nigeria 3-yr peak years and annual-peak ρ against GRDC, 1981–2023; Nepal DHM crossings at Chatara,</text>"
    )
    out.append(
        f"<text x='8' y='{ly + 32}' fill='{QUIET}'>model at the 2025 trigger's RP5; Chad 4-yr peak years and annual-peak ρ against the DRE level at N'Djamena 2003–2022; Bangladesh FFWC severe floods at Bahadurabad, model at RP5. Full tables in section 3.</text>"
    )
    out.append("</svg>")
    return "".join(out)
