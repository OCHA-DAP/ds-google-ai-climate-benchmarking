"""Aggregate the step-1 coverage outputs (basins by country, NaN sample) into outputs/page/page_data.json."""

import json

import pandas as pd
from charts import REPO as R


def write():
    bc = pd.read_csv(R + "distributed_model_2026_11_basins_by_country.csv")
    iso = [
        "AFG",
        "BFA",
        "BGD",
        "COD",
        "CUB",
        "ETH",
        "FJI",
        "GTM",
        "HND",
        "HTI",
        "KEN",
        "MDG",
        "MMR",
        "MOZ",
        "MRT",
        "MWI",
        "NER",
        "NGA",
        "NIC",
        "NPL",
        "PHL",
        "SLV",
        "SOM",
        "SSD",
        "TCD",
        "UGA",
        "VUT",
        "YEM",
    ]
    flood = ["BFA", "BGD", "NER", "NGA", "NPL", "TCD", "UGA", "SOM", "SSD", "YEM"]
    t = (
        bc[bc.iso.isin(iso)]
        .groupby(["iso", "country"])
        .has_prediction.agg(basins="size", with_prediction="sum")
        .reset_index()
    )
    t["missing"] = t.basins - t.with_prediction
    t["flood"] = t.iso.isin(flood)
    rows = t.sort_values("iso").to_dict("records")
    miss = bc[~bc.has_prediction].groupby("iso").size().sort_values(ascending=False)
    nojoin = bc[bc.iso.isna()]
    s = pd.read_csv(R + "distributed_model_2026_11_nan_sample.csv")
    samp = (
        s.groupby("iso")
        .agg(
            chunks=("gauge_id", "size"),
            basins=("chunk_basins", "sum"),
            ra=("reanalysis_nan_pct", "max"),
            rf=("reforecast_nan_pct", "max"),
            allnan=("reanalysis_allnan_basins", "sum"),
        )
        .reset_index()
        .to_dict("records")
    )
    out = {
        "countries": rows,
        "missing_top": [{"iso": k, "n": int(v)} for k, v in miss.head(6).items()],
        "totals": {
            "outlets": len(bc),
            "with_pred": int(bc.has_prediction.sum()),
            "missing": int((~bc.has_prediction).sum()),
            "nojoin": len(nojoin),
            "nojoin_pred": int(nojoin.has_prediction.sum()),
        },
        "sample": samp,
    }
    json.dump(out, open(R + "page/page_data.json", "w"), default=int)
    print("page_data.json written:", out["totals"])
