"""Add the incumbent (GloFAS) legs to outputs/rescore_summary.json from the rescore CSVs. Idempotent."""

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
    d["incumbent"] = {
        "Somalia": "GloFAS v5",
        "Nepal": "GloFAS v4",
        "Nigeria": "GRRR 2023",
        "Chad": "GloFAS v4",
        "Bangladesh": "GloFAS v4",
    }
    json.dump(d, open(R + "rescore_summary.json", "w"), indent=1)
