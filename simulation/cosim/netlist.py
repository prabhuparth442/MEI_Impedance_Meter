"""
netlist.py  -  builds the SPICE text of the analog front end + the Wheatstone bridge module.

Everything *outside* the Raspberry Pi Pico 2 chip is in this netlist:
the PWM-output RC filters, the quad op-amp (U1A..U1D), the plug-in bridge module,
and the ADC input RC networks.  The Pico itself is NOT here: its two PWM pins are
"external" voltage sources whose values Python supplies (see virtual_pico.py).

Node names (match the circuit diagram, mei_circuit.tex):
    p14, p15     ideal PWM driver outputs inside the Pico (set by Python)
    n14, n15     Pico pin after its output resistance
    a1,b1 / a2,b2   first / second RC stage nodes of channel A / channel B
    v1           U1A output  = bridge excitation  (EXC)      -> ADC0
    v2           U1B output  = bridge return      (RET)
    ma, mb       bridge mid nodes (MIDA, MIDB), buffered by U1C / U1D
    sma, smb     buffered mid nodes                          -> ADC1 / ADC2
    adc0..adc2   the three Pico ADC pins (after 100 ohm + 1 nF input network)
"""
import math
import os

MCP_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "MCP6001_MM_F.lib")


def mcp6004_subckt():
    """
    Microchip's own macromodel (MCP6001/2/4 family, rev F, models/MCP6001_MM_F.lib, unmodified file),
    wrapped in the same pin order as opamp_subckt().  It contains input offset, bias current, noise
    sources, finite gain/PSRR/CMRR, slew rate, output swing and short-circuit current limit.
    One mechanical fix is applied at load time: PSpice writes 'TC 3.11M 4.51U' on resistor R61,
    which ngspice wants as 'TC1=3.11M TC2=4.51U'.  Nothing else is changed.
    """
    with open(MCP_LIB) as f:
        lib = f.read().replace("R61 0 61 100 TC 3.11M 4.51U", "R61 0 61 100 TC1=3.11M TC2=4.51U")
    wrap = """.subckt opamp inp inn out vdd vss
X1 inp inn vdd vss out MCP6001
.ends opamp"""
    return lib + "\n" + wrap


def opamp_subckt(gbw_hz=1.0e6, a0=1.0e5, rout=100.0, headroom=0.025):
    """
    Simple op-amp macro-model (NOT the Microchip model; parameters are datasheet-style guesses).

      * input stage : transconductance gm into R_p || C_p   -> one dominant pole
                      DC gain a0, gain-bandwidth product gbw_hz
      * output stage: hard clamp to [VSS+headroom, VDD-headroom]  (rail-to-rail limit)
                      followed by output resistance rout
    Open-loop: A(s) = a0 / (1 + s/(2*pi*fp)), fp = gbw/a0.
    Not modelled: input offset, bias current, slew-rate limit, noise, load-dependent rout.
    """
    gm = 1.0e-3
    rp = a0 / gm
    fp = gbw_hz / a0
    cp = 1.0 / (2 * math.pi * fp * rp)
    return f""".subckt opamp inp inn out vdd vss
G1 0 n1 inp inn {gm:.6g}
Rp n1 0 {rp:.6g}
Cp n1 0 {cp:.6g}
B1 mid 0 V=min(max(V(n1),V(vss)+{headroom}),V(vdd)-{headroom})
Ro mid out {rout:.6g}
.ends opamp"""


def wheatstone_netlist(*, rx_true, r3_true, rr1_true, rr2_true,
                       tstop, tmax,
                       r_pin=100.0,             # Pico GPIO output resistance.  Datasheet gives only VOH >= 2.62 V at
                                                # 3.3 V for IOH = 2..12 mA, i.e. <= 170 ohm at the default 4 mA drive,
                                                # <= 57 ohm at 12 mA.  100 ohm is a mid-range guess; sweep it.
                       r_filt=1e3, c_filt=100e-9,
                       r_adc=100.0, c_adc=1e-9, c_pin=5e-12,   # ADC input RC + pin capacitance (c_pin = guess)
                       r_in_adc=100e3,          # RP2350 datasheet Table 1685: ADC input impedance >= 100 kohm
                       c_in_adc=1e-12,          # RP2350 datasheet 12.4.3: ~1 pF across the input while sampling
                       opamp_model="mcp6004",   # "mcp6004" = Microchip macromodel, "simple" = old toy model
                       opamp=None):
    """Return the full netlist as text.  *_true are the real (tolerance-affected) values."""
    opamp = opamp or {}
    opamp_text = mcp6004_subckt() if opamp_model == "mcp6004" else opamp_subckt(**opamp)
    return f"""MEI impedance meter - Wheatstone module - front end for co-simulation
* ---------------- supply (3V3(OUT) of the Pico, AGND = node 0) ----------------
Vdd vdd 0 DC 3.3

* ---------------- Pico PWM pins: external sources driven from Python ----------------
Vp14 p14 0 dc 0 external
Rp14 p14 n14 {r_pin:g}
Vp15 p15 0 dc 0 external
Rp15 p15 n15 {r_pin:g}

* ---------------- channel A: two-stage RC low-pass -> follower U1A -> V1 ----------------
R1 n14 a1 {r_filt:g}
C1 a1 0 {c_filt:g}
R2 a1 b1 {r_filt:g}
C2 b1 0 {c_filt:g}
XU1A b1 v1 v1 vdd 0 opamp

* ---------------- channel B: same chain -> follower U1B -> V2 (return, held at mid-rail) ----
R3f n15 a2 {r_filt:g}
C3 a2 0 {c_filt:g}
R4f a2 b2 {r_filt:g}
C4 b2 0 {c_filt:g}
XU1B b2 v2 v2 vdd 0 opamp

* ---------------- plug-in module: Wheatstone  (EXC=v1, MIDA=ma, MIDB=mb, RET=v2) -------
Rb3  v1 ma {r3_true:.9g}
Rbx  ma v2 {rx_true:.9g}
Rbr1 v1 mb {rr1_true:.9g}
Rbr2 mb v2 {rr2_true:.9g}

* ---------------- sense buffers U1C, U1D ----------------
XU1C ma sma sma vdd 0 opamp
XU1D mb smb smb vdd 0 opamp

* ---------------- ADC input networks: 100 ohm + 1 nF, plus pin capacitance ----------------
Radc0 v1  adc0 {r_adc:g}
Cadc0 adc0 0 {c_adc + c_pin + c_in_adc:g}
Rin0 adc0 0 {r_in_adc:g}
Radc1 sma adc1 {r_adc:g}
Cadc1 adc1 0 {c_adc + c_pin + c_in_adc:g}
Rin1 adc1 0 {r_in_adc:g}
Radc2 smb adc2 {r_adc:g}
Cadc2 adc2 0 {c_adc + c_pin + c_in_adc:g}
Rin2 adc2 0 {r_in_adc:g}

{opamp_text}

.options reltol=1e-5 abstol=1e-12 vntol=1e-9 method=trap gmin=1e-13
.tran {tmax:g} {tstop:g} 0 {tmax:g}
.end
"""
