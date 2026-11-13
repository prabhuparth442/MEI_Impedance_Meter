#!/usr/bin/env python3
"""
monte_carlo.py - repeat run_wheatstone.py over many random "true" bridges and ADC noise seeds.

    python3 monte_carlo.py                       # 40 seeds, datasheet-typical settings
    python3 monte_carlo.py --n 100 --tol 0.01    # 1 % resistors
    python3 monte_carlo.py --rpin 170 --noise-mv 1.86   # datasheet worst case

Uses the fast toy op-amp (--opamp simple): the Microchip macromodel takes ~9 min per run
and gave the same answer within the window scatter (see README).
"""
import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=40)
ap.add_argument("--jobs", type=int, default=4)
ap.add_argument("--rx", type=float, default=2200.0)
ap.add_argument("--tol", type=float, default=0.001)
ap.add_argument("--rpin", type=float, default=100.0)
ap.add_argument("--noise-mv", type=float, default=1.3)
ap.add_argument("--windows", type=int, default=6)
args = ap.parse_args()

here = Path(__file__).parent
pat = re.compile(r"^\s*(bridge|divider): mean ([\d.]+) ohm, error ([+-][\d.]+) %")


def one(seed):
    cmd = [sys.executable, str(here / "run_wheatstone.py"), "--opamp", "simple", "--seed", str(seed),
           "--rx", str(args.rx), "--tol", str(args.tol), "--rpin", str(args.rpin),
           "--noise-mv", str(args.noise_mv), "--windows", str(args.windows)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=here).stdout
    return {m.group(1): float(m.group(3)) for m in map(pat.match, out.splitlines()) if m}


with ThreadPoolExecutor(args.jobs) as ex:
    runs = list(ex.map(one, range(1, args.n + 1)))
runs = [r for r in runs if len(r) == 2]
print(f"{len(runs)} runs  Rx={args.rx:g}  tol=+-{args.tol * 100:g}%  rpin={args.rpin:g}  noise={args.noise_mv} mV")
for k in ("bridge", "divider"):
    e = np.array([r[k] for r in runs])
    print(f"{k:>8}: mean {e.mean():+.3f} %  std {e.std(ddof=1):.3f} %  "
          f"worst |err| {np.abs(e).max():.3f} %  95th pct |err| {np.percentile(np.abs(e), 95):.3f} %")
