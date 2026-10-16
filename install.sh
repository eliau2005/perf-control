#!/bin/bash
# Install Performance Control system-wide and remove the legacy pieces that
# fought the thermald/DTT policy. Run as root (pkexec ./install.sh).
set -eu
HERE=$(dirname "$(readlink -f "$0")")

# legacy: static power limits, fan-level daemon
systemctl disable --now power-limits.service 2>/dev/null || true
systemctl disable --now perfctl-fand.service 2>/dev/null || true
rm -f /etc/systemd/system/power-limits.service /etc/systemd/system/perfctl-fand.service \
      /usr/local/sbin/set-power-limits /usr/local/libexec/perfctl-fand \
      /usr/local/libexec/perfctl-fand.bak-28w /usr/local/bin/perf-control.bak-28w \
      /etc/perfctl/fan.json

install -m 0755 "$HERE/bin/perf-control" /usr/local/bin/perf-control
install -m 0755 "$HERE/bin/powermon" /usr/local/bin/powermon
install -m 0755 "$HERE/libexec/perfctl-helper" /usr/local/libexec/perfctl-helper
install -m 0755 "$HERE/libexec/perfctld" /usr/local/libexec/perfctld
install -m 0644 "$HERE/polkit/local.perfctl.policy" /usr/share/polkit-1/actions/local.perfctl.policy
install -m 0644 "$HERE/systemd/perfctld.service" /etc/systemd/system/perfctld.service
install -m 0644 "$HERE/share/local.PerfControl.desktop" /usr/share/applications/local.PerfControl.desktop
systemctl daemon-reload
systemctl enable --now perfctld.service
systemctl restart perfctld.service
sleep 2
systemctl is-active perfctld.service
cat /run/perfctl/state.json; echo
