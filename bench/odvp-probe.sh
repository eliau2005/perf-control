#!/bin/bash
# Empirically map platform_profile -> ASUS throttle_thermal_policy -> ODVP0 (DTT Oem0),
# and see what the firmware itself does to RAPL MMIO/MSR limits and the fan on each switch.
# Run as root. Restores the original profile at the end.
set -u
PP=/sys/firmware/acpi/platform_profile
INT=/sys/bus/platform/devices/INTC1041:00
ASUS=$(grep -l '^asus$' /sys/class/hwmon/hwmon*/name | xargs dirname)
orig=$(cat $PP)
show() {
  printf "%-12s ttp=%s odvp0=%s odvp1=%s mmio PL1/PL2=%s/%s W  msr PL1/PL2=%s/%s W  tcc=%s  fan=%s rpm  pwm1_enable=%s\n" \
    "$1" "$(cat /sys/devices/platform/asus-nb-wmi/throttle_thermal_policy)" \
    "$(cat $INT/odvp0)" "$(cat $INT/odvp1)" \
    "$(( $(cat /sys/class/powercap/intel-rapl-mmio:0/constraint_0_power_limit_uw)/1000000 ))" \
    "$(( $(cat /sys/class/powercap/intel-rapl-mmio:0/constraint_1_power_limit_uw)/1000000 ))" \
    "$(( $(cat /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw)/1000000 ))" \
    "$(( $(cat /sys/class/powercap/intel-rapl:0/constraint_1_power_limit_uw)/1000000 ))" \
    "$(cat /sys/bus/pci/devices/0000:00:04.0/tcc_offset_degree_celsius)" \
    "$(cat $ASUS/fan1_input)" "$(cat $ASUS/pwm1_enable)"
}
show "initial($orig)"
for p in quiet balanced performance; do
  echo "$p" > $PP; sleep 4; show "$p"
done
echo "$orig" > $PP; sleep 2; show "restored"
