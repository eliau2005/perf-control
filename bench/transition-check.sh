#!/bin/bash
# Unprivileged check that thermald/ppd re-apply the policy across suspend/resume
# and AC<->battery. Run it, then suspend (or unplug/replug) while it samples.
#   bench/transition-check.sh results/suspend-1 180
# Prints every distinct (ppd profile, platform_profile, odvp0, PL1/PL2 mmio, TCC,
# AC) state seen, with the first timestamp, plus thermald's target changes.
set -u
OUT=${1:?out dir}; SECS=${2:-180}
HERE=$(dirname "$(readlink -f "$0")")
mkdir -p "$OUT"
START=$(date +%T)
echo "sampling $SECS s into $OUT (suspend / unplug now) …"
python3 "$HERE/monitor.py" "$OUT" "$SECS" >/dev/null 2>&1
python3 - "$OUT/monitor.csv" <<'EOF'
import csv, sys, time
rows = list(csv.DictReader(open(sys.argv[1])))
seen, last = [], None
for r in rows:
    key = (r.get("profile"), r.get("pl1_mmio"), r.get("pl2_mmio"), r.get("tcc_off"), r.get("ac"), r.get("no_turbo"), r.get("epp0"))
    if key != last:
        seen.append((time.strftime("%H:%M:%S", time.localtime(float(r["t"]))), key)); last = key
print(f"{len(rows)} samples; distinct states (time, profile, PL1, PL2, TCC, AC, no_turbo, EPP):")
for t, k in seen: print(" ", t, *k)
gaps = [(rows[i-1]["t"], rows[i]["t"]) for i in range(1, len(rows)) if float(rows[i]["t"]) - float(rows[i-1]["t"]) > 5]
for a, b in gaps: print("  gap (suspend?)", time.strftime("%H:%M:%S", time.localtime(float(a))), "->", time.strftime("%H:%M:%S", time.localtime(float(b))))
EOF
echo "thermald since $START:"
journalctl -u thermald --since "$START" --no-pager -o short-precise 2>/dev/null | grep -E "Condition Set matched|Target Name|suspend|resume|Restor|PL1MAX|rapl_update|GDDV" | tail -40
echo "ppd now: $(powerprofilesctl get)  platform_profile: $(cat /sys/firmware/acpi/platform_profile)  odvp0: $(cat /sys/bus/platform/devices/INTC1041:00/odvp0 2>/dev/null)"
