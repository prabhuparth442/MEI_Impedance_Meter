"""Compare estimators: 'diff' (true bridge reading D=(MA-MB)/V1) vs 'A' (MA/V1 divider reading)."""
import numpy as np, mei_sim as ms, refine as rf

def run(case, scen, mode, n, seed):
    rng = np.random.default_rng(seed); acc = {}
    for _ in range(n):
        m = ms.metrics(case, ms.run_trial(case, scen, ms.SRC_ALL, rng, mode=mode))
        for k, v in m.items(): acc.setdefault(k, []).append(v)
    return {k: float(np.percentile(np.abs(v), 95)) for k, v in acc.items()}

groups = [("Wheatstone", ms.build_cases()["Wheatstone"]),
          ("Maxwell-Wien (improved arms)", rf.maxwell_cases()),
          ("Schering (improved arms)", rf.schering_cases())]
lines = []
seed = 9000
for sk in ("S2", "S3"):
    lines += [f"\n### Estimator comparison, {ms.SCEN[sk].name} (p95 |Z| err % / p95 phase err deg)\n",
              "| Bridge | Case | bridge reading D | divider reading MA/V1 |", "|---|---|---|---|"]
    for name, cs in groups:
        for c in cs:
            seed += 1
            a = run(c, ms.SCEN[sk], "diff", 300, seed)
            b = run(c, ms.SCEN[sk], "A", 300, seed)
            lines.append(f"| {name} | {c['id']} | {a['mag']:.3f} / {a['ph']:.3f} | {b['mag']:.3f} / {b['ph']:.3f} |")
open("refine2_tables.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
