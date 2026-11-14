"""Turn the data captured from the real GNU Radio runs into the README figures and animations.

    # 1. run the flowgraphs (GNU Radio 3.10 environment), e.g.
    python tools/run_headless.py labs/lab6_qpsk_matched_filter/task4_qpsk_decoder.grc runs/lab6_task4.npz
    # 2. draw everything (any Python with numpy / scipy / matplotlib / pillow)
    COMMS_RUNS=runs python docs/make_figures.py

Every signal plotted here came out of a GNU Radio flowgraph from labs/ (or tools/costas_lock_demo.py);
see docs/how_figures_were_made.md for which run produced which figure.
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.signal import welch

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
RUNS = Path(os.environ.get("COMMS_RUNS", ROOT / "runs"))
REF = np.frombuffer((ROOT / "data" / "Original_Text.txt").read_bytes(), np.uint8)
# black / red / white, like a GNU Radio QT GUI scope
BG, FG, GRID, MUTED = "#000000", "#ffffff", "#262626", "#a3a3a3"
RED, WHITE, GREY, PINK = "#ff3b3b", "#f5f5f5", "#8a8a8a", "#ff9a9a"
C1, C2, C3, C4 = RED, WHITE, GREY, RED


def load(name):
    return np.load(RUNS / f"{name}.npz")


def dark(ax, title=None):
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=9)
    for s in ax.spines.values():
        s.set_color("#404040")
    ax.grid(color=GRID, lw=0.7)
    if title:
        ax.set_title(title, color=FG, fontsize=11.5, loc="left")


def grab(fig, frames):
    fig.canvas.draw()
    frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]).quantize(colors=255))


def bit_errors(rx_bytes):
    """Best alignment of the received bytes against one copy of the original text -> (bit errors, offset)."""
    rx = np.frombuffer(rx_bytes, np.uint8)
    L = len(REF)
    if len(rx) < L:
        return None, 0
    best = (10 ** 9, 0)
    for off in range(0, min(len(rx) - L, 2 * L)):
        e = int(np.unpackbits(rx[off:off + L] ^ REF).sum())
        if e < best[0]:
            best = (e, off)
    return best


# ====================================================================================== text links
LINKS = [  # (run name, label, what it is)
    ("lab5_bpsk_pulse_shaping__Q3", "Lab 5 · BPSK", "RRC pulse shaping, 100 kHz carrier"),
    ("lab6_qpsk_matched_filter__q1_bpsk_with_noise", "Lab 6 · BPSK + noise", "noise amplitude 0.1"),
    ("lab6_qpsk_matched_filter__task2_matched_filter", "Lab 6 · BPSK, matched filter", "RRC matched filter at the receiver"),
    ("lab6_qpsk_matched_filter__task4_qpsk_decoder", "Lab 6 · QPSK", "2 bits/symbol, I/Q demodulation"),
    ("lab7_multipath_equalization__task1a", "Lab 7 · 8-PSK", "3 bits/symbol, clean channel"),
    ("lab7_multipath_equalization__task1b", "Lab 7 · 8-PSK + multipath", "echo of 0.5 one symbol later, no equaliser"),
    ("lab7_multipath_equalization__task1_e", "Lab 7 · 8-PSK + multipath + equaliser", "4-tap inverse of H(z)"),
]


def fig_text_links(draw=True):
    rows = []
    for run, lab, what in LINKS:
        p = RUNS / f"{run}.received.txt"
        e, off = bit_errors(p.read_bytes())
        rows.append((lab, what, e, off, p.read_bytes()))
        print(f"{lab:40s} bit errors {e}/{8 * len(REF)}")
    if not draw:
        return rows
    fig, ax = plt.subplots(figsize=(11, 4.4), dpi=110, facecolor=BG)
    dark(ax)
    y = np.arange(len(rows))[::-1]
    ber = [max(r[2], 0) / (8 * len(REF)) for r in rows]
    cols = [C4 if b == 0 else (C3 if b > 0.2 else C2) for b in ber]
    ax.barh(y, [max(b, 2e-5) for b in ber], color=cols, height=0.6)
    ax.set_xscale("log"); ax.set_xlim(1e-5, 1)
    for yy, b, r in zip(y, ber, rows):
        ax.text(max(b, 2e-5) * 1.3, yy, "0 errors ✓" if b == 0 else f"{b:.1%} of bits wrong", va="center",
                color=FG, fontsize=10, weight="bold")
    ax.set_yticks(y, [f"{r[0]}\n{r[1]}" for r in rows], color=FG, fontsize=9)
    ax.set_xlabel(f"bit error rate after sending the {len(REF):,}-byte text through the flowgraph", color=MUTED)
    ax.set_title("Text in → GNU Radio link → text out (real runs of the lab flowgraphs)", color=FG, loc="left",
                 fontsize=12.5, weight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "text_links.png", facecolor=BG); plt.close(fig)
    return rows


def fig_multipath_text(rows):
    """What the received text actually looks like with and without the equaliser."""
    pick = {r[0]: r for r in rows}
    bad = pick["Lab 7 · 8-PSK + multipath"]
    good = pick["Lab 7 · 8-PSK + multipath + equaliser"]
    start = REF.tobytes().find(b"The scientific")

    def snippet(r, n=150):
        b = np.frombuffer(r[4], np.uint8)[r[3] + start:r[3] + start + n]
        return "".join(chr(c) if 32 <= c < 127 else "·" for c in b)
    fig = plt.figure(figsize=(11, 2.9), dpi=110, facecolor=BG)
    for i, (lab, r, col) in enumerate((("without equaliser", bad, GREY), ("with the 4-tap equaliser", good, RED))):
        txt = snippet(r)
        lines = [txt[k:k + 75] for k in range(0, len(txt), 75)]
        fig.text(0.02, 0.86 - i * 0.45, f"8-PSK over a two-path channel, {lab}:", color=col, fontsize=11, weight="bold")
        for j, ln in enumerate(lines):
            fig.text(0.02, 0.73 - i * 0.45 - j * 0.11, ln, color=FG, fontsize=10.5, family="monospace")
    fig.savefig(OUT / "multipath_text.png", facecolor=BG); plt.close(fig)


# ====================================================================================== analog labs
def psd(x, fs, nper=4096):
    f, p = welch(x, fs, nperseg=nper, return_onesided=not np.iscomplexobj(x))
    if np.iscomplexobj(x):
        f, p = np.fft.fftshift(f), np.fft.fftshift(p)
    return f, 10 * np.log10(p + 1e-20)


def fig_fm():
    z = load("lab3_fm__task2_fm_demodulation")
    fm, demod, msg = z["qtgui_sink_x_1_p0"], z["qtgui_sink_x_0_p0"], z["qtgui_sink_x_0_1_p0"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.2), dpi=110, facecolor=BG, gridspec_kw=dict(width_ratios=[1.2, 1]))
    f, p = psd(fm[: 2 ** 20], 960e3, 8192)
    a.plot(f / 1e3, p - p.max(), color=C1, lw=1)
    a.set_xlim(-50, 300); a.set_ylim(-80, 3)
    a.axvspan(100 - 97, 100 + 97, color=C2, alpha=0.08)
    a.text(100, -6, "Carson bandwidth ≈ 2(Δf + f_m) ≈ 194 kHz", color=C2, ha="center", fontsize=9.5)
    dark(a, "FM signal spectrum: 100 kHz carrier, Δf = 75 kHz, tones at 1.1 + 11 kHz")
    a.set_xlabel("frequency (kHz)", color=MUTED); a.set_ylabel("power (dB)", color=MUTED)
    n0 = 4000
    t = np.arange(150) / 48e3 * 1e3
    m = msg[n0:n0 + 150]; d = demod[n0:n0 + 150]
    lag = np.argmax(np.correlate(demod[n0:n0 + 2000] - demod[n0:n0 + 2000].mean(), msg[n0:n0 + 2000], "full")) - 1999
    d = demod[n0 + lag:n0 + lag + 150]
    b.plot(t, (m - m.mean()) / m.std(), color=MUTED, lw=2.5, label="message (two tones)")
    b.plot(t, (d - d.mean()) / d.std(), color=RED, lw=1.3, label="demodulated (delay–conjugate–arg)")
    dark(b, "Quadrature FM demodulator output"); b.set_xlabel("time (ms)", color=MUTED); b.set_yticks([])
    b.legend(facecolor=BG, edgecolor="#404040", labelcolor=FG, fontsize=9, loc="upper right")
    fig.tight_layout(); fig.savefig(OUT / "fm.png", facecolor=BG); plt.close(fig)


def fig_nonlinearity():
    """Lab 4 task 1b: an amplifier modelled as tanh(), driven harder and harder (real GNU Radio runs)."""
    fs = 4.3e6
    fig, ax = plt.subplots(figsize=(12, 4.3), dpi=110, facecolor=BG)
    for a, lab, col in ((0.0025, "gentle drive: still linear", GREY), (0.025, "moderate drive", WHITE),
                        (0.075, "hard drive: saturating", RED)):
        y = np.load(RUNS / "sweeps" / f"tanh_amp_{a}.npz")["qtgui_freq_sink_x_0_p0"]
        f, p = psd((y - y.mean()) / y.std(), fs, 16384)
        ax.plot(f / 1e3, p, color=col, lw=1.1, label=f"slider amp = {a}  ({lab})")
    top = ax.get_ylim()[1]
    for lo, hi, txt in ((340, 520, "the signal\n(340–520 kHz)"), (1020, 1560, "3rd harmonic\nband"),
                        (1700, 2150, "5th")):
        ax.axvspan(lo, hi, color="white", alpha=0.04)
        ax.text((lo + hi) / 2, top - 8, txt, color=MUTED, ha="center", va="top", fontsize=9)
    ax.set_xlim(0, 2150)
    dark(ax, "Lab 4 · a saturating amplifier (tanh) spills the signal into new frequency bands")
    ax.set_xlabel("frequency (kHz)", color=MUTED); ax.set_ylabel("power (dB/Hz)", color=MUTED)
    ax.legend(facecolor=BG, edgecolor="#404040", labelcolor=FG, fontsize=9, loc="center right")
    fig.tight_layout(); fig.savefig(OUT / "nonlinearity.png", facecolor=BG); plt.close(fig)


# ====================================================================================== digital labs
def eye_traces(x, sps=8, span=2, n=300):
    """Cut a matched-filter output into 2-symbol traces, aligned so the eye opening sits in the middle."""
    x = np.asarray(x, float)
    x = x[len(x) // 4:]
    best = max(range(sps), key=lambda o: np.mean(np.abs(x[o::sps][:2000])) / (np.std(np.abs(x[o::sps][:2000])) + 1e-9))
    start = best                       # trace starts at a sampling instant, so the eye opens at t = 1
    ks = np.random.default_rng(0).choice((len(x) - start) // sps - span - 1, n, replace=False)
    tr = [x[start + k * sps:start + k * sps + span * sps + 1] for k in ks]
    return np.array([t for t in tr if len(t) == span * sps + 1])


def fig_eyes():
    noises = (0, 0.2, 0.4, 0.7, 1.0)
    fig, axs = plt.subplots(1, len(noises), figsize=(15, 3.6), dpi=110, facecolor=BG, sharey=True)
    for ax, n in zip(axs, noises):
        z = np.load(RUNS / "sweeps" / f"qpsk_noise_{n}.npz")
        key = [k for k in z.files if k.startswith("qtgui_eye_sink")][0]
        tr = eye_traces(z[key])
        sc = np.percentile(np.abs(tr), 99)
        for t in tr:
            ax.plot(np.arange(len(t)) / 8, t / sc, color=C1, lw=0.6, alpha=0.18)
        dark(ax, f"noise amplitude {n}"); ax.set_xlabel("time (symbols)", color=MUTED)
    axs[0].set_ylabel("matched-filter output (I)", color=MUTED)
    fig.suptitle("Lab 6 · QPSK eye diagrams from the receiver's matched filter: the eye closes as noise grows",
                 color=FG, x=0.01, ha="left", fontsize=12.5, weight="bold")
    fig.tight_layout(); fig.savefig(OUT / "eye_vs_noise.png", facecolor=BG); plt.close(fig)


def fig_eye_gif():
    """Eye diagram building up trace by trace at each noise level (black / red / white, like the GNU Radio eye sink)."""
    runs = sorted((float(p.stem.split("_")[-1]), p) for p in (RUNS / "sweeps").glob("qpsk_noise_*.npz"))
    fig = plt.figure(figsize=(9.6, 5.4), dpi=80, facecolor=BG)
    frames, dur = [], []
    for n, path in runs:
        z = np.load(path)
        tr = eye_traces(z[[k for k in z.files if k.startswith("qtgui_eye_sink")][0]], n=240)
        tr = tr / np.percentile(np.abs(tr), 99)
        mid = tr[:, 8]
        opening = max(0.0, (np.percentile(mid[mid > 0], 5) - np.percentile(mid[mid < 0], 95)) / 2) if (mid > 0).any() and (mid < 0).any() else 0
        for k in (60, 120, 180, 240):
            fig.clf(); fig.set_facecolor(BG)
            ax = fig.add_axes([0.08, 0.12, 0.6, 0.72]); dark(ax)
            for t in tr[:k]:
                ax.plot(np.arange(len(t)) / 8, t, color=RED, lw=0.8, alpha=0.22)
            ax.set_xlim(0, 2); ax.set_ylim(-1.5, 1.5)
            ax.set_xlabel("time (symbols)", color=MUTED); ax.set_ylabel("matched-filter output (I)", color=MUTED)
            fig.text(0.08, 0.91, "Lab 6 · QPSK eye diagram (GNU Radio receiver, matched-filter output)", color=FG,
                     fontsize=13, weight="bold")
            fig.text(0.72, 0.72, "noise amplitude", color=MUTED, fontsize=11)
            fig.text(0.72, 0.62, f"{n:.1f}", color=FG, fontsize=30, weight="bold")
            fig.text(0.72, 0.5, "eye opening", color=MUTED, fontsize=11)
            fig.text(0.72, 0.4, f"{100 * opening:.0f} %", color=RED if opening < 0.25 else FG, fontsize=30, weight="bold")
            fig.text(0.72, 0.18, "wide open eye → the receiver\ncan tell 0 from 1 at the\nsampling instant (t = 1)",
                     color=MUTED, fontsize=9.5)
            grab(fig, frames); dur.append(1100 if k == 240 else 120)
    frames[0].save(OUT / "eye_diagram.gif", save_all=True, append_images=frames[1:], duration=dur, loop=0)
    plt.close(fig)


def fig_rolloff():
    fig, ax = plt.subplots(figsize=(10, 4), dpi=110, facecolor=BG)
    for a, col in zip((0.1, 0.35, 0.6, 1.0), (GREY, WHITE, PINK, RED)):
        z = np.load(RUNS / "sweeps" / f"bpsk_alpha_{a}.npz")
        key = "qtgui_freq_sink_x_0_p0" if "qtgui_freq_sink_x_0_p0" in z.files else [k for k in z.files if "freq" in k][0]
        f, p = psd(z[key], 80e3, 4096)
        ax.plot(f / 1e3, p - p.max(), color=col, lw=1.5, label=f"roll-off α = {a}  →  bandwidth ≈ {(1 + a) * 5:.1f} kHz")
    ax.set_xlim(0, 14); ax.set_ylim(-70, 3)
    dark(ax, "Lab 5/6 · root-raised-cosine pulse shaping: α trades bandwidth for easier timing (10 k symbols/s)")
    ax.set_xlabel("frequency (kHz)", color=MUTED); ax.set_ylabel("power (dB)", color=MUTED)
    ax.legend(facecolor=BG, edgecolor="#404040", labelcolor=FG, fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "rolloff.png", facecolor=BG); plt.close(fig)


EQ_SCALES = (0, 0.25, 0.5, 0.75, 1)


def eq_points(s):
    z = np.load(RUNS / "sweeps" / f"eq_{s}.npz")
    pts = z["qtgui_const_sink_x_0_0_0_0_p0"]          # receiver output, one point per symbol
    return pts[len(pts) // 3:][:2400]


def fig_equalizer_gif():
    fig = plt.figure(figsize=(9.6, 5.4), dpi=80, facecolor=BG)
    frames, dur = [], []
    taps = np.array([-0.5, 0.25, -0.125, 0.0625])
    for s in EQ_SCALES:
        pts = eq_points(s)
        lim = np.percentile(np.abs(pts), 99.5) * 1.15
        for k in range(1, 6):
            fig.clf(); fig.set_facecolor(BG)
            ax = fig.add_axes([0.05, 0.08, 0.5, 0.78]); dark(ax)
            ax.plot(pts[: k * 480].real, pts[: k * 480].imag, ".", color=GREY if s < 1 else RED, ms=3.5, alpha=0.6)
            ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
            fig.text(0.03, 0.93, "Lab 7 · 8-PSK through a two-path channel  H(z) = 1 + 0.5 z⁻¹", color=FG, fontsize=13, weight="bold")
            fig.text(0.6, 0.78, "equaliser taps", color=MUTED, fontsize=11)
            for i, t in enumerate(taps * s):
                fig.text(0.6, 0.71 - i * 0.065, f"b{i + 1} = {t:+.4f}", color=FG, fontsize=12, family="monospace")
            fig.text(0.6, 0.38, f"{int(s * 100)} % of the exact inverse\nE(z) = 1/H(z) = 1 − 0.5z⁻¹ + 0.25z⁻² − …",
                     color=RED if s == 1 else WHITE, fontsize=11)
            fig.text(0.6, 0.2, "points recorded from the flowgraph's\nconstellation sink in real GNU Radio runs",
                     color=MUTED, fontsize=9.5)
            grab(fig, frames); dur.append(1600 if (k == 5 and s in (0, 1)) else 220)
    frames[0].save(OUT / "equalizer.gif", save_all=True, append_images=frames[1:], duration=dur, loop=0)
    plt.close(fig)


def fig_costas_gif():
    z = np.load(RUNS / "costas.npz")
    rx, lk, fr = z["rx"], z["locked"], z["freq"]
    true = float(z["true_freq"])
    fig = plt.figure(figsize=(12, 4.6), dpi=80, facecolor=BG)
    frames = []
    W = 150
    for k in range(0, 3600, 60):
        fig.clf(); fig.set_facecolor(BG)
        a = fig.add_axes([0.03, 0.12, 0.25, 0.68]); b = fig.add_axes([0.32, 0.12, 0.25, 0.68]); c = fig.add_axes([0.64, 0.14, 0.34, 0.66])
        for ax, pts, ttl, col in ((a, rx, "received (offset spins it)", GREY), (b, lk, "after the Costas loop", RED)):
            dark(ax, ttl); w = pts[k:k + W]
            ax.plot(w.real, w.imag, ".", color=col, ms=4, alpha=0.8)
            ax.set_xlim(-1.6, 1.6); ax.set_ylim(-1.6, 1.6); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        dark(c, "loop's frequency estimate")
        c.plot(fr[: k + W], color=RED, lw=1.4); c.axhline(true, color=WHITE, ls="--", lw=1.1)
        c.text(3500, true * 1.08, "true offset", color=WHITE, ha="right", fontsize=9)
        c.set_xlim(0, 3600); c.set_ylim(min(-0.005, fr[:3600].min()), true * 1.6)
        c.set_xlabel("symbols", color=MUTED); c.set_ylabel("rad / symbol", color=MUTED)
        fig.text(0.03, 0.9, "Lab 8 · Costas loop locking a QPSK signal with a carrier frequency offset (GNU Radio)",
                 color=FG, fontsize=13, weight="bold")
        grab(fig, frames)
    frames[0].save(OUT / "costas_lock.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)
    plt.close(fig)


def banner():
    z = np.load(RUNS / "costas.npz"); lk = z["locked"][3000:4500]
    fig = plt.figure(figsize=(16, 4), dpi=100, facecolor=BG)
    t = fig.add_axes([0, 0, 0.55, 1]); t.axis("off")
    t.text(0.06, 0.6, "Communications Lab", color="white", fontsize=36, weight="bold", transform=t.transAxes)
    t.text(0.06, 0.43, "FM · BPSK · QPSK · 8-PSK · multipath · equalisation · carrier sync · wavelets", color=FG, fontsize=14,
           transform=t.transAxes)
    t.text(0.06, 0.3, "GNU Radio flowgraphs, run for real · EE340 · IIT Bombay", color=MUTED, fontsize=13,
           transform=t.transAxes)
    a = fig.add_axes([0.57, 0.08, 0.2, 0.84]); a.set_facecolor(BG); a.axis("off")
    a.plot(lk.real, lk.imag, ".", color=RED, ms=3, alpha=0.6); a.set_aspect("equal")
    b = fig.add_axes([0.79, 0.12, 0.19, 0.76]); b.set_facecolor(BG); b.axis("off")
    zq = np.load(RUNS / "sweeps" / "qpsk_noise_0.2.npz")
    tr = eye_traces(zq[[k for k in zq.files if k.startswith("qtgui_eye_sink")][0]], n=160)
    for tt in tr:
        b.plot(tt, color=RED, lw=0.7, alpha=0.25)
    fig.savefig(OUT / "banner.png", facecolor=BG); plt.close(fig)


if __name__ == "__main__":
    rows = fig_text_links(draw=False)
    fig_multipath_text(rows)
    fig_fm()
    fig_nonlinearity()
    fig_eye_gif()
    fig_rolloff()
    fig_equalizer_gif()
    fig_costas_gif()
    banner()
    for f in sorted(OUT.iterdir()):
        print(f"{f.name:24s} {f.stat().st_size / 1e6:6.2f} MB")
