"""The backfill as Databricks ran it: every run of the mirror job since a given run, with its
state, hours and cost at the single-node rate, and the years whose load marker was written while
it ran. Writes outputs/glofas_mirror/backfill.json so the page reports the run from the API,
not from memory.

    uv run scripts/glofas_mirror_runs.py --job 748542173483203 --since-run 586864369657320
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import glofas_mirror as gm

OUT = Path("outputs/glofas_mirror")
VM_USD_H = 0.229  # Standard_DS3_v2 on-demand, East US 2, Azure retail price API, 10 Nov 2026
DBU_USD_H = 0.75 * 0.30  # 0.75 DBU/h for DS3_v2 at the Jobs Compute premium list price


def cli(*args) -> dict:
    return json.loads(subprocess.check_output(["databricks", *args, "--profile", "DEFAULT"]))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job", required=True)
    p.add_argument("--since-run", required=True, help="first run of the backfill")
    a = p.parse_args(argv)
    runs = cli("jobs", "list-runs", "--job-id", a.job, "--expand-tasks", "-o", "json")
    runs = runs if isinstance(runs, list) else runs.get("runs", [])
    runs = sorted(runs, key=lambda r: r["start_time"])
    first = next(r for r in runs if str(r["run_id"]) == a.since_run)
    runs = [r for r in runs if r["start_time"] >= first["start_time"]]
    loaded = gm.loaded_years()
    out, total_h = [], 0.0
    for r in runs:
        s, e = r["start_time"] / 1000, (r.get("end_time") or 0) / 1000
        if not e:
            raise RuntimeError(f"run {r['run_id']} has not ended; rerun when it has")
        h = (e - s) / 3600
        total_h += h
        t0, t1 = (dt.datetime.fromtimestamp(x, dt.UTC) for x in (s, e))
        years = sorted(
            int(y)
            for y, rec in loaded.items()
            if t0 <= dt.datetime.fromisoformat(rec["loaded_at"]) <= t1
        )
        tasks = {t["task_key"]: t["state"] for t in r.get("tasks", [])}
        failed = [k for k, st in tasks.items() if st.get("result_state") == "FAILED"]
        out.append(
            {
                "run_id": r["run_id"],
                "start": t0.isoformat(timespec="minutes"),
                "end": t1.isoformat(timespec="minutes"),
                "hours": round(h, 2),
                "usd": round(h * (VM_USD_H + DBU_USD_H), 2),
                "result": r["state"].get("result_state"),
                "message": r["state"].get("state_message", "")[:200],
                "failed_task": failed[0] if failed else None,
                "years_loaded": years,
            }
        )
    jobs = gm._jobs()
    attempts = {y: v["attempts"] for y, v in jobs.items() if isinstance(v, dict)}
    res = {
        "job_id": a.job,
        "runs": out,
        "hours": round(total_h, 2),
        "usd": round(total_h * (VM_USD_H + DBU_USD_H), 2),
        "usd_per_hour": round(VM_USD_H + DBU_USD_H, 3),
        "rate_note": "Standard_DS3_v2 on-demand plus 0.75 DBU/h at the Jobs Compute premium list price",
        "ewds_requests": len(attempts),
        "ewds_resubmitted": sorted(y for y, n in attempts.items() if n > 1),
        "years_loaded_total": len(loaded),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "backfill.json").write_text(json.dumps(res, indent=1))
    for r in out:
        print(
            r["run_id"],
            r["start"],
            f"{r['hours']} h",
            r["result"],
            r["failed_task"],
            len(r["years_loaded"]),
            "years",
        )
    print(
        f"total {res['hours']} h, ${res['usd']}, {res['ewds_requests']} EWDS requests, resubmitted {res['ewds_resubmitted']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
