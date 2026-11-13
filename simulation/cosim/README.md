# mei_cosim: Pico 2 + analog front end co-simulation (iteration 1, Wheatstone)

## What it is

A Python "virtual Pico 2" runs *inside* an ngspice transient simulation of the analog circuit.
At every simulated time step ngspice asks Python for the PWM pin voltages and hands back the
ADC pin voltages, so both advance on one clock. No waveform files, no post-processing.

```
 virtual_pico.py (Python)                     ngspice engine (libngspice)
 ------------------------                     ---------------------------
 pin_voltage(Vp14/Vp15, t) ----- volts -----> external sources Vp14, Vp15
                                              RC filters -> U1A/U1B followers -> V1, V2
                                              Wheatstone module -> MIDA, MIDB
                                              U1C/U1D buffers -> 100 ohm + 1 nF
 on_step(t, [adc0, adc1, adc2]) <-- volts ---- adc0, adc1, adc2 nodes
   |- 12-bit ADC model at 480 kS/s round-robin
   |- every 20 ms: lock-in -> Rx estimate -> update_drive() [hook, closed loop in iteration 2]
```

## Files

| File | Role |
|---|---|
| `ngspice_link.py` | ctypes wrapper around libngspice: external-source callback + per-step data callback |
| `netlist.py` | SPICE text: PWM pin resistance, RC filters, op-amp macro-model, Wheatstone module, ADC input networks |
| `virtual_pico.py` | PWM generator, ADC model (true conversion times, noise, 12-bit), lock-in, Rx estimate, `update_drive` hook |
| `run_wheatstone.py` | Picks a "true" bridge with tolerance, runs the co-simulation, prints estimate vs truth |

## Install and run

```
sudo apt install ngspice libngspice0-dev        # Ubuntu; provides libngspice.so
pip install numpy
python3 run_wheatstone.py                        # ideal sine drive, about 1 s
python3 run_wheatstone.py --pwm                  # real 150 kHz PWM drive, about 20 s
python3 run_wheatstone.py --rx 4700 --tol 0.001 --seed 3
python3 run_wheatstone.py --noise-mv 0 --gbw 1e8 # remove ADC noise and op-amp lag (sanity check)
```

libngspice is the ngspice engine as a shared library. It is not part of LTspice.
On Windows, install ngspice and make sure `ngspice.dll` is on PATH.

## Results of the first run (Rx 2.2 kohm, R3 1 kohm, ratio arms 10 kohm, 0.1 % resistors)

| Run | Divider reading error | Bridge reading error |
|---|---|---|
| Closed-form expectation (tolerance only) | -0.089 % | -0.187 % |
| Co-sim, GBW 100 MHz, no noise | -0.083 % | -0.183 % |
| Co-sim, GBW 1 MHz, no noise | -0.093 % | -0.218 % |
| Co-sim, GBW 1 MHz, ADC noise 1.9 mV | -0.078 % (window std 0.05 %) | -0.149 % (window std 0.06 %) |
| Same with real 150 kHz PWM | -0.076 % | -0.146 % |

What the numbers say:

1. **The machinery is right.** With an ideal op-amp and no noise the co-simulation lands within 0.006 % of the closed-form tolerance error.
2. **A 1 MHz op-amp costs about 0.09 degrees of phase and 0.035 % on the bridge reading.** The phasor model of Stage 0 did not have this effect. MCP6004 typical GBW of 1 MHz is from my recollection of the datasheet and must be checked.
3. **The two-stage RC filter reduces V1 to about 0.68 V peak from the 0.9 V set on the pin** (gain about 0.77 at 500 Hz, plus 46 degrees of lag). The measurement is ratiometric so accuracy is unaffected, but Stage 0 assumed 0.9 V at V1, so signal-to-noise is about 25 % lower than assumed. Raise the pin amplitude to about 1.15 V if the headroom allows.
4. **PWM carrier leakage is negligible** at the assumed 150 kHz carrier (difference to the ideal drive 0.01 %, below noise). This holds only for the assumed carrier frequency, 10-bit duty resolution and 40 ohm pin resistance.
5. Window 0 is the warm-up (RC filters and the DC operating point settling) and is dropped.

## Iteration 1b: datasheet values and the real op-amp model

Changes (sources: RP2350 datasheet Tables 1683/1685 and sec. 12.4; MCP6001/2/4 datasheet DS20001733L):

| Item | Before | Now | Source |
|---|---|---|---|
| Op-amp | toy single-pole model | Microchip macromodel rev F (`models/MCP6001_MM_F.lib`, `--opamp mcp6004`); toy kept as `--opamp simple` | Microchip, ww1.microchip.com/downloads/en/DeviceDoc/MCP6001_MM_F.zip |
| ADC noise | 1.9 mV (this is ENOB 9, the *minimum*) | 1.3 mV (ENOB 9.5 typ); 1.86 mV = worst case | RP2350 Table 1685 |
| GPIO output resistance | 40 ohm | 100 ohm; datasheet only bounds it at <= 170 ohm (4 mA drive) | RP2350 Table 1683 (VOH >= 2.62 V) |
| ADC input load | none | 100 kohm and 1 pF per ADC pin | RP2350 Table 1685, sec. 12.4.3 |

Checked and unchanged: GBW 1 MHz typ, slew 0.6 V/us, rail swing within 25 mV, bias current 1 pA, Vos +-4.5 mV max.
Op-amp offset and bias current are removed by the lock-in (DC) or negligible against 10 kohm; op-amp noise (28 nV/rtHz,
about 28 uV over 1 MHz) is far below the ADC noise. The ADC rate stays at 480 kS/s (48 MHz / 100 via the pacing timer; the
RP2350 maximum is 500 kS/s) so that a window holds a whole number of 3-channel rounds.

Results (Rx 2.2 kohm, R3 1 kohm, ratio arms 10 kohm, ideal drive):

* Microchip macromodel vs toy model, seed 1: bridge -0.172 % vs -0.161 %, divider -0.108 % vs -0.085 %. The difference
  is below the window-to-window scatter (0.04 %). The Microchip run takes about 9 minutes, the toy model under 1 s.
* `monte_carlo.py`, 40 random bridges each (toy op-amp), 6 windows, error of the mean over the windows:

| Case | Bridge reading, std / 95th pct | Divider reading, std / 95th pct |
|---|---|---|
| 0.1 % resistors, 100 ohm pin, 1.3 mV noise | 0.103 % / 0.172 % | 0.059 % / 0.097 % |
| same, worst case 170 ohm pin, 1.86 mV noise | 0.103 % / 0.171 % | 0.058 % / 0.105 % |
| same, 40 ohm pin | 0.103 % / 0.174 % | 0.059 % / 0.101 % |
| 1 % resistors | 1.05 % / 1.82 % | 0.62 % / 0.94 % |
| 0.01 % resistors | 0.018 % / 0.037 % | 0.012 % / 0.025 % |

What this says: the error is set by resistor tolerance, not by the electronics. Pin resistance and ADC noise change
nothing visible, because the measurement is a ratio. With near-perfect resistors the modelled electronics contribute
about 0.02 %. The divider reading is better than the bridge reading in every case.

Still not modelled, and not answerable from the datasheet: ADC INL/DNL (datasheet says "Details to follow"), ADC
sampling kick-back, clock jitter, breadboard strays, temperature, and any DUT other than an ideal resistor. Keep the
ADC input pins' digital input disabled (IE low) because of erratum RP2350-E9 leakage. Treat 0.02 % as a floor, not a spec.

## Assumptions to replace with measurements

PWM carrier 150 kHz (TOP 999, 150 MHz clock), pin output resistance 40 ohm, ADC pin capacitance 5 pF,
ADC rate 480 kS/s total, ADC noise 1.9 mV rms, op-amp GBW 1 MHz / A0 100 dB / output resistance 100 ohm / 25 mV rail headroom.
Not modelled: ADC sampling-capacitor kick-back, op-amp offset, bias current, noise and slew limit,
temperature, breadboard strays, inductor/capacitor DUT parasitics, supply ripple.

## Next iterations

1. Closed loop: fill in `update_drive()` (software null search on V2 amplitude and phase).
2. Other three modules (Maxwell-Wien, Schering, Kelvin): replace the bridge block in `netlist.py` and the estimator in `virtual_pico.py`.
3. Monte Carlo around the co-simulation (component tolerance, ADC mismatch) and comparison with Stage 0.
4. Replace the op-amp macro-model with the Microchip MCP6004 SPICE model.
