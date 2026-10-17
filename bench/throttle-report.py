#!/usr/bin/env python3
"""Throttle comparison report: baseline vs Standard vs Performance.

usage: throttle-report.py STRESS_RUN... [--builds BUILD_RUN...] [-o results/throttle-report.md]

A stress run directory holds monitor.csv, markers.csv (sustained_start/_end),
sustained.yaml and optionally counters.txt / turbostat.txt. A build run holds
monitor.csv, markers.csv (build_start/_end), counters.txt, time.txt.
"""
import argparse
import csv
import os
import re
import statistics as st
import sys

LIMIT_BITS = {"PROCHOT": 0x1, "thermal": 0x2, "PL1": 0x400, "PL2": 0x800}


def load(run):
    rows = list(csv.DictReader(open(f"{run}/monitor.csv")))
    marks = {}
    for line in open(f"{run}/markers.csv"):
        a = line.strip().split(",")
        try:
            marks[a[1]] = float(a[0])
        except (ValueError, IndexError):
            pass
    return rows, marks


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def window(rows, t0, t1):
    return [r for r in rows if t0 <= float(r["t"]) <= t1]


def mean(rows, col):
    vals = [f(r.get(col)) for r in rows]
    vals = [v for v in vals if v is not None]
    return st.mean(vals) if vals else None


def delta(rows, col):
    vals = [f(r.get(col)) for r in rows]
    vals = [v for v in vals if v is not None]
    return (vals[-1] - vals[0]) if len(vals) >= 2 else None


def per_minute(rows, col, t0, minutes=10):
    out = []
    for m in range(minutes):
        w = window(rows, t0 + 60 * m, t0 + 60 * (m + 1))
        d = delta(w, col)
        out.append(None if d is None else int(d))
    return out


def limit_shares(rows):
    vals = [r.get("limit_reasons") for r in rows if r.get("limit_reasons")]
    if not vals:
        return {}
    n = len(vals)
    out = {}
    for name, bit in LIMIT_BITS.items():
        out[name] = 100 * sum(1 for v in vals if int(v, 16) & bit) / n
    out["none"] = 100 * sum(1 for v in vals if int(v, 16) == 0) / n
    return out


def turbostat(run, t0, t1):
    path = f"{run}/turbostat.txt"
    if not os.path.exists(path):
        return {}
    cols, acc = None, {}
    for line in open(path):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "Time_Of_Day_Seconds":
            cols = parts
            continue
        if cols is None or len(parts) != len(cols):
            continue
        try:
            t = float(parts[0])
        except ValueError:
            continue
        if t0 <= t <= t1:
            for c, v in zip(cols[1:], parts[1:]):
                try:
                    acc.setdefault(c, []).append(float(v))
                except ValueError:
                    pass
    return {c: st.mean(v) for c, v in acc.items() if v}


def bogo(run, name="sustained"):
    path = f"{run}/{name}.yaml"
    if not os.path.exists(path):
        return None
    m = re.search(r"bogo-ops-per-second-real-time:\s*([0-9.]+)", open(path).read())
    return float(m.group(1)) if m else None


def counters(run):
    path = f"{run}/counters.txt"
    if not os.path.exists(path):
        return {}
    vals = {}
    for line in open(path):
        parts = line.split()
        if len(parts) < 3:
            continue
        vals[parts[0]] = {kv.split("=")[0]: int(kv.split("=")[1]) for kv in parts[2:]}
    if "before" in vals and "after" in vals:
        return {k: vals["after"][k] - vals["before"][k] for k in vals["after"]}
    return {}


def fmt(v, nd=1):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:,.{nd}f}" if nd else f"{v:,.0f}"
    return f"{v:,}"


def stress_report(run):
    rows, marks = load(run)
    t0, t1 = marks["sustained_start"], marks["sustained_end"]
    load_rows = window(rows, t0, t1)
    stable = window(rows, t0 + 120, t1)
    ts = turbostat(run, t0 + 120, t1)
    core_col = "core_thr_all" if load_rows and load_rows[0].get("core_thr_all") not in (None, "") else "core_thr"
    cnt = counters(run)
    return {
        "run": os.path.basename(run.rstrip("/")),
        "config": open(f"{run}/config.txt").read().strip() if os.path.exists(f"{run}/config.txt") else "",
        "load_s": round(t1 - t0),
        "pkg_thr": delta(load_rows, "pkg_thr"),
        "core_thr": delta(load_rows, core_col),
        "core_col": core_col,
        "pkg_thr_ms": delta(load_rows, "pkg_thr_ms"),
        "pkg_per_min": per_minute(load_rows, "pkg_thr", t0),
        "core_per_min": per_minute(load_rows, core_col, t0),
        "limits": limit_shares(load_rows),
        "pkg_w": mean(stable, "pkg_w"),
        "pkg_c": mean(stable, "pkg_c"),
        "pkg_c_max": max(f(r["pkg_c"]) for r in load_rows if f(r["pkg_c"]) is not None),
        "avg_mhz": mean(stable, "avg_mhz"),
        "fan": mean(stable, "fan_rpm"),
        "pl1": mean(stable, "pl1_mmio"),
        "tcc": mean(stable, "tcc_off"),
        "profile": sorted({r["profile"] for r in load_rows}),
        "ts": ts,
        "bogo": bogo(run),
        "counters": cnt,
    }


def build_report(run):
    rows, marks = load(run)
    t0, t1 = marks["build_start"], marks["build_end"]
    b = window(rows, t0, t1)
    core_col = "core_thr_all" if b and b[0].get("core_thr_all") not in (None, "") else "core_thr"
    elapsed = rc = None
    if os.path.exists(f"{run}/time.txt"):
        txt = open(f"{run}/time.txt").read()
        m = re.search(r"Elapsed \(wall clock\) time.*?:\s*(.+)", txt)
        elapsed = m.group(1).strip() if m else None
        m = re.search(r"ninja rc=(\d+)", txt)
        rc = int(m.group(1)) if m else None
    return {
        "run": os.path.basename(run.rstrip("/")),
        "config": open(f"{run}/config.txt").read().strip() if os.path.exists(f"{run}/config.txt") else "",
        "secs": t1 - t0, "elapsed": elapsed, "rc": rc,
        "pkg_thr": delta(b, "pkg_thr"), "core_thr": delta(b, core_col), "core_col": core_col,
        "limits": limit_shares(b),
        "pkg_w": mean(b, "pkg_w"), "pkg_c": mean(b, "pkg_c"),
        "pkg_c_max": max(f(r["pkg_c"]) for r in b if f(r["pkg_c"]) is not None),
        "avg_mhz": mean(b, "avg_mhz"), "fan": mean(b, "fan_rpm"),
        "ts": turbostat(run, t0, t1), "counters": counters(run),
        "profile": sorted({r["profile"] for r in b}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stress", nargs="+")
    ap.add_argument("--builds", nargs="*", default=[])
    ap.add_argument("-o", default=None)
    a = ap.parse_args()
    S = [stress_report(r) for r in a.stress]
    B = [build_report(r) for r in a.builds if os.path.exists(f"{r}/markers.csv")]
    out = []
    out.append("# Throttle comparison\n")
    for s in S:
        out.append(f"- **{s['run']}**: {s['config']}")
    out.append("")
    out.append("## 10-min all-core stress (stable window = minutes 3–10)\n")
    hdr = ["metric"] + [s["run"] for s in S]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    rowsdef = [
        ("profile / PL1 mmio W / TCC", lambda s: f"{','.join(s['profile'])} / {fmt(s['pl1'],0)} / {fmt(s['tcc'],0)}"),
        ("package throttle events (Δ over 10 min)", lambda s: fmt(s["pkg_thr"], 0)),
        ("core throttle events, all cores (Δ)", lambda s: fmt(s["core_thr"], 0) + ("" if s["core_col"] == "core_thr_all" else " (cpu0 only)")),
        ("package throttle time ms (Δ)", lambda s: fmt(s["pkg_thr_ms"], 0)),
        ("% time thermal/TCC-limited", lambda s: fmt(s["limits"].get("thermal"), 0)),
        ("% time PL1-limited", lambda s: fmt(s["limits"].get("PL1"), 0)),
        ("% time PL2-limited", lambda s: fmt(s["limits"].get("PL2"), 0)),
        ("% time PROCHOT", lambda s: fmt(s["limits"].get("PROCHOT"), 0)),
        ("% time unlimited", lambda s: fmt(s["limits"].get("none"), 0)),
        ("PkgWatt (RAPL / turbostat)", lambda s: f"{fmt(s['pkg_w'])} / {fmt(s['ts'].get('PkgWatt'))}"),
        ("PkgTmp °C avg (max in run)", lambda s: f"{fmt(s['pkg_c'])} ({fmt(s['pkg_c_max'],0)})"),
        ("Bzy_MHz (turbostat) / avg MHz (sysfs)", lambda s: f"{fmt(s['ts'].get('Bzy_MHz'),0)} / {fmt(s['avg_mhz'],0)}"),
        ("bogo-ops/s", lambda s: fmt(s["bogo"], 0)),
        ("fan rpm", lambda s: fmt(s["fan"], 0)),
    ]
    for name, fn in rowsdef:
        out.append("| " + name + " | " + " | ".join(fn(s) for s in S) + " |")
    out.append("")
    out.append("Per-minute throttle events (package / core-all):\n")
    out.append("| minute | " + " | ".join(s["run"] for s in S) + " |")
    out.append("|" + "---|" * (len(S) + 1))
    for m in range(10):
        out.append(f"| {m+1} | " + " | ".join(f"{fmt(s['pkg_per_min'][m])} / {fmt(s['core_per_min'][m])}" for s in S) + " |")
    out.append("")
    if B:
        out.append("## Clean V8 build\n")
        for b in B:
            out.append(f"- **{b['run']}**: {b['config']}")
        out.append("")
        hdr = ["metric"] + [b["run"] for b in B]
        out.append("| " + " | ".join(hdr) + " |")
        out.append("|" + "---|" * len(hdr))
        bdef = [
            ("wall time", lambda b: f"{b['secs']/60:.1f} min ({b['elapsed']}, rc {b['rc']})"),
            ("package throttle events (Δ)", lambda b: fmt(b["pkg_thr"], 0)),
            ("core throttle events, all cores (Δ)", lambda b: fmt(b["core_thr"], 0)),
            ("% time thermal / PL1 / PL2 / none", lambda b: " / ".join(fmt(b["limits"].get(k), 0) for k in ("thermal", "PL1", "PL2", "none"))),
            ("PkgWatt (RAPL / turbostat)", lambda b: f"{fmt(b['pkg_w'])} / {fmt(b['ts'].get('PkgWatt'))}"),
            ("PkgTmp °C avg (max)", lambda b: f"{fmt(b['pkg_c'])} ({fmt(b['pkg_c_max'],0)})"),
            ("Bzy_MHz / avg MHz", lambda b: f"{fmt(b['ts'].get('Bzy_MHz'),0)} / {fmt(b['avg_mhz'],0)}"),
            ("fan rpm", lambda b: fmt(b["fan"], 0)),
        ]
        for name, fn in bdef:
            out.append("| " + name + " | " + " | ".join(fn(b) for b in B) + " |")
        out.append("")
    text = "\n".join(out)
    print(text)
    if a.o:
        open(a.o, "w").write(text + "\n")


if __name__ == "__main__":
    main()
