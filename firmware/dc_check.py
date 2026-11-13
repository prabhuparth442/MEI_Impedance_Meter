#!/usr/bin/env python3
"""Independent DC check of a RESISTOR DUT: steps V1 between 25% and 75% duty.
Z = Rref * dVmid / (dV1 - dVmid).  Series capacitors read as open at DC.
usage: python3 dc_check.py [rref_ohms]   (default 9900)"""
import subprocess, sys, tempfile, os, statistics as st
RREF = float(sys.argv[1]) if len(sys.argv) > 1 else 9900.0
G1 = 1.00055
SRC = '''
from machine import ADC, Pin, PWM
import time
pa = PWM(Pin(14), freq=150000, duty_u16=32768)
pb = PWM(Pin(15), freq=150000, duty_u16=32768)
Pin(23, Pin.OUT).value(1)
a0, a1 = ADC(26), ADC(27)
def meas(duty, n=1500):
    pa.duty_u16(int(duty * 65535)); time.sleep_ms(600)
    s0 = s1 = 0
    for i in range(n):
        s0 += a0.read_u16(); s1 += a1.read_u16()
    return s0 / n / 65535 * 3300, s1 / n / 65535 * 3300
for r in range(5):
    lo = meas(0.25); hi = meas(0.75)
    print("REP", *["%.3f" % x for x in lo + hi])
pa.duty_u16(32768)
'''
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "dc.py"); open(p, "w").write(SRC)
    r = subprocess.run(["mpremote", "connect", "/dev/ttyACM0", "run", p], capture_output=True, text=True, timeout=90)
z = []
for l in r.stdout.splitlines():
    if l.startswith("REP"):
        v1a, vma, v1b, vmb = map(float, l.split()[1:])
        d1, dm = v1b - v1a, (vmb - vma) / G1
        z.append(RREF * dm / (d1 - dm))
        print(f"dV1={d1:.1f} dVmid={dm:.2f} ratio={dm/d1:.4f}  Z={z[-1]:.1f} ohm")
if not z: sys.exit("no data: run ./pico_check.sh\n" + r.stderr[-300:])
print(f"DC mean Z = {st.mean(z):.1f} ohm (std {st.stdev(z):.1f}) with Rref = {RREF:.0f}")
