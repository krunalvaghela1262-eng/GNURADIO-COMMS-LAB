# Extra task · Time–frequency analysis of an FM link with the wavelet transform

*An additional exercise in the style of the lab sheets, building on Lab 3 (FM). Not part of the official EE340 lab list.*

## Problem statement

A Fourier spectrum tells you **which** frequencies are present, but not **when**. Real messages change over time: a voice glides in pitch, a modem sends short bursts, and interference shows up as clicks. In this task you transmit such a message over an FM link and look at it in time and frequency at once.

1. **Message (48 kHz sampling), 1.2 s long**, built from:
   - a linear **chirp** sweeping from 300 Hz to 6 kHz between 0.05 s and 0.65 s
   - a **1 kHz tone burst** (0.75–0.95 s) and an **8 kHz tone burst** (0.80–0.90 s), overlapping in time
   - a sharp **click** (a 0.3 ms pulse) at 1.05 s
2. **Transmitter:** resample the message to 480 kHz and frequency-modulate it with a deviation of 15 kHz (`Frequency Mod` block).
3. **Channel:** add white Gaussian noise (`Channel Model`, noise voltage 0.05).
4. **Receiver:** demodulate with the `Quadrature Demod` block (gain = fs / (2π·Δf)), low-pass filter and decimate back to 48 kHz.
5. **Analysis:** compare the received message using
   - a **spectrogram** (short-time Fourier transform, fixed 1024-sample window)
   - a **scalogram** (continuous wavelet transform with a complex Morlet wavelet)

   Answer:
   - Which representation shows the click as a sharp vertical line, and why?
   - Which shows the 1 kHz burst as a thin horizontal band?
   - How does the wavelet's time and frequency resolution change with frequency?

## Solution

- [`fm_wavelet_flowgraph.py`](fm_wavelet_flowgraph.py) is the GNU Radio flowgraph for steps 1–4. It saves the transmitted and received message to `.npz`.
- [`wavelet_analysis.py`](wavelet_analysis.py) computes the spectrogram and the Morlet scalogram (PyWavelets) and draws the figure and animation shown in the main README.

**Answer.** The spectrogram uses one window length for every frequency, so it has to trade off: a long window blurs the click across about 20 ms, and a short window would smear the tones in frequency. The wavelet transform uses **short wavelets at high frequency and long ones at low frequency**. So the click appears as a sharp vertical line, the 1 kHz burst as a thin band, and the chirp as a clean rising curve: constant *relative* resolution, Δf / f ≈ constant.
