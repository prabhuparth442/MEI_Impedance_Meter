#!/usr/bin/env python3
"""
run_wheatstone.py  -  co-simulation, iteration 1: Pico 2 front end + Wheatstone module.

    python3 run_wheatstone.py                      # fast: ideal drive, 4 windows (80 ms)
    python3 run_wheatstone.py --pwm                # real 150 kHz PWM drive (slow, shows carrier effects)
    python3 run_wheatstone.py --rx 4700 --tol 0.001 --seed 3

WHAT HAPPENS
------------
1. We choose a "true" bridge: nominal resistors times a random tolerance (the real world).
   The firmware only knows the nominal values (R3 = 1 kohm, ratio arms 10 kohm).
2. ngspice runs the analog circuit.  At every time step it asks VirtualPico for the PWM pin
   voltages and hands back the ADC pin voltages.
3. VirtualPico samples the ADC like the chip would, runs the lock-in every 20 ms and
   estimates Rx.  Window 0 is warm-up (RC filters settling) and is dropped.
4. We compare the estimate with the true Rx.  The difference is the error of the whole
   measurement chain (op-amps, filters, ADC noise/quantisation, tolerance).
"""
import argparse
import time

import numpy as np

from netlist import wheatstone_netlist
from ngspice_link import NgspiceLink
from virtual_pico import PicoConfig, VirtualPico

ap = argparse.ArgumentParser()
ap.add_argument("--rx", type=float, default=2200.0, help="true device under test, ohm")
ap.add_argument("--r3", type=float, default=1000.0, help="nominal R3 (decade box setting), ohm")
ap.add_argument("--rr", type=float, default=10000.0, help="nominal ratio arms Rr1 = Rr2, ohm")
ap.add_argument("--tol", type=float, default=0.001, help="resistor tolerance (uniform +/-), 0.001 = 0.1 %%")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--pwm", action="store_true", help="use real 150 kHz PWM instead of an ideal sine drive")
ap.add_argument("--windows", type=int, default=4)
ap.add_argument("--noise-mv", type=float, default=1.3,
                help="ADC rms noise incl. quantisation, mV.  RP2350 Table 1685: ENOB 9 min / 9.5 typ -> 1.86 / 1.32 mV")
ap.add_argument("--gbw", type=float, default=1e6, help="only for --opamp simple")
ap.add_argument("--opamp", choices=["mcp6004", "simple"], default="mcp6004",
                help="mcp6004 = Microchip macromodel (default), simple = old toy model")
ap.add_argument("--rpin", type=float, default=100.0, help="Pico GPIO output resistance, ohm (datasheet: <=170 at 4 mA drive)")
args = ap.parse_args()

rng = np.random.default_rng(args.seed + 100)
tol = lambda: 1.0 + rng.uniform(-args.tol, args.tol)
# The real parts differ from the labels by their tolerance.  Rx (the DUT) is taken as exact.
r3_true, rr1_true, rr2_true = args.r3 * tol(), args.rr * tol(), args.rr * tol()
rx_true = args.rx

cfg = PicoConfig(pwm_mode="pwm" if args.pwm else "ideal", n_windows=args.windows,
                 adc_noise_mv=args.noise_mv, seed=args.seed)
pico = VirtualPico(cfg, r3_nominal=args.r3)

# ngspice time step limit.  Ideal drive: the signal is a 500 Hz sine, 2 us steps are plenty.
# PWM drive: resolve the carrier edges, 1/100 of a carrier period.
tmax = pico.tc / 100 if args.pwm else 2e-6
tstop = cfg.n_windows * pico.win_len

netlist = wheatstone_netlist(rx_true=rx_true, r3_true=r3_true, rr1_true=rr1_true, rr2_true=rr2_true,
                             tstop=tstop, tmax=tmax, opamp=dict(gbw_hz=args.gbw), opamp_model=args.opamp, r_pin=args.rpin)

link = NgspiceLink()
link.set_vsrc_callback(pico.pin_voltage)                       # ngspice <- Pico   (PWM pins)
link.set_data_callback(["adc0", "adc1", "adc2"], pico.on_step)  # ngspice -> Pico   (ADC pins)
link.load(netlist)

t0 = time.time()
link.run()
wall = time.time() - t0

print(f"drive: {cfg.pwm_mode}   simulated {tstop * 1e3:.0f} ms in {wall:.1f} s wall-clock   "
      f"({len(pico.results)} windows)")
print(f"true  Rx = {rx_true:.3f} ohm   (R3 true {r3_true:.3f}, Rr1 {rr1_true:.3f}, Rr2 {rr2_true:.3f})")
print(f"{'win':>3} {'|V1| V':>8} {'Rx bridge':>12} {'err %':>8} {'Rx divider':>12} {'err %':>8}")
for r in pico.results:
    tag = "  (warm-up, dropped)" if r["window"] == 0 else ""
    eb = (r["rx_bridge"].real / rx_true - 1) * 100
    ed = (r["rx_divider"].real / rx_true - 1) * 100
    print(f"{r['window']:>3} {r['v1_amp']:>8.4f} {r['rx_bridge'].real:>12.3f} {eb:>8.3f} "
          f"{r['rx_divider'].real:>12.3f} {ed:>8.3f}{tag}")

good = pico.results[1:]
if good:
    for key, label in (("rx_bridge", "bridge"), ("rx_divider", "divider")):
        vals = np.array([g[key] for g in good])
        print(f"{label:>8}: mean {vals.real.mean():.3f} ohm, error {(vals.real.mean() / rx_true - 1) * 100:+.3f} %, "
              f"window-to-window std {vals.real.std(ddof=1) / rx_true * 100 if len(vals) > 1 else float('nan'):.3f} %, "
              f"phase {np.degrees(np.angle(vals.mean())):+.3f} deg (true 0)")
errs = link.errors()
if errs:
    print("ngspice reported:", errs[:3])
