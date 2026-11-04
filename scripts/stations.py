"""Trigger stations of the CERF flood frameworks, as the benchmark addresses them.

One entry per station and season. `hybas_id` is the Flood Hub gauge id the framework uses
(None for real gauges that Google never served). Coordinates and ids are copied from the
spoke repos' constants on 4 Nov 2026:

- Nigeria: `ds-aa-nga-flooding/src/constants.py` (ACTION_GAUGE_THRESHOLDS, 10 GRRR gauges)
- Somalia: `ds-aa-som-floods/src/constants.py` (STATIONS, TRIGGER_STATIONS)
- Nepal: `ds-aa-npl-flooding/src/constants.py`
- Chad: `pa-aa-tcd-flooding/src/constants.py` (GloFAS cell at N'Djamena)
- Bangladesh: `pa-aa-bgd-flooding/src/bgd.yaml` (GloFAS reporting points)
- Uganda: `ds-aa-uga-flooding/src/constants.py` (G5196 gauge)
- Niger: Niamey, GRDC 1234150; coordinates approximate, to be confirmed against the GRDC
  catalogue before any scoring.

Season months are the framework's own window where it states one, else the flood season the
framework page describes. `known_rp2` is a published 2-yr discharge where the team has one
(GloFAS at N'Djamena), used only as a sanity check on the nearest-outlet mapping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    name: str
    framework: str
    iso3: str
    hybas_id: str | None
    lat: float | None
    lon: float | None
    season_months: tuple[int, ...]
    known_rp2: float | None = None


AUG_NOV = (8, 9, 10, 11)
JUN_SEP = (6, 7, 8, 9)
GU = (4, 5, 6)
DEYR = (10, 11, 12)
OCT_DEC = (10, 11, 12)

NGA_GAUGES = {
    "hybas_1120842990": None,
    "hybas_1120843610": None,
    "hybas_1120845060": None,
    "hybas_1120849600": None,
    "hybas_1120848550": None,
    "hybas_1121970280": None,
    "hybas_1120842550": "Wuroboki",  # quality-verified gauge, the 2025 single station
    "hybas_1120840700": None,
    "hybas_1120840560": None,
    "hybas_1120840690": "tributary outlier",
}

SOM_GAUGES = {  # upstream to downstream; the seven SWALIM gauges the trigger is built on
    "Dollow": "hybas_1121039440",
    "Luuq": "hybas_1122050700",
    "Bardheere": "hybas_1121087010",
    "Bualle": "hybas_1121116000",
    "Belet Weyne": "hybas_1121024250",
    "Bulo Burti": "hybas_1121049060",
    "Jowhar": "hybas_1122059030",
}

STATIONS: list[Station] = []
for gid, label in NGA_GAUGES.items():
    nm = f"NGA {gid.replace('hybas_', '')}" + (f" ({label})" if label else "")
    STATIONS.append(Station(nm, "Nigeria 2026 action", "NGA", gid, None, None, AUG_NOV))
for nm, gid in SOM_GAUGES.items():
    STATIONS.append(Station(f"{nm} (Gu)", "Somalia", "SOM", gid, None, None, GU))
    STATIONS.append(Station(f"{nm} (Deyr)", "Somalia", "SOM", gid, None, None, DEYR))
STATIONS += [
    Station(
        "Chatara (Koshi)",
        "Nepal 2025 readiness",
        "NPL",
        "hybas_4120864110",
        26.867,
        87.160,
        JUN_SEP,
    ),
    Station(
        "Chisapani (Karnali)",
        "Nepal, out of 2025 scope",
        "NPL",
        "hybas_4121455820",
        28.64,
        81.29,
        JUN_SEP,
    ),
    Station(
        "N'Djamena (Chari)", "Chad 2025", "TCD", None, 12.125, 15.025, AUG_NOV, known_rp2=4030.0
    ),
    Station("Bahadurabad (Jamuna)", "Bangladesh 2025", "BGD", None, 25.15, 89.65, JUN_SEP),
    Station("Mawa (Padma)", "Bangladesh 2025 action", "BGD", None, 23.472, 90.257, JUN_SEP),
    Station("Niamey (Niger), local flood", "Niger 2025", "NER", None, 13.517, 2.083, (8, 9)),
    Station("Niamey (Niger), Guinean flood", "Niger 2025", "NER", None, 13.517, 2.083, (12, 1, 2)),
    Station("Akokoro G5196 (Teso)", "Uganda dev", "UGA", None, 1.80, 33.90, OCT_DEC),
]
