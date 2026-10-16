#!/bin/bash
# Repeatable workloads, run as the desktop user while monitor.py samples as root.
# usage: run-workloads.sh OUT_DIR [SUSTAINED_S] [MIXED_S]
# Phases (markers.csv): idle 30 s -> sustained all-core -> cooldown 120 s ->
# 8 bursts of 8 s on / 22 s off -> optional mixed CPU+GPU (glmark2-wayland).
set -u
OUT=$1; SUST=${2:-600}; MIXED=${3:-120}
mkdir -p "$OUT"
M="$OUT/markers.csv"; echo "t,phase" > "$M"
mark() { echo "$(date +%s.%N),$1" >> "$M"; echo "[$(date +%T)] $1"; }
cpu() { stress-ng --cpu 0 --cpu-method matrixprod -t "$1" --metrics-brief --yaml "$OUT/$2.yaml" > "$OUT/$2.log" 2>&1; }

# Wait (up to 10 min) for the root monitor to be up so phases are covered.
for _ in $(seq 600); do [ -f "$OUT/monitor.csv" ] && break; sleep 1; done

mark idle_start;      sleep 30;              mark idle_end
mark sustained_start; cpu "${SUST}s" sustained; mark sustained_end
mark cooldown_start;  sleep 120;             mark cooldown_end
for i in $(seq 1 8); do
  mark "burst${i}_start"; cpu 8s "burst$i"; mark "burst${i}_end"; sleep 22
done
if [ "$MIXED" -gt 0 ] && command -v glmark2-wayland >/dev/null && [ -n "${WAYLAND_DISPLAY:-}" ]; then
  mark mixed_start
  stress-ng --cpu 4 --cpu-method matrixprod -t "${MIXED}s" --metrics-brief --yaml "$OUT/mixed-cpu.yaml" > "$OUT/mixed-cpu.log" 2>&1 &
  timeout "${MIXED}s" glmark2-wayland --run-forever -s 800x600 > "$OUT/mixed-gpu.log" 2>&1
  wait
  mark mixed_end
fi
mark done
