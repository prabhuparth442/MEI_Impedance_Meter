import numpy as np, sys
RREF, G1, F0 = 1000.0, 1.00055, 500.0
ROFF = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0    # extra series R to subtract from Re(Z)
w = 2*np.pi*F0
M = 2**30
reps, cur = [], {}
for l in open(sys.argv[1]):
    l = l.strip()
    if l.startswith('REP'):
        if cur: reps.append(cur)
        cur = {'start': float(l.split()[3])}
    for key in ('T0','T1','T2','VA','VB'):
        if l.startswith(key+' '):
            cur[key] = np.array([float(x) for x in l[3:].split(',')])
if cur: reps.append(cur)
def phasor(t_us, v_counts, f=F0):
    v = v_counts/65535*3300.0
    v = v - v.mean()
    return 2*np.sum(v*np.exp(-2j*np.pi*f*t_us*1e-6))/len(v)
Zs = []
for i, r in enumerate(reps):
    t0 = (r['T0']-r['start']) % M; t1 = (r['T1']-r['start']) % M; t2 = (r['T2']-r['start']) % M
    ta = (t0+t1)/2; tb = (t1+t2)/2
    fs = np.arange(400, 600, 1.0)
    pk = fs[np.argmax([abs(phasor(ta, r['VA'], f)) for f in fs])]
    V1 = phasor(ta, r['VA']); Vm = phasor(tb, r['VB'])/G1
    Z = RREF*Vm/(V1-Vm); Z = complex(Z.real-ROFF, Z.imag); Zs.append(Z)
    print(f"rep{i}: peak freq {pk:.0f} Hz | |V1|={abs(V1):.1f} mV |Vmid|={abs(Vm):.1f} mV | "
          f"V1 pp {np.ptp(r['VA'])/65535*3300:.0f} mV, mid pp {np.ptp(r['VB'])/65535*3300:.0f} mV | "
          f"skew {np.mean(tb-ta):.1f} us")
    print(f"        Z = {Z.real:.2f} {Z.imag:+.2f}j ohm  |Z|={abs(Z):.2f}  phase={np.degrees(np.angle(Z)):+.2f} deg")
Z = np.array(Zs); R, X = Z.real, Z.imag
print(f"\nmean R = {R.mean():.2f} ohm (std {R.std(ddof=1):.2f}),  X = {X.mean():+.2f} ohm (std {X.std(ddof=1):.2f})")
Xm = X.mean()
print(f"inductive: L = {Xm/w*1e3:.3f} mH" if Xm > 0 else f"capacitive: C = {-1/(w*Xm)*1e9:.2f} nF")
