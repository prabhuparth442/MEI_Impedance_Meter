#!/usr/bin/env python3
"""Run the Monte Carlo experiments and write results.json + results_tables.md"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

import mei_sim as ms

N_MAIN = int(os.environ.get("N_MAIN", 400))
N_BUD = int(os.environ.get("N_BUD", 250))
TARGET_MAG, TARGET_PH = 0.5, 0.5       # proposed PASS targets (percent, degrees), 95th percentile

REP = {"Wheatstone": [2, 7], "Kelvin": [0, 3], "Maxwell-Wien": [0, 3], "Schering": [1, 4]}


def work(job):
    br, idx, scen_key, over, src, n, seed = job
    case = ms.build_cases()[br][idx]
    scen = replace(ms.SCEN[scen_key], **over)
    rng = np.random.default_rng(seed)
    acc = {}
    bad = 0
    for _ in range(n):
        try:
            z = ms.run_trial(case, scen, src, rng)
            m = ms.metrics(case, z)
            if not np.isfinite(m["mag"]):
                raise ValueError
        except Exception:
            bad += 1
            continue
        for k, v in m.items():
            acc.setdefault(k, []).append(v)
    return (br, idx, scen_key, json.dumps(over), json.dumps(src),
            {k: list(map(float, v)) for k, v in acc.items()}, bad)


def stats(a):
    a = np.asarray(a)
    return dict(mean=float(a.mean()), std=float(a.std(ddof=1)), p95=float(np.percentile(np.abs(a), 95)))


def main():
    cases = ms.build_cases()
    jobs = []
    seed = 1000
    for sk in ("S1", "S2", "S3"):
        for br, lst in cases.items():
            for i in range(len(lst)):
                seed += 1
                jobs.append((br, i, sk, {}, ms.SRC_ALL, N_MAIN, seed))
    main_n = len(jobs)
    for sk in ("S2", "S3"):
        for br, idxs in REP.items():
            for i in idxs:
                for s in ms.SRC_KEYS:
                    seed += 1
                    src = dict(ms.SRC_NONE)
                    src[s] = True
                    jobs.append((br, i, sk, {}, src, N_BUD, seed))
    bud_n = len(jobs) - main_n
    for br, idxs in REP.items():
        for i in idxs:
            for g in (1e-4, 5e-4, 2e-3):
                seed += 1
                jobs.append((br, i, "S3", {"gmis": g}, ms.SRC_ALL, N_BUD, seed))

    print(f"{len(jobs)} jobs ({main_n} main, {bud_n} budget), N_MAIN={N_MAIN}, N_BUD={N_BUD}", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(work, jobs, chunksize=4))
    print(f"done in {time.time() - t0:.0f} s", flush=True)

    out = []
    for br, idx, sk, over, src, acc, bad in results:
        out.append(dict(bridge=br, idx=idx, case=cases[br][idx]["id"], scen=sk, over=json.loads(over),
                        src=json.loads(src), bad=bad, stats={k: stats(v) for k, v in acc.items()}))
    json.dump(out, open("results.json", "w"), indent=1)

    def is_all(r):
        return all(r["src"].values())

    lines = []
    for sk in ("S1", "S2", "S3"):
        lines.append(f"\n### {ms.SCEN[sk].name}\n")
        lines.append("| Bridge | Case | \\|Z\\| err std % | \\|Z\\| err p95 % | phase err std deg | phase err p95 deg | extra metric (p95) | 0.5 % / 0.5 deg |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in out:
            if r["scen"] != sk or r["over"] or not is_all(r):
                continue
            s = r["stats"]
            if "L" in s:
                extra = f"L {s['L']['p95']:.2f} %, dR {s['dR']['p95']:.2f} ohm"
            elif "C" in s:
                extra = f"C {s['C']['p95']:.2f} %, d tan {s['dtan']['p95']:.4f}"
            else:
                extra = ""
            ok = s["mag"]["p95"] <= TARGET_MAG and s["ph"]["p95"] <= TARGET_PH
            lines.append(f"| {r['bridge']} | {r['case']} | {s['mag']['std']:.3f} | {s['mag']['p95']:.3f} | "
                         f"{s['ph']['std']:.3f} | {s['ph']['p95']:.3f} | {extra} | {'PASS' if ok else 'FAIL'}"
                         f"{' (bad ' + str(r['bad']) + ')' if r['bad'] else ''} |")

    for sk in ("S2", "S3"):
        lines.append(f"\n### Error budget, one source at a time, {ms.SCEN[sk].name} (std of |Z| error % / phase error deg)\n")
        hdr = "| Bridge | Case | " + " | ".join(ms.SRC_LABEL[s] for s in ms.SRC_KEYS) + " | all together |"
        lines.append(hdr)
        lines.append("|---|---|" + "---|" * (len(ms.SRC_KEYS) + 1))
        for br, idxs in REP.items():
            for i in idxs:
                cells = []
                for s in ms.SRC_KEYS:
                    r = next(x for x in out if x["bridge"] == br and x["idx"] == i and x["scen"] == sk
                             and not x["over"] and x["src"][s] and sum(x["src"].values()) == 1)
                    cells.append(f"{r['stats']['mag']['std']:.3f} / {r['stats']['ph']['std']:.3f}")
                a = next(x for x in out if x["bridge"] == br and x["idx"] == i and x["scen"] == sk
                         and not x["over"] and is_all(x))
                cells.append(f"{a['stats']['mag']['std']:.3f} / {a['stats']['ph']['std']:.3f}")
                lines.append(f"| {br} | {cases[br][i]['id']} | " + " | ".join(cells) + " |")

    lines.append("\n### ADC channel gain mismatch sweep (S3 otherwise; p95 of |Z| error % / phase error deg)\n")
    lines.append("| Bridge | Case | 0.01 % | 0.05 % | 0.2 % |")
    lines.append("|---|---|---|---|---|")
    for br, idxs in REP.items():
        for i in idxs:
            cells = []
            for g in (1e-4, 5e-4, 2e-3):
                r = next(x for x in out if x["bridge"] == br and x["idx"] == i and x["scen"] == "S3"
                         and x["over"].get("gmis") == g)
                cells.append(f"{r['stats']['mag']['p95']:.3f} / {r['stats']['ph']['p95']:.3f}")
            lines.append(f"| {br} | {cases[br][i]['id']} | " + " | ".join(cells) + " |")
    open("results_tables.md", "w").write("\n".join(lines) + "\n")
    print("wrote results.json and results_tables.md", flush=True)


if __name__ == "__main__":
    main()
