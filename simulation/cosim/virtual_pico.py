"""
virtual_pico.py  -  a Python model of the Raspberry Pi Pico 2 as the analog circuit sees it.

The real chip does three jobs; each is a method here:

  1. PWM output          pin_voltage(name, t)     -> what GP14 / GP15 put on the wire at time t
  2. 12-bit ADC           on_step(t, volts)        -> sample ADC0/1/2 at the right instants
  3. Firmware (math)      measure_window / estimate -> lock-in, then impedance from the readings

ngspice calls pin_voltage() (through the vsrc callback) and on_step() (through the data
callback) while the transient simulation is running, so this object lives "inside" the
simulation clock.  Sections marked  >>> ASSUMPTION <<<  must be replaced by measured values
once the real board is available (loopback test).
"""
import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class PicoConfig:
    # ---- signal definition ---------------------------------------------------------
    f0: float = 500.0            # excitation frequency, Hz
    vdd: float = 3.3             # logic / ADC full scale, V
    amp1: float = 0.9            # V1 amplitude (peak) on the 1.65 V bias, V
    phase1: float = 0.0          # V1 phase, rad
    amp2: float = 0.0            # V2 amplitude (0 = return held at mid-rail)
    phase2: float = 0.0

    # ---- how the pin voltage is produced ------------------------------------------
    pwm_mode: str = "ideal"      # "ideal": pin = bias + sine (an ideal DAC, fast to simulate)
                                 # "pwm"  : real 0/3.3 V PWM; the RC filter must remove the carrier
    pwm_clk: float = 150e6       # RP2350 default system clock = PWM counter clock (150 MHz)
    pwm_top: int = 999           # counter wraps at TOP -> carrier = clk/(TOP+1) = 150 kHz  >>> ASSUMPTION <<<

    # ---- ADC ------------------------------------------------------------------------
    adc_bits: int = 12
    adc_fs_total: float = 480e3  # total conversion rate, shared by the 3 channels (round-robin) >>> ASSUMPTION <<<
    adc_noise_mv: float = 1.9    # rms noise, ~9 effective bits  >>> ASSUMPTION (unverified datasheet summary) <<<
    adc_gain_err: tuple = (0.0, 0.0, 0.0)   # per-channel relative gain error (loopback calibration target)

    # ---- measurement window -------------------------------------------------------
    cycles: int = 10             # integer number of excitation cycles per lock-in window (20 ms)
    n_windows: int = 4           # window 0 is warm-up (filters settling), the rest are measurements

    seed: int = 1


class VirtualPico:
    """Holds the Pico's state (drive settings, ADC buffers, results) during one simulation."""

    CH = 3                                   # ADC0, ADC1, ADC2 are read in turn

    def __init__(self, cfg: PicoConfig, r3_nominal: float):
        self.cfg = cfg
        self.r3_nom = r3_nominal             # firmware knows only the NOMINAL bridge values
        self.rng = np.random.default_rng(cfg.seed)
        self.lsb = cfg.vdd / (2 ** cfg.adc_bits)
        self.t_conv = 1.0 / cfg.adc_fs_total                     # time between two conversions
        self.win_len = cfg.cycles / cfg.f0                       # window duration, s
        self.conv_per_win = int(round(self.win_len * cfg.adc_fs_total))
        assert self.conv_per_win % self.CH == 0, "window must hold a whole number of 3-channel rounds"

        # PWM bookkeeping
        self.tclk = 1.0 / cfg.pwm_clk
        self.tc = (cfg.pwm_top + 1) * self.tclk                  # carrier period
        self._duty_cache = {}                                    # (pin, period index) -> counts

        # ADC bookkeeping: conversion m happens at t = m * t_conv, on channel m % 3
        self.m_next = 0
        self.t_prev = None
        self.v_prev = None
        self._buf_t = [[] for _ in range(self.CH)]
        self._buf_x = [[] for _ in range(self.CH)]
        self.results = []                                        # one dict per finished window

    # ====================================================================================
    # 1. PWM OUTPUT   (called by ngspice for the external sources Vp14 / Vp15)
    # ====================================================================================
    def _target_voltage(self, pin, t):
        """The *average* voltage the firmware wants on a pin at time t: bias + sine."""
        c = self.cfg
        amp, ph = (c.amp1, c.phase1) if pin == "vp14" else (c.amp2, c.phase2)
        return c.vdd / 2 + amp * math.sin(2 * math.pi * c.f0 * t + ph)

    def pin_voltage(self, name, t):
        """Voltage on the Pico pin (ideal driver, before the pin's output resistance)."""
        c = self.cfg
        if c.pwm_mode == "ideal":
            return self._target_voltage(name, t)

        # --- real PWM -------------------------------------------------------------------
        # The counter runs 0..TOP at 150 MHz; the pin is high while counter < LEVEL.
        # Firmware updates LEVEL once per carrier period: LEVEL = round(duty * (TOP+1)).
        k = int(t // self.tc)                                    # which carrier period are we in
        key = (name, k)
        level = self._duty_cache.get(key)
        if level is None:                                        # new period: compute duty from the sine
            duty = self._target_voltage(name, k * self.tc) / c.vdd
            level = int(round(duty * (c.pwm_top + 1)))
            level = min(max(level, 0), c.pwm_top + 1)
            if len(self._duty_cache) > 64:
                self._duty_cache.clear()
            self._duty_cache[key] = level
        t_in_period = t - k * self.tc
        return c.vdd if t_in_period < level * self.tclk else 0.0

    # ====================================================================================
    # 2. ADC   (called by ngspice after every accepted time step)
    # ====================================================================================
    def on_step(self, t, volts):
        """
        ngspice gives the three ADC-pin voltages at its own (irregular) time points.
        The real ADC converts at fixed instants t_m = m / fs_total, channel (m mod 3).
        We linearly interpolate between the two surrounding ngspice points.
        """
        if self.t_prev is None:
            self.t_prev, self.v_prev = t, list(volts)
            return
        while self.m_next * self.t_conv <= t:
            tm = self.m_next * self.t_conv
            if tm > self.t_prev:                                 # skip m = 0 (needs a point before it)
                ch = self.m_next % self.CH
                frac = (tm - self.t_prev) / (t - self.t_prev)
                v = self.v_prev[ch] + frac * (volts[ch] - self.v_prev[ch])
                self._convert(ch, tm, v)
            self.m_next += 1
            if self.m_next % self.conv_per_win == 0:
                self._finish_window()
        self.t_prev, self.v_prev = t, list(volts)

    def _convert(self, ch, tm, v):
        """One ADC conversion: gain error, noise, 12-bit rounding, clipping.  Stores (time, volts)."""
        c = self.cfg
        v = v * (1.0 + c.adc_gain_err[ch]) + self.rng.normal(0.0, c.adc_noise_mv * 1e-3)
        code = int(math.floor(v / self.lsb))
        code = min(max(code, 0), 2 ** c.adc_bits - 1)
        self._buf_t[ch].append(tm)                               # TRUE conversion time (skew compensation)
        self._buf_x[ch].append((code + 0.5) * self.lsb)          # mid-tread reconstruction

    # ====================================================================================
    # 3. FIRMWARE MATH
    # ====================================================================================
    @staticmethod
    def lockin(t, x, f0):
        """
        Coherent lock-in: phasor of x at f0, using each sample's TRUE time t.
        Over an integer number of cycles this ignores DC and every other harmonic of 1/T_window
        (50 Hz mains included, since the 20 ms window holds exactly one mains cycle).
        Using the true per-channel time also removes the 2 us channel-to-channel skew.
        """
        t = np.asarray(t)
        x = np.asarray(x)
        return 2.0 / len(x) * np.sum(x * np.exp(-2j * math.pi * f0 * t))

    def _finish_window(self):
        """Window complete -> lock-in on each channel -> impedance estimate -> maybe change drive."""
        ph = [self.lockin(self._buf_t[c], self._buf_x[c], self.cfg.f0) for c in range(self.CH)]
        for c in range(self.CH):
            self._buf_t[c].clear()
            self._buf_x[c].clear()
        v1, ma, mb = ph
        est = self.estimate_wheatstone(v1, ma, mb)
        est["window"] = len(self.results)
        est["phasors"] = ph
        self.results.append(est)
        self.update_drive(est)                                   # <- the closed-loop hook

    def estimate_wheatstone(self, v1, ma, mb):
        """
        Wheatstone bridge in deflection mode (nothing is balanced; we read the imbalance).

            q_A = MA/V1 = Rx/(R3+Rx)           divider reading (left arm only)
            D   = (MA-MB)/V1 = q_A - 1/2       bridge reading  (ratio arms Rr1 = Rr2, nominal)

        Solving the divider for Rx:   Rx = R3 * q/(1-q)
          - from the bridge reading:  q = 1/2 + D        (uses the right arm as the reference)
          - from the divider reading: q = q_A            (right arm not used)
        Stage 0 showed the divider reading is often more accurate; both are kept as a cross-check.
        """
        q_bridge = 0.5 + (ma - mb) / v1
        q_div = ma / v1
        f = lambda q: self.r3_nom * q / (1.0 - q)
        return dict(rx_bridge=f(q_bridge), rx_divider=f(q_div), v1_amp=abs(v1))

    def update_drive(self, est):
        """
        HOOK FOR ITERATION 2 (closed loop).  Today it changes nothing, so the drive is fixed.
        Planned: software null search - adjust amp2/phase2 (the return voltage) until the bridge
        difference MA-MB is small, then read Rx from the amount of correction needed.
        Because this runs inside the ngspice time loop, the new amp2/phase2 take effect
        on the very next simulated time step.
        """
        return
