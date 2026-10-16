#!/usr/bin/env python3
"""Per-phase summary of one bench run (monitor.csv + markers.csv + stress-ng/glmark2 logs).

usage: summarize.py RESULT_DIR [RESULT_DIR ...]   -> prints Markdown, also writes summary.md
"""
import csv
import glob
import os
import re
import statistics as st
import sys

PL1, PL2, THERMAL, PROCHOT = 0x400, 0x800, 0x2, 0x1


def load_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k in ("profile", "epp0", "gov0", "limit_reasons"):
                continue
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                r[k] = None
    return rows


def phases(markers):
    out, start = [], {}
    for t, name in markers:
        if name.endswith("_start"):
            start[name[:-6]] = t
        elif name.endswith("_end") and name[:-4] in start:
            out.append((name[:-4], start.pop(name[:-4]), t))
    return out


def mean(vals):
    vals = [v for v in vals if v is not None]
    return st.fmean(vals) if vals else None


def fmt(v, nd=1):
    return "–" if v is None else f"{v:.{nd}f}"


def bogo(path):
    try:
        m = re.search(r"bogo-ops-per-second-real-time:\s*([\d.]+)", open(path).read())
        return float(m.group(1)) if m else None
    except OSError:
        return None


def glmark_fps(path):
    try:
        fps = [float(x) for x in re.findall(r"FPS:\s*(\d+)", open(path).read())]
        return st.fmean(fps) if fps else None, len(fps)
    except OSError:
        return None, 0


def turbostat_phase(ts_path, t0, t1):
    """Mean of turbostat summary columns within [t0, t1]."""
    try:
        lines = open(ts_path).read().splitlines()
    except OSError:
        return {}
    cols, acc = None, {}
    for ln in lines:
        parts = ln.split("\t")
        if parts and parts[0] == "Time_Of_Day_Seconds":
            cols = parts
            continue
        if not cols or len(parts) != len(cols):
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
    return {c: st.fmean(v) for c, v in acc.items() if v}


def summarize(d):
    rows = load_csv(f"{d}/monitor.csv")
    markers = [(float(t), n) for t, n in csv.reader(open(f"{d}/markers.csv")) if t != "t"]
    out = [f"## {os.path.basename(d.rstrip('/'))}", ""]
    if os.path.exists(f"{d}/config.txt"):
        out += ["```", open(f"{d}/config.txt").read().strip(), "```", ""]
    out.append("| phase | s | PkgW | PkgW(ts) | pkg°C avg/max | hot°C max | SEN1 avg/max | MHz max/avg | fan | PL1 mmio | %PL1 | %PL2 | %therm | pkg_thr | core_thr | thr ms | bogo/s |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    bursts = []
    for name, t0, t1 in phases(markers):
        ph = [r for r in rows if r["t"] is not None and t0 <= r["t"] <= t1]
        if not ph:
            continue
        lr = [int(r["limit_reasons"], 16) for r in ph if r["limit_reasons"]]
        pct = lambda bit: 100 * sum(1 for x in lr if x & bit) / len(lr) if lr else None  # noqa: E731
        ts = turbostat_phase(f"{d}/turbostat.txt", t0, t1)
        delta = lambda k: (ph[-1][k] - ph[0][k]) if ph[0][k] is not None and ph[-1][k] is not None else None  # noqa: E731
        b = bogo(f"{d}/{name}.yaml") if name != "mixed" else bogo(f"{d}/mixed-cpu.yaml")
        if name.startswith("burst") and b:
            bursts.append(b)
        extra = ""
        if name == "mixed":
            fps, n = glmark_fps(f"{d}/mixed-gpu.log")
            extra = f" · glmark2 {fmt(fps, 0)} fps ({n} scenes) · GT {fmt(mean(r['gt_mhz'] for r in ph), 0)} MHz · GFXW {fmt(ts.get('GFXWatt'), 2)}"
        out.append(
            f"| {name} | {t1 - t0:.0f} | {fmt(mean(r['pkg_w'] for r in ph))} | {fmt(ts.get('PkgWatt'))} "
            f"| {fmt(mean(r['pkg_c'] for r in ph))}/{fmt(max(r['pkg_c'] for r in ph if r['pkg_c'] is not None), 0)} "
            f"| {fmt(max(r['hot_c'] for r in ph if r['hot_c'] is not None), 0)} "
            f"| {fmt(mean(r['sen1'] for r in ph))}/{fmt(max(r['sen1'] for r in ph if r['sen1'] is not None), 0)} "
            f"| {fmt(mean(r['max_mhz'] for r in ph), 0)}/{fmt(mean(r['avg_mhz'] for r in ph), 0)} "
            f"| {fmt(mean(r['fan_rpm'] for r in ph), 0)} | {fmt(mean(r['pl1_mmio'] for r in ph), 0)} "
            f"| {fmt(pct(PL1), 0)} | {fmt(pct(PL2), 0)} | {fmt(pct(THERMAL), 0)} "
            f"| {fmt(delta('pkg_thr'), 0)} | {fmt(delta('core_thr'), 0)} | {fmt(delta('pkg_thr_ms'), 0)} "
            f"| {fmt(b, 0)}{extra} |")
    if bursts:
        out.append("")
        out.append(f"bursts bogo/s: mean {st.fmean(bursts):.0f}, min {min(bursts):.0f}, max {max(bursts):.0f} "
                   f"({', '.join(f'{b:.0f}' for b in bursts)})")
    # profile / turbo / limits seen
    profs = sorted({r["profile"] for r in rows if r["profile"]})
    nt = sorted({r["no_turbo"] for r in rows if r["no_turbo"] is not None})
    out.append(f"\nprofiles seen: {profs}; no_turbo values: {nt}; PL1/PL2 msr: "
               f"{sorted({(r['pl1_msr'], r['pl2_msr']) for r in rows})}; mmio: {sorted({(r['pl1_mmio'], r['pl2_mmio']) for r in rows})}; "
               f"tcc: {sorted({r['tcc_off'] for r in rows})}")
    text = "\n".join(out) + "\n"
    with open(f"{d}/summary.md", "w") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    for d in sys.argv[1:] or sorted(glob.glob("results/*/")):
        print(summarize(d))
