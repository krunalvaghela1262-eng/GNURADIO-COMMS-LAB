"""Draw a GNU Radio Companion flowgraph (.grc) as a clean block diagram.

    python tools/grc_render.py labs/lab6_qpsk/task4.grc  out.png

A .grc file stores every block's type, parameters and canvas position, plus every wire, so the picture is the
flowgraph exactly as it was laid out in GNU Radio Companion, just redrawn to be readable on GitHub.
"""
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path as MPath

NAMES = {
    "analog_sig_source_x": "Signal Source", "analog_noise_source_x": "Noise Source",
    "analog_random_source_x": "Random Source", "analog_const_source_x": "Constant Source",
    "analog_phase_modulator_fc": "Phase Modulator", "blocks_file_source": "File Source", "blocks_file_sink": "File Sink",
    "blocks_wavfile_source": "Wav File Source", "audio_sink": "Audio Sink", "blocks_vector_source_x": "Vector Source",
    "blocks_vco_f": "VCO", "blocks_repeat": "Repeat", "blocks_throttle2": "Throttle", "blocks_add_xx": "Add",
    "blocks_multiply_xx": "Multiply", "blocks_multiply_const_vxx": "Multiply Const", "blocks_add_const_vxx": "Add Const",
    "blocks_divide_xx": "Divide", "blocks_transcendental": "Transcendental", "blocks_delay": "Delay",
    "blocks_conjugate_cc": "Conjugate", "blocks_complex_to_arg": "Complex to Arg", "blocks_complex_to_real": "Complex to Real",
    "blocks_complex_to_imag": "Complex to Imag", "blocks_complex_to_float": "Complex to Float",
    "blocks_float_to_complex": "Float to Complex", "blocks_complex_to_mag_squared": "Complex to Mag²",
    "blocks_abs_xx": "Abs", "blocks_moving_average_xx": "Moving Average", "blocks_threshold_ff": "Threshold",
    "blocks_float_to_uchar": "Float to UChar", "blocks_or_xx": "Or", "blocks_skiphead": "Skip Head",
    "blocks_pack_k_bits_bb": "Pack K Bits", "blocks_unpack_k_bits_bb": "Unpack K Bits",
    "digital_chunks_to_symbols_xx": "Chunks to Symbols", "digital_constellation_decoder_cb": "Constellation Decoder",
    "digital_linear_equalizer": "Linear Equalizer", "interp_fir_filter_xxx": "Interpolating FIR",
    "fir_filter_xxx": "Decimating FIR", "iir_filter_xxx": "IIR Filter", "low_pass_filter": "Low Pass Filter",
    "band_pass_filter": "Band Pass Filter", "band_reject_filter": "Band Reject Filter",
    "root_raised_cosine_filter": "Root Raised Cosine", "rational_resampler_xxx": "Rational Resampler",
    "dc_blocker_xx": "DC Blocker", "qtgui_time_sink_x": "Time Sink", "qtgui_freq_sink_x": "Frequency Sink",
    "qtgui_const_sink_x": "Constellation Sink", "qtgui_eye_sink_x": "Eye Diagram Sink", "qtgui_sink_x": "QT GUI Sink",
}
KEY = {  # parameters worth printing under the title
    "analog_sig_source_x": ("waveform", "freq"), "analog_noise_source_x": ("amp",), "blocks_delay": ("delay",),
    "blocks_multiply_const_vxx": ("const",), "blocks_add_const_vxx": ("const",), "blocks_threshold_ff": ("low", "high"),
    "blocks_pack_k_bits_bb": ("k",), "blocks_unpack_k_bits_bb": ("k",), "interp_fir_filter_xxx": ("interp",),
    "fir_filter_xxx": ("decim",), "low_pass_filter": ("cutoff_freq",), "band_pass_filter": ("low_cutoff_freq", "high_cutoff_freq"),
    "root_raised_cosine_filter": ("alpha", "sym_rate"), "rational_resampler_xxx": ("interp", "decim"),
    "digital_chunks_to_symbols_xx": ("symbol_table",), "blocks_transcendental": ("name",), "blocks_moving_average_xx": ("length",),
    "iir_filter_xxx": ("fftaps", "fbtaps"), "digital_linear_equalizer": ("num_taps", "adapt_after_training"),
    "analog_phase_modulator_fc": ("sensitivity",), "blocks_vco_f": ("sensitivity",), "blocks_skiphead": ("num_items",),
}
PRETTY = {"waveform": "", "analog.GR_COS_WAVE": "cos", "analog.GR_SIN_WAVE": "sin", "analog.GR_SQR_WAVE": "square",
          "analog.GR_CONST_WAVE": "const"}
COL = {  # (fill, edge) per category
    "source": ("#dcfce7", "#16a34a"), "sink": ("#fce7f3", "#db2777"), "filter": ("#dbeafe", "#2563eb"),
    "digital": ("#ffedd5", "#ea580c"), "math": ("#ede9fe", "#7c3aed"), "other": ("#f1f5f9", "#64748b"),
}


def category(bid):
    if "source" in bid or bid in ("blocks_vco_f",):
        return "source"
    if "sink" in bid:
        return "sink"
    if any(k in bid for k in ("filter", "fir", "iir", "resampler", "dc_blocker", "moving_average")):
        return "filter"
    if bid.startswith("digital") or "bits" in bid or bid in ("blocks_threshold_ff", "blocks_float_to_uchar", "blocks_skiphead"):
        return "digital"
    if any(k in bid for k in ("multiply", "add", "divide", "abs", "conjugate", "complex", "float_to", "transcendental",
                              "delay", "or_xx", "modulator")):
        return "math"
    return "other"


def fmt(bid, params):
    out = []
    for k in KEY.get(bid, ()):
        v = str(params.get(k, "")).strip()
        if not v:
            continue
        v = PRETTY.get(v, v)
        if len(v) > 18:
            v = v[:16] + "…"
        out.append(v if k == "waveform" else f"{k.replace('_freq', '').replace('_', ' ')}: {v}")
    return out


def render(grc_path, out_path, title=None, max_w=16.0):
    d = yaml.safe_load(open(grc_path, encoding="utf-8"))
    blocks = {b["name"]: b for b in d["blocks"]
              if not b["id"].startswith("variable") and b["id"] not in ("options", "import", "qtgui_tab_widget")}
    n_in, n_out = defaultdict(int), defaultdict(int)
    wires = []
    for src, sp, dst, dp in d["connections"]:
        if src in blocks and dst in blocks and str(sp).isdigit() and str(dp).isdigit():
            n_out[src] = max(n_out[src], int(sp) + 1)
            n_in[dst] = max(n_in[dst], int(dp) + 1)
            wires.append((src, int(sp), dst, int(dp)))
    geo = {}
    for name, b in blocks.items():
        x, y = b["states"]["coordinate"]
        lines = fmt(b["id"], b["parameters"])
        label = NAMES.get(b["id"], b["id"].replace("_", " ").title())
        w = max(len(label) * 6.9, max([len(s) * 5.6 for s in lines] + [0])) + 18
        h = max(30 + 13 * len(lines), 22 * max(n_in[name], n_out[name], 1) + 12)
        geo[name] = (x, y, w, h, label, lines, b["states"].get("rotation", 0) in (180, 180.0))
    xs = [g[0] for g in geo.values()] + [g[0] + g[2] for g in geo.values()]
    ys = [g[1] for g in geo.values()] + [g[1] + g[3] for g in geo.values()]
    x0, x1, y0, y1 = min(xs) - 30, max(xs) + 30, min(ys) - 40, max(ys) + 30
    # one canvas pixel = one image pixel, exactly like the GRC canvas, so text never gets squashed
    W, H = (x1 - x0) / 100, (y1 - y0) / 100
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor="#0f172a")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor("#0f172a")
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.axis("off")
    fs = 8.5

    def port(name, idx, is_out):
        x, y, w, h, *_ , flipped = geo[name]
        n = n_out[name] if is_out else n_in[name]
        py = y + h * (idx + 1) / (n + 1)
        right = is_out != flipped
        return (x + w, py) if right else (x, py), (1 if right else -1)

    for src, sp, dst, dp in wires:
        (a, da), (b, db) = port(src, sp, True), port(dst, dp, False)
        k = max(40, abs(b[0] - a[0]) * 0.45)
        verts = [a, (a[0] + da * k, a[1]), (b[0] + db * k, b[1]), b]
        ax.add_patch(PathPatch(MPath(verts, [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4]),
                               fc="none", ec="#94a3b8", lw=1.1, alpha=0.85, zorder=1))
        ax.plot(*b, marker=">" if db < 0 else "<", ms=4, color="#94a3b8", zorder=2)
    for name, (x, y, w, h, label, lines, flipped) in geo.items():
        fc, ec = COL[category(blocks[name]["id"])]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6", fc=fc, ec=ec, lw=1.6, zorder=3))
        ax.text(x + w / 2, y + 15, label, ha="center", va="center", fontsize=fs, weight="bold", color="#0f172a", zorder=4)
        for i, s in enumerate(lines):
            ax.text(x + w / 2, y + 30 + 13 * i, s, ha="center", va="center", fontsize=fs * 0.82, color="#334155", zorder=4)
    if title:
        ax.text(x0 + 10, y0 + 18, title, color="white", fontsize=fs * 1.5, weight="bold", va="center")
    fig.savefig(out_path, facecolor=fig.get_facecolor()); plt.close(fig)
    return len(blocks), len(wires)


if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
