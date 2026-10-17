#!/bin/bash
# One authenticated root batch (pkexec) that runs the remaining configuration
# steps and their measurements without further input:
#   1. apply-b4.sh  (remove auto-cpufreq, power-profiles-daemon on, new app installed)
#   2. monitor results/b4-ppd-standard  — workloads started by a user-side wait-and-run.sh
#   3. install the 89 C package-temperature override vault, monitor results/b6-override-cool89
#   4. remove the override (stock ASUS policy stays the default), drop thermald debug logging
# usage: night-batch.sh /path/to/perf-control
set -u
P=${1:?repo path}
R=$P/results
log() { echo "[$(date +%T)] $*"; }
wait_done() {  # wait for the user-side workload run to write its final marker (max 45 min)
  for _ in $(seq 540); do grep -q ",done" "$1/markers.csv" 2>/dev/null && return 0; sleep 5; done
  log "timeout waiting for $1"; return 1
}

log "step 1: apply B4"
"$P/bench/apply-b4.sh" > "$R/apply-b4.log" 2>&1; log "apply-b4 rc=$?"; tail -6 "$R/apply-b4.log"
# ppd mapping check (what each GNOME power mode does to the ASUS profile)
for prof in power-saver balanced performance; do
  powerprofilesctl set $prof 2>/dev/null; sleep 6
  echo "ppd=$prof -> platform_profile=$(cat /sys/firmware/acpi/platform_profile) odvp0=$(cat /sys/bus/platform/devices/INTC1041:00/odvp0) epp=$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference) gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor) mmio PL1=$(( $(cat /sys/class/powercap/intel-rapl-mmio:0/constraint_0_power_limit_uw)/1000 )) tcc=$(cat /sys/bus/pci/devices/0000:00:04.0/tcc_offset_degree_celsius)"
done | tee "$R/ppd-mapping.txt"
powerprofilesctl set balanced; sleep 8

OUT=$R/b4-ppd-standard; install -d -o "$(stat -c %u "$R")" -g "$(stat -c %g "$R")" "$OUT"   # user-side workloads write here
echo "config: B4 = B3 + auto-cpufreq removed, power-profiles-daemon balanced (owns platform_profile/EPP), new app + perfctld installed, legacy units removed. ASUS Standard via patched thermald. date=$(date -Is)" > "$OUT/config.txt"
log "step 2: monitor B4"; "$P/bench/start-monitor.sh" "$OUT" 1250 | tail -1
wait_done "$OUT"; sleep 20

log "step 3: override vault + monitor B6"
"$P/thermald/vault-override.sh" install "$P/research/gddv/x1402_p28_0322-cool89.bin" > "$R/vault-override-install.log" 2>&1; cat "$R/vault-override-install.log"
sleep 10
OUT=$R/b6-override-cool89; install -d -o "$(stat -c %u "$R")" -g "$(stat -c %g "$R")" "$OUT"
echo "config: B6 = B4 + override vault (TCPU->TCPU 89 C passive row in every PSVT), ppd balanced -> ASUS Standard. date=$(date -Is)" > "$OUT/config.txt"
"$P/bench/start-monitor.sh" "$OUT" 1250 | tail -1
wait_done "$OUT"; sleep 20

log "step 4: back to the stock ASUS policy, debug logging off"
"$P/thermald/vault-override.sh" remove > "$R/vault-override-remove.log" 2>&1; cat "$R/vault-override-remove.log"
rm -f /etc/systemd/system/thermald.service.d/zz-debug.conf
systemctl daemon-reload; systemctl restart thermald
powerprofilesctl set balanced
chown -R 1000:1000 "$R"
log "night batch finished"
