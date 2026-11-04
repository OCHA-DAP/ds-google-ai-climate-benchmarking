"""Map every trigger station in `stations.py` to a sub-basin of the November 2026 release.

Two cases:

- The station already has a Flood Hub gauge id (`hybas_<id>`). The release keys its basins
  `subhybas_<id>` on the same HydroBASINS numbering, so the mapping is the identity. Verified
  4 Nov 2026 for all 31 ids used in the Nigeria, Somalia and Nepal work. The script checks
  presence and raises if an id is missing.
- The station is a real gauge with coordinates only (N'Djamena, Bahadurabad, Mawa, Niamey,
  Akokoro). The nearest outlet in Google's UNOFFICIAL outlet file is taken, with the distance
  and the release's own 2-year flow written out so a wrong river is visible: a 2-yr flow an
  order of magnitude off the station's known discharge means the nearest outlet is a tributary.
  These rows are flagged `needs_check` and must be confirmed by a human before scoring.

Writes outputs/stations_mapped.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from grrr_2026_11 import open_release
from stations import STATIONS

RADIUS_KM = 10.0


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    d = (
        np.sin((p2 - p1) / 2) ** 2
        + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * r * np.arcsin(np.sqrt(d))


def main() -> int:
    _, _, return_periods, outlets = open_release()
    out = outlets.to_dataframe().reset_index()
    out = out[out.gauge_id.isin(return_periods.index)]  # only basins with predictions
    rows = []
    for s in STATIONS:
        if s.hybas_id:
            gid = "sub" + s.hybas_id
            if gid not in return_periods.index:
                raise KeyError(f"{s.name}: {gid} is not in the release")
            loc = out[out.gauge_id == gid]
            rows.append(
                {
                    "station": s.name,
                    "framework": s.framework,
                    "iso3": s.iso3,
                    "subhybas": gid,
                    "method": "identity",
                    "distance_km": 0.0,
                    "outlet_lat": float(loc.latitude.iloc[0]) if len(loc) else np.nan,
                    "outlet_lon": float(loc.longitude.iloc[0]) if len(loc) else np.nan,
                    "needs_check": False,
                }
            )
        else:
            # The nearest outlet is often a small tributary draining past the gauge. A river
            # gauge sits on the main stem, which is the largest basin close by, so take the
            # outlet with the largest 2-yr flow within RADIUS_KM; report the distance so a
            # human can judge it.
            d = haversine_km(s.lat, s.lon, out.latitude.values, out.longitude.values)
            near = np.flatnonzero(d <= RADIUS_KM)
            if len(near) == 0:
                raise LookupError(
                    f"{s.name}: no outlet within {RADIUS_KM} km of ({s.lat}, {s.lon})"
                )
            rp2_near = return_periods.loc[out.gauge_id.iloc[near], 2.0].values
            i = int(near[np.argmax(rp2_near)])
            gid = out.gauge_id.iloc[i]
            rows.append(
                {
                    "station": s.name,
                    "framework": s.framework,
                    "iso3": s.iso3,
                    "subhybas": gid,
                    "method": f"largest_within_{RADIUS_KM:g}km",
                    "distance_km": float(d[i]),
                    "outlet_lat": float(out.latitude.iloc[i]),
                    "outlet_lon": float(out.longitude.iloc[i]),
                    "needs_check": True,
                }
            )
        rows[-1]["rp2_m3s"] = float(return_periods.loc[rows[-1]["subhybas"], 2.0])
        rows[-1]["rp5_m3s"] = float(return_periods.loc[rows[-1]["subhybas"], 5.0])
        rows[-1]["known_rp2_m3s"] = s.known_rp2
        rows[-1]["season_months"] = "".join(
            str(m) if m < 10 else chr(55 + m) for m in s.season_months
        )
    df = pd.DataFrame(rows)
    Path("outputs").mkdir(exist_ok=True)
    df.to_csv("outputs/stations_mapped.csv", index=False)
    pd.set_option("display.width", 200)
    print(
        df[
            [
                "station",
                "framework",
                "subhybas",
                "method",
                "distance_km",
                "rp2_m3s",
                "known_rp2_m3s",
                "needs_check",
            ]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
