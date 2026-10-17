#!/bin/bash
# Root batch (pkexec): throttle comparison Standard vs Performance, measurement only.
# For each mode: cool down to idle, 30 s idle + 600 s all-core stress-ng matrixprod
# (same workload as the baseline), then a clean V8 build (gn clean + ninja TARGET)
# as the desktop user. Everything sampled by monitor.py (1 Hz sysfs/MSR + turbostat).
# No configuration is changed; the profile is restored to balanced at the end.
# usage: throttle-compare.sh REPO V8_DIR [TARGET=d8] [MODES="standard performance"] [STEPS="stress build"]
set -u
P=${1:?repo}; V8=${2:?v8 dir}; TARGET=${3:-d8}; MODES=${4:-"standard performance"}; STEPS=${5:-"stress build"}
R=$P/results; UID_=$(stat -c %u "$R"); GID_=$(stat -c %g "$R"); USER_=$(id -nu "$UID_")
NINJA=$V8/third_party/ninja/ninja; GN=$V8/buildtools/linux64/gn
log() { echo "[$(date +%T)] $*"; }
for h in /sys/class/hwmon/hwmon*; do [ "$(cat "$h/name")" = coretemp ] && PKG=$h/temp1_input; done
pkg_c() { echo $(( $(cat "$PKG") / 1000 )); }
ppd_for() { case $1 in standard) echo balanced;; performance) echo performance;; quiet) echo power-saver;; esac; }
cool_down() {  # wait until package temperature stays <= 52 C for 30 s (max 12 min)
  local ok=0 i
  for i in $(seq 360); do
    if [ "$(pkg_c)" -le 52 ]; then ok=$((ok+1)); else ok=0; fi
    [ $ok -ge 15 ] && { log "cool: pkg $(pkg_c) C after $((i*2)) s"; return; }
    sleep 2
  done
  log "cool-down timeout, pkg $(pkg_c) C"
}
counters() {  # sum of core_throttle_count over all cpus, package count, package ms
  local c=0 f
  for f in /sys/devices/system/cpu/cpu[0-9]*/thermal_throttle/core_throttle_count; do c=$((c + $(cat "$f"))); done
  echo "$1 $(date +%s.%N) core_all=$c pkg=$(cat /sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count) pkg_ms=$(cat /sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_total_time_ms)"
}
start_mon() { install -d -o "$UID_" -g "$GID_" "$1"; "$P/bench/start-monitor.sh" "$1" "$2" | tail -1 | sed 's/.*pid //'; }
mark() { echo "$(date +%s.%N),$1" >> "$2/markers.csv"; log "$1"; }

case " $STEPS " in *" stress "*) for mode in $MODES; do
  powerprofilesctl set "$(ppd_for "$mode")"; sleep 8
  log "== $mode: profile $(cat /sys/firmware/acpi/platform_profile) odvp0 $(cat /sys/bus/platform/devices/INTC1041:00/odvp0) PL1 $(( $(cat /sys/class/powercap/intel-rapl-mmio:0/constraint_0_power_limit_uw)/1000 )) tcc $(cat /sys/bus/pci/devices/0000:00:04.0/tcc_offset_degree_celsius)"
  cool_down
  OUT=$R/tc-$mode-stress; install -d -o "$UID_" -g "$GID_" "$OUT"
  echo "config: throttle comparison, $mode (ppd $(ppd_for "$mode")), stock ASUS policy via patched thermald, 30 s idle + 600 s stress-ng matrixprod all cores. date=$(date -Is)" > "$OUT/config.txt"
  PID=$(start_mon "$OUT" 660); sleep 5
  echo "t,phase" > "$OUT/markers.csv"
  mark idle_start "$OUT"; sleep 30; mark idle_end "$OUT"
  counters before >> "$OUT/counters.txt"
  mark sustained_start "$OUT"
  stress-ng --cpu 0 --cpu-method matrixprod -t 600s --metrics-brief --yaml "$OUT/sustained.yaml" > "$OUT/sustained.log" 2>&1
  mark sustained_end "$OUT"
  counters after >> "$OUT/counters.txt"
  mark done "$OUT"
  while kill -0 "$PID" 2>/dev/null; do sleep 2; done
  chown -R "$UID_:$GID_" "$OUT"
done;; esac

case " $STEPS " in *" build "*) for mode in $MODES; do
  powerprofilesctl set "$(ppd_for "$mode")"; sleep 8
  log "== $mode: V8 $TARGET clean build"
  cool_down
  OUT=$R/tc-$mode-build; install -d -o "$UID_" -g "$GID_" "$OUT"
  echo "config: throttle comparison, $mode (ppd $(ppd_for "$mode")), clean V8 build: gn clean + ninja -j16 $TARGET in $V8/out/x64.release ($(git -C "$V8" log -1 --format=%h)). date=$(date -Is)" > "$OUT/config.txt"
  PID=$(start_mon "$OUT" 0); sleep 5
  echo "t,phase" > "$OUT/markers.csv"
  mark idle_start "$OUT"; sleep 30; mark idle_end "$OUT"
  # remove every built output but keep build.ninja (no gn regeneration inside the timed build);
  # gn clean needs to run inside the source tree, which the first version of this script got wrong
  runuser -u "$USER_" -- bash -c "cd '$V8' && '$NINJA' -C out/x64.release -t clean" > "$OUT/clean.log" 2>&1
  echo "outputs left: $(find "$V8/out/x64.release/obj" -name '*.o' 2>/dev/null | wc -l) .o files" >> "$OUT/clean.log"
  counters before >> "$OUT/counters.txt"
  mark build_start "$OUT"
  runuser -u "$USER_" -- /usr/bin/time -v -o "$OUT/time.txt" "$NINJA" -C "$V8/out/x64.release" -j16 "$TARGET" > "$OUT/ninja.log" 2>&1
  echo "ninja rc=$?" >> "$OUT/time.txt"
  mark build_end "$OUT"
  counters after >> "$OUT/counters.txt"
  cp "$V8/out/x64.release/.ninja_log" "$OUT/ninja_log" 2>/dev/null
  mark done "$OUT"
  sleep 3; kill "$PID" 2>/dev/null; while kill -0 "$PID" 2>/dev/null; do sleep 1; done
  chown -R "$UID_:$GID_" "$OUT"
done;; esac

powerprofilesctl set balanced
chown -R "$UID_:$GID_" "$R"
log "throttle comparison finished"
