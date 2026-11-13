"""
ngspice_link.py  -  thin ctypes wrapper around libngspice (the ngspice engine as a library)

WHAT THIS FILE DOES
-------------------
libngspice is the ngspice circuit-simulator engine packaged as a shared library
(libngspice.so on Linux, ngspice.dll on Windows, libngspice.dylib on macOS).
Python can load it and *steer* the simulation while it is running.  Two things
matter for us:

  1. "External voltage source": in the netlist, a source declared as
         Vp14 p14 0 dc 0 external
     has no fixed waveform.  Every time ngspice needs its value at time t it calls a
     Python function we registered (the "vsrc callback").  Python returns the voltage.
     This is how the virtual Pico drives its PWM pins.

  2. "Data callback": after every accepted time step ngspice calls a Python function and
     passes the voltages of all nodes.  This is how the virtual Pico reads its ADC pins.

Both callbacks run *inside* the ngspice time loop, so Python and the circuit really do
advance together, step by step.  Nothing is exported to a file and post-processed.

WHY ctypes AND NOT PySpice
--------------------------
PySpice 1.5 raised "Unsupported Ngspice version 42" here and its run() failed, so we call
the C API directly.  The API used (ngSpice_Init, ngSpice_Init_Sync, ngSpice_Circ,
ngSpice_Command) is the documented "shared ngspice" interface.
"""
import ctypes as C
import ctypes.util
import os
import sys


# ---- C structures (layout copied from ngspice's sharedspice.h) -------------------------
class _VecValues(C.Structure):          # one node voltage at one time point
    _fields_ = [("name", C.c_char_p), ("creal", C.c_double), ("cimag", C.c_double),
                ("is_scale", C.c_bool), ("is_complex", C.c_bool)]


class _VecValuesAll(C.Structure):       # all vectors at one time point
    _fields_ = [("veccount", C.c_int), ("vecindex", C.c_int),
                ("vecs", C.POINTER(C.POINTER(_VecValues)))]


# ---- C callback prototypes -------------------------------------------------------------
_SEND_CHAR = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
_SEND_STAT = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
_CTRL_EXIT = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
_SEND_DATA = C.CFUNCTYPE(C.c_int, C.POINTER(_VecValuesAll), C.c_int, C.c_int, C.c_void_p)
_SEND_INIT = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int, C.c_void_p)
_BG_RUNNING = C.CFUNCTYPE(C.c_int, C.c_bool, C.c_int, C.c_void_p)
_GET_VSRC = C.CFUNCTYPE(C.c_int, C.POINTER(C.c_double), C.c_double, C.c_char_p, C.c_int, C.c_void_p)
_GET_ISRC = C.CFUNCTYPE(C.c_int, C.POINTER(C.c_double), C.c_double, C.c_char_p, C.c_int, C.c_void_p)
_GET_SYNC = C.CFUNCTYPE(C.c_int, C.c_double, C.POINTER(C.c_double), C.c_double, C.c_int, C.c_int, C.c_void_p)


def _find_library():
    """Locate libngspice on Linux / macOS / Windows."""
    cands = []
    found = ctypes.util.find_library("ngspice")
    if found:
        cands.append(found)
    cands += ["libngspice.so.0", "libngspice.so", "libngspice.dylib", "ngspice.dll", "libngspice-0.dll"]
    for c in cands:
        try:
            return C.CDLL(c)
        except OSError:
            continue
    raise OSError("libngspice not found. Linux: sudo apt install libngspice0-dev   "
                  "Windows: install ngspice and put ngspice.dll on PATH.")


class NgspiceLink:
    """
    Usage:
        link = NgspiceLink()
        link.set_vsrc_callback(lambda name, t: ...voltage...)        # drives 'external' sources
        link.set_data_callback(["adc0", "adc1", "adc2"], lambda t, v: ...)   # reads nodes
        link.load(netlist_text)
        link.run()                                                    # blocks until .tran ends
    """

    def __init__(self):
        self.lib = _find_library()
        self._vsrc_cb = None
        self._data_cb = None
        self._watch = []
        self._idx = None
        self.messages = []              # everything ngspice prints (useful for debugging)

        # --- callbacks that ngspice requires, even if we ignore their content ---
        def on_char(s, ident, user):
            self.messages.append(s.decode(errors="ignore"))
            return 0

        def on_stat(s, ident, user):
            return 0

        def on_exit(status, immediate, quit_, ident, user):
            return 0

        def on_init(p, ident, user):
            return 0

        def on_bg(is_running, ident, user):
            return 0

        def on_data(p, nvec, ident, user):
            # Called after each accepted time step.  p.vecs[k] holds vector k (time, v(node)...).
            a = p.contents
            if self._idx is None:       # first call: find where "time" and our watched nodes sit
                names = [a.vecs[k].contents.name.decode().lower() for k in range(a.veccount)]
                self._t_idx = names.index("time")
                self._idx = [names.index(w.lower()) for w in self._watch]
            if self._data_cb is not None:
                t = a.vecs[self._t_idx].contents.creal
                vals = [a.vecs[i].contents.creal for i in self._idx]
                self._data_cb(t, vals)
            return 0

        def on_vsrc(vptr, t, name, ident, user):
            if self._vsrc_cb is not None:
                vptr[0] = self._vsrc_cb(name.decode().lower(), t)
            return 0

        def on_isrc(vptr, t, name, ident, user):
            return 0

        def on_sync(t, delta, old_delta, redo, ident, user):
            return 0

        # keep references, otherwise Python garbage-collects them and ngspice crashes
        self._cb = (_SEND_CHAR(on_char), _SEND_STAT(on_stat), _CTRL_EXIT(on_exit),
                    _SEND_DATA(on_data), _SEND_INIT(on_init), _BG_RUNNING(on_bg),
                    _GET_VSRC(on_vsrc), _GET_ISRC(on_isrc), _GET_SYNC(on_sync))
        self.lib.ngSpice_Init(self._cb[0], self._cb[1], self._cb[2], self._cb[3],
                              self._cb[4], self._cb[5], None)
        self.lib.ngSpice_Init_Sync(self._cb[6], self._cb[7], self._cb[8], None, None)
        # PSpice compatibility: the Microchip op-amp model uses POLY/TABLE sources written for PSpice.
        self.lib.ngSpice_Command(b"set ngbehavior=psa")

    # ---------------------------------------------------------------------------------
    def set_vsrc_callback(self, fn):
        """fn(source_name: str, t: float) -> volts.   Called for every 'external' voltage source."""
        self._vsrc_cb = fn

    def set_data_callback(self, watch_nodes, fn):
        """fn(t: float, values: list[float]) after every time step; values follow watch_nodes order."""
        self._watch = list(watch_nodes)
        self._idx = None
        self._data_cb = fn

    def load(self, netlist_text):
        lines = [ln for ln in netlist_text.splitlines() if ln.strip() != ""]
        arr = (C.c_char_p * (len(lines) + 1))(*[ln.encode() for ln in lines], None)
        rc = self.lib.ngSpice_Circ(arr)
        if rc != 0:
            raise RuntimeError("ngspice rejected the netlist:\n" + "\n".join(self.messages[-15:]))

    def run(self):
        rc = self.lib.ngSpice_Command(b"run")
        if rc != 0:
            raise RuntimeError("ngspice 'run' failed:\n" + "\n".join(self.messages[-15:]))

    def errors(self):
        return [m for m in self.messages if "rror" in m]
