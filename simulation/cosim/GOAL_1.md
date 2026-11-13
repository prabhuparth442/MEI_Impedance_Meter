# GOAL 1: a realistic, closed-loop simulation of the MEI impedance meter

Written 2026-10-29 for Claude (or any assistant) to read first and then work on.
Read also: `../MEI_CONTEXT.md`, `README.md` (this folder), `../circuit/mei_circuit.tex`, `../mei_sim_stage0/results.md`.

## 1. What we want

A simulation that behaves like the real instrument: a Raspberry Pi Pico 2 (RP2350) running firmware,
driving and reading the analog front end plus a bridge module, with the firmware reacting to what it measures
(software null search, switching ranges, compensating skew), all while the circuit state evolves in time.

We want to answer, before buying parts or building hardware:
- What accuracy can this design reach, and which non-ideality limits it (resistor tolerance, ADC, op-amp, timing, strays)?
- Does the closed-loop firmware converge and stay stable?
- What is the cheapest parts list that still meets the target (budget: about Rs 60 per resistor is too much)?

## 2. Why this is hard (the core problem)

The circuit and the Pico form a **feedback loop in real time**, not a sequence of independent calculations.

1. **LTspice (or any plain SPICE run) is a batch solver.** You give it the full netlist and all source
   waveforms up front; it computes the whole transient and writes results afterwards. A source value at time t
   cannot depend on a voltage the circuit produces at time t-dt, unless that dependence is written as a SPICE
   behavioural expression. Firmware logic (sampling the ADC, running a lock-in, deciding the next drive
   amplitude and phase) is not expressible that way.
2. **The Pico cannot be dropped into LTspice.** There is no RP2350 SPICE model, and SPICE cannot execute firmware.
   The Pico's pins must be replaced by their electrical behaviour (PWM output with pin resistance,
   ADC input with pin capacitance and sampling kick-back) and the firmware must run somewhere else.
3. **A two-step workflow does not work for closed loop.** "Simulate circuit, export waveform, process in Python,
   feed result back" only works if the Pico's output does not depend on the circuit's response.
   For a null search, auto-ranging or any adaptive drive, the next input depends on the previous output,
   so you cannot get all the data first and process it afterwards.
4. **Timing is part of the physics.** The Pico samples three ADC channels round-robin (not simultaneously),
   so there is inter-channel skew, which Stage 0 found must be compensated. PWM edges, the 480 kS/s ADC pacing
   and the 20 ms processing windows all interact with the analog time constants.
   A model that only knows phasors misses these.

## 3. Approach chosen (Option A: live co-simulation) and why

ngspice as a shared library (`libngspice`, called through `ctypes`, not LTspice) with Python playing the Pico:
- ngspice asks Python for the PWM pin voltage at every time step (external voltage-source callback).
- ngspice hands the ADC-pin voltages back to Python at every step (data callback).
- Both advance on one clock, so Python can change the drive and the change takes effect on the next step.

Rejected or deferred:
- LTspice: no usable live callback interface for this, no firmware execution.
- PySpice 1.5: fails with ngspice 42 ("Unsupported Ngspice version"). Use ctypes directly.
- Option B (real firmware in an emulator such as Wokwi or Renode): RP2350 analog support unverified; not pursued.
- Offline batch export (Level 1): fine for open-loop effects (carrier leakage, op-amp lag, loading), not for the closed loop.

## 4. Other issues that also limit realism

Modelling gaps (see README "Assumptions" for the full list):
- ADC: INL/DNL unknown (datasheet says "Details to follow"), sampling-capacitor kick-back, clock jitter not modelled.
  Digital input on ADC pins must be disabled (erratum RP2350-E9 leakage).
- Op-amp: Microchip MCP6004 macromodel is available (`models/MCP6001_MM_F.lib`) but one run takes about 9 minutes
  versus under 1 s for the toy model, so Monte Carlo uses the toy model.
- Not modelled: breadboard strays, temperature, supply ripple, inductor/capacitor DUT parasitics, DUT other than an ideal resistor.
- Unmeasured assumptions: PWM carrier 150 kHz, pin output resistance (datasheet only bounds it at <= 170 ohm), ADC noise 1.3 mV (typ) to 1.86 mV (min).

Findings already known:
- Error is dominated by resistor tolerance, not the electronics (electronics floor about 0.02 %).
- Divider reading beats the bridge-difference reading in deflection mode.
- The 2-stage RC filter drops V1 to about 0.68 V from 0.9 V set; raise pin amplitude to about 1.15 V if headroom allows.
- Window 0 is warm-up and must be dropped.
- Op-amp lag at 1 MHz GBW costs about 0.09 degrees, which matters for tan-delta (Maxwell-Wien, Schering).

Practical issues:
- Budget: 1 % resistors plus calibration is the plan; this only works if the firmware uses measured values
  and a reference meter good to about 0.05 % is available (unconfirmed).
- Deadline assumed Nov 16 (unconfirmed with the professor; end-sems start Nov 23). Demo format unconfirmed.
- Only 3 ADC pins, so one bridge module is connected at a time.
- Two copies of the code may exist (this folder and `Practice_Projects/MEI_Impedance_Meter/`). On 2026-10-29 a run
  reproduced the old iteration-1 numbers exactly, which suggests a stale copy was executed. Always check
  `grep -n opamp run_wheatstone.py` before trusting a run.

## 5. Current state

Iteration 1 / 1b done for the Wheatstone module, **open loop only**: `update_drive()` in `virtual_pico.py` is an empty hook.
Machinery validated against the closed form within 0.006 %. Monte Carlo script exists (`monte_carlo.py`).

## 6. Tasks, in order

1. Add `--cal-err X`: firmware knows R3, Rr1, Rr2 only to within +/-X % (the reference-meter uncertainty). Sweep X to size the meter needed for 1 % parts.
2. Implement closed-loop `update_drive()`: software null search on V2 amplitude and phase; report convergence time and final error.
3. Raise the pin amplitude (about 1.15 V) and re-check headroom and SNR.
4. Add the other modules (Maxwell-Wien, Schering, Kelvin/Hay): replace the bridge block in `netlist.py` and the estimator in `virtual_pico.py`; include a reactive DUT with parasitics.
5. Add ADC channel gain mismatch and loopback calibration; add skew compensation test.
6. Monte Carlo around the co-simulation and compare with Stage 0 tables.
7. Loopback on real hardware to replace the unmeasured assumptions.

## 7. Done when

- Closed-loop run converges for all four modules across random tolerance and noise seeds.
- A table of error versus resistor grade and calibration-meter accuracy exists, and the cheapest parts list meeting the target is named.
- Each remaining assumption is either measured or listed with its effect on the result.

## 8. Working rules for the assistant

- State which code copy and which flags produced every number.
- Keep README results and `../MEI_CONTEXT.md` in sync with what you change.
- Do not claim accuracy below the 0.02 % electronics floor; treat it as a floor, not a spec.
- Ask the user before spending money or changing the module list.
