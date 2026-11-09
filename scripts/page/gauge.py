"""The frameworks' own gauge tests as a 2x2, GRRR 2026 against the incumbent, per trigger station.

Section 3 of the page re-runs each framework's own evaluation with the model it runs on and
with GRRR 2026. Those tests differ in unit (RP3 episodes, danger-level crossings, severe
floods, 4-yr peak years), but each reduces to the same four numbers the impact side uses:

- rho: rank correlation with the observed record, where the framework reports one (Somalia
  daily rho against the river's reference gauge, mean of Gu and Deyr; Nigeria and Chad
  annual-peak rho against the observed discharge or level)
- hits of n_obs: observed events caught
- fa: false alarms, model events that match no observed event
- csi: hits / (hits + misses + fa)

Thresholds are on the same convention for both models of a pair: each at the quantile of its
own reanalysis where the incumbent has no published level (Somalia, Bangladesh, Chad, Nigeria),
each at its provider's published level in Nepal (GloFAS at the Copernicus dashboard value the
framework uses, GRRR at the release's table). Nepal is scored at the 2025 trigger's RP5 at
Chatara. Section 3 also shows GRRR at its shipped levels, which sit lower and fire more often: in
Somalia they catch one more episode at 4 of 7 gauges and in Bangladesh one more flood, with
more false alarms in both.

No pooled row: the event units differ across frameworks, so their counts do not add.

Reads the rescore CSVs in outputs/ and writes outputs/rescore_gauge_2x2.csv; a missing input
raises. Niger has no model in its trigger and gets an empty row.
"""

from __future__ import annotations

import pandas as pd
from charts import REPO as R

INCUMBENT = {
    "Somalia": "GloFAS v5",
    "Nigeria 2026": "GRRR 2023",
    "Nepal 2025 (Chatara)": "GloFAS v4",
    "Chad 2025": "GloFAS v4",
    "Bangladesh 2025 (Bahadurabad)": "GloFAS v4",
    "Niger 2025": "ABN gauge (no model)",
}
TEST = {
    "Somalia": "RP3 episodes at each SWALIM gauge, 2002–2023",
    "Nigeria 2026": "3-yr peak years at each GRDC station",
    "Nepal 2025 (Chatara)": "DHM danger-level crossings, model at RP5",
    "Chad 2025": "4-yr peak years at N'Djamena, 2003–2022",
    "Bangladesh 2025 (Bahadurabad)": "FFWC severe floods, model at RP5",
    "Niger 2025": "trigger is the gauge itself",
}
LOKOJA_BASIN = "hybas_1120908000"  # the notebook's first choice; the alternative scores the same


def _csv(name: str) -> pd.DataFrame:
    try:
        return pd.read_csv(R + name)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"{R}{name} missing: run the rescore script that writes it") from e


def _int(x: float, what: str) -> int:
    if abs(x - round(x)) > 1e-6:
        raise ValueError(f"{what} = {x} is not a whole count")
    return round(x)


def _csi(h: int, n: int, fa: int) -> float | None:
    return h / (n + fa) if (n + fa) else None


def _row(
    fw: str,
    station: str,
    n: int,
    h_inc: int,
    fa_inc: int,
    h26: int,
    fa26: int,
    rho_inc=None,
    rho26=None,
) -> dict:
    return {
        "framework": fw,
        "station": station,
        "incumbent": INCUMBENT[fw],
        "test": TEST[fw],
        "n_obs": n,
        "hits_incumbent": h_inc,
        "fa_incumbent": fa_inc,
        "hits_grrr_2026": h26,
        "fa_grrr_2026": fa26,
        "rho_incumbent": rho_inc,
        "rho_grrr_2026": rho26,
        "csi_incumbent": _csi(h_inc, n, fa_inc),
        "csi_grrr_2026": _csi(h26, n, fa26),
    }


def _somalia() -> list[dict]:
    g26, inc = _csv("rescore_som_2026.csv"), _csv("rescore_som_glofas_v5.csv")
    e26 = g26[(g26.block == "episodes") & (g26.model_rp == 3) & (g26.rp_convention == "derived")]
    einc = inc[(inc.block == "episodes") & (inc.model_rp == 3)]
    c26 = g26[g26.block == "correlation"].groupby("station").daily_rho_ref.mean()
    cinc = inc[inc.block == "correlation"].groupby("station").daily_rho_ref.mean()
    out = []
    for st in ["dollow", "luuq", "bardheere", "bualle", "belet_weyne", "bulo_burti", "jowhar"]:
        a, b = e26[e26.station == st].iloc[0], einc[einc.station == st].iloc[0]
        if a.obs_episodes != b.obs_episodes:
            raise ValueError(f"Somalia {st}: observed episodes differ between runs")
        n = _int(a.obs_episodes, f"{st} obs")
        out.append(
            _row(
                "Somalia",
                st.replace("_", " ").title(),
                n,
                _int(b.POD * n, f"{st} GloFAS hits"),
                _int(b.FAR * b.model_episodes, f"{st} GloFAS FA"),
                _int(a.POD * n, f"{st} 2026 hits"),
                _int(a.FAR * a.model_episodes, f"{st} 2026 FA"),
                float(cinc[st]),
                float(c26[st]),
            )
        )
    return out


def _nigeria() -> list[dict]:
    a, b = _csv("rescore_nga_2023.csv"), _csv("rescore_nga_2026.csv")
    keep = lambda d: d[d.excluded.isna() & ~((d.station == "Lokoja") & (d.hybas != LOKOJA_BASIN))]
    a, b = keep(a).set_index("station"), keep(b).set_index("station")
    out = []
    for st in b.index:
        x, y = a.loc[st], b.loc[st]
        n = _int(y.hits_3yr + y.misses_3yr, f"{st} obs years")
        if n != _int(x.hits_3yr + x.misses_3yr, f"{st} obs years 2023"):
            raise ValueError(f"Nigeria {st}: observed 3-yr years differ between releases")
        out.append(
            _row(
                "Nigeria 2026",
                st,
                n,
                _int(x.hits_3yr, "hits"),
                _int(x.false_alarms_3yr, "fa"),
                _int(y.hits_3yr, "hits"),
                _int(y.false_alarms_3yr, "fa"),
                float(x.peak_rho),
                float(y.peak_rho),
            )
        )
    return out


def _nepal() -> list[dict]:
    d = _csv("rescore_npl_2026.csv")
    d = d[(d.station == "Chatara") & (d.rp == 5)]
    g = d[(d.source == "GRRR") & (d.rp_convention == "shipped")].iloc[0]
    v = d[(d.source == "GloFAS v4") & (d.rp_convention == "dashboard")].iloc[0]
    return [
        _row(
            "Nepal 2025 (Chatara)",
            "Chatara",
            int(g.n_reference),
            int(v.n_matched),
            int(v.false_alarms),
            int(g.n_matched),
            int(g.false_alarms),
        )
    ]


def _chad() -> list[dict]:
    d = _csv("rescore_tcd_2026.csv").set_index("model")
    g, v = d.loc["GRRR 2026"], d.loc["GloFAS v4 reanalysis"]
    n_fa = lambda s: 0 if s == "none" else len(str(s).split(","))
    n = len(g.obs_years_over.split(","))
    return [
        _row(
            "Chad 2025",
            "N'Djamena",
            n,
            int(v.hits),
            n_fa(v.false_positives),
            int(g.hits),
            n_fa(g.false_positives),
            float(v.peak_rho),
            float(g.peak_rho),
        )
    ]


def _bangladesh() -> list[dict]:
    d = _csv("rescore_bgd_2026.csv")
    g = d[(d.release == "2026") & (d.rp_convention == "quantile_full")].iloc[0]
    v = d[d.release == "glofas_v4"].iloc[0]
    return [
        _row(
            "Bangladesh 2025 (Bahadurabad)",
            "Bahadurabad",
            int(g.n_reference),
            int(v.n_matched),
            int(v.false_alarms),
            int(g.n_matched),
            int(g.false_alarms),
        )
    ]


def rows() -> list[dict]:
    out = _nigeria() + _somalia() + _nepal() + _chad() + _bangladesh()
    out.append(
        {
            "framework": "Niger 2025",
            "station": "Niamey",
            "incumbent": INCUMBENT["Niger 2025"],
            "test": TEST["Niger 2025"],
        }
    )
    return out


def write() -> list[dict]:
    r = rows()
    pd.DataFrame(r).to_csv(R + "rescore_gauge_2x2.csv", index=False)
    return r


def verdicts(r: list[dict] | None = None) -> dict[str, tuple[str, str]]:
    """Per framework: (verdict word, detail) on the CSI of its own gauge test, 2026 against
    the incumbent. One station: same / higher / lower. Several: the same if every station
    agrees, otherwise 'mixed by station'."""
    r = r or rows()
    out = {}
    for fw in INCUMBENT:
        rs = [x for x in r if x["framework"] == fw and x.get("csi_grrr_2026") is not None]
        if not rs:
            out[fw] = ("not applicable", TEST[fw])
            continue
        sgn = [
            (x["csi_grrr_2026"] > x["csi_incumbent"] + 1e-9)
            - (x["csi_grrr_2026"] < x["csi_incumbent"] - 1e-9)
            for x in rs
        ]
        word = {1: "higher", -1: "lower", 0: "same"}
        if len(rs) == 1:
            x = rs[0]
            detail = (
                f"{x['hits_grrr_2026']} vs {x['hits_incumbent']} of {x['n_obs']} caught, "
                f"FA {x['fa_grrr_2026']} vs {x['fa_incumbent']}, CSI {x['csi_grrr_2026']:.2f} vs {x['csi_incumbent']:.2f}"
            )
            out[fw] = (word[sgn[0]], detail)
        else:
            up, down = sum(s > 0 for s in sgn), sum(s < 0 for s in sgn)
            v = word[sgn[0]] if len(set(sgn)) == 1 else "mixed by station"
            out[fw] = (v, f"CSI higher at {up} of {len(rs)} stations, lower at {down}")
    return out


if __name__ == "__main__":
    for x in write():
        print(x)
    for k, v in verdicts().items():
        print(k, v)
