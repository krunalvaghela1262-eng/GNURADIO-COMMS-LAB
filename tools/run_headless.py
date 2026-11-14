"""Run a GNU Radio Companion flowgraph without its GUI and record what every scope would have shown.

    python tools/run_headless.py labs/lab6_qpsk/task4.grc results/lab6_task4.npz --seconds 3 --inputs data

How: the .grc file is rewritten before compiling it with `grcc`:
  * every QT GUI sink (time / frequency / constellation / eye) becomes one Vector Sink per input, so the samples
    that would have been plotted are captured instead;
  * every QT GUI slider becomes a plain variable with the slider's default value;
  * File / WAV sources read the file of the same name from --inputs; File Sinks write next to the .npz.
The flowgraph is compiled in "no GUI" mode, run for a few seconds, and every captured stream is saved to .npz.
"""
import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import yaml

GUI_SINKS = {"qtgui_time_sink_x", "qtgui_freq_sink_x", "qtgui_const_sink_x", "qtgui_eye_sink_x", "qtgui_sink_x",
             "qtgui_waterfall_sink_x", "qtgui_number_sink", "qtgui_histogram_sink_x"}
AUDIO_SINKS = {"audio_sink"}


def sink_type(b):
    t = str(b["parameters"].get("type", "float"))
    return "complex" if "complex" in t else "float"


def headless(grc, out_grc, inputs, outp, once=False, all_sinks=False, overrides=None):
    overrides = overrides or {}
    d = yaml.safe_load(open(grc, encoding="utf-8"))
    d["options"]["parameters"]["generate_options"] = "no_gui"
    d["options"]["parameters"]["id"] = "flowgraph"
    d["options"]["parameters"]["run_options"] = "run"
    keep, captured = [], {}
    names = {b["name"]: b for b in d["blocks"]}
    n_in = {}
    for s, sp, t, tp in d["connections"]:
        if str(tp).isdigit():
            n_in[t] = max(n_in.get(t, 0), int(tp) + 1)
    for b in d["blocks"]:
        bid, p = b["id"], b["parameters"]
        off = b.get("states", {}).get("state") in ("disabled", "bypassed")
        if off and bid in GUI_SINKS and not all_sinks:
            continue                       # a scope switched off in GRC stays off (unless --all-sinks)
        if bid == "qtgui_tab_widget" or bid.startswith("qtgui_") and bid not in GUI_SINKS and bid != "variable_qtgui_range":
            continue
        if bid in ("variable_qtgui_range", "variable_qtgui_chooser", "variable_qtgui_check_box"):
            val = overrides.get(b["name"], p.get("value", p.get("default", "0")))
            b = {"name": b["name"], "id": "variable", "parameters": {"comment": "", "value": str(val)},
                 "states": b["states"]}
        elif bid in GUI_SINKS or bid in AUDIO_SINKS:
            typ = "float" if bid in AUDIO_SINKS else sink_type(b)
            for k in range(max(1, n_in.get(b["name"], 1))):
                nm = f"{b['name']}_p{k}"
                keep.append({"name": nm, "id": "blocks_vector_sink_x",
                             "parameters": {"affinity": "", "alias": "", "comment": "", "reserve_items": "1024",
                                            "type": typ, "vlen": "1"}, "states": b["states"]})
                keep[-1]["states"] = dict(b["states"], state="enabled")
                captured[nm] = (b["name"], bid, k)
            continue
        elif bid in ("blocks_file_source", "blocks_wavfile_source"):
            # the lab machine's absolute path -> the file with the same name in the inputs folder
            p["file"] = str((Path(inputs) / Path(str(p["file"]).replace("\\", "/")).name).resolve())
            p["repeat"] = "False" if once else "True"
        elif bid == "blocks_file_sink":
            p["file"] = str(outp); p["unbuffered"] = "True"
        if "gui_hint" in b.get("parameters", {}):
            b["parameters"]["gui_hint"] = ""
        keep.append(b)
    conns = []
    for s, sp, t, tp in d["connections"]:
        tb = names.get(t)
        if tb is not None and (tb["id"] in GUI_SINKS or tb["id"] in AUDIO_SINKS):
            if all_sinks or tb.get("states", {}).get("state") not in ("disabled", "bypassed"):
                conns.append([s, sp, f"{t}_p{tp}", "0"])
        elif tb is not None and (tb["id"] == "qtgui_tab_widget"):
            continue
        else:
            conns.append([s, sp, t, tp])
    d["blocks"], d["connections"] = keep, conns
    yaml.safe_dump(d, open(out_grc, "w", encoding="utf-8"), sort_keys=False)
    return captured


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("grc"); ap.add_argument("out")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--inputs", default="data", help="folder holding Original_Text.txt, Input.bin, *.wav")
    ap.add_argument("--grcc", default="grcc")
    ap.add_argument("--all-sinks", action="store_true", help="also capture scopes that are disabled in the .grc")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a slider's value")
    ap.add_argument("--once", action="store_true", help="play input files once and run to completion "
                    "(for flowgraphs without a Throttle, which would otherwise run flat out forever)")
    a = ap.parse_args()
    work = Path(tempfile.mkdtemp())
    out_txt = Path(a.out).with_suffix(".received.txt")
    overrides = dict(kv.split("=", 1) for kv in a.set)
    captured = headless(a.grc, work / "flowgraph.grc", a.inputs, out_txt.resolve(), a.once, a.all_sinks, overrides)
    r = subprocess.run([a.grcc, "-o", str(work), str(work / "flowgraph.grc")], capture_output=True, text=True)
    if r.returncode:
        sys.exit("grcc failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
    spec = importlib.util.spec_from_file_location("flowgraph", work / "flowgraph.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    tb = mod.flowgraph()
    if a.once:
        tb.run()
    else:
        tb.start(); time.sleep(a.seconds); tb.stop(); tb.wait()
    data = {nm: np.array(getattr(tb, nm).data()) for nm in captured if hasattr(tb, nm)}
    variables = {k: v for k, v in vars(tb).items() if isinstance(v, (int, float, complex)) and not k.startswith("_")}
    np.savez_compressed(a.out, **data, _variables=np.array(repr(variables)), _sinks=np.array(repr(captured)))
    print({nm: v.shape for nm, v in data.items()}, "| received file:", out_txt.stat().st_size if out_txt.exists() else None)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
