#!/bin/bash
# Step B4: remove the remaining conflicting actors and install the reworked app.
# Run as root (pkexec). Assumes apply-b3.sh already ran (patched thermald active).
#  - auto-cpufreq removed (it rewrote governor/EPP every ~3 s and toggled no_turbo);
#    its --remove also unmasks and starts power-profiles-daemon, which then owns
#    platform_profile + EPP and is what the app/GNOME use to switch modes
#  - legacy power-limits.service / perfctl-fand removed, perfctld + new app installed
set -eu
HERE=$(dirname "$(readlink -f "$0")")
if [ -x /usr/local/bin/auto-cpufreq ]; then
  /usr/local/bin/auto-cpufreq --remove 2>&1 | tail -3 || true
fi
rm -f /opt/auto-cpufreq/turbo-override.pickle /opt/auto-cpufreq/override.pickle
systemctl disable --now auto-cpufreq.service 2>/dev/null || true
rm -f /etc/systemd/system/auto-cpufreq.service
systemctl daemon-reload
echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo
# power-profiles-daemon: make sure it's running and in balanced
systemctl unmask power-profiles-daemon.service 2>/dev/null || true
systemctl enable --now power-profiles-daemon.service
sleep 2
powerprofilesctl set balanced || true
"$HERE/../install.sh"
sleep 2
echo "--- state"
echo "ppd=$(systemctl is-active power-profiles-daemon) profile=$(cat /sys/firmware/acpi/platform_profile) odvp0=$(cat /sys/bus/platform/devices/INTC1041:00/odvp0)"
echo "no_turbo=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo) gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor) epp=$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference)"
powerprofilesctl 2>/dev/null | head -20
