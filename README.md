<p align="center">
  <img src="docs/figures/banner.png" alt="Communications Lab: GNU Radio flowgraphs run for real" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IIT%20Bombay-EE340%20Communications%20Lab-1f5fbf" alt="EE340">
  <img src="https://img.shields.io/badge/GNU%20Radio-3.10-d32f2f" alt="GNU Radio 3.10">
  <img src="https://img.shields.io/badge/flowgraphs-26-111111" alt="26 flowgraphs">
  <img src="https://img.shields.io/badge/modulation-FM%20%7C%20BPSK%20%7C%20QPSK%20%7C%208--PSK-b91c1c" alt="modulation">
  <img src="https://img.shields.io/badge/text%20links-0%20bit%20errors-22c55e" alt="0 bit errors">
</p>

> **TL;DR.** My **26 GNU Radio flowgraphs** from IIT Bombay's communications lab (EE340). They take a signal from a single sine wave to a complete digital radio link:
> - FM, and what non-linear amplifiers do to signals
> - pulse shaping, matched filtering, BPSK, QPSK and 8-PSK
> - a multipath channel with the equaliser that undoes it
> - carrier synchronisation with a Costas loop
> - a wavelet time–frequency analysis of an FM link
>
> **Every plot here comes from actually running the flowgraphs in GNU Radio 3.10**. A paragraph of text goes through each digital link and comes back with **zero bit errors**.

---

## Text in → radio → text out

Each digital lab sends the same 1,421-character paragraph through its flowgraph: bits → symbols → pulse shaping → 100 kHz carrier → noise → receiver → bits. The received file is then compared with the original, bit by bit:

| Lab | Link | Bits per symbol | Bit errors (of 11,368) |
|---|---|:---:|:---:|
| 5 | BPSK, root-raised-cosine pulse shaping, 100 kHz carrier | 1 | **0** ✅ |
| 6 | BPSK + Gaussian noise | 1 | **0** ✅ |
| 6 | BPSK with a matched filter at the receiver | 1 | **0** ✅ |
| 6 | QPSK, I/Q modulation and demodulation | 2 | **0** ✅ |
| 7 | 8-PSK, clean channel | 3 | **0** ✅ |
| 7 | 8-PSK through a two-path (echo) channel, **no equaliser** | 3 | 5,963 (52 %) ❌ |
| 7 | 8-PSK through the same channel, **with a 4-tap equaliser** | 3 | **0** ✅ |

The ❌ row is the point of Lab 7. An echo arriving one symbol late smears every symbol into the next (inter-symbol interference), and the text comes out as garbage. The equaliser inverts the channel and brings it back perfectly:

<p align="center">
  <img src="docs/figures/multipath_text.png" alt="Received text without equaliser (unreadable) and with equaliser (correct)" width="90%">
</p>

---

## The labs

| Lab | Topic | What I built |
|---|---|---|
| 1 | GNU Radio basics | 5-band audio equaliser, notch filter, VCO tone generator, mixing two audio tracks |
| 3 | FM | FM modulator (Δf = 75 kHz) and quadrature demodulator, with noise and pre-/de-emphasis |
| 4 | Non-linearity | diode (exp) and amplifier (tanh) models driven by a band-limited signal |
| 5 | BPSK + pulse shaping | root-raised-cosine (RRC) pulse shaping, carrier up-conversion, complete text link |
| 6 | Matched filter + QPSK | RRC matched filter, QPSK modulator, I/Q demodulator, 2×4 decoder |
| 7 | Multipath + equalisation | 8-PSK, channel H(z) = 1 + 0.5z⁻¹, 4-tap feed-forward equaliser, adaptive (CMA) equaliser |
| 8 | Carrier synchronisation | Costas loops for QPSK and M-PSK |
| extra | Time–frequency analysis | FM link carrying a chirp, tone bursts and a click; spectrogram vs wavelet scalogram |

### Lab 3 · FM modulation and demodulation

Two tones (1.1 kHz and 11 kHz) frequency-modulate a 100 kHz carrier with 75 kHz deviation, the same deviation as broadcast FM. The receiver is a **quadrature demodulator**: multiply the signal by a one-sample-delayed conjugate of itself and take the angle. That gives the phase change per sample, which is the instantaneous frequency, which is the message.

<p align="center"><img src="docs/figures/fm.png" alt="FM spectrum and demodulated message overlaid on the original" width="100%"></p>

### Lab 4 · Non-linearity

Real amplifiers saturate. Modelling one as tanh() and driving it harder makes the 340–520 kHz signal leak into its **3rd and 5th harmonic bands**, about 50 dB higher than with gentle drive. That is why a transmitter's power amplifier needs filtering after it.

<p align="center"><img src="docs/figures/nonlinearity.png" alt="Spectrum of a tanh amplifier output at three drive levels showing harmonic bands" width="100%"></p>

### Labs 5 & 6 · Pulse shaping, matched filtering, QPSK

Sharp rectangular pulses waste bandwidth, so every symbol is shaped with a **root-raised-cosine (RRC)** pulse. The roll-off α sets the trade-off: the bandwidth is (1 + α) × symbol rate / 2.

<p align="center"><img src="docs/figures/rolloff.png" alt="Spectrum of the RRC-shaped signal for four roll-off values" width="85%"></p>

The receiver applies **the same RRC filter again: the matched filter**. The two together form a raised-cosine pulse with no inter-symbol interference at the sampling instants, and this choice maximises the SNR. The eye diagram shows how well the receiver can separate symbols. It is wide open with no noise and closes as the noise grows. Each step below is a separate GNU Radio run of my QPSK flowgraph:

<p align="center"><img src="docs/figures/eye_diagram.gif" alt="Animated eye diagram closing as noise amplitude increases from 0 to 1" width="80%"></p>

### Lab 7 · Multipath and equalisation

The channel adds an echo of half the strength one symbol later: **H(z) = 1 + 0.5z⁻¹**. Its inverse is an infinite series, 1/H(z) = 1 − 0.5z⁻¹ + 0.25z⁻² − 0.125z⁻³ + …, and the equaliser keeps the first four taps. The animation steps the taps from 0 to that exact inverse. Each frame is a separate GNU Radio run, and the points come from the receiver's constellation sink:

<p align="center"><img src="docs/figures/equalizer.gif" alt="Animation: 8-PSK constellation turning from a smeared cloud into 8 clean points as the equaliser taps approach the channel inverse" width="80%"></p>

### Lab 8 · Carrier synchronisation (Costas loop)

A receiver's oscillator is never exactly at the transmitter's frequency, so the constellation **spins**. A **Costas loop** measures the phase error from the symbols themselves, filters it, and steers its own oscillator until the spin stops. My lab flowgraphs, with an M-PSK version on the right:

<p align="center"><img src="labs/lab8_carrier_sync/costas_loop_qpsk.jpg" alt="Costas loop for QPSK flowgraph" width="49%"> <img src="labs/lab8_carrier_sync/costas_loop_mpsk_viterbi.jpg" alt="Costas loop with Viterbi for M-PSK flowgraph" width="49%"></p>

The same idea, run in GNU Radio ([`tools/costas_lock_demo.py`](tools/costas_lock_demo.py)): the loop's frequency estimate converges to the true offset and the spinning ring collapses to four points.

<p align="center"><img src="docs/figures/costas_lock.gif" alt="Animation: Costas loop acquiring lock, constellation spinning then settling" width="100%"></p>

### Extra · Wavelet time–frequency analysis of an FM link

*An additional exercise I wrote in the style of the lab sheets ([problem statement and solution](labs/extra_wavelet_time_frequency)).*

A message that changes over time goes through a GNU Radio FM link. It contains a chirp sweeping from 300 Hz to 6 kHz, two overlapping tone bursts and a 0.3 ms click. The received message is then viewed in time and frequency at once.

A **spectrogram** uses one window length for every frequency, so the click smears across about 20 ms. A **Morlet wavelet scalogram** uses short wavelets at high frequency and long ones at low frequency. The click therefore becomes a sharp vertical line, while the 1 kHz burst stays a thin band.

<p align="center"><img src="docs/figures/wavelet_scalogram.gif" alt="Animation: wavelet scalogram of the received FM message being revealed in time" width="100%"></p>

<details>
<summary><b>Spectrogram vs scalogram, side by side</b></summary>
<p align="center"><img src="docs/figures/wavelet_vs_stft.png" alt="Received message, its spectrogram and its wavelet scalogram" width="100%"></p>
</details>

---

## How this repo was made

These are GUI flowgraphs: during the lab every result was a live scope window. To get real data out of them, [`tools/run_headless.py`](tools/run_headless.py) rewrites each `.grc` file before compiling it with GNU Radio's `grcc`:
- every scope (time, frequency, constellation, eye) becomes a recorder;
- every slider becomes a fixed value that can be overridden with `--set` (that is how the sweeps were made);
- file paths point at [`data/`](data).

[`docs/make_figures.py`](docs/make_figures.py) turns the recordings into the figures and animations.

```bash
# GNU Radio 3.10 environment (e.g. radioconda, or: micromamba create -n gr -c conda-forge gnuradio=3.10)
python tools/run_headless.py labs/lab6_qpsk_matched_filter/task4_qpsk_decoder.grc runs/lab6_task4.npz --inputs data
python tools/run_headless.py labs/lab7_multipath_equalization/task1_e.grc runs/sweeps/eq_1.npz --inputs data \
       --set b1=-0.5 --set b2=0.25 --set b3=-0.125 --set b4=0.0625
python tools/costas_lock_demo.py runs/costas.npz
python labs/extra_wavelet_time_frequency/fm_wavelet_flowgraph.py runs/fm_wavelet.npz
COMMS_RUNS=runs python docs/make_figures.py
```

---

## Repository

```
labs/          my flowgraphs (.grc) and the Python GNU Radio generated from them, one folder per lab, plus the extra wavelet task
data/          inputs: the transmitted text (Original_Text.txt) and the Lab 4 test signal (Input.bin)
tools/         headless runner and the Costas loop demo
docs/          figures, animations and the script that makes them
```

<details open>
<summary><b>What every file does</b></summary>

| Folder / file | What it is |
|---|---|
| **`labs/lab1_gnuradio_basics/`** | `equalizer` (5-band audio EQ), `noise_notch_filter` (band-reject + low-pass on noisy audio), `vco_tone` (tones from a VCO), `voice_over_karaoke` (mixing two audio tracks with resampling) |
| **`labs/lab3_fm/`** | `task1_fm_modulation`, `task2_fm_demodulation` (quadrature demodulator), `task3_fm_noise` (FM with noise, pre-emphasis and de-emphasis) |
| **`labs/lab4_nonlinearity/`** | `task1a` diode exp() model, `task1b` tanh() amplifier, `task2a` tanh() with an added 48 kHz interferer |
| **`labs/lab5_bpsk_pulse_shaping/`** | `lab5_1` RRC pulse shaping, `lab5_2` up-conversion, `lab5_3` and `Q3` complete BPSK text links; `received_text_Q3.txt` is the text decoded during the lab |
| **`labs/lab6_qpsk_matched_filter/`** | `q1` BPSK with noise, `task1` eye diagram, `task2` matched filter, `task3` QPSK, `task4` QPSK with constellation decoder; `received_text_*.txt` decoded during the lab |
| **`labs/lab7_multipath_equalization/`** | `task1a` 8-PSK, `task1b` + multipath, `task1c`/`task1d` + manual equaliser with error monitor, `task1_e` complete text link, `task2`/`lab7_task2` adaptive (CMA, constant-modulus) linear equaliser |
| **`labs/lab8_carrier_sync/`** | screenshots of the Costas loop flowgraphs for QPSK and M-PSK |
| **`labs/extra_wavelet_time_frequency/`** | problem statement, GNU Radio FM flowgraph, wavelet / spectrogram analysis |
| `tools/run_headless.py` | runs any of the flowgraphs without a GUI and records every scope |
| `tools/costas_lock_demo.py` | Costas loop locking a QPSK signal with a frequency offset |
| `docs/make_figures.py` | all README figures and animations, from the recorded runs |

</details>

---

## Acknowledgements

EE340 Communications Lab, Wadhwani Electronics Lab, Department of Electrical Engineering, IIT Bombay (Autumn 2025). Built with [GNU Radio](https://www.gnuradio.org/) and [PyWavelets](https://pywavelets.readthedocs.io).
