#!/usr/bin/env python3
"""Refinement runs: (1) better standard-arm selection for Maxwell-Wien / Schering,
(2) Kelvin with an ideal x10 gain stage on the two detector nodes (optimistic estimate)."""
import math
from dataclasses import replace

import numpy as np

import mei_sim as ms

W = 2 * np.pi * ms.F0
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]


def e12_list(lo_dec, hi_dec):
    return [m * 10 ** d for d in range(lo_dec, hi_dec + 1) for m in E12]


def nearest(x, options):
    return min(options, key=lambda o: abs(math.log10(x / o)))


def maxwell_cases():
    out = []
    for l, rdc in [(10e-3, 8.0), (22e-3, 18.0), (47e-3, 35.0), (100e-3, 60.0)]:
        r2, c4 = 1e3, 100e-9
        r3 = nearest(l / (r2 * c4), [100.0, 470.0, 1e3])
        r4 = nearest(r2 * r3 / rdc, e12_list(3, 4) + [1e5])
        zt = 1 / (1 / (rdc + 1j * W * l) + 1j * W * 30e-12)
        zg = r2 * r3 / r4 + 1j * W * r2 * r3 * c4
        out.append(dict(bridge="Maxwell-Wien", id=f"L {l * 1e3:g}mH (R3={r3:g}, R4={r4:g})", kind="L",
                        builder=ms.b_maxwell, p_nom=dict(R2=r2, R3=r3, R4=r4, C4=c4, esr4=0.0),
                        ptype=dict(R2="R", R3="R", R4="R", C4="C", esr4="esr"),
                        z_true=complex(zt), z_guess=complex(zg)))
    return out


def schering_cases():
    out = []
    cn = 100e-9
    for cx, esr in [(10e-9, 15.9), (47e-9, 3.39), (100e-9, 63.7), (220e-9, 0.723), (1e-6, 0.318), (10e-6, 2.0)]:
        zx = abs(1 / (W * cx))
        r3 = nearest(zx, [100.0, 1e3, 1e4])
        r4 = nearest(cx * r3 / cn, e12_list(2, 4) + [1e5])
        c4 = min([1e-9, 10e-9], key=lambda c: abs(math.log10(r3 * c / cn / esr)))
        zt = esr + 1 / (1j * W * cx)
        zg = r3 * c4 / cn + 1 / (1j * W * (cn * r4 / r3))
        out.append(dict(bridge="Schering", id=f"C {cx * 1e9:g}nF (R3={r3:g}, R4={r4:g}, C4={c4 * 1e9:g}nF)", kind="C",
                        builder=ms.b_schering,
                        p_nom=dict(R3=r3, R4=r4, C4=c4, CN=cn, esr4=0.0, esrN=0.0),
                        ptype=dict(R3="R", R4="R", C4="C", CN="C", esr4="esr", esrN="esr"),
                        z_true=complex(zt), z_guess=complex(zg)))
    return out


def run(case, scen, n, seed):
    rng = np.random.default_rng(seed)
    acc = {}
    for _ in range(n):
        m = ms.metrics(case, ms.run_trial(case, scen, ms.SRC_ALL, rng))
        for k, v in m.items():
            acc.setdefault(k, []).append(v)
    return {k: (float(np.std(v, ddof=1)), float(np.percentile(np.abs(v), 95))) for k, v in acc.items()}


def row(case, st):
    ok = st["mag"][1] <= 0.5 and st["ph"][1] <= 0.5
    ex = ""
    if "L" in st:
        ex = f"L p95 {st['L'][1]:.2f} %"
    if "C" in st:
        ex = f"C p95 {st['C'][1]:.2f} %, d tan p95 {st['dtan'][1]:.4f}"
    return (f"| {case['id']} | {st['mag'][0]:.3f} | {st['mag'][1]:.3f} | {st['ph'][0]:.3f} | "
            f"{st['ph'][1]:.3f} | {ex} | {'PASS' if ok else 'FAIL'} |")


if __name__ == "__main__":
    lines = []
    hdr = ("| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |\n"
           "|---|---|---|---|---|---|---|")
    seed = 5000
    for sk in ("S2", "S3"):
        for name, cs in (("Maxwell-Wien, improved arm choice", maxwell_cases()),
                         ("Schering, improved arm choice", schering_cases())):
            lines += [f"\n### {name}, {ms.SCEN[sk].name}\n", hdr]
            for c in cs:
                seed += 1
                lines.append(row(c, run(c, ms.SCEN[sk], 400, seed)))

    kc = ms.build_cases()["Kelvin"]
    for sk in ("S2", "S3"):
        lines += [f"\n### Kelvin with ideal x10 gain on detector nodes (noise / 10), {ms.SCEN[sk].name}\n", hdr]
        for c in kc:
            seed += 1
            scen = replace(ms.SCEN[sk], noise_mv=ms.SCEN[sk].noise_mv / 10)
            lines.append(row(c, run(c, scen, 400, seed)))
    open("refine_tables.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
