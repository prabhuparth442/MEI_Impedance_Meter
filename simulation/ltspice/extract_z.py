"""Read an LTspice .raw file (AC analysis, stepped) and print Zx = Rref*V(adc1)/(V(adc0)-V(adc1)).

Usage: python3 extract_z.py Model1.raw [out.csv]

CASES gives Rref (ohm) and the true DUT (R, L) for each .step value, in step order.
Edit it to match the .param table in the schematic.
"""
import sys
import numpy as np

# case: (Rref, R_dut, L_dut)   -- same as the .param tables
CASES = {1: (100, 100, 10e-3), 2: (9.9e3, 6150, 1e-9), 3: (9.9e3, 4700, 1e-9),
         4: (9.9e3, 2664, 1e-9), 5: (1e3, 220, 1e-9), 6: (1e3, 2000, 1e-9),
         7: (9.9e3, 1000, 100e-3)}


def read_raw(path):
    d = open(path, "rb").read()
    tag = "Binary:\n".encode("utf-16le")
    i = d.find(tag)
    if i >= 0:
        head = d[:i].decode("utf-16le")
        body = d[i + len(tag):]
    else:
        i = d.find(b"Binary:\n")
        head = d[:i].decode("ascii", "replace")
        body = d[i + 8:]
    names, npts, nvar, in_vars = [], 0, 0, False
    for line in head.splitlines():
        if line.startswith("No. Variables:"):
            nvar = int(line.split(":")[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":")[1])
        elif line.startswith("Variables:"):
            in_vars = True
        elif in_vars and line.strip():
            names.append(line.split()[1])
    a = np.frombuffer(body[: npts * nvar * 16], dtype="<f8").reshape(npts, nvar, 2)
    return names, a[:, :, 0] + 1j * a[:, :, 1]


def main():
    names, c = read_raw(sys.argv[1])
    ia, ib = names.index("V(adc0)"), names.index("V(adc1)")
    first = names[0].lower()
    rows = []
    if first == "frequency":
        f = c[:, 0].real
        step = 1
        for k in range(len(f)):
            if k and f[k] <= f[k - 1]:
                step += 1
            rref, r, l = CASES[step]
            z = rref * c[k, ib] / (c[k, ia] - c[k, ib])
            rows.append((step, f[k], rref, r, l, z))
    else:  # single frequency 500 Hz, first variable is the stepped parameter (Rref)
        for k in range(len(c)):
            rref = c[k, 0].real
            z = rref * c[k, ib] / (c[k, ia] - c[k, ib])
            rows.append((k + 1, 500.0, rref, 100, 10e-3, z))
    print("case  f(Hz)   Rref     R_true   X_true     R_meas     X_meas    R err %")
    out = ["case,f,Rref,R_true,X_true,R_meas,X_meas"]
    for step, f, rref, r, l, z in rows:
        x = 2 * np.pi * f * l
        print(f"{step:3d} {f:7.0f} {rref:8.0f} {r:8.1f} {x:9.2f} {z.real:10.2f} {z.imag:10.2f} {100*(z.real-r)/r:8.3f}")
        out.append(f"{step},{f},{rref},{r},{x},{z.real},{z.imag}")
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write("\n".join(out) + "\n")


main()
