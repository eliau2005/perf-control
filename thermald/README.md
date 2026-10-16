# Patched thermald for the ASUS X1402ZA

Ubuntu 26.04 ships thermald 2.5.11, which cannot parse this laptop's DTT data
vault (see `../research/gddv/README.md`). Upstream (v2.5.13, master) has the
same bug. We run upstream master plus a one-hunk fix to `parse_itmt()`.

## Source

`~/GitHub/thermal_daemon` — clone of https://github.com/intel/thermal_daemon,
branch `asus-itmt-v1` on top of master (v2.5.13-2-g39f4bdb). The fix:
`src/thd_gddv.cpp`, `cthd_gddv::parse_itmt()` — only read the trailing
`unused` string of a version‑1 entry when it is present.

## Build

```sh
cd ~/GitHub/thermal_daemon
./autogen.sh && ./configure --prefix=/usr/local --sysconfdir=/etc --localstatedir=/var
make -j"$(nproc)"
```

Build deps (installed 2026-10-17): autoconf automake libtool pkg-config g++
libdbus-1-dev libdbus-glib-1-dev libglib2.0-dev libxml2-dev libevdev-dev
libupower-glib-dev liblzma-dev gtk-doc-tools.

## Install (survives apt upgrades)

The distro package stays installed — it owns the D-Bus policy, the unit and
`/etc/thermald/`. Only the binary is replaced via a systemd drop-in:

```sh
pkexec ./install.sh ~/GitHub/thermal_daemon/thermald
```

→ `/usr/local/sbin/thermald` + `/etc/systemd/system/thermald.service.d/override.conf`
(`ExecStart=/usr/local/sbin/thermald --systemd --dbus-enable --adaptive`).
An apt upgrade of `thermald` replaces `/usr/sbin/thermald` but the drop-in keeps
pointing at ours. When a distro version ≥ the upstream fix lands, revert with:

```sh
pkexec sh -c 'rm -r /etc/systemd/system/thermald.service.d && systemctl daemon-reload && systemctl restart thermald'
```

## Verify

```sh
journalctl -u thermald -b --no-pager | grep -E "GDDV|target|apat|odvp|Standard|Whisper|Performance"
```

Expect no "GDDV parsing failed"; in adaptive mode thermald logs the selected
APAT target when `odvp0`/SEN1 change. Debug: add `--loglevel=debug` to the
drop-in temporarily.
