#!/usr/bin/env python3
"""MEI impedance meter: drives the Pico 2 lock-in, calibrates, and identifies the DUT.

  python3 imeter.py measure   --rref 1k [--freqs 250,500,1000]
  python3 imeter.py cal-add   --rref 10k --r 0     (calibration point: DUT terminals shorted)
  python3 imeter.py cal-add   --rref 10k --r open  (calibration point: nothing connected)
  python3 imeter.py cal-add   --rref 10k --r 998.7 (calibration point: known resistor, ohm)
  python3 imeter.py cal-show  --rref 10k           (show the fitted calibration)
  python3 imeter.py selftest                       (checks the model-fitting code, no hardware)

Circuit: V1 -- Rref -- mid -- Zx -- V2 (V2 = DC mid-rail). ADC0 reads V1, ADC1 reads mid.
Z = Rref * H / (1 - H), H = Vmid/V1 (complex phasors from a 500 Hz-style lock-in).
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CAL_FILE = os.path.join(HERE, "cal.json")
PORT = "/dev/ttyACM0"
G1 = 1.00055                      # ADC1/ADC0 DC gain ratio from the three-level test
RREF = {"100": 100.0, "1k": 1000.0, "10k": 9900.0, "100k": 100400.0}   # measured values (config.py)
FREQ_PLAN = {125: (40, 200), 250: (20, 200), 500: (10, 200), 1000: (5, 200)}  # f: (steps/cycle, us/step)
SAMPLES = 400                     # samples per channel per run
REPS = 3
TOL = 0.02                        # model-fit tolerance (instrument accuracy)

PICO = r'''
from machine import ADC, Pin, PWM
from array import array
import time, math, gc
pa = PWM(Pin(14), freq=150000, duty_u16=32768)
pb = PWM(Pin(15), freq=150000, duty_u16=32768)
Pin(23, Pin.OUT).value(1)
a0, a1 = ADC(26), ADC(27)
N, STEP, PRE, REC, REPS = @N@, @STEP@, @PRE@, @REC@, @REPS@
tab = [int(65535 * (0.5 + 0.40 * math.sin(2 * math.pi * k / N))) for k in range(N)]
nrec = REC * N
ticks_us, ticks_diff, ticks_add = time.ticks_us, time.ticks_diff, time.ticks_add
for rep in range(REPS):
    t0a = array('I', bytes(4 * nrec)); t1a = array('I', bytes(4 * nrec)); t2a = array('I', bytes(4 * nrec))
    va = array('H', bytes(2 * nrec)); vb = array('H', bytes(2 * nrec))
    gc.collect(); gc.disable()
    nxt = ticks_us(); start = nxt; j = 0; slips = 0
    for k in range((PRE + REC) * N):
        while ticks_diff(nxt, ticks_us()) > 0: pass
        if ticks_diff(ticks_us(), nxt) > 20: slips += 1
        pa.duty_u16(tab[k % N])
        if k >= PRE * N:
            t0a[j] = ticks_us(); va[j] = a0.read_u16()
            t1a[j] = ticks_us(); vb[j] = a1.read_u16()
            t2a[j] = ticks_us(); j += 1
        nxt = ticks_add(nxt, STEP)
    gc.enable()
    print("REP", rep, "start", start, "slips", slips)
    for name, arr in (("T0", t0a), ("T1", t1a), ("T2", t2a), ("VA", va), ("VB", vb)):
        print(name, ",".join(map(str, arr)))
pa.duty_u16(32768)
print("DONE")
'''


# ---------------------------------------------------------------- hardware
def run_pico(f):
    n, step = FREQ_PLAN[f]
    rec = SAMPLES // n
    pre = max(8, int(0.05 * f))
    src = PICO
    for k, v in (("@N@", n), ("@STEP@", step), ("@PRE@", pre), ("@REC@", rec), ("@REPS@", REPS)):
        src = src.replace(k, str(v))
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "run.py")
        open(p, "w").write(src)
        try:
            r = subprocess.run(["mpremote", "connect", PORT, "run", p], capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            sys.exit("Pico did not respond (timeout). Run ./pico_check.sh and replug the USB cable.")
    if "DONE" not in r.stdout:
        sys.exit("Pico run failed. Run ./pico_check.sh and replug the USB cable.\n" + (r.stderr or r.stdout)[-400:])
    reps, cur = [], None
    for line in r.stdout.splitlines():
        if line.startswith("REP"):
            if cur: reps.append(cur)
            p_ = line.split(); cur = {"start": float(p_[3]), "slips": int(p_[5])}
        for key in ("T0", "T1", "T2", "VA", "VB"):
            if line.startswith(key + " ") and cur is not None:
                cur[key] = np.array([float(x) for x in line[3:].split(",")])
    if cur: reps.append(cur)
    return reps


def phasor(t_us, counts, f):
    v = counts / 65535 * 3300.0
    v = v - v.mean()
    return 2 * np.sum(v * np.exp(-2j * np.pi * f * t_us * 1e-6)) / len(v)


def analyse_runs(reps, f):
    """-> (H complex mean over reps, list of per-rep H, warnings)"""
    M, Hs, warn = 2 ** 30, [], []
    for r in reps:
        t0 = (r["T0"] - r["start"]) % M; t1 = (r["T1"] - r["start"]) % M; t2 = (r["T2"] - r["start"]) % M
        ta, tb = (t0 + t1) / 2, (t1 + t2) / 2
        fs = f * np.arange(0.9, 1.1001, 0.005)
        pk = fs[np.argmax([abs(phasor(ta, r["VA"], x)) for x in fs])]
        if abs(pk - f) / f > 0.01:
            warn.append(f"excitation peak at {pk:.1f} Hz, expected {f} Hz: loop timing slipped")
        if r["slips"] > 3:
            warn.append(f"{r['slips']} timing slips in a run")
        lo, hi = r["VA"].min() / 65535 * 3300, r["VA"].max() / 65535 * 3300
        lo2, hi2 = r["VB"].min() / 65535 * 3300, r["VB"].max() / 65535 * 3300
        if min(lo, lo2) < 100 or max(hi, hi2) > 3200:
            warn.append("ADC near its limits (clipping risk)")
        V1 = phasor(ta, r["VA"], f)
        Vm = phasor(tb, r["VB"], f) / G1
        Hs.append(Vm / V1)
    return np.mean(Hs), Hs, sorted(set(warn))


# ---------------------------------------------------------------- calibration
# Model: H_measured = k * H_true + c  (complex k = gain/phase error, c = leakage/offset).
# Known points: short (H_true = 0), open (H_true = 1), known resistor R (H_true = R/(Rref+R)).
def load_cal():
    try:
        return json.load(open(CAL_FILE))
    except Exception:
        return {}


def save_cal(c):
    json.dump(c, open(CAL_FILE, "w"), indent=1)


def h_true(r, rref_ohm):
    return 1 + 0j if r == "open" else r / (rref_ohm + r) + 0j


def fit_cal(pts, rref_ohm):
    """pts: list of {"R": float|'open', "H": [re, im]} -> (k, c, n, max_residual)"""
    if not pts: return 1 + 0j, 0j, 0, 0.0
    Ht = np.array([h_true(p["R"], rref_ohm) for p in pts])
    Hm = np.array([complex(*p["H"]) for p in pts])
    if len(pts) == 1:
        if Ht[0] == 0: return 1 + 0j, Hm[0], 1, 0.0
        return Hm[0] / Ht[0], 0j, 1, 0.0
    A = np.column_stack([Ht, np.ones(len(pts))])
    (k, c), *_ = np.linalg.lstsq(A, Hm, rcond=None)
    return k, c, len(pts), float(np.max(np.abs(A @ np.array([k, c]) - Hm)))


def get_cal(cal, rref, f):
    pts = cal.get(rref, {}).get(str(f), {}).get("pts", [])
    return fit_cal(pts, RREF[rref])


def z_from_h(H, rref_ohm, k=1 + 0j, c=0j):
    Hc = (H - c) / k
    return rref_ohm * Hc / (1 - Hc)


# ---------------------------------------------------------------- model fitting
def _fmt_c(c):
    return f"{c*1e9:.2f} nF" if c < 1e-6 else f"{c*1e6:.3f} uF"


def _fmt_l(l):
    return f"{l*1e3:.3f} mH" if l >= 1e-3 else f"{l*1e6:.2f} uH"


def fit_models(freqs, Z):
    w = 2 * np.pi * np.asarray(freqs, float)
    Z = np.asarray(Z, complex)
    Y = 1 / Z
    wz, wy = 1 / np.abs(Z) ** 2, 1 / np.abs(Y) ** 2
    slope = lambda x, y, wt: np.sum(wt * x * y) / np.sum(wt * x * x)
    Rs = np.sum(wz * Z.real) / np.sum(wz)
    Ls = slope(w, Z.imag, wz)
    xc = slope(-1 / w, Z.imag, wz)        # Im Z = -xc/w, xc = 1/C
    G = np.sum(wy * Y.real) / np.sum(wy)
    Cp = slope(w, Y.imag, wy)
    xl = slope(-1 / w, Y.imag, wy)        # Im Y = -xl/w, xl = 1/L
    cands = []
    if Rs > 0:  cands.append(("R", 1, f"R = {Rs:.2f} ohm", Rs + 0j * w))
    if Ls > 0:  cands.append(("L", 1, f"L = {_fmt_l(Ls)}", 1j * w * Ls))
    if Cp > 0:  cands.append(("C", 1, f"C = {_fmt_c(Cp)}", 1 / (1j * w * Cp)))
    if Rs > 0 and Ls > 0: cands.append(("R + L (series)", 2, f"R = {Rs:.2f} ohm, L = {_fmt_l(Ls)}", Rs + 1j * w * Ls))
    if Rs > 0 and xc > 0: cands.append(("R + C (series)", 2, f"R = {Rs:.2f} ohm, C = {_fmt_c(1/xc)}", Rs - 1j * xc / w))
    if G > 0 and Cp > 0:  cands.append(("R || C (parallel)", 2, f"R = {1/G:.2f} ohm, C = {_fmt_c(Cp)}", 1 / (G + 1j * w * Cp)))
    if G > 0 and xl > 0:  cands.append(("R || L (parallel)", 2, f"R = {1/G:.2f} ohm, L = {_fmt_l(1/xl)}", 1 / (G - 1j * xl / w)))
    out = []
    for name, npar, desc, Zm in cands:
        err = float(np.sqrt(np.mean(np.abs(Zm - Z) ** 2 / np.abs(Z) ** 2)))
        out.append((name, npar, desc, err))
    return out


def identify(freqs, Z):
    ms = fit_models(freqs, Z)
    if not ms: return None, []
    best = min(m[3] for m in ms)
    ok = [m for m in ms if m[3] <= max(1.5 * best, TOL)]
    pick = min(ok, key=lambda m: (m[1], m[3]))
    return pick, sorted(ms, key=lambda m: m[3])


# ---------------------------------------------------------------- commands
def measure_all(rref, freqs, cal):
    rv = RREF[rref]
    rows = []
    for f in freqs:
        reps = run_pico(f)
        H, Hs, warn = analyse_runs(reps, f)
        k, c, n, _ = get_cal(cal, rref, f)
        Hc = (H - c) / k
        Z = z_from_h(H, rv, k, c)
        Zr = np.array([z_from_h(h, rv, k, c) for h in Hs])
        rows.append((f, Z, Zr.real.std(ddof=1), Zr.imag.std(ddof=1), warn, Hc, n))
    return rows


def cmd_measure(a):
    cal = load_cal()
    freqs = [int(x) for x in a.freqs.split(",")]
    rows = measure_all(a.rref, freqs, cal)
    print(f"Rref = {a.rref} ({RREF[a.rref]:.1f} ohm)")
    hmag = np.mean([abs(r[5]) for r in rows])
    if hmag > 0.97:
        print(f"\n*** OPEN CIRCUIT: mid-node is {hmag:.1%} of V1, so Zx is very large. Is the DUT connected, or is it a series capacitor? Try a larger Rref.")
    elif hmag < 0.03:
        print(f"\n*** SHORT CIRCUIT: mid-node is only {hmag:.1%} of V1, so Zx is nearly 0 ohm. Try a smaller Rref.")
    for f, Z, sr, sx, warn, Hc, n in rows:
        w = 2 * np.pi * f
        tag = f"calibrated, {n} pts" if n >= 2 else ("1-point cal" if n == 1 else "UNCALIBRATED")
        Y = 1 / Z
        print(f"\n{f:5d} Hz [{tag}]  Z = {Z.real:9.2f} {Z.imag:+9.2f}j ohm   |Z| = {abs(Z):.2f}  phase = {np.degrees(np.angle(Z)):+.2f} deg"
              f"   (repeat scatter: {sr:.2f}, {sx:.2f} ohm)")
        xs = Z.imag
        s_eq = f"L_s = {_fmt_l(xs/w)}" if xs > 0 else f"C_s = {_fmt_c(-1/(w*xs))}"
        p_eq = (f"C_p = {_fmt_c(Y.imag/w)}" if Y.imag > 0 else f"L_p = {_fmt_l(-1/(w*Y.imag))}")
        print(f"        series: R_s = {Z.real:.2f} ohm + {s_eq}     parallel: R_p = {1/Y.real:.2f} ohm || {p_eq}")
        ratio = abs(Z) / RREF[a.rref]
        if not 0.1 <= ratio <= 10:
            best = min(RREF, key=lambda r: abs(np.log(abs(Z) / RREF[r])))
            print(f"        WARNING: |Z| is {ratio:.2g} x Rref; accuracy is poor. Use Rref = {best}.")
        for w_ in warn: print("        WARNING:", w_)
    if len(freqs) >= 2:
        pick, allm = identify(freqs, [r[1] for r in rows])
        print("\nModel fits (rms relative error):")
        for name, npar, desc, err in allm: print(f"   {name:20s} {err*100:6.2f} %   {desc}")
        if hmag > 0.97 or hmag < 0.03:
            print("\n==> No result: fix the connection / Rref first.")
        elif pick[3] > 0.10:
            print(f"\n==> NO GOOD FIT (best {pick[0]} has {pick[3]*100:.0f} % error). Check connection, Rref choice, and calibration; do not trust these numbers.")
        else:
            print(f"\n==> DUT looks like: {pick[0]}:  {pick[2]}   (fit error {pick[3]*100:.2f} %)")
    else:
        print("\nOne frequency only: series and parallel forms fit equally well. Use --freqs with 2 or more to decide.")
    if any(r[6] < 2 for r in rows):
        print("\nNote: not fully calibrated. Run cal-add with short, open and at least one known resistor (see --help).")


def _parse_r(x):
    return "open" if x.lower() == "open" else float(x)


def cmd_cal_add(a):
    cal = load_cal(); freqs = [int(x) for x in a.freqs.split(",")]
    cal.setdefault(a.rref, {})
    r = _parse_r(a.r)
    for f in freqs:
        reps = run_pico(f); H, _, warn = analyse_runs(reps, f)
        e = cal[a.rref].setdefault(str(f), {"pts": []})
        e["pts"] = [p for p in e["pts"] if p["R"] != r] + [{"R": r, "H": [H.real, H.imag]}]
        k, c, n, res = get_cal(cal, a.rref, f)
        print(f"{f:5d} Hz: H = {abs(H):.4f} at {np.degrees(np.angle(H)):+.2f} deg | now {n} pts: |k| = {abs(k):.4f} at {np.degrees(np.angle(k)):+.2f} deg, |c| = {abs(c):.4f}"
              + (f", fit residual {res:.5f}" if n >= 3 else ""), *warn)
    save_cal(cal); print("saved", CAL_FILE)


def cmd_cal_show(a):
    cal = load_cal().get(a.rref, {})
    for f, e in sorted(cal.items(), key=lambda x: int(x[0])):
        k, c, n, res = fit_cal(e["pts"], RREF[a.rref])
        print(f"{f:>5s} Hz  points: {[p['R'] for p in e['pts']]}  |k|={abs(k):.4f} {np.degrees(np.angle(k)):+.2f} deg  c={c.real:+.4f}{c.imag:+.4f}j  residual={res:.5f}")


def cmd_cal_clear(a):
    cal = load_cal(); cal.pop(a.rref, None); save_cal(cal); print("cleared calibration for Rref", a.rref)


def cmd_selftest(_):
    rng = np.random.default_rng(1)
    fr = [250, 500, 1000]; w = 2 * np.pi * np.array(fr)
    cases = {
        "R || C (parallel)": 1 / (1 / 2000 + 1j * w * 100e-9),
        "R + C (series)": 1000 - 1j / (w * 220e-9),
        "R + L (series)": 50 + 1j * w * 10e-3,
        "R": 1000 + 0j * w,
        "C": 1 / (1j * w * 47e-9),
    }
    bad = 0
    for want, Z in cases.items():
        Zn = Z * (1 + 0.003 * (rng.standard_normal(3) + 1j * rng.standard_normal(3)))
        pick, _ = identify(fr, Zn)
        ok = pick[0] == want; bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  want {want:18s} got {pick[0]:18s} {pick[2]}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("measure", cmd_measure), ("cal-add", cmd_cal_add), ("cal-show", cmd_cal_show), ("cal-clear", cmd_cal_clear)):
        p = sp.add_parser(name); p.set_defaults(fn=fn)
        p.add_argument("--rref", default="1k", choices=list(RREF))
        p.add_argument("--freqs", default="250,500,1000")
        if name == "cal-add": p.add_argument("--r", required=True, help="known DUT: 0 = short, open = nothing connected, or the resistor value in ohm")
    sp.add_parser("selftest").set_defaults(fn=cmd_selftest)
    a = ap.parse_args(); a.fn(a)
