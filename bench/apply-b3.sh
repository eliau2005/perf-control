#!/bin/bash
# Step B3: hand PL1/PL2/TCC control to the patched thermald running ASUS's own DTT policy.
# Run as root (pkexec). usage: apply-b3.sh /path/to/thermal_daemon/thermald
#  - power-limits.service (static 35/48 W) disabled and stopped
#  - fan daemon switched to "auto" (hands profile back, stops rewriting it)
#  - platform_profile = balanced  (ODVP0 = 0 -> Standard / Standard_Turbo)
#  - patched thermald installed via systemd drop-in, with debug logging for now
set -eu
BIN=${1:?path to built thermald}
HERE=$(dirname "$(readlink -f "$0")")
systemctl disable --now power-limits.service 2>/dev/null || true
python3 - <<'EOF'
import json
p = "/etc/perfctl/fan.json"
c = json.load(open(p)); c["mode"] = "auto"; json.dump(c, open(p, "w"))
EOF
sleep 3   # let perfctl-fand see "auto" and hand back to balanced
echo balanced > /sys/firmware/acpi/platform_profile
echo 2 > "$(grep -l '^asus$' /sys/class/hwmon/hwmon*/name | xargs dirname)/pwm1_enable"
"$HERE/../thermald/install.sh" "$BIN"
# debug logging while we validate the policy selection
mkdir -p /etc/systemd/system/thermald.service.d
cat > /etc/systemd/system/thermald.service.d/debug.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/local/sbin/thermald --systemd --dbus-enable --adaptive --loglevel=debug
EOF
systemctl daemon-reload
systemctl restart thermald
sleep 8
echo "--- state"
echo "profile=$(cat /sys/firmware/acpi/platform_profile) odvp0=$(cat /sys/bus/platform/devices/INTC1041:00/odvp0)"
for z in intel-rapl:0 intel-rapl-mmio:0; do
  echo "$z PL1=$(( $(cat /sys/class/powercap/$z/constraint_0_power_limit_uw)/1000 )) mW PL2=$(( $(cat /sys/class/powercap/$z/constraint_1_power_limit_uw)/1000 )) mW tau=$(cat /sys/class/powercap/$z/constraint_0_time_window_us)"
done
echo "tcc=$(cat /sys/bus/pci/devices/0000:00:04.0/tcc_offset_degree_celsius)"
echo "--- thermald log"
journalctl -u thermald -b --no-pager --since "-30s" | grep -vE "^\s*$" | tail -80
