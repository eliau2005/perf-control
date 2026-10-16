#!/usr/bin/env python3
"""1 Hz sampler of the package power/thermal/frequency state. Run as root.

usage: monitor.py OUT_DIR [DURATION_S]

Writes OUT_DIR/monitor.csv (sysfs + MSR view) and OUT_DIR/turbostat.txt
(turbostat's own view, for cross-checking PkgWatt/Bzy_MHz/GFX)."""
import csv
import glob
import os
import signal
import struct
import subprocess
import sys
import time

OUT = sys.argv[1]
DURATION = float(sys.argv[2]) if len(sys.argv) > 2 else 0
CPU = "/sys/devices/system/cpu"
RAPL = "/sys/class/powercap/intel-rapl:0"
MMIO = "/sys/class/powercap/intel-rapl-mmio:0"
TT = f"{CPU}/cpu0/thermal_throttle"
MSR_PERF_LIMIT_REASONS = 0x64F
TS_COLS = ["Time_Of_Day_Seconds", "Avg_MHz", "Busy%", "Bzy_MHz", "CoreTmp", "PkgTmp",
           "PkgWatt", "CorWatt", "GFXWatt", "GFXMHz", "GFXAMHz", "GFX%rc6", "UncMHz",
           "SysWatt"]


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def read_int(path):
    try:
        return int(read(path))
    except ValueError:
        return None


def hwmon(name):
    for h in glob.glob("/sys/class/hwmon/hwmon*"):
        if read(f"{h}/name") == name:
            return h
    return None


def read_msr(cpu, reg):
    try:
        with open(f"/dev/cpu/{cpu}/msr", "rb") as f:
            return struct.unpack("<Q", os.pread(f.fileno(), 8, reg))[0]
    except OSError:
        return None


def start_turbostat():
    try:
        avail = subprocess.run(["turbostat", "--list"], capture_output=True, text=True,
                               timeout=10).stdout
        avail = {c.strip() for c in avail.replace("\n", ",").split(",")}
    except Exception:
        avail = set()
    cols = [c for c in TS_COLS if c in avail]
    err = open(f"{OUT}/turbostat.err", "w")
    cmd = ["turbostat", "-S", "-q", "-i", "1", "-o", f"{OUT}/turbostat.txt"]
    if cols:
        cmd += ["--show", ",".join(cols)]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err)
    time.sleep(2)
    if p.poll() is not None and cols:  # --show rejected; fall back to defaults
        p = subprocess.Popen(cmd[:7], stdout=subprocess.DEVNULL, stderr=err)
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    subprocess.call(["modprobe", "msr"], stderr=subprocess.DEVNULL)
    coretemp, asus = hwmon("coretemp"), hwmon("asus")
    core_temps = sorted(glob.glob(f"{coretemp}/temp*_input")) if coretemp else []
    zones = {read(f"{z}/type"): z for z in glob.glob("/sys/class/thermal/thermal_zone*")}
    sens = sorted(t for t in zones if t.startswith("SEN"))
    tcc = [c for c in glob.glob("/sys/class/thermal/cooling_device*")
           if read(f"{c}/type") == "TCC Offset"]
    gt = (glob.glob("/sys/class/drm/card*/gt_act_freq_mhz") or [None])[0]
    freqs = sorted(glob.glob(f"{CPU}/cpu[0-9]*/cpufreq/scaling_cur_freq"))
    wrap = read_int(f"{RAPL}/max_energy_range_uj") or 2 ** 32

    cols = ["t", "pkg_w", "pkg_c", "hot_c", "max_mhz", "avg_mhz", "fan_rpm", "profile",
            "pwm1_enable", "no_turbo", "epp0", "gov0", "pl1_msr", "pl2_msr", "pl1_mmio",
            "pl2_mmio", "tcc_off", "core_thr", "pkg_thr", "pkg_thr_ms", "gt_mhz",
            "ac", "limit_reasons", *[s.lower() for s in sens]]
    ts = start_turbostat()
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    signal.signal(signal.SIGINT, lambda *_: stop.append(1))

    last = None
    t_end = time.monotonic() + DURATION if DURATION else None
    with open(f"{OUT}/monitor.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        f.flush()
        while not stop and (t_end is None or time.monotonic() < t_end):
            now, e = time.time(), read_int(f"{RAPL}/energy_uj")
            watts = None
            if last and e is not None:
                watts = round(((e - last[1]) % wrap) / 1e6 / (now - last[0]), 2)
            last = (now, e)
            temps = [v for v in map(read_int, core_temps) if v is not None]
            mhz = [v / 1000 for v in map(read_int, freqs) if v is not None]
            plr = read_msr(0, MSR_PERF_LIMIT_REASONS)
            row = [
                round(now, 3), watts,
                (read_int(f"{coretemp}/temp1_input") or 0) / 1000 if coretemp else None,
                max(temps) / 1000 if temps else None,
                round(max(mhz)) if mhz else None,
                round(sum(mhz) / len(mhz)) if mhz else None,
                read_int(f"{asus}/fan1_input") if asus else None,
                read("/sys/firmware/acpi/platform_profile"),
                read_int(f"{asus}/pwm1_enable") if asus else None,
                read_int(f"{CPU}/intel_pstate/no_turbo"),
                read(f"{CPU}/cpu0/cpufreq/energy_performance_preference"),
                read(f"{CPU}/cpu0/cpufreq/scaling_governor"),
                (read_int(f"{RAPL}/constraint_0_power_limit_uw") or 0) / 1e6,
                (read_int(f"{RAPL}/constraint_1_power_limit_uw") or 0) / 1e6,
                (read_int(f"{MMIO}/constraint_0_power_limit_uw") or 0) / 1e6,
                (read_int(f"{MMIO}/constraint_1_power_limit_uw") or 0) / 1e6,
                read_int(f"{tcc[0]}/cur_state") if tcc else None,
                read_int(f"{TT}/core_throttle_count"),
                read_int(f"{TT}/package_throttle_count"),
                read_int(f"{TT}/package_throttle_total_time_ms"),
                read_int(gt) if gt else None,
                read_int("/sys/class/power_supply/AC0/online"),
                f"{plr & 0xffff:04x}" if plr is not None else None,
                *[(read_int(f"{zones[s]}/temp") or 0) / 1000 for s in sens],
            ]
            w.writerow(row)
            f.flush()
            time.sleep(max(0.0, 1.0 - (time.time() - now)))
    ts.terminate()
    try:
        ts.wait(5)
    except subprocess.TimeoutExpired:
        ts.kill()
    uid = os.environ.get("PKEXEC_UID") or os.environ.get("SUDO_UID")
    if uid:
        for p in glob.glob(f"{OUT}/*") + [OUT]:
            os.chown(p, int(uid), -1)


if __name__ == "__main__":
    main()
