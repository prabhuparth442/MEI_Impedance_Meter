from machine import ADC, Pin, PWM
from array import array
import time, math, gc
pa = PWM(Pin(14), freq=150000, duty_u16=32768)
pb = PWM(Pin(15), freq=150000, duty_u16=32768)
Pin(23, Pin.OUT).value(1)
a0, a1 = ADC(26), ADC(27)
N, STEP = 10, 200            # 10 steps/cycle, 200 us per step -> 500 Hz
PRE, REC = 30, 50
tab = [int(65535 * (0.5 + 0.40 * math.sin(2 * math.pi * k / N))) for k in range(N)]
nrec = REC * N
ticks_us, ticks_diff, ticks_add = time.ticks_us, time.ticks_diff, time.ticks_add
for rep in range(3):
    t0a = array('I', bytes(4 * nrec)); t1a = array('I', bytes(4 * nrec)); t2a = array('I', bytes(4 * nrec))
    va = array('H', bytes(2 * nrec)); vb = array('H', bytes(2 * nrec))
    gc.collect(); gc.disable()
    nxt = ticks_us()
    start = nxt
    j = 0
    slips = 0
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
