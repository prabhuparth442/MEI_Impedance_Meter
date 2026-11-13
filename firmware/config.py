# Measured component values (multimeter, 2026-11-11). Update if remeasured with a better meter.
# u_rel = relative standard uncertainty: PLACEHOLDER until meter resolution/accuracy is known.
RREF = {            # ohms, nominal -> measured
    "100":  {"R": 100.0,    "u_rel": None},
    "1k":   {"R": 1000.0,   "u_rel": None},
    "10k":  {"R": 9900.0,   "u_rel": None},
    "100k": {"R": 100400.0, "u_rel": None},
}
R_FILTER = {"R1": 1000.0, "R2": 1000.0, "R3": 990.0, "R4": 990.0}   # not used in Z calc (see NOTES)
R_ADC_IN = {"ADC0": 100.0, "ADC1": 100.0}   # series resistor to each ADC pin
C_ADC_IN = 1e-9                             # nominal, not measured
F0 = 500.0                                  # excitation frequency, Hz
