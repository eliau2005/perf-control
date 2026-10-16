#!/bin/bash
# Install the locally built, patched thermald next to the distro package.
# Run as root (pkexec). usage: install.sh /path/to/thermal_daemon/thermald
#
# The distro package stays installed (dbus policy, default configs, unit) but
# the unit's ExecStart is overridden by a drop-in to run /usr/local/sbin/thermald.
# To revert: rm -r /etc/systemd/system/thermald.service.d; systemctl daemon-reload;
#            systemctl restart thermald
set -eu
BIN=${1:?path to built thermald binary}
HERE=$(dirname "$(readlink -f "$0")")
install -m 0755 "$BIN" /usr/local/sbin/thermald
install -d /etc/systemd/system/thermald.service.d
install -m 0644 "$HERE/override.conf" /etc/systemd/system/thermald.service.d/override.conf
systemctl daemon-reload
systemctl restart thermald
sleep 3
/usr/local/sbin/thermald --version
systemctl is-active thermald
journalctl -u thermald -b --no-pager | tail -5
