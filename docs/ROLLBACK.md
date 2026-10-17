# Rollback — every change made on 2026‑10‑17 and how to undo it

All commands run as root (`pkexec bash -c '…'`). Nothing here requires a reboot.

## 1. Patched thermald (upstream 2.5.13 + two fixes) via systemd drop‑in

What changed: `/usr/local/sbin/thermald` installed; drop‑ins
`/etc/systemd/system/thermald.service.d/override.conf` (ExecStart → our binary)
and `zz-debug.conf` (adds `--loglevel=debug`, temporary). The distro package
(`thermald 2.5.11-0ubuntu1.1`, `/usr/sbin/thermald`) is untouched.

Undo (back to the distro daemon):
```sh
rm -r /etc/systemd/system/thermald.service.d
systemctl daemon-reload && systemctl restart thermald
```
Effect: thermald 2.5.11 again fails GDDV parsing and runs its default engine
(PL1 modulation on the MSR domain only). thermald restores the power‑on RAPL
limits it recorded when it exits (`Registered RAPL …` lines in the journal).

Just drop debug logging: `rm /etc/systemd/system/thermald.service.d/zz-debug.conf`.

## 2. Static power limits (`power-limits.service`, PL1 35 W / PL2 48 W)

What changed: disabled and stopped (`bench/apply-b3.sh`); files removed by
`install.sh`. Copies: `legacy/set-power-limits`, `legacy/power-limits.service`.

Undo:
```sh
install -m 0755 legacy/set-power-limits /usr/local/sbin/set-power-limits
install -m 0644 legacy/power-limits.service /etc/systemd/system/power-limits.service
systemctl daemon-reload && systemctl enable --now power-limits.service
```
(Only sensible together with §1's undo — with thermald adaptive active the two
would fight over the MMIO PL1.)

## 3. Fan daemon `perfctl-fand` (curve mode → auto → removed)

What changed: `/etc/perfctl/fan.json` mode `curve` → `auto` (B3), then the
daemon/unit removed by `install.sh` (B4). Original files: `legacy/perfctl-fand*`,
`legacy/fan.json.installed`, old UI `legacy/perf-control.bak-28w`, and the full
pre‑rework tree at git commit `c56dca6`.

Undo:
```sh
git -C ~/GitHub/perf-control show c56dca6:libexec/perfctl-fand > /usr/local/libexec/perfctl-fand
chmod 755 /usr/local/libexec/perfctl-fand
git -C ~/GitHub/perf-control show c56dca6:systemd/perfctl-fand.service > /etc/systemd/system/perfctl-fand.service
install -m 0644 legacy/fan.json.installed /etc/perfctl/fan.json
systemctl daemon-reload && systemctl enable --now perfctl-fand
```

## 4. auto‑cpufreq

What changed: B2 set `--turbo=always` (pickle `/opt/auto-cpufreq/turbo-override.pickle`);
B4 runs `auto-cpufreq --remove` (stops/disables the unit, removes
`/usr/local/bin/cpufreqctl.auto-cpufreq`, deletes `override.pickle`, unmasks
and starts power‑profiles‑daemon). 2026‑10‑17 17:40: the GTK launcher
`/usr/local/bin/auto-cpufreq-gtk` and `/usr/share/applications/auto-cpufreq-gtk.desktop`
were deleted so it cannot be opened by accident. Kept on purpose until ~2026‑10‑31
(two weeks of stable operation): the venv `/opt/auto-cpufreq`, the CLI
`/usr/local/bin/auto-cpufreq` + `auto-cpufreq-install`, `/usr/local/share/auto-cpufreq`
and the polkit policy `/usr/share/polkit-1/actions/org.auto-cpufreq.pkexec.policy`.
Final purge when the time comes:
```sh
pkexec rm -rf /opt/auto-cpufreq /usr/local/share/auto-cpufreq /usr/local/bin/auto-cpufreq /usr/local/bin/auto-cpufreq-install /usr/share/polkit-1/actions/org.auto-cpufreq.pkexec.policy
```

Undo turbo pin only: `/usr/local/bin/auto-cpufreq --turbo=auto`.

Undo removal (reinstall from the kept venv):
```sh
/usr/local/bin/auto-cpufreq --install      # recreates the unit, masks ppd again
/usr/local/bin/auto-cpufreq --force=performance
```

## 5. power‑profiles‑daemon

What changed: unmasked and enabled by B4 (it was masked by auto‑cpufreq's
installer). Undo: `systemctl mask --now power-profiles-daemon`.

## 6. Performance Control app

What changed: `install.sh` replaces `/usr/local/bin/perf-control`,
`/usr/local/libexec/perfctl-helper`, the polkit policy and the desktop entry,
adds `/usr/local/libexec/perfctld` + `perfctld.service`.

Undo (old app, commit `c56dca6`):
```sh
systemctl disable --now perfctld; rm -f /etc/systemd/system/perfctld.service /usr/local/libexec/perfctld
cd ~/GitHub/perf-control && git show c56dca6:bin/perf-control > /usr/local/bin/perf-control
git show c56dca6:libexec/perfctl-helper > /usr/local/libexec/perfctl-helper
git show c56dca6:polkit/local.perfctl.policy > /usr/share/polkit-1/actions/local.perfctl.policy
chmod 755 /usr/local/bin/perf-control /usr/local/libexec/perfctl-helper
```
then §3 for the fan daemon the old UI expects.

## 7. Packages installed

`acpica-tools glmark2-wayland intel-gpu-tools autoconf-archive` and thermald
build deps (`autoconf automake libtool pkg-config g++ make libdbus-1-dev
libdbus-glib-1-dev libglib2.0-dev libxml2-dev libevdev-dev libupower-glib-dev
liblzma-dev gtk-doc-tools`). Harmless; `apt-get remove` if unwanted.
