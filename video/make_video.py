#!/usr/bin/env python3
"""
Side-by-side demo video builder for the Pico 2 divider-type impedance meter.

  Left  : breadboard camera (CKT_VIEW_Compressed.mp4)
  Right : terminal screen   (Terminal_Compressed.mp4), cropped + zoomed
  Added : intro card, live captions / Rref chips, result boxes that follow the
          terminal output as it scrolls, speed-up badge, summary table, .srt file

Everything you may want to edit (captions, notes, nominal values, timings)
is in the DATA section below -- change it and re-run:

    python3 make_video.py                 # full render  -> ../MEI_Impedance_Meter_Demo.mp4
    python3 make_video.py --only 3,4      # quick test of runs 3 and 4 only
"""
import argparse, subprocess, sys, os, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.dirname(HERE)
CKT = os.path.join(VID, "CKT_VIEW_Compressed.mp4")
TERM = os.path.join(VID, "Terminal_Compressed.mp4")

# ============================ DATA (edit me) ================================
# terminal clock = circuit clock + OFFSET  (measured by audio cross-correlation)
OFFSET = 7.95
GAP_SPEED = 4          # speed-up for idle / hardware-swap time
FPS = 30
W, H = 1920, 1080

TITLE = "Divider-Type Impedance Meter"
SUBTITLE = "Raspberry Pi Pico 2 (RP2350)  ·  PWM sine + ADC lock-in  ·  MicroPython"
COURSE = "MEI Course Project"
CAP_NOMINAL = "≈ 80 nF"          # what the ceramic capacitor is claimed to be
FOOTER = "Rref values measured with a multimeter  ·  ceramic capacitor nominal " + CAP_NOMINAL

# Terminal clock (seconds): (command executed, result on screen).
# Found by frame-differencing the terminal recording.
# rref_hw  : resistor physically on the board       flag : what the command used
# result   : headline reading, as printed by the tool (read from the screen)
# short    : same reading for the summary table
RUNS = [
 dict(tc=36,  tr=42,  rref_hw="9.9 kΩ", flag="10k", cal=True,  fit="DUT looks like: R: R = 6039.55 ohm   (fit error 0.35 %)",
      setup="Setup: Zx = 6.15 kΩ resistor, Rref = 9.9 kΩ",
      zx="6.15 kΩ resistor", result="R = 6039.55 Ω", detail="−1.8 % vs 6.15 kΩ  ·  fit error 0.35 %", note=""),
 dict(tc=99,  tr=104, rref_hw="9.9 kΩ", flag="10k", cal=True,  fit="DUT looks like: R || C (parallel):  R = 5764.95 ohm, C = 70.36 nF   (fit error 5.21 %)",
      setup="80 nF ceramic capacitor added in parallel with the resistor",
      zx="6.15 kΩ ∥ 80 nF", result="R = 5764.95 Ω  ∥  C = 70.36 nF", detail="R: −6.3 % vs 6.15 kΩ  ·  fit error 5.21 %",
      note="Tool picks the parallel R∥C model by itself.  C nominal " + CAP_NOMINAL),
 dict(tc=126, tr=130, rref_hw="1 kΩ",   flag="10k", cal=True,  fit="DUT looks like: R || C (parallel):  R = 57895.44 ohm, C = 6.62 nF   (fit error 5.69 %)",
      setup="Rref swapped 9.9 kΩ → 1 kΩ on the board, but the command still says --ref 10k",
      zx="6.15 kΩ ∥ 80 nF", result="R = 57895 Ω  ∥  C = 6.62 nF  (INVALID)", detail="Software assumes Rref = 9.9 kΩ, hardware has 1 kΩ",
      note="Range mismatch → wrong numbers. Always change --ref together with the resistor.", bad=True),
 dict(tc=172, tr=175, rref_hw="9.9 kΩ", flag="10k", cal=True,  fit="DUT looks like: R:  R = 4723.35 ohm   (fit error 0.17 %)",
      setup="Rref back to 9.9 kΩ  ·  Zx = 4.7 kΩ resistor",
      zx="4.7 kΩ resistor", result="R = 4723.35 Ω", detail="+0.5 % vs 4.7 kΩ  ·  fit error 0.17 %", note="Matched Rref: accurate again."),
 dict(tc=205, tr=209, rref_hw="1 kΩ",   flag="1k",  cal=False, fit="DUT looks like: R:  R = 3969.47 ohm   (fit error 9.84 %)",
      setup="Rref swapped to 1 kΩ, command updated to --ref 1k  ·  Zx unchanged (4.7 kΩ)",
      zx="4.7 kΩ resistor", result="R = 3969.47 Ω", detail="−15.5 % vs 4.7 kΩ  ·  fit error 9.84 %",
      note="4.7 kΩ is outside the sweet spot of a 1 kΩ Rref, and this range is not calibrated yet."),
 dict(tc=247, tr=251, rref_hw="9.9 kΩ", flag="10k", cal=True,  fit="DUT looks like: R:  R = 2648.34 ohm   (fit error 0.26 %)",
      setup="Rref back to 9.9 kΩ  ·  Zx = 4.7 kΩ ∥ 6.15 kΩ (two resistors in parallel)",
      zx="4.7 kΩ ∥ 6.15 kΩ", result="R = 2648.34 Ω", detail="−0.6 % vs 2.66 kΩ (calculated parallel value)  ·  fit 0.26 %", note=""),
 dict(tc=288, tr=292, rref_hw="9.9 kΩ", flag="10k", cal=True,  fit="DUT looks like: R + C (series):  R = 268.22 ohm, C = 72.36 nF   (fit error 1.77 %)",
      setup="Zx = 80 nF ceramic capacitor only (no resistor)",
      zx="80 nF capacitor", result="C = 72.36 nF  (series R = 268 Ω)", detail="fit error 1.77 %  ·  C nominal " + CAP_NOMINAL,
      note="Identified as a capacitor. The ~268 Ω is apparent series loss (ideal cap → 0 Ω)."),
 dict(tc=352, tr=356, rref_hw="9.9 kΩ", flag="10k", cal=True,  fit="DUT looks like: R + C (series):  R = 1274.34 ohm, C = 74.77 nF   (fit error 2.01 %)",
      setup="Zx = 80 nF capacitor in series with a 1 kΩ resistor",
      zx="1 kΩ + 80 nF (series)", result="R = 1274.34 Ω  +  C = 74.77 nF", detail="fit error 2.01 %  ·  C nominal " + CAP_NOMINAL,
      note="Extra ≈ 274 Ω over 1 kΩ ≈ the 268 Ω loss seen with the capacitor alone."),
 dict(tc=394, tr=398, rref_hw="1 kΩ",   flag="1k",  cal=False, fit="DUT looks like: R:  R = 215.43 ohm   (fit error 2.62 %)",
      setup="Rref → 1 kΩ (--ref 1k)  ·  Zx = 220 \u03a9 resistor",
      zx="220 Ω resistor", result="R = 215.43 Ω", detail="−2.1 % vs 220 Ω  ·  fit error 2.62 %", note="Low-value part: the 1 kΩ Rref range suits it."),
 dict(tc=446, tr=449, dy=13, rref_hw="1 kΩ",   flag="1k",  cal=False, fit="DUT looks like: R + C (series):  R = 475.03 ohm, C = 66.14 nF   (fit error 2.02 %)",
      setup="Zx = 80 nF ceramic capacitor, Rref still 1 kΩ",
      zx="80 nF capacitor", result="C = 66.14 nF  (series R = 475 Ω)", detail="fit error 2.02 %  ·  C nominal " + CAP_NOMINAL,
      note="1 kΩ range is uncalibrated, so C reads lower than on the 9.9 kΩ range."),
 dict(tc=476, tr=479, rref_hw="1 kΩ",   flag="1k",  cal=False, fit="DUT looks like: R:  R = 1891.91 ohm   (fit error 5.95 %)",
      setup="Zx = 2 kΩ resistor, Rref = 1 kΩ",
      zx="2 kΩ resistor", result="R = 1891.91 Ω", detail="−5.4 % vs 2 kΩ  ·  fit error 5.95 %", note="Uncalibrated 1 kΩ range."),
 dict(tc=537, tr=541, rref_hw="1 kΩ",   flag="1k",  cal=False, fit="DUT looks like: R || C (parallel):  R = 2094.05 ohm, C = 53.65 nF   (fit error 7.33 %)",
      setup="Zx = 2 kΩ ∥ 80 nF, plus 0.22 kΩ",
      zx="2 kΩ ∥ 80 nF  (+ 0.22 kΩ)", result="R = 2094.05 Ω  ∥  C = 53.65 nF", detail="fit error 7.33 % (poor)  ·  C nominal " + CAP_NOMINAL,
      note="Largest fit error of the session — mixed R/C network, uncalibrated range."),
]
RUN_PRE, RUN_POST = 3, 4   # seconds kept before the command / after the result
# ============================================================================

FD = "/usr/share/fonts/truetype/dejavu/"
def F(sz, bold=False):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)

BG = (13, 17, 27); PANEL = (24, 30, 46); WHITE = (236, 241, 250); MUTED = (140, 152, 176)
CYAN = (80, 200, 255); AMBER = (255, 190, 60); RED = (255, 92, 92); GREEN = (96, 222, 142)

# layout
CX, CY, CW, CH = 10, 10, 940, 529            # circuit video
TX, TY = 966, 10                              # terminal video
TCW, TCH = 660, 672                           # terminal crop (source px)
TSC = 1.40                                    # terminal zoom
TW, TH = int(TCW * TSC), int(TCH * TSC)       # 924 x 940

def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw: cur = t
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def chip(d, x, y, label, value, color, w=None):
    f1, f2 = F(17), F(26, True)
    w = w or int(max(d.textlength(label, font=f1), d.textlength(value, font=f2)) + 36)
    d.rounded_rectangle((x, y, x + w, y + 62), 12, fill=PANEL, outline=color, width=2)
    d.text((x + 16, y + 6), label, font=f1, fill=MUTED)
    d.text((x + 16, y + 28), value, font=f2, fill=color)
    return x + w + 14

def header(d, runno, phase_txt, speed):
    d.rectangle((0, 0, W, 66), fill=(9, 12, 20))
    d.text((24, 14), TITLE, font=F(32, True), fill=WHITE)
    d.text((24 + d.textlength(TITLE, font=F(32, True)) + 22, 24), "Pico 2  ·  live bench test", font=F(20), fill=MUTED)
    if runno:
        txt = f"RUN {runno} / {len(RUNS)}"
        d.text((W - 24 - d.textlength(txt, font=F(30, True)), 15), txt, font=F(30, True), fill=CYAN)
    # speed badge
    bx = W - 330
    col = AMBER if speed > 1 else GREEN
    label = f"▶▶ {speed}× SPEED" if speed > 1 else "● REAL TIME"
    d.rounded_rectangle((bx - 190, 14, bx - 10, 52), 10, outline=col, width=2)
    d.text((bx - 100 - d.textlength(label, font=F(20, True)) / 2, 22), label, font=F(20, True), fill=col)

def base_canvas(runno, run, phase, speed):
    """Plain layout: black background, captions as simple text under the circuit video."""
    im = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(im)
    y = 566
    f = F(30)
    for ln in wrap(d, run["setup"], f, CW - 10)[:3]:
        d.text((CX + 6, y), ln, font=f, fill=(255, 255, 255)); y += 40
    y += 10
    d.text((CX + 6, y), ("" if "Zx" in run["setup"] else "Zx: " + run["zx"] + "      ") + "Rref: " + run["rref_hw"] + "      command: --ref " + run["flag"], font=F(24), fill=(210, 210, 210))
    y += 40
    if not run["cal"]:
        d.text((CX + 6, y), "(this Rref range is not calibrated)", font=F(22), fill=(170, 170, 170)); y += 34
    y = max(y + 14, 790)
    if phase == "post":
        fr = F(34, True); txt = "Reading: " + run["result"]
        while d.textlength(txt, font=fr) > CW - 10 and fr.size > 22: fr = F(fr.size - 2, True)
        d.text((CX + 6, y), txt, font=fr, fill=(255, 90, 90) if run.get("bad") else (255, 255, 255)); y += 50
        d.text((CX + 6, y), run["detail"], font=F(24), fill=(210, 210, 210)); y += 36
        for ln in wrap(d, run["note"], F(22), CW - 10)[:2]:
            d.text((CX + 6, y), ln, font=F(22), fill=(190, 190, 190)); y += 30
    if speed > 1:
        d.text((CX + 6, 1030), "idle time sped up %d\u00d7" % speed, font=F(20), fill=(150, 150, 150))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)

def card(lines, alpha=1.0):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    for (txt, sz, bold, col, y) in lines:
        f = F(sz, bold)
        d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=col)
    a = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    return (a * alpha).astype(np.uint8)

def intro_frames():
    lines = [
        (COURSE, 30, False, MUTED, 250),
        (TITLE, 84, True, WHITE, 310),
        (SUBTITLE, 34, False, CYAN, 430),
        ("Live bench test: swapping the unknown impedance Zx and the reference resistor Rref", 30, False, WHITE, 560),
        ("Left: breadboard   ·   Right: measurement terminal   ·   idle time sped up %d×" % GAP_SPEED, 26, False, MUTED, 620),
        ("12 measurements: resistors, capacitor, R∥C, R+C", 26, False, AMBER, 700),
    ]
    n = 6 * FPS
    for i in range(n):
        a = min(1, i / 10, (n - i) / 8)
        yield card(lines, a)

def outro_frames():
    im = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((80, 40), "Summary of measurements", font=F(40, True), fill=WHITE)
    cols = [80, 170, 700, 1000, 1380]
    heads = ["#", "Zx (actual)", "Rref", "Tool reading", "Note"]
    y = 120
    for c, h in zip(cols, heads): d.text((c, y), h, font=F(22, True), fill=WHITE)
    y += 38
    for i, r in enumerate(RUNS, 1):
        bad = r.get("bad", False)
        col = RED if bad else WHITE
        d.line((70, y - 4, W - 70, y - 4), fill=(40, 48, 70), width=1)
        short = r["result"].replace("  (INVALID)", "")
        vals = [str(i), r["zx"], r["rref_hw"] + ("  ≠ --ref 10k" if bad else ""), short, "invalid: range mismatch" if bad else ("uncalibrated range" if not r["cal"] else "")]
        for c, v, w in zip(cols, vals, [60, 520, 260, 360, 440]):
            f = F(23, c == cols[3]);
            while d.textlength(v, font=f) > w and f.size > 15: f = F(f.size - 1, c == cols[3])
            d.text((c, y), v, font=f, fill=col)
        y += 62
    d.text((80, 1000), "Capacitor nominal " + CAP_NOMINAL + " (ceramic).  Rref values measured with a multimeter.  Run 3 is a deliberate demonstration of a range mismatch.", font=F(20), fill=MUTED)
    base = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    n = 10 * FPS
    for i in range(n):
        yield base

# ------------------------------------------------------------------ terminal
def cmd_centres(crop):
    """y-centres of green 'python3' command words at the left margin."""
    c = crop[:, :60].astype(int)
    b, g, r = c[..., 0], c[..., 1], c[..., 2]
    rows = ((g > r + 20) & (g > b + 40) & (g > 100)).sum(1)
    ys = [y for y in range(len(rows)) if rows[y] >= 2]
    out, cur = [], []
    for y in ys:
        if cur and y - cur[-1] > 3: out.append(sum(cur) / len(cur)); cur = []
        cur.append(y)
    if cur: out.append(sum(cur) / len(cur))
    return out

CHAR_W = 5.3
def draw_box(img, x0, y0, x1, y1, color, thick=3, fill=0.16):
    ov = img.copy(); cv2.rectangle(ov, (x0, y0), (x1, y1), color, -1)
    cv2.addWeighted(ov, fill, img, 1 - fill, 0, img)
    cv2.rectangle(img, (x0, y0), (x1, y1), color, thick)

def tag(img, x, y, text, color):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(img, (x, y - th - 8), (x + tw + 12, y + 6), color, -1)
    cv2.putText(img, text, (x + 6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (10, 10, 10), 2, cv2.LINE_AA)

def annotate_terminal(img, crop, run, prev, t, bad):
    """img: scaled terminal (TH,TW,3).  Draw flag box + result box following the scroll."""
    cs = cmd_centres(crop)
    if not cs: return
    cy = cs[-1]
    sc = TSC
    if t >= run["tc"] - 1.0:
        flagtxt = "--rref " + run["flag"]
        switched = prev is None or prev["rref_hw"] != run["rref_hw"] or prev["flag"] != run["flag"]
        col = (60, 60, 255) if bad else ((40, 160, 255) if switched else (255, 200, 60))
        x0 = int(146 * sc); x1 = int((146 + CHAR_W * len(flagtxt) + 6) * sc)
        draw_box(img, x0, int((cy - 7) * sc), x1, int((cy + 7) * sc), col, 2, 0.18)
        if switched:
            tag(img, int((12 + CHAR_W * 62) * sc) + 14, int(cy * sc) + 17, "Rref changed" if not bad else "range mismatch!", col)
    if t >= run["tr"]:
        yc = cy + 253 + run.get('dy', 0)
        txt = run["fit"]
        x1 = int((CHAR_W * (len(txt) + 4) + 14) * sc)
        col = (60, 60, 255) if bad else (60, 220, 130)
        draw_box(img, 2, int((yc - 8) * sc), min(x1, TW - 4), int((yc + 8) * sc), col, 2, 0.20)
        tag(img, min(x1, TW - 120) + 6 if x1 < TW - 140 else TW - 130, int((yc - 14) * sc), "RESULT", col)

# ------------------------------------------------------------------ plumbing
def reader(path, a, b, speed, vf, w, h):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", path,
           "-vf", f"setpts=PTS/{speed},fps={FPS},{vf}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8), w * h * 3, (h, w, 3)

def next_frame(proc, nbytes, shape, last):
    buf = proc.stdout.read(nbytes)
    if len(buf) < nbytes: return last
    return np.frombuffer(buf, np.uint8).reshape(shape).copy()

def build_segments():
    segs = []   # (kind, run_index, a_term, b_term, speed)
    prev_end = OFFSET
    for i, r in enumerate(RUNS):
        a, b = r["tc"] - RUN_PRE, r["tr"] + RUN_POST
        if a > prev_end + 0.5: segs.append(("gap", i, prev_end, a, GAP_SPEED))
        segs.append(("run", i, a, b, 1))
        prev_end = b
    return segs

def fmt(t):
    h, m = divmod(int(t), 3600); m, s = divmod(m, 60); ms = int((t % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default="")
    ap.add_argument("--no-cards", action="store_true")
    args = ap.parse_args()
    only = {int(x) for x in args.only.split(",") if x}
    out = args.out or os.path.join(VID, "MEI_Impedance_Meter_Demo.mp4" if not only else "preview_test.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    emit = lambda fr: enc.stdin.write(fr.tobytes())
    srt, tout = [], 0.0
    for kind, i, a, b, sp in build_segments():
        if only and (i + 1) not in only: continue
        run = RUNS[i]; prev = RUNS[i - 1] if i else None
        bad = run.get("bad", False)
        n = int(round((b - a) / sp * FPS))
        pc, pcb, pcs = reader(CKT, a - OFFSET, b - OFFSET + 0.2, sp, f"scale={CW}:{CH}:flags=area", CW, CH)
        pt, ptb, pts = reader(TERM, a, b + 0.2, sp, f"crop={TCW}:{TCH}:0:0", TCW, TCH)
        bases = {ph: base_canvas(i + 1, run, ph, sp) for ph in (("gap",) if kind == "gap" else ("pre", "post"))}
        lc = lt = None
        for k in range(n):
            t = a + k / FPS * sp
            lc = next_frame(pc, pcb, pcs, lc); lt = next_frame(pt, ptb, pts, lt)
            if lc is None or lt is None: break
            ph = "gap" if kind == "gap" else ("post" if t >= run["tr"] else "pre")
            fr = bases[ph].copy()
            fr[CY:CY + CH, CX:CX + CW] = lc
            tz = cv2.resize(lt, (TW, TH), interpolation=cv2.INTER_CUBIC)
            if kind == "run": annotate_terminal(tz, lt, run, prev, t, bad)
            fr[TY:TY + TH, TX:TX + TW] = tz
            emit(fr)
        for p in (pc, pt):
            p.kill(); p.wait()
        dur = n / FPS
        txt = run["setup"] if kind == "gap" else f"Run {i + 1}: {run['zx']} → {run['result']}"
        srt.append((tout, tout + dur, txt)); tout += dur
        print(f"seg {kind:3s} run {i + 1:2d}  term {a:6.1f}-{b:6.1f}  x{sp}  -> {dur:5.1f}s  (total {tout:6.1f}s)", flush=True)
    if not only and not args.no_cards:
        for fr in outro_frames(): emit(fr)
    enc.stdin.close(); enc.wait()
    if not only:
        with open(out.replace(".mp4", ".srt"), "w") as f:
            for j, (s, e, tx) in enumerate(srt, 1):
                f.write(f"{j}\n{fmt(s)} --> {fmt(e)}\n{tx}\n\n")
    print("wrote", out)

if __name__ == "__main__":
    main()
