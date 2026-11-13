# MEI Impedance Meter

Digital impedance meter (R, L, C) using a Raspberry Pi Pico 2, a reference resistor, MCP6004 op-amp buffers and a software lock-in. MEI course project, IIT Bhubaneswar.

The meter is a divider: V1 - Rref - Vmid - Zx - V2. The Pico drives V1 with a PWM sine, reads V1 and Vmid with its ADC, and computes Zx = Rref * H / (1 - H), H = Vmid / V1 (complex, from the lock-in).

## Layout

| Folder | Contents |
|---|---|
| `report/` | Project report (PDF, DOCX, HTML source, figures) |
| `hardware/` | Circuit drawing of the built meter (PDF, LaTeX source) |
| `firmware/` | Pico 2 MicroPython lock-in (`lockin.py`), host tool (`imeter.py`), calibration (`cal.json`), part values (`config.py`), bring-up log (`NOTES.md`) |
| `simulation/ltspice/` | LTspice schematic `Model1.asc`, results `Model1.raw`, log, drawing of the simulated circuit |
| `simulation/stage0/` | Python phasor Monte Carlo (Stage 0) and result tables |
| `simulation/cosim/` | Pico + ngspice co-simulation (Wheatstone module), see its `README.md` |
| `video/` | Demo video captions (`.srt`) and the script that built it. The video itself is not in the repository (size). |

## Run

Needs a Pico 2 with MicroPython flashed, and `mpremote`, `numpy`, `scipy` on the host.

```
cd firmware
python3 imeter.py cal-add --rref 10k --r 0 --freqs 125,250,500,1000       # short
python3 imeter.py cal-add --rref 10k --r open --freqs 125,250,500,1000    # open
python3 imeter.py cal-add --rref 10k --r 1001 --freqs 125,250,500,1000    # known resistor
python3 imeter.py measure --rref 10k --freqs 125,250,500,1000
python3 imeter.py selftest                                                # offline check
```

`--rref` must match the resistor fitted on the board. The label `10k` is the 9.9 kOhm part (measured value in `config.py`).
`cal.json` holds the calibration of this particular breadboard; redo it for another build.

Co-simulation: `sudo apt install ngspice libngspice0-dev`, then `python3 simulation/cosim/run_wheatstone.py`.
