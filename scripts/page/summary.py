"""Add the incumbent (GloFAS) legs to outputs/rescore_summary.json from the rescore CSVs, and rebuild
the Nigeria block from the two Nigeria CSVs (hits/false alarms/misses order in `hit3_*`). Idempotent."""

import json

import pandas as pd
from charts import REPO as R


def patch():
    d = json.load(open(R + "rescore_summary.json"))
    som = pd.read_csv(R + "rescore_som_glofas_v5.csv")
    c = som[som.block == "correlation"].set_index(["station", "season"])
    for r in d["som_corr"]:
        k = (r["station"].lower().replace(" ", "_"), r["season"].lower())
        row = c.loc[k]
        r["cinc"], r["laginc"], r["owninc"], r["peakinc"] = (
            f"{row.daily_rho_ref:.2f}",
            int(row.best_lag_ref),
            f"{row.daily_rho_own:.2f}",
            f"{row.peak_rho_own:.2f}",
        )
    e = som[(som.block == "episodes") & (som.model_rp == 3)].set_index("station")
    for r in d["som_ep"]:
        row = e.loc[r["station"].lower().replace(" ", "_")]
        r["modinc"], r["podinc"], r["farinc"], r["thrinc"] = (
            int(row.model_episodes),
            f"{row.POD:.2f}",
            f"{row.FAR:.2f}",
            f"{row.threshold_m3s:.0f}",
        )
    bgd = pd.read_csv(R + "rescore_bgd_2026.csv")
    g = bgd[bgd.release == "glofas_v4"].iloc[0]
    d["bgd"] = [r for r in d["bgd"] if r["release"] != "glofas_v4"] + [
        {
            "release": "glofas_v4",
            "conv": "quantile_full",
            "thr": int(g.threshold_m3s),
            "n_ref": int(g.n_reference),
            "n_model": int(g.n_source),
            "matched": int(g.n_matched),
            "fa": int(g.false_alarms),
        }
    ]
    a = pd.read_csv(R + "rescore_nga_2023.csv").fillna({"note": "", "excluded": ""})
    b = pd.read_csv(R + "rescore_nga_2026.csv").fillna({"note": "", "excluded": ""})
    m = a.merge(b, on=["station", "hybas", "note"], suffixes=("23", "26"), validate="1:1")
    if len(m) != len(a) or (m.excluded23 != m.excluded26).any():
        raise ValueError(
            "rescore_nga_2023.csv and rescore_nga_2026.csv disagree on stations or exclusions"
        )
    nga = []
    for _, r in m.iterrows():
        ex = bool(r.excluded26)
        row = {
            "station": r.station,
            "hybas": r.hybas,
            "note": r.note,
            "excluded": r.excluded26,
            "years": None if ex else int(r.n_valid_years26),
            "daily23": round(float(r.daily_rho23), 2),
            "daily26": round(float(r.daily_rho26), 2),
            "pub_peak": "0.76 (KB page)" if r.station == "Yidere Bode" else "",
        }
        for k, kk in (("peak_rho", "peak"), ("f1_3yr", "f1_3_"), ("f1_5yr", "f1_5_")):
            row[f"{kk}23"] = None if ex else round(float(r[f"{k}23"]), 2)
            row[f"{kk}26"] = None if ex else round(float(r[f"{k}26"]), 2)
        for rel in ("23", "26"):
            row[f"hit3_{rel}"] = (
                ""
                if ex
                else f"{int(r[f'hits_3yr{rel}'])}/{int(r[f'false_alarms_3yr{rel}'])}/{int(r[f'misses_3yr{rel}'])}"
            )
        nga.append(row)
    d["nga"] = nga
    d["incumbent"] = {
        "Somalia": "GloFAS v5",
        "Nepal": "GloFAS v4",
        "Nigeria": "GRRR 2023",
        "Chad": "GloFAS v4",
        "Bangladesh": "GloFAS v4",
    }
    json.dump(d, open(R + "rescore_summary.json", "w"), indent=1)
