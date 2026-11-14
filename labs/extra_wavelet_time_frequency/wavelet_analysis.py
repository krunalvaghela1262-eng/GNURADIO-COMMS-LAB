"""Extra task, part 2: spectrogram vs Morlet scalogram of the message received over the GNU Radio FM link.

    python labs/extra_wavelet_time_frequency/wavelet_analysis.py fm_wavelet.npz docs/figures

Needs numpy, scipy, matplotlib, pillow and PyWavelets (pip install PyWavelets).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pywt
from PIL import Image
from scipy.signal import spectrogram

BG, FG, RED, GRID, MUTED = "#000000", "#ffffff", "#ff3b3b", "#262626", "#a3a3a3"
EVENTS = ((0.35, 2500, "chirp 300 Hz → 6 kHz"), (0.85, 1000, "1 kHz burst"), (0.85, 8000, "8 kHz burst"),
          (1.05, 3000, "click"))


def scalogram(x, fs, fmin=150, fmax=12_000, n=150):
    wav = "cmor1.5-1.0"
    freqs = np.geomspace(fmin, fmax, n)
    scales = pywt.central_frequency(wav) * fs / freqs
    coef, f = pywt.cwt(x, scales, wav, sampling_period=1 / fs, method="fft")
    p = np.abs(coef) ** 2
    return f, 10 * np.log10(p / p.max() + 1e-6)


def style(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=9)
    for s in ax.spines.values():
        s.set_color("#404040")


def main(npz, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    z = np.load(npz)
    fs, rx = int(z["fs"]), z["received"].astype(float)
    t = np.arange(len(rx)) / fs
    fw, P = scalogram(rx, fs)
    fsg, tsg, S = spectrogram(rx, fs, nperseg=1024, noverlap=896)
    S = 10 * np.log10(S / S.max() + 1e-6)

    # ---------- static comparison
    fig, axs = plt.subplots(3, 1, figsize=(12, 9), dpi=110, facecolor=BG, sharex=True,
                            gridspec_kw=dict(height_ratios=[0.6, 1, 1]))
    style(axs[0]); axs[0].plot(t, rx, color=RED, lw=0.6); axs[0].set_yticks([])
    axs[0].set_title("received message after the FM link (GNU Radio)", color=FG, loc="left", fontsize=11.5)
    style(axs[1])
    axs[1].pcolormesh(tsg, fsg / 1e3, S, cmap="inferno", vmin=-60, vmax=0, shading="auto")
    axs[1].set_ylim(0.15, 12); axs[1].set_yscale("log")
    axs[1].set_title("spectrogram (STFT, 1024-sample window): one resolution for every frequency", color=FG,
                     loc="left", fontsize=11.5)
    style(axs[2])
    axs[2].pcolormesh(t[::8], fw / 1e3, P[:, ::8], cmap="inferno", vmin=-50, vmax=0, shading="auto")
    axs[2].set_yscale("log"); axs[2].set_ylim(0.15, 12)
    axs[2].set_title("scalogram (Morlet wavelet): sharp in time at high frequency, sharp in frequency at low",
                     color=FG, loc="left", fontsize=11.5)
    for ax in axs[1:]:
        ax.set_ylabel("frequency (kHz)", color=MUTED)
        ax.set_yticks([0.25, 0.5, 1, 2, 4, 8], ["0.25", "0.5", "1", "2", "4", "8"])
    for tt, ff, lab in EVENTS:
        axs[2].annotate(lab, (tt, ff / 1e3), xytext=(tt + 0.02, ff / 1e3 * 1.45), color=FG, fontsize=9,
                        arrowprops=dict(arrowstyle="-", color=FG, lw=0.8))
    axs[2].set_xlabel("time (s)", color=MUTED)
    fig.tight_layout(); fig.savefig(out / "wavelet_vs_stft.png", facecolor=BG); plt.close(fig)

    # ---------- animation: the scalogram is revealed as a cursor sweeps through the message
    fig = plt.figure(figsize=(12, 6), dpi=80, facecolor=BG)
    a = fig.add_axes([0.07, 0.72, 0.9, 0.17]); b = fig.add_axes([0.07, 0.1, 0.9, 0.57])
    frames = []
    T = t[-1]
    stops = np.linspace(0.02, T, 48)
    for k, tc in enumerate(list(stops) + [T] * 10):
        a.clear(); b.clear(); style(a); style(b)
        n = int(tc * fs)
        a.plot(t[:n], rx[:n], color=RED, lw=0.6); a.set_xlim(0, T); a.set_ylim(-1.1, 1.1); a.set_yticks([])
        a.axvline(tc, color=FG, lw=1)
        m = P[:, ::8].copy(); m[:, int(n / 8):] = -60
        b.pcolormesh(t[::8], fw / 1e3, m, cmap="inferno", vmin=-50, vmax=0, shading="auto")
        b.set_yscale("log"); b.set_ylim(0.15, 12); b.set_xlim(0, T)
        b.set_yticks([0.25, 0.5, 1, 2, 4, 8], ["0.25", "0.5", "1", "2", "4", "8"])
        b.axvline(tc, color=FG, lw=1)
        b.set_ylabel("frequency (kHz)", color=MUTED); b.set_xlabel("time (s)", color=MUTED)
        for tt, ff, lab in EVENTS:
            if tc > tt + 0.03:
                b.text(tt + 0.02, ff / 1e3 * 1.35, lab, color=FG, fontsize=10)
        fig.texts.clear()
        fig.text(0.07, 0.93, "Wavelet scalogram of a message received over a GNU Radio FM link", color=FG,
                 fontsize=14, weight="bold")
        fig.canvas.draw()
        frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]).quantize(colors=255))
    frames[0].save(out / "wavelet_scalogram.gif", save_all=True, append_images=frames[1:],
                   duration=[90] * len(stops) + [300] * 9 + [2500], loop=0)
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
