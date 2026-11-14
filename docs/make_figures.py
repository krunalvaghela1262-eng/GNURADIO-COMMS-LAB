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


def band_db(f, p, lo, hi):
    m = (f >= lo) & (f <= hi)
    return 10 * np.log10(np.mean(10 ** (p[m] / 10)))


def fig_nonlinearity_gif():
    """Lab 4 task 1b: the tanh() amplifier driven harder and harder; one GNU Radio run per drive level."""
    runs = sorted((float(p.stem.split("_")[-1]), p) for p in (RUNS / "sweeps").glob("tanh_amp_*.npz"))
    fs = 4.3e6
    x_in = np.fromfile(ROOT / "data" / "Input.bin", np.float32)
    sig = np.percentile(np.abs(x_in), 99)
    spectra = []
    for a, path in runs:
        y = np.load(path)["qtgui_freq_sink_x_0_p0"]
        f, p = psd((y - y.mean()) / y.std(), fs, 16384)
        spectra.append((a, f / 1e3, p))
    fig = plt.figure(figsize=(12, 5.4), dpi=80, facecolor=BG)
    frames, dur = [], []
    xs = np.linspace(-2, 2, 400)
    for i, (a, f, p) in enumerate(spectra):
        g = a / 0.025
        rel3 = band_db(f, p, 1020, 1560) - band_db(f, p, 340, 520)
        for hold in range(3):
            fig.clf(); fig.set_facecolor(BG)
            fig.text(0.04, 0.92, "Lab 4 · a saturating amplifier spills the signal into new frequency bands", color=FG,
                     fontsize=14, weight="bold")
            ax = fig.add_axes([0.05, 0.13, 0.22, 0.62]); dark(ax, "amplifier: y = tanh(g·x)")
            ax.axvspan(-sig, sig, color=RED, alpha=0.15)
            ax.plot(xs, np.tanh(g * xs) / np.tanh(g * sig), color=RED, lw=2.2)
            ax.plot(xs, xs / sig, color=GREY, lw=1, ls="--")
            ax.set_xlim(-2, 2); ax.set_ylim(-1.6, 1.6)
            ax.set_xlabel("input x", color=MUTED); ax.set_ylabel("output (normalised)", color=MUTED)
            ax.text(0, -1.45, "shaded: range the input signal covers", color=MUTED, ha="center", fontsize=8.5)
            b = fig.add_axes([0.34, 0.13, 0.63, 0.62]); dark(b, "output spectrum (GNU Radio run)")
            for a0, f0, p0 in spectra[:i]:
                b.plot(f0, p0, color="#3a3a3a", lw=0.8)
            b.plot(f, p, color=RED, lw=1.3)
            b.set_xlim(0, 2150); b.set_ylim(-195, -20)
            for lo, hi, txt in ((340, 520, "signal"), (1020, 1560, "3rd harmonic"), (1700, 2150, "5th harmonic")):
                b.axvspan(lo, hi, color="white", alpha=0.05)
                b.text((lo + hi) / 2, -28, txt, color=MUTED, ha="center", va="top", fontsize=9.5)
            b.set_xlabel("frequency (kHz)", color=MUTED); b.set_ylabel("power (dB/Hz, normalised)", color=MUTED)
            fig.text(0.34, 0.83, f"drive slider amp = {a:g}", color=FG, fontsize=13, family="monospace")
            fig.text(0.6, 0.83, f"3rd harmonic: {rel3:+.0f} dB vs the signal",
                     color=RED if rel3 > -40 else FG, fontsize=13, family="monospace")
            grab(fig, frames); dur.append(1800 if (hold == 2 and i == len(spectra) - 1) else 260)
    frames[0].save(OUT / "nonlinearity.gif", save_all=True, append_images=frames[1:], duration=dur, loop=0)
    plt.close(fig)


def rrc(t, a):
    """Root-raised-cosine impulse response, t in symbol periods."""
    t = np.asarray(t, float)
    h = np.empty_like(t)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-9:
            h[i] = 1 - a + 4 * a / np.pi
        elif a > 0 and abs(abs(ti) - 1 / (4 * a)) < 1e-9:
            h[i] = a / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * a)) + (1 - 2 / np.pi) * np.cos(np.pi / (4 * a)))
        else:
            h[i] = (np.sin(np.pi * ti * (1 - a)) + 4 * a * ti * np.cos(np.pi * ti * (1 + a))) / (np.pi * ti * (1 - (4 * a * ti) ** 2))
    return h


def fig_rolloff_gif():
    """Roll-off α slider: the pulse shape and the measured spectrum (one GNU Radio run per α, 10 k symbols/s)."""
    runs = sorted((float(p.stem.split("_")[-1]), p) for p in (RUNS / "sweeps").glob("bpsk_alpha_*.npz"))
    sps = 32
    t = np.arange(-6 * sps, 6 * sps + 1) / sps
    fig = plt.figure(figsize=(12, 5.4), dpi=80, facecolor=BG)
    frames, dur, prev = [], [], []
    for i, (a, path) in enumerate(runs):
        z = np.load(path)
        f, p = psd(z["qtgui_freq_sink_x_0_p0"], 80e3, 8192)
        f = f / 1e3; p = p - p[(f > 0.3) & (f < 3)].mean()
        h = rrc(t, max(a, 1e-3)); rc = np.convolve(h, h)[::1] / sps
        rc = rc[len(rc) // 2 - 6 * sps:len(rc) // 2 + 6 * sps + 1]; rc /= rc.max()
        bw = (1 + a) * 5
        for hold in range(2):
            fig.clf(); fig.set_facecolor(BG)
            fig.text(0.04, 0.92, "Labs 5 & 6 · root-raised-cosine pulse shaping: sliding the roll-off α", color=FG,
                     fontsize=14, weight="bold")
            ax = fig.add_axes([0.05, 0.13, 0.36, 0.62]); dark(ax, "pulse after TX + matched RX filter (raised cosine)")
            ax.axhline(0, color="#404040", lw=0.8)
            ax.plot(t, rc, color=RED, lw=2.2)
            ks = np.arange(-6, 7); ks = ks[ks != 0]
            ax.plot(ks, np.zeros_like(ks), "o", color=WHITE, ms=5)
            ax.set_xlim(-6, 6); ax.set_ylim(-0.3, 1.1)
            ax.set_xlabel("time (symbol periods)", color=MUTED)
            ax.text(0, -0.24, "white dots: zero at every other symbol instant → no ISI", color=MUTED, ha="center", fontsize=8.5)
            b = fig.add_axes([0.48, 0.13, 0.49, 0.62]); dark(b, "spectrum of the shaped signal (GNU Radio run)")
            for f0, p0 in prev[-3:]:
                b.plot(f0, p0, color="#3a3a3a", lw=0.9)
            b.axvspan(0, bw, color=RED, alpha=0.08)
            b.plot(f, p, color=RED, lw=1.3)
            b.axvline(bw, color=WHITE, lw=1.2, ls="--")
            b.text(bw + 0.15, 2, f"(1+α)·Rs/2 = {bw:.1f} kHz", color=WHITE, fontsize=10)
            b.set_xlim(0, 14); b.set_ylim(-60, 8)
            b.set_xlabel("frequency (kHz)", color=MUTED); b.set_ylabel("power (dB)", color=MUTED)
            fig.text(0.48, 0.83, f"α = {a:.2f}", color=FG, fontsize=15, weight="bold", family="monospace")
            fig.text(0.66, 0.83, f"bandwidth {bw:.1f} kHz  ·  10 k symbols/s", color=MUTED, fontsize=12)
            grab(fig, frames); dur.append(1800 if (hold == 1 and i == len(runs) - 1) else 350)
        prev.append((f, p))
    frames[0].save(OUT / "rolloff.gif", save_all=True, append_images=frames[1:], duration=dur, loop=0)
    plt.close(fig)


if __name__ == "__main__":
    fig_fm()
    fig_nonlinearity_gif()
    fig_eye_gif()
    fig_rolloff_gif()
    fig_equalizer_gif()
    fig_costas_gif()
    banner()
    for f in sorted(OUT.iterdir()):
        print(f"{f.name:24s} {f.stat().st_size / 1e6:6.2f} MB")
