"""Lab 8 companion: watch a Costas loop lock onto a QPSK signal with a carrier frequency and phase offset.

    python tools/costas_lock_demo.py results/costas.npz

Pure GNU Radio: random QPSK symbols -> channel (frequency offset, phase offset, noise) -> digital.costas_loop_cc.
The loop's corrected output and its running frequency estimate are recorded for the animation in the README.
"""
import sys

import numpy as np
from gnuradio import analog, blocks, channels, digital, gr

N_SYMBOLS = 6000
FREQ_OFFSET = 0.004          # cycles per symbol: the constellation spins one full turn every 250 symbols
PHASE_OFFSET = 0.6           # rad
NOISE = 0.12
LOOP_BW = 2 * np.pi / 1200


class Demo(gr.top_block):
    def __init__(self):
        super().__init__("costas_lock_demo")
        rng = np.random.default_rng(7)
        pts = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
        syms = pts[rng.integers(0, 4, N_SYMBOLS)]
        self.src = blocks.vector_source_c(syms.tolist(), False)
        self.chan = channels.channel_model(noise_voltage=NOISE, frequency_offset=FREQ_OFFSET, epsilon=1.0,
                                           taps=[np.exp(1j * PHASE_OFFSET)], noise_seed=3)
        self.costas = digital.costas_loop_cc(LOOP_BW, 4, False)
        self.rx, self.out, self.freq = blocks.vector_sink_c(), blocks.vector_sink_c(), blocks.vector_sink_f()
        self.connect(self.src, self.chan, self.costas, self.out)
        self.connect(self.chan, self.rx)
        self.connect((self.costas, 1), self.freq)


if __name__ == "__main__":
    tb = Demo(); tb.run()
    np.savez_compressed(sys.argv[1], rx=np.array(tb.rx.data()), locked=np.array(tb.out.data()),
                        freq=np.array(tb.freq.data()), true_freq=2 * np.pi * FREQ_OFFSET, loop_bw=LOOP_BW)
    f = np.array(tb.freq.data())
    print("samples", len(f), "| loop frequency estimate (rad/sym) final:", round(float(np.mean(f[-500:])), 4),
          "true:", round(2 * np.pi * FREQ_OFFSET, 4))
