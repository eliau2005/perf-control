#!/bin/bash
# Root batch (pkexec): measure the 89 C package-temperature override vault, then
# return to the stock ASUS policy. Workloads are started by a user-side
# wait-and-run.sh watching the same results directory.
# usage: b6-batch.sh /path/to/perf-control [results-name]
set -u
P=${1:?repo path}
NAME=${2:-b6-override-cool89}
R=$P/results
OUT=$R/$NAME
log() { echo "[$(date +%T)] $*"; }
wait_done() {
  for _ in $(seq 540); do grep -q ",done" "$1/markers.csv" 2>/dev/null && return 0; sleep 5; done
  log "timeout waiting for $1"; return 1
}

log "step 1: install override vault"
if ! "$P/thermald/vault-override.sh" install "$P/research/gddv/x1402_p28_0322-cool89.bin" > "$R/vault-override-install.log" 2>&1; then
  cat "$R/vault-override-install.log"; log "override rejected — nothing measured, stock policy active"; exit 1
fi
cat "$R/vault-override-install.log"
sleep 10
# the workloads run unprivileged and write into OUT: it must belong to the repo owner, not root
install -d -o "$(stat -c %u "$R")" -g "$(stat -c %g "$R")" "$OUT"
echo "config: B6 = B4 + override vault (TCPU->TCPU 89 C passive row, 500 mW / 2 s, in every PSVT), ppd balanced -> ASUS Standard, thermald adaptive. date=$(date -Is)" > "$OUT/config.txt"
log "step 2: monitor $NAME"; "$P/bench/start-monitor.sh" "$OUT" 1250 | tail -1
wait_done "$OUT"; sleep 20

log "step 3: back to the stock ASUS policy"
"$P/thermald/vault-override.sh" remove > "$R/vault-override-remove.log" 2>&1; cat "$R/vault-override-remove.log"
powerprofilesctl set balanced
chown -R 1000:1000 "$R"
log "b6 batch finished"
