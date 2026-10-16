#!/bin/bash
# Run as root (pkexec). Self-tests monitor.py for 3 s, then starts it detached.
# usage: start-monitor.sh OUT_DIR DURATION_S
set -eu
OUT=$1; DUR=$2
HERE=$(dirname "$(readlink -f "$0")")
T=$(mktemp -d)
python3 "$HERE/monitor.py" "$T" 3
rows=$(wc -l < "$T/monitor.csv")
if [ "$rows" -lt 3 ]; then
  echo "self-test failed: $rows rows"; cat "$T"/*; exit 1
fi
echo "self-test ok: $rows rows; turbostat: $(head -c 300 "$T/turbostat.txt" | tr '\n' '|') err: $(cat "$T/turbostat.err")"
rm -rf "$T"
mkdir -p "$OUT"
nohup python3 "$HERE/monitor.py" "$OUT" "$DUR" > "$OUT/monitor.log" 2>&1 &
echo "monitor pid $!"
