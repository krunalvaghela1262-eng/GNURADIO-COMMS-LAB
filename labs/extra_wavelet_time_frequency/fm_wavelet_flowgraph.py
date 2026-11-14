"""Extra task: FM link carrying a time-varying message, for wavelet time-frequency analysis (GNU Radio 3.10).

    python labs/extra_wavelet_time_frequency/fm_wavelet_flowgraph.py fm_wavelet.npz

message (chirp + tone bursts + click, 48 kHz) -> resample x10 -> Frequency Mod (Δf = 15 kHz)
    -> Channel Model (AWGN) -> Quadrature Demod -> low-pass + decimate /10 -> received message
"""
import sys

import numpy as np
from gnuradio import analog, blocks, channels, filter, gr
from gnuradio.filter import firdes

FS = 48_000
INTERP = 10
DEV = 15_000
NOISE = 0.05


def message(fs=FS, dur=1.2):
    t = np.arange(int(dur * fs)) / fs
    m = np.zeros_like(t)
    on = (t >= 0.05) & (t < 0.65)                      # linear chirp 300 Hz -> 6 kHz
    tc = t[on] - 0.05
    f0, f1, T = 300.0, 6000.0, 0.6
    m[on] += 0.5 * np.sin(2 * np.pi * (f0 * tc + (f1 - f0) / (2 * T) * tc ** 2))
    win = lambda a, b: ((t >= a) & (t < b)) * np.sin(np.pi * np.clip((t - a) / (b - a), 0, 1)) ** 0.3
    m += 0.45 * np.sin(2 * np.pi * 1000 * t) * win(0.75, 0.95)      # 1 kHz burst
    m += 0.35 * np.sin(2 * np.pi * 8000 * t) * win(0.80, 0.90)      # 8 kHz burst
    k = int(1.05 * fs)
    m[k:k + 15] += 0.9 * np.hanning(15)                              # 0.3 ms click
    return t, m.astype(np.float32)


class FMWavelet(gr.top_block):
    def __init__(self, msg):
        super().__init__("fm_wavelet")
        fs_rf = FS * INTERP
        self.src = blocks.vector_source_f(msg.tolist(), False)
        self.up = filter.rational_resampler_fff(INTERP, 1)
        self.mod = analog.frequency_modulator_fc(2 * np.pi * DEV / fs_rf)
        self.chan = channels.channel_model(noise_voltage=NOISE, noise_seed=11)
        self.demod = analog.quadrature_demod_cf(fs_rf / (2 * np.pi * DEV))
        self.lpf = filter.fir_filter_fff(INTERP, firdes.low_pass(1, fs_rf, 12_000, 2_000))
        self.rx, self.rf = blocks.vector_sink_f(), blocks.vector_sink_c()
        self.connect(self.src, self.up, self.mod, self.chan, self.demod, self.lpf, self.rx)
        self.connect(self.chan, self.rf)


if __name__ == "__main__":
    t, m = message()
    tb = FMWavelet(m)
    tb.run()
    rx = np.array(tb.rx.data())
    rf = np.array(tb.rf.data())
    np.savez_compressed(sys.argv[1], fs=FS, sent=m, received=rx, rf=rf[::4], fs_rf=FS * INTERP / 4)
    lag = int(np.argmax([np.corrcoef(m[1000:40000], rx[1000 + d:40000 + d])[0, 1] for d in range(80)]))
    r = np.corrcoef(m[1000:40000], rx[1000 + lag:40000 + lag])[0, 1]
    print(f"received {len(rx)} samples | filter delay {lag} samples | correlation with the sent message {r:.3f}")
