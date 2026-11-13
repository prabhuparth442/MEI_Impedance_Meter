# MEI impedance bridges: Stage 0 simulation results (2026-10-25)

Python phasor + ADC + lock-in Monte Carlo. Code: `mei_sim.py` (model, self-tests), `run_all.py` (main runs), `refine.py` / `refine2.py` (arm selection, estimator comparison). Raw tables: `results_tables.md`, `refine_tables.md`, `refine2_tables.md`.

**Read this first:** every number depends on the assumptions in section 2. They are guesses until the loopback test on the real Pico 2 replaces them. The PASS targets (|Z| within 0.5 %, phase within 0.5 deg, 95th percentile) are my proposals, not course requirements.

---

## 1. What was simulated

```
true components (tolerance) -> nodal solve (stray C, return impedance)
-> phasors [V1, MA, MB] -> ADC chain (mux skew, gain mismatch, INL, noise, 12-bit rounding)
-> coherent lock-in -> D = (MA - MB)/V1 -> least-squares fit of Zx on the NOMINAL model
-> error of Zx against truth
```

Bridges (deflection mode, return at 1.65 V mid-rail): Wheatstone, Kelvin double, Maxwell-Wien, Schering. 23 test devices, 400 trials each, three part scenarios.

### Bridge equations used (divider form, MA = V1 Zb/(Za+Zb))

Balance of two dividers: Zb Zc = Za Zd.

- **Wheatstone:** Rx = R3 Rr2/Rr1.
- **Maxwell-Wien:** Zx Z4 = R2 R3 with Z4 = R4 || C4, so Zx = R2 R3 (1/R4 + j w C4), giving Rx = R2 R3/R4 and Lx = R2 R3 C4.
- **Schering:** Zx Z4 = R3 Z_CN with Z4 = R4 || C4 and Z_CN = 1/(j w CN), giving Cx = CN R4/R3, Rx = R3 C4/CN, tan(delta) = w Cx Rx = w C4 R4.
- **Kelvin double:** with c/d = a/b, Rx = Rs b/a independent of the link resistance r. Verified numerically: D stays below 1e-15 for r = 0.01, 0.1 and 1 ohm.

In deflection mode nothing is balanced. The ADC reads D, and Zx is solved from the bridge equation using the nominal component values, so tolerance of every arm enters the result.

## 2. Assumptions (replace with measurements)

| Item | Value used | Source |
|---|---|---|
| Drive | 500 Hz, 0.9 V peak on 1.65 V bias | design choice |
| ADC | 12 bit, 0.806 mV/LSB, 480 kS/s total shared by 3 channels (160 kS/s each, 320 samples per cycle) | assumption: clock divider chosen for an integer count |
| Window | 10 cycles = 20 ms, 3200 samples per channel | also an exact multiple of 50 Hz |
| ADC noise | 1.9 mV rms white (about 9 ENOB) | from the datasheet summary you pasted, not verified |
| Channel gain mismatch | sigma 0.05 % raw, 0.01 % after loopback calibration | guess, the single most important number to measure |
| Phase mismatch | sigma 0.01 deg raw, 0.003 deg calibrated | guess |
| INL | cubic, sigma 1.5 mV | guess |
| Stray C at detector nodes | 15 pF +/- 5 pF | guess for breadboard + op-amp input |
| Return buffer (A2) output impedance | 0.1 +/- 0.05 ohm | guess |
| Inductor DCR | 8, 18, 35, 60 ohm for 10, 22, 47, 100 mH; 30 pF self-capacitance | typical values, not your parts |
| Capacitor loss | tan(delta) 5e-4 film, 0.02 X7R, ESR 2 ohm for 10 uF electrolytic | typical values |

Scenarios: **S1** 1 % resistors, 5 % capacitors, no calibration. **S2** 0.1 % resistors, 1 % capacitors, no calibration. **S3** standards calibrated against a reference meter (R to 0.05 %, low-ohm to 0.2 %, C to 0.2 %) and the ADC channels calibrated by loopback.

Not modelled: PWM carrier and harmonic leakage, temperature drift, op-amp bandwidth and output limits, frequency error, contact resistance, supply ripple correlated with the signal, ADC DNL, inductor core non-linearity. LTspice should cover the first and third.

## 3. Validation of the machinery

| Test | Result |
|---|---|
| Ideal phasors, fit recovers Zx, all 23 cases | worst error 6.6e-14 |
| Noise-free ADC and lock-in, ratio error | 3e-16 |
| Kelvin balance independent of link r | D below 1.2e-15 |
| 100 mV DC + 20 mV at 50 Hz + 10 mV at 100 Hz | phasor change 8e-17 V |
| **Mux skew, uncompensated** | **0.75 deg phase error (compensated: 0.0000)** |

Compensating the 2 microsecond channel skew in the lock-in (use each sample's true time) is mandatory. Without it you exceed the 0.5 deg target before any other error.

## 4. Results, scenario S3 (calibrated), p95 error

Maxwell-Wien and Schering use the improved arm choices from `refine.py`.

| Bridge | Device (standards) | abs(Z) p95 % | phase p95 deg | vs 0.5 % / 0.5 deg |
|---|---|---|---|---|
| Wheatstone | 100 ohm to 10 kohm (R3 = decade) | 0.19 to 0.22 | 0.04 to 0.07 | PASS |
| Wheatstone | 47 kohm / 100 kohm (R3 = 100 k) | 0.20 / 0.19 | 0.17 / **0.39** | PASS (phase near limit, stray C) |
| Kelvin | 1 ohm / 2.2 ohm | 2.98 / 1.40 | 1.77 / 0.75 | FAIL |
| Kelvin | 4.7 ohm / 10 ohm / 22 ohm | 1.14 / 0.56 / 0.44 | 0.40 / 0.22 / 0.13 | FAIL / FAIL (marginal) / PASS |
| Kelvin + ideal x10 gain on detector nodes | 1 / 2.2 / 4.7 / 10 / 22 ohm | 0.82 / 0.50 / 0.99 / 0.44 / 0.41 | 0.27 / 0.12 / 0.07 / 0.04 / 0.03 | only 10 and 22 ohm pass |
| Maxwell-Wien | 10 mH (R3 100, R4 12 k) | 0.56 | 0.26 | FAIL (marginal) |
| Maxwell-Wien | 22 mH (R3 100, R4 10 k) | 0.31 | 0.13 | PASS |
| Maxwell-Wien | 47 mH (R3 470, R4 15 k) | 0.43 | 0.09 | PASS |
| Maxwell-Wien | 100 mH (R3 1 k, R4 10 k) | 0.38 | 0.06 | PASS |
| Schering | 10 nF (R3 10 k, R4 1 k, C4 1 nF) | 0.50 | 0.07 | FAIL (marginal) |
| Schering | 47 nF, 100 nF, 220 nF, 1 uF, 10 uF | 0.39 to 0.44 | 0.04 to 0.05 | PASS |

Schering tan(delta) error p95 is 0.0007 to 0.0012 (absolute) once the arms are chosen well.

Other scenarios, same devices:

- **S2 (0.1 % R, 1 % C, uncalibrated):** Wheatstone is marginal (0.31 to 0.50 % depending on the run). Kelvin fails (0.84 to 3.2 %), Maxwell-Wien fails (0.5 to 2.0 %), Schering fails (0.8 to 1.9 %, about 1 % with the improved arms).
- **S1 (1 % R, 5 % C):** everything fails, 1.9 to 10 %.

## 5. What actually limits each bridge (one source at a time, standard deviation of the abs(Z) error)

- **Component tolerance** dominates almost everywhere. S2 to S3 improves the L and C bridges from about 0.5 % to about 0.2 % per source.
- **Wheatstone:** tolerance 0.10 %, ADC channel mismatch 0.15 % (raw), noise 0.03 %. Stray 15 pF only matters for phase at 100 kohm (0.09 deg).
- **Kelvin:** ADC noise at low ohms (1.66 % at 1 ohm, 0.18 % at 10 ohm) plus tolerance of the low-ohm standard. The signal across a 1 ohm Rx is about 8 mV.
- **Schering and Maxwell-Wien:** tolerance of the capacitor standards (0.4 to 0.55 % at 1 %, 0.15 to 0.2 % at 0.2 %).
- **ADC channel mismatch sweep (S3 otherwise):** at 0.2 % mismatch a 1 kohm Wheatstone reading goes to 1.09 % p95 and a 47 nF Schering phase to 2.2 deg. At 0.01 % both are fine. **The loopback calibration must bring mismatch below about 0.02 %.**
- **Negligible in this model:** INL (cancels because MA and MB distort alike), return-buffer impedance, capacitor loss, link resistance, channel timing (0.03 deg).

## 6. Finding that changes the plan: bridge reading vs divider reading

Estimating Zx from MA/V1 alone (a divider reading, the ratio arms on MB unused) is more accurate than the classical bridge difference D = (MA - MB)/V1:

| S3, p95 abs(Z) error % | bridge reading | divider reading |
|---|---|---|
| Wheatstone 1 kohm / 10 kohm | 0.18 / 0.19 | 0.14 / 0.13 |
| Maxwell-Wien 47 mH / 100 mH | 0.39 / 0.38 | 0.17 / 0.14 |
| Schering 100 nF / 1 uF | 0.42 / 0.48 | 0.12 / 0.11 |

Reason: with a ratiometric ADC good to about 0.05 %, the second arm is a reference whose tolerance adds error instead of removing it. This is a property of deflection mode, not of null bridges (where the detector only needs to find zero).

Consequences:

1. The classical bridge reading is what exposes each topology's own standards (C4 for Maxwell-Wien, CN for Schering), so it is the independent-error-profile method you asked for. Keep it.
2. The divider reading is cheaper and often more accurate, but it makes the topologies collapse into "one divider against one reference arm". Use it as a **cross-check**: if the bridge reading and the divider reading disagree, a standard (usually C4 or CN) is off.
3. Report the best-supported value and put the disagreement between readings into the Type B term of the GUM budget, as planned earlier.

## 7. Decisions this supports

1. **0.1 % resistors are required.** With 1 % parts every bridge misses by 2 to 10 %.
2. **Calibrate every standard against the reference meter** (S2 to S3 roughly halves the error). The capacitor standards need to be known to about 0.2 %, so ask for lab LCR access.
3. **Mux skew compensation and a loopback measurement of channel gain mismatch are mandatory.**
4. **Arm choice matters:** 22 mH gave 0.31 % with R3 = 100 ohm, R4 = 10 k and 0.84 % with R3 = 470 ohm, R4 = 27 k, because the reference arm's tolerance gets amplified when it carries more signal than the unknown side. Stage 1 should sweep arm values per device. Buy a few spare values.
5. **Suggested extra resistors (0.1 %):** 470 ohm x2, 2.2 k x2, 4.7 k x2, 12 k, 15 k, 18 k, 27 k (one each), on top of the earlier list.
6. **Kelvin is the weak bridge.** Without gain it fails everywhere below 22 ohm. With an ideal x10 gain stage on the detector nodes only 10 and 22 ohm pass, and gain would need another quad op-amp and a Rg return to V2 so the 1.65 V bias is not amplified. Options: restrict Kelvin to 10 ohm and above and say so in the report, or replace it with Hay (reuses the same parts).

## 8. Next steps

1. Loopback on the real board: V1 = MA = MB. Measure per-channel noise, gain mismatch and phase mismatch, and replace the section 2 guesses.
2. LTspice front end: PWM carrier leakage through the RC filter, op-amp phase lag, output limits driving 100 ohm bridge arms.
3. Re-run `run_all.py` with the measured numbers (edit the `Scenario` values in `mei_sim.py`).
