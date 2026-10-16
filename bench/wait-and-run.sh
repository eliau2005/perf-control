#!/bin/bash
# Wait (indefinitely) until a root monitor has started writing OUT/monitor.csv,
# then run the standard workloads. Lets a pkexec'd "apply + start-monitor" batch
# be authenticated later while the measurement still starts by itself.
# usage: wait-and-run.sh OUT_DIR [SUSTAINED_S] [MIXED_S]
set -u
OUT=$1
HERE=$(dirname "$(readlink -f "$0")")
echo "[$(date +%T)] waiting for $OUT/monitor.csv …"
while [ ! -f "$OUT/monitor.csv" ]; do sleep 5; done
sleep 5
echo "[$(date +%T)] monitor up — starting workloads (pkill stress-ng to abort)"
exec "$HERE/run-workloads.sh" "$OUT" "${2:-600}" "${3:-120}"
