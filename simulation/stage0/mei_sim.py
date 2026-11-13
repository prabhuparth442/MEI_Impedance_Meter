#!/usr/bin/env python3
"""
MEI impedance-bridge meter -- Stage 0 simulation
=================================================
Phasor model of four bridges (Wheatstone, Kelvin double, Maxwell-Wien, Schering)
driven from one excitation node V1, read in DEFLECTION mode through a 3-channel
multiplexed 12-bit ADC (Pico 2 style), with a software lock-in and a numerical
inversion of the nominal bridge model.

Pipeline per trial
    true components (tolerance)  ->  nodal solve (parasitics, return impedance)
    -> 3 phasors [V1, MA, MB]    ->  ADC chain (skew, gain mismatch, INL, noise,
                                     quantisation)  ->  coherent lock-in
    -> D = (MA - MB)/V1          ->  least-squares fit of Zx on the NOMINAL model
    -> error of Zx vs truth (|Z| in %, phase in degrees, plus L / C / ESR metrics)

Everything marked ASSUMPTION is a guess to be replaced by loopback measurements.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import least_squares

# ----------------------------------------------------------------------------
# Instrument assumptions
# ----------------------------------------------------------------------------
F0 = 500.0            # drive frequency, Hz
VDC = 1.65            # DC bias of all nodes (50 % PWM), V
AMP = 0.90            # peak amplitude of V1, V (all nodes stay inside 0.75..2.55 V)
VREF = 3.3            # ADC reference, V
NBITS = 12
LSB = VREF / 2 ** NBITS
FS_TOT = 480e3        # ASSUMPTION: aggregate ADC rate, chosen so FS_TOT/3/F0 is an integer
NCH = 3               # round-robin: V1, MA, MB  (sample instants are k/FS_TOT apart)
NCYC = 10             # coherent window: 10 cycles = 20 ms (also an exact multiple of 50 Hz)
SPC = int(round(FS_TOT / NCH / F0))
NS = SPC * NCYC
assert abs(FS_TOT / NCH / F0 - SPC) < 1e-9

_n = np.arange(NS)
T_CH = np.array([(NCH * _n + k) / FS_TOT for k in range(NCH)])   # nominal sample instants
E_CH = np.exp(-1j * 2 * np.pi * F0 * T_CH)                       # lock-in references


# ----------------------------------------------------------------------------
# Network solver (complex nodal analysis)
#   node 0 = AC ground, node 1 = excitation (V1 fixed), nodes >= 2 unknown
# ----------------------------------------------------------------------------
def solve_nodes(branches, nunk, v1):
    n = nunk + 2
    y = np.zeros((n, n), complex)
    for i, j, a in branches:
        y[i, i] += a
        y[j, j] += a
        y[i, j] -= a
        y[j, i] -= a
    v = np.linalg.solve(y[2:, 2:], -y[2:, 1] * v1)
    out = np.zeros(n, complex)
    out[1] = v1
    out[2:] = v
    return out


def _ground(rret, nbase):
    """Return node used as bridge return; with rret>0 the return sits above ground
    by the output impedance of the return buffer (A2)."""
    if rret > 0:
        g = 2 + nbase
        return g, nbase + 1, [(g, 0, 1.0 / rret)]
    return 0, nbase, []


def _y_c(c, esr, w):
    return 1.0 / (esr + 1.0 / (1j * w * c))


def _y4(p, w):
    return 1.0 / p["R4"] + _y_c(p["C4"], p.get("esr4", 0.0), w)


def b_wheat(p, zx, cp, rret, w):
    g, nunk, ex = _ground(rret, 2)
    br = [(1, 2, 1 / p["R3"]), (2, g, 1 / zx), (1, 3, 1 / p["Rr1"]), (3, g, 1 / p["Rr2"]),
          (2, g, 1j * w * cp[0]), (3, g, 1j * w * cp[1])] + ex
    return br, nunk, 2, 3


def b_maxwell(p, zx, cp, rret, w):
    g, nunk, ex = _ground(rret, 2)
    br = [(1, 2, 1 / p["R2"]), (2, g, 1 / zx), (1, 3, _y4(p, w)), (3, g, 1 / p["R3"]),
          (2, g, 1j * w * cp[0]), (3, g, 1j * w * cp[1])] + ex
    return br, nunk, 2, 3


def b_schering(p, zx, cp, rret, w):
    g, nunk, ex = _ground(rret, 2)
    yn = _y_c(p["CN"], p.get("esrN", 0.0), w)
    br = [(1, 2, 1 / p["R3"]), (2, g, 1 / zx), (1, 3, _y4(p, w)), (3, g, yn),
          (2, g, 1j * w * cp[0]), (3, g, 1j * w * cp[1])] + ex
    return br, nunk, 2, 3


def b_kelvin(p, zx, cp, rret, w):
    # EXC -Rlim- N1 -Rs- N2 -r- N3 -Rx- RET ;  ratio arms a,b ; link arms c,d ; detector X,Y
    g, nunk, ex = _ground(rret, 5)
    br = [(1, 2, 1 / p["Rlim"]), (2, 3, 1 / p["Rs"]), (3, 4, 1 / p["r"]), (4, g, 1 / zx),
          (2, 5, 1 / p["a"]), (5, g, 1 / p["b"]), (3, 6, 1 / p["c"]), (6, 4, 1 / p["d"]),
          (5, g, 1j * w * cp[0]), (6, g, 1j * w * cp[1])] + ex
    return br, nunk, 5, 6


def fwd(builder, p, zx, cp, rret, w, v1):
    br, nunk, ia, ib = builder(p, zx, cp, rret, w)
    v = solve_nodes(br, nunk, v1)
    return v1, v[ia], v[ib]


# ----------------------------------------------------------------------------
# Test cases (unknown device + the standards chosen for it)
# ----------------------------------------------------------------------------
def fmt(x):
    for s, u in ((1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m")):
        if abs(x) >= s:
            return f"{x / s:g}{u}"
    return f"{x:g}"


def nearest(x, options):
    return min(options, key=lambda o: abs(math.log10(x / o)))


def build_cases():
    w = 2 * np.pi * F0
    cases = {"Wheatstone": [], "Kelvin": [], "Maxwell-Wien": [], "Schering": []}

    for rx in [100, 220, 1e3, 2.2e3, 4.7e3, 1e4, 4.7e4, 1e5]:
        r3 = nearest(rx, [1e2, 1e3, 1e4, 1e5])
        cases["Wheatstone"].append(dict(
            bridge="Wheatstone", id=f"R {fmt(rx)}ohm (R3={fmt(r3)})", kind="R", builder=b_wheat,
            p_nom=dict(R3=r3, Rr1=1e4, Rr2=1e4), ptype=dict(R3="R", Rr1="R", Rr2="R"),
            z_true=complex(rx), z_guess=complex(r3)))

    for rx in [1.0, 2.2, 4.7, 10.0, 22.0]:
        rs = nearest(rx, [1.0, 10.0])
        cases["Kelvin"].append(dict(
            bridge="Kelvin", id=f"R {fmt(rx)}ohm (Rs={fmt(rs)})", kind="R", builder=b_kelvin,
            p_nom=dict(Rlim=100.0, Rs=rs, r=0.05, a=1e3, b=1e3, c=1e3, d=1e3),
            ptype=dict(Rlim="Rl", Rs="Rs", r="link", a="R", b="R", c="R", d="R"),
            z_true=complex(rx), z_guess=complex(rs)))

    for l, rdc in [(10e-3, 8.0), (22e-3, 18.0), (47e-3, 35.0), (100e-3, 60.0)]:
        r2, c4 = 1e3, 100e-9
        r3 = nearest(l / (r2 * c4), [1e2, 1e3])
        r4 = nearest(r2 * r3 / rdc, [1e4, 3.3e4, 1e5])
        zl = rdc + 1j * w * l
        zt = 1 / (1 / zl + 1j * w * 30e-12)                  # 30 pF self-capacitance
        zg = r2 * r3 / r4 + 1j * w * r2 * r3 * c4
        cases["Maxwell-Wien"].append(dict(
            bridge="Maxwell-Wien", id=f"L {fmt(l)}H, DCR {rdc:g}ohm (R3={fmt(r3)}, R4={fmt(r4)})",
            kind="L", builder=b_maxwell,
            p_nom=dict(R2=r2, R3=r3, R4=r4, C4=c4, esr4=0.0),
            ptype=dict(R2="R", R3="R", R4="R", C4="C", esr4="esr"),
            z_true=complex(zt), z_guess=complex(zg)))

    cn, c4, r3 = 100e-9, 10e-9, 1e3
    for cx, tand, esr in [(10e-9, 5e-4, None), (47e-9, 5e-4, None), (100e-9, 0.02, None),
                          (220e-9, 5e-4, None), (1e-6, 1e-3, None), (10e-6, None, 2.0)]:
        if esr is None:
            esr = tand / (w * cx)
        r4 = nearest(cx * r3 / cn, [1e2, 330.0, 1e3, 3.3e3, 1e4, 1e5])
        zt = esr + 1 / (1j * w * cx)
        zg = r3 * c4 / cn + 1 / (1j * w * (cn * r4 / r3))
        cases["Schering"].append(dict(
            bridge="Schering", id=f"C {fmt(cx)}F, ESR {esr:.3g}ohm (R4={fmt(r4)})", kind="C",
            builder=b_schering,
            p_nom=dict(R3=r3, R4=r4, C4=c4, CN=cn, esr4=0.0, esrN=0.0),
            ptype=dict(R3="R", R4="R", C4="C", CN="C", esr4="esr", esrN="esr"),
            z_true=complex(zt), z_guess=complex(zg)))
    return cases


# ----------------------------------------------------------------------------
# Scenarios and error sources
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Scenario:
    name: str
    kind: str            # 'uniform' = +/-tol (rectangular), 'normal' = calibrated residual (sigma)
    tR: float            # precision resistors (ratio arms, standards)
    tRs: float           # low-ohm standards (1 ohm, 10 ohm)
    tC: float            # film capacitor standards
    tRl: float           # current-limit resistor
    gmis: float          # sigma of per-channel ADC gain mismatch (relative)
    phi_deg: float       # sigma of per-channel phase mismatch (degrees at F0)
    noise_mv: float = 1.9    # ASSUMPTION: white noise + quantisation ~ 9 ENOB
    inl_mv: float = 1.5      # ASSUMPTION: sigma of cubic INL amplitude
    cp_mean_pf: float = 15.0 # ASSUMPTION: breadboard + op-amp input capacitance at detector nodes
    cp_sd_pf: float = 5.0
    rret_mean: float = 0.10  # ASSUMPTION: A2 (return buffer) output impedance, ohm
    rret_sd: float = 0.05


SCEN = {
    "S1": Scenario("S1: budget parts (1% R, 5% C), no calibration", "uniform",
                   tR=0.01, tRs=0.05, tC=0.05, tRl=0.01, gmis=5e-4, phi_deg=0.01),
    "S2": Scenario("S2: 0.1% R / 1% C standards, no calibration", "uniform",
                   tR=0.001, tRs=0.01, tC=0.01, tRl=0.01, gmis=5e-4, phi_deg=0.01),
    "S3": Scenario("S3: standards calibrated vs reference + ADC loopback-calibrated", "normal",
                   tR=0.0005, tRs=0.002, tC=0.002, tRl=0.003, gmis=1e-4, phi_deg=0.003),
}
SRC_KEYS = ["tol", "cp", "noise", "gmis", "inl", "phi", "rret", "esr", "link"]
SRC_ALL = {k: True for k in SRC_KEYS}
SRC_NONE = {k: False for k in SRC_KEYS}
SRC_LABEL = {
    "tol": "component tolerance", "cp": "stray capacitance (detector nodes)",
    "noise": "ADC noise + quantisation", "gmis": "ADC channel gain mismatch",
    "inl": "ADC INL (cubic)", "phi": "channel timing / phase mismatch",
    "rret": "return-buffer (A2) output impedance", "esr": "loss of C standards",
    "link": "Kelvin link resistance r",
}


def draw_true(case, scen, src, rng, w):
    pt = {}
    for k, v in case["p_nom"].items():
        typ = case["ptype"][k]
        if typ == "link":
            pt[k] = rng.uniform(0.02, 0.15) if src["link"] else v
        elif typ == "esr":
            pt[k] = 0.0
        else:
            t = {"R": scen.tR, "Rs": scen.tRs, "C": scen.tC, "Rl": scen.tRl}[typ]
            if not src["tol"]:
                t = 0.0
            d = rng.uniform(-t, t) if scen.kind == "uniform" else rng.normal(0, t)
            pt[k] = v * (1 + d)
    if src["esr"]:
        for k, ck in (("esr4", "C4"), ("esrN", "CN")):
            if k in pt:
                pt[k] = rng.uniform(1e-4, 5e-4) / (w * pt[ck])
    if src["cp"]:
        cp = tuple(max(2.0, rng.normal(scen.cp_mean_pf, scen.cp_sd_pf)) * 1e-12 for _ in range(2))
    else:
        cp = (0.0, 0.0)
    rret = max(0.0, rng.normal(scen.rret_mean, scen.rret_sd)) if src["rret"] else 0.0
    return pt, cp, rret


# ----------------------------------------------------------------------------
# ADC chain + lock-in
# ----------------------------------------------------------------------------
def adc_chain(ph, scen, src, rng, comp_skew=True):
    """ph = true peak phasors [V1, MA, MB]; returns lock-in estimates of the three phasors."""
    w = 2 * np.pi * F0
    phi = rng.normal(0, np.deg2rad(scen.phi_deg), NCH) if src["phi"] else np.zeros(NCH)
    gm = rng.normal(0, scen.gmis, NCH) if src["gmis"] else np.zeros(NCH)
    gc = rng.normal(0, 0.003)                          # common gain error: cancels in ratios
    off = 0.030 + rng.normal(0, 0.010) + rng.normal(0, 0.003, NCH)
    kinl = rng.normal(0, scen.inl_mv * 1e-3) if src["inl"] else 0.0
    sig = scen.noise_mv * 1e-3
    est = np.empty(NCH, complex)
    for k in range(NCH):
        p = ph[k] * np.exp(1j * phi[k])
        x = np.real(p * np.exp(1j * w * T_CH[k]))      # sampled at the true instants
        u = VDC + x
        u = u + kinl * ((u - VDC) / VDC) ** 3
        u = u * (1 + gc) * (1 + gm[k]) + off[k]
        if src["noise"]:
            u = u + rng.normal(0, sig, NS)
            v = np.clip(np.round(u / LSB), 0, 2 ** NBITS - 1) * LSB
        else:
            v = u
        ref = E_CH[k] if comp_skew else E_CH[0]        # comp_skew=False ignores the mux skew
        est[k] = 2.0 / NS * np.sum((v - v.mean()) * ref)
    return est


# ----------------------------------------------------------------------------
# Inversion on the NOMINAL model
# ----------------------------------------------------------------------------
def invert(case, d_meas, w, mode="diff"):
    """mode 'diff': fit D = (MA-MB)/V1 (true bridge reading).
       mode 'A'   : fit MA/V1 only (divider reading; ratio arms on the MB side are not used)."""
    scale = abs(case["z_guess"])
    p = case["p_nom"]

    def fun(x):
        z = scale * (x[0] + 1j * x[1])
        _, va, vb = fwd(case["builder"], p, z, (0.0, 0.0), 0.0, w, 1.0 + 0j)
        r = (va - vb if mode == "diff" else va) - d_meas
        return [r.real * 1e3, r.imag * 1e3]

    z0 = case["z_guess"]
    sol = least_squares(fun, [z0.real / scale, z0.imag / scale], method="lm",
                        xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=300)
    return scale * (sol.x[0] + 1j * sol.x[1])


def run_trial(case, scen, src, rng, comp_skew=True, mode="diff"):
    w = 2 * np.pi * F0
    pt, cp, rret = draw_true(case, scen, src, rng, w)
    v1 = AMP * np.exp(1j * rng.uniform(0, 2 * np.pi))
    ph = np.array(fwd(case["builder"], pt, case["z_true"], cp, rret, w, v1))
    est = adc_chain(ph, scen, src, rng, comp_skew)
    d = (est[1] - est[2]) / est[0] if mode == "diff" else est[1] / est[0]
    return invert(case, d, w, mode)


def metrics(case, z):
    zt, w = case["z_true"], 2 * np.pi * F0
    m = dict(mag=(abs(z) / abs(zt) - 1) * 100, ph=float(np.rad2deg(np.angle(z / zt))))
    if case["kind"] == "L":
        m["L"] = (z.imag / zt.imag - 1) * 100
        m["dR"] = z.real - zt.real
    if case["kind"] == "C":
        m["C"] = (zt.imag / z.imag - 1) * 100
        m["dtan"] = z.real / abs(z.imag) - zt.real / abs(zt.imag)
    return m


# ----------------------------------------------------------------------------
# Self-tests (noise-free validation of the machinery)
# ----------------------------------------------------------------------------
def selftest():
    import time
    w = 2 * np.pi * F0
    cases = build_cases()
    print(f"samples/channel = {NS}, samples/cycle = {SPC}, LSB = {LSB * 1e3:.4f} mV")

    worst = 0.0
    for lst in cases.values():
        for c in lst:
            v1 = AMP * np.exp(0.3j)
            _, va, vb = fwd(c["builder"], c["p_nom"], c["z_true"], (0, 0), 0.0, w, v1)
            z = invert(c, (va - vb) / v1, w)
            worst = max(worst, abs(z / c["z_true"] - 1))
    print(f"T1 ideal phasor round trip, worst |dZ|/|Z| over all cases: {worst:.2e}")

    rng = np.random.default_rng(1)
    ph = np.array([0.9 * np.exp(0.7j), 0.31 * np.exp(-0.4j), 0.28 * np.exp(1.1j)])
    est = adc_chain(ph, SCEN["S2"], SRC_NONE, rng)
    # common gain error gc cancels in ratios, compare ratios
    r_true = ph[1:] / ph[0]
    r_est = est[1:] / est[0]
    print(f"T2 noise-free ADC+lock-in ratio error: {np.max(np.abs(r_est / r_true - 1)):.2e}")

    p = dict(Rlim=100.0, Rs=10.0, r=0.0, a=1e3, b=1e3, c=1e3, d=1e3)
    outs = []
    for r in (0.01, 0.1, 1.0):
        p["r"] = r
        _, va, vb = fwd(b_kelvin, p, 10.0 + 0j, (0, 0), 0.0, w, 1.0 + 0j)
        outs.append(abs(va - vb))
    print(f"T3 Kelvin balanced (Rx=Rs, a/b=c/d) |D| for r=0.01/0.1/1 ohm: "
          f"{outs[0]:.1e} {outs[1]:.1e} {outs[2]:.1e}")

    t = T_CH[1]
    x = 0.4 * np.cos(2 * np.pi * F0 * t + 0.5)
    base = 2 / NS * np.sum(x * E_CH[1])
    x2 = x + 0.100 + 0.020 * np.cos(2 * np.pi * 50 * t + 1.0) + 0.010 * np.cos(2 * np.pi * 100 * t)
    pert = 2 / NS * np.sum((x2 - x2.mean()) * E_CH[1])
    print(f"T4 100 mV DC + 20 mV @50 Hz + 10 mV @100 Hz rejected, change in phasor: {abs(pert - base):.2e} V")

    c = cases["Wheatstone"][2]
    ph_meas = {}
    for comp in (True, False):
        rng = np.random.default_rng(5)
        zs = [run_trial(c, SCEN["S3"], SRC_NONE, rng, comp_skew=comp) for _ in range(3)]
        ph_meas[comp] = np.rad2deg(np.angle(zs[0] / c["z_true"]))
    print(f"T5 mux skew: phase error with compensation {ph_meas[True]:.4f} deg, "
          f"without compensation {ph_meas[False]:.3f} deg "
          f"(expected {np.rad2deg(w * 2e-6 / 1):.3f} / {np.rad2deg(w * 4e-6 / 1):.3f} deg per channel)")

    rng = np.random.default_rng(7)
    t0 = time.time()
    for _ in range(40):
        run_trial(cases["Maxwell-Wien"][1], SCEN["S2"], SRC_ALL, rng)
    print(f"speed: {(time.time() - t0) / 40 * 1e3:.1f} ms per full trial")


if __name__ == "__main__":
    selftest()
