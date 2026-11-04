"""Where does Google's November 2026 release have usable output?

Two checks, because "coverage" has two failure modes:

1. **Is there a basin at all?** The outlet file lists 1,034,083 HydroBasins sub-basins; the
   release carries predictions for 970,005 of them. Every outlet is joined to a country
   (Natural Earth 50m admin-0) and the basins with and without predictions are counted per
   country.
2. **Is the series real?** A basin can exist and be all NaN. For each requested country,
   `--sample` basins are drawn at random; each one's 128-basin chunk is read in full from
   both stores, and the NaN share and the number of all-NaN basins in that chunk are
   reported. 3 samples per country means ~384 basins inspected per country.

Outputs go to `outputs/` (gitignored):
    grrr_2026_11_basins_by_country.csv    every basin: id, lat, lon, iso, has_prediction
    grrr_2026_11_coverage_summary.csv     per country: basins, with_prediction, missing
    grrr_2026_11_nan_sample.csv           per sampled chunk: NaN shares, all-NaN counts

Results on 4 Nov 2026 are written up in docs/grrr-2026-11.md.

Usage:
    uv run scripts/check_grrr_coverage.py --iso NGA SOM NPL TCD BGD NER BFA UGA
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from grrr_2026_11 import RELEASE, open_release

NE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_50m_admin_0_countries.geojson"
)
CHUNK = 128  # basins per zarr chunk along gauge_id, in both stores


def natural_earth(cache: Path) -> gpd.GeoDataFrame:
    f = cache / "ne_50m_admin_0_countries.geojson"
    if not f.exists():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(NE_URL, f)
    ne = gpd.read_file(f)[["ADM0_A3", "ISO_A3", "NAME", "geometry"]]
    # Natural Earth leaves ISO_A3 as -99 for a few territories; fall back to ADM0_A3
    ne["iso"] = ne.ISO_A3.where(ne.ISO_A3 != "-99", ne.ADM0_A3)
    return ne


def basins_by_country(cache: Path) -> pd.DataFrame:
    _, _, return_periods, outlets = open_release()
    o = outlets.to_dataframe().reset_index()
    o["has_prediction"] = o.gauge_id.isin(return_periods.index)
    missing_outlet = (~return_periods.index.isin(o.gauge_id)).sum()
    if missing_outlet:
        print(
            f"note: {missing_outlet} basins with predictions have no outlet location",
            file=sys.stderr,
        )
    g = gpd.GeoDataFrame(o, geometry=gpd.points_from_xy(o.longitude, o.latitude), crs="EPSG:4326")
    j = gpd.sjoin(g, natural_earth(cache), how="left", predicate="within")
    # an outlet on the coast or in a lake can fall outside every polygon: keep it, iso = NaN
    return j[["gauge_id", "latitude", "longitude", "iso", "NAME", "has_prediction"]].rename(
        columns={"NAME": "country"}
    )


def sample_nan(by_country: pd.DataFrame, isos: list[str], n: int, seed: int) -> pd.DataFrame:
    reanalysis, reforecast, _, _ = open_release()
    ids = pd.Index(reanalysis.gauge_id.values)
    with_pred = by_country[by_country.has_prediction]
    rng = np.random.default_rng(seed)
    rows = []
    for iso in isos:
        pool = with_pred[with_pred.iso == iso]
        if pool.empty:
            raise LookupError(f"{iso}: no basin with predictions joined to this country")
        for gid in pool.sample(min(n, len(pool)), random_state=int(rng.integers(1 << 31))).gauge_id:
            i = ids.get_loc(gid)
            c0 = (i // CHUNK) * CHUNK
            sl = slice(c0, min(c0 + CHUNK, len(ids)))
            ra = reanalysis.streamflow.isel(gauge_id=sl).values
            rf = reforecast.streamflow.isel(gauge_id=sl).values
            rows.append(
                {
                    "iso": iso,
                    "gauge_id": gid,
                    "chunk_start": c0,
                    "chunk_basins": ra.shape[0],
                    "reanalysis_nan_pct": 100 * float(np.isnan(ra).mean()),
                    "reforecast_nan_pct": 100 * float(np.isnan(rf).mean()),
                    "reanalysis_allnan_basins": int(np.isnan(ra).all(axis=1).sum()),
                    "reforecast_allnan_basins": int(np.isnan(rf).all(axis=(1, 2)).sum()),
                    "this_basin_reanalysis_max": float(np.nanmax(ra[i - c0])),
                }
            )
            print(rows[-1], flush=True)
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--iso", nargs="+", required=True, help="ISO3 codes to report and sample")
    p.add_argument("--sample", type=int, default=3, help="basins (chunks) to read per country")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=Path, default=Path("outputs"))
    p.add_argument("--cache", type=Path, default=Path("cache"))
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)

    bc = basins_by_country(a.cache)
    bc.to_csv(a.out / f"{RELEASE}_basins_by_country.csv", index=False)
    print(f"outlets {len(bc)}, with predictions {int(bc.has_prediction.sum())}")

    summary = (
        bc[bc.iso.isin(a.iso)]
        .groupby("iso")
        .has_prediction.agg(basins="size", with_prediction="sum")
        .assign(missing=lambda t: t.basins - t.with_prediction)
    )
    unmatched = [i for i in a.iso if i not in summary.index]
    if unmatched:
        raise LookupError(
            f"no basin outlet joined to {unmatched}; check the ISO3 code against Natural Earth"
        )
    summary.to_csv(a.out / f"{RELEASE}_coverage_summary.csv")
    print(summary.to_string())
    top_missing = bc[~bc.has_prediction].groupby("iso").size().sort_values(ascending=False).head(6)
    print("basins without predictions, worldwide, by country:")
    print(top_missing.to_string())

    s = sample_nan(bc, a.iso, a.sample, a.seed)
    s.to_csv(a.out / f"{RELEASE}_nan_sample.csv", index=False)
    print(
        f"sampled {len(s)} chunks ({int(s.chunk_basins.sum())} basins): "
        f"max NaN share reanalysis {s.reanalysis_nan_pct.max():.3f}%, reforecast {s.reforecast_nan_pct.max():.3f}%; "
        f"all-NaN basins {int(s.reanalysis_allnan_basins.sum())} / {int(s.reforecast_allnan_basins.sum())}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
