# Pico 2 bring-up notes

- 2026-11-11: MicroPython v1.29.0 (RPI_PICO2-20260824) flashed. Board enumerates as 2e8a:0005, serial /dev/ttyACM0 (use `mpremote connect /dev/ttyACM0`).
- Flash recovery: hold BOOTSEL while plugging USB -> drive RP2350 (2e8a:000f), copy the .uf2.
- USB dropouts seen (kernel error -71): loose micro-USB connection. Reseat cable first.
- ADC0 (GP26) offset with input shorted to AGND: 4.54 mV, noise 0.53 mV rms (2000 samples, read_u16).
  Datasheet predicted ~30 mV; each channel differs, GP27/GP28 not yet measured.
  Re-measure at the start of every run (drifts with temperature).
- Internal VSYS/3 channel reads low (~2.0 V vs ~4.7 V real): high-impedance divider, ignore.
- 2026-11-11 offsets (inputs shorted to AGND, 2000 samples): ADC0/GP26 4.54 mV, ADC1/GP27 4.66 mV, ADC2/GP28 4.60 mV; noise 0.51-0.58 mV rms. Channels agree within 0.1 mV.
  Gain mismatch NOT yet measured (needs known non-zero voltage: loopback test).
- 2026-11-11 DC loopback (GP14/GP15 50% PWM @150 kHz, DUT open, Rref 1k, GP28 jumpered to V1): ADC0 1647.08, ADC1 1647.11, ADC2 1647.91 mV.
  ADC1 vs ADC0 0.002%; ADC2 vs ADC0 0.05% (ADC2 has no 100 ohm series, so not a pure ADC mismatch). Single level only, gain needs 2+ levels.
  First attempt: ADC1 floated (~500-900 mV) due to a missed breadboard connection; multimeter showed U1C+/out, Rref mid, V1 all ~1.64 V once fixed.
- mpremote sometimes fails with "could not enter raw repl"/errno 71 after the board has been running PWM: replug or retry.
- Note: U1C+ (GP18 row), U1C out (GP19), Rref mid (GP21), V1 (GP22) rows are on Pico header rows: unused GPIOs, never drive them in firmware.
- 2026-11-11 GOTCHA: after PWM.deinit() (or when a script ends) GP14/GP15 freeze at an arbitrary level (saw 3.3 V and 0 V), so ADCs read 3300 or ~24 mV. Not a wiring fault. Start PWM in the same script that measures; don't deinit.
- 2026-11-11 three-level DC test (duty 10/25/50/75/90 %, DUT open, Rref 1k): linear fits vs duty: ADC0 slope 3314.6 int -5.2 mV; ADC1 3316.4, -5.5; ADC2 3317.3, -5.9.
  Gain vs ADC0: ADC1 +0.055 %, ADC2 +0.082 %. Intercepts agree within 0.7 mV. Common residual up to ~5 mV is in V1 (PWM/filter/opamp), not the ADCs.
  Firmware correction: multiply ADC1 by 1/1.00055 relative to ADC0 (DC only; AC/phase/skew not yet tested).
- 2026-11-11 measured parts (multimeter): R1=R2=1k, R3=R4=0.99k, ADC0/ADC1 series R = 100 each, Rref set: 100, 1k, 9.9k, 100.4k. 1 nF not measured. Stored in config.py.
  R1-R4 do NOT enter Z = Rref*Vmid/(V1-Vmid) (only shape V1/V2); Rref value and ADC ratio do.
- 2026-11-11 DC differential Z test (Rref 1k, duty 25%->75%, Z = Rref*dVmid/(dV1-dVmid), ADC1 gain corr 1.00055): unknown 98.9 ohm (meter) -> 124.5 ohm (+25.6, std 0.4); unknown nominal 2k -> 2030.3 ohm (+30, std 1.5).
  Consistent with ~25-30 ohm fixed extra series resistance in Zx path (not a % error: gain would give ~2520). Source unknown: suspect contacts/binding posts/V2 buffer. Next: short test, measure 2k with meter, probe V2 with GP28.
- pico_check.sh checks USB/serial health.
- 2026-11-11 AC lock-in (lockin.py on Pico -> analyze.py on host: `mpremote run lockin.py > out.txt; python3 -I analyze.py out.txt [R_offset]`).
  500 Hz via PWM duty sine, 10 steps/cycle @200 us. A first version used 100 us steps, loop could not keep pace (110.9 us real) -> real f 451 Hz, demod at 500 Hz gave garbage (70 mV vs 1107 mV). analyze.py now scans for the peak frequency and prints it: it must say 500 Hz.
  ADC1 sampled ~19.3 us after ADC0 (3.5 deg): timestamps correct it.
  Unknown DUT (identity not yet confirmed), Rref 1k: Z = 1672 - j664 ohm (std ~10), |Z| 1.80k, -21.6 deg; series C 479.6 nF; parallel Rp~1935 ohm || Cp~65 nF. +25 ohm offset NOT subtracted yet (short test pending).
- 2026-11-11 imeter.py: host tool (measure / cal-short / cal-res / selftest). Runs lock-in at 125/250/500/1000 Hz, calibrates (series offset b from a short, complex gain k from a known resistor), fits R, L, C, R+L, R+C, R||C, R||L and picks the simplest within 2 %. Selftest passes. Flags open/short circuit and bad fits. Calibration is stored in cal.json.
  Expected for DUT 2k || 100 nF at 500 Hz: Z = 1434 - j901 ohm. Uncalibrated reading earlier: 1672 - j664 (phase ~4 deg off; skew correction suspected).
  At the time of the last run DUT looked OPEN (mid = 98 % of V1): DUT had come loose.
- 2026-11-12 DUT = 1k + 200 nF series, Rref 9.9k (label 10k), uncalibrated imeter: picked R+C series correctly (fit err 3.4 %) but R=1759, C=160 nF (true 1000, 200).
  Error vs expected H=Vmid/V1: magnitude x1.11/1.21/1.33/1.43 at 125/250/500/1000 Hz, phase +9.0/+10.4/+10.9/+9.5 deg: not a single gain/phase error.
  Earlier "open circuit" diagnosis was WRONG for the series-capacitor DUTs (a series C blocks DC, so DC reads open).
  imeter.py calibration rebuilt: H_meas = k*H_true + c (complex k, c) per Rref and frequency, fitted from known points: cal-add --r 0 (short), --r open, --r <ohm>.
  Offline test: recovers a fake instrument (|k|=1.3, 10.5 deg, c=0.065) and corrects 1k+200nF to <0.7 %. Real-hardware calibration not yet done.
- 2026-11-12 cal-add (Rref 10k = 9.9k): short H=0.4 % of V1 (~27-41 ohm offset, real); open H = 0.9994/0.9968/0.9890/0.9543 at 125/250/500/1000 Hz, phase ~0: AC amplitude droop up to 4.6 %, phase fine (skew correction OK). Leakage theory ruled out (short would read 7-13 %).
  Part labelled "1k" across Zx: AC (short+open cal) read 125/118/95/65 ohm, ~0 deg; independent DC check (dc_check.py) read ~135-150 ohm (includes ~40 ohm offset) -> part is ~100 ohm, NOT 1k, OR Rref in the header is not 9.9k. Needs multimeter check of the part and of Rref in place. Known-resistor cal point NOT recorded yet.
- dc_check.py: independent DC resistor check (python3 dc_check.py 9900).
- 2026-11-12 powered check (PWM 25/50/75 %): V1 = 821.5 / 1647.3 / 2480.0 mV (unloaded, ideal); ADC1 (mid) = 1638.6 mV constant -> mid is stuck at V2 (~1.639 V) and does not follow V1: Rref not conducting (probably out of its header from the unpowered checks). V2 ~ 1.639 V.
  Unpowered in-circuit multimeter readings are UNRELIABLE here (V1-V2 read 35.6 ohm, V1-mid read 0.79-0.97k with Rref out) because the op-amp protection diodes conduct at the meter's test voltage. The "1k is across Rref" diagnosis was retracted. 1k part alone = 1.001k, mid-V2 with it = 1.002k (correct slot), Rref alone = 9.9k.
- 2026-11-12 CORRECTED wiring (Rref 9.9k seated, part in Zx slot) -> instrument works. Uncalibrated AC on a 1.001k resistor: 1010.8/1010.4/993.4/955.0 ohm at 125/250/500/1000 Hz, phase within 0.4 deg; DC 1012.7 ohm.
  Calibration (rref 10k, 125/250/500/1000 Hz): short H<=0.0008 (<8 ohm), open H=0.9991/0.9970/0.9878/0.9531 (repeatable amplitude droop), known 1001 ohm; 3-pt residual 0.0006-0.0012 in H (~12 ohm, consistent with Rref 9.9k being ~1 % uncertain from the multimeter).
  Calibrated measurement of "1k + 200 nF" series: R_s = 1386/1190/1109/1107 ohm, C_s = 162.9/158.6/156.3/159.0 nF; fit R+C series, R = 1120 ohm, C = 159.4 nF (fit err 2.4 %). Consistent across frequency -> likely the part: C ~160 nF (not 200) with extra loss R_s - 1001 = 385/189/108/106 ohm = tan(delta) ~0.06 (lossy capacitor, e.g. electrolytic / Y5V). To verify: lab LCR meter or a second capacitor of known value.
