# perf-control

Make an **ASUS Vivobook 14 X1402ZA** (Intel i7‑1260P) run its thermals and power
limits on Linux the way Windows Intel DTT + MyASUS does. Every change is
measured.

Tested on Ubuntu 26.04.1, kernel 7.0.0‑38. The firmware ships a full Intel DTT
policy in its GDDV data vault, and that policy is the reference here.

## What's in it

- **Performance Control app** (`bin/perf-control`, GTK 4 / libadwaita): picks the
  ASUS mode (Whisper / Standard / Performance) through power‑profiles‑daemon,
  switches the fan between auto and full, and shows live monitoring: DTT target,
  PL1/PL2/TCC, package power and temperature, clocks, SEN1/SEN2, throttle counters.
- **`perfctld`** (`libexec/perfctld`, systemd unit in `systemd/`): a read‑only root
  daemon. Once a second it writes `/run/perfctl/state.json` with the values the
  UI cannot read unprivileged. It never writes hardware.
- **`perfctl-helper`** + polkit policy: a pkexec fallback for switching profiles
  and the fan when ppd isn't available.
- **`powermon`**: a console monitor for package power, temperature and throttling,
  with a CSV log.
- **Patched thermald** (`thermald/`): install script, systemd drop‑in and notes
  for running upstream thermald with two fixes that let it parse and apply the
  ASUS GDDV policy. Upstream PR: [intel/thermal_daemon#609](https://github.com/intel/thermal_daemon/pull/609).
- **GDDV research** (`research/gddv/`, `tools/`): the decoded firmware policy, a
  dumper (`gddv_dump.py`), a patcher (`gddv_patch.py`) and an LZMA check harness.
- **Benchmarks** (`bench/`, `results/`): a fixed measurement protocol, the batch
  scripts, and raw and summarized results for every configuration tried.

## How it fits together

Only two actors touch power management:

| actor | owns |
|---|---|
| power‑profiles‑daemon | `platform_profile` (→ ASUS mode / EC fan table) and EPP |
| thermald `--adaptive` (patched) | PL1 / PL2 / TCC, taken from the ASUS DTT tables for the current mode |

ppd maps its profiles to the ASUS modes:

| ppd profile | ASUS mode | PL1 | TCC offset |
|---|---|---|---|
| power‑saver | Whisper | 20 W | 11 |
| balanced | Standard | 38 W | 8 |
| performance | Performance | 38 W | 5 |

The app only selects the mode. It never writes power limits.

## Install

Requires Python 3, PyGObject with GTK 4 and libadwaita, power‑profiles‑daemon,
and (for the DTT policy to apply) the patched thermald.

```sh
# 1. patched thermald: build per thermald/README.md, then
pkexec thermald/install.sh /path/to/thermal_daemon/thermald

# 2. app + daemon (also removes the legacy static-limit and fan units)
pkexec ./install.sh
```

Installed paths: `/usr/local/bin/perf-control`, `/usr/local/bin/powermon`,
`/usr/local/libexec/perfctl{d,-helper}`, `/etc/systemd/system/perfctld.service`,
the polkit action and a `.desktop` entry.

Rollback for every piece is in [`docs/ROLLBACK.md`](docs/ROLLBACK.md).

## Results in brief

Ten minutes of all‑core `stress-ng matrixprod` (full protocol in
[`bench/README.md`](bench/README.md); details in
[`research/STATUS.md`](research/STATUS.md) and
[`results/throttle-report.md`](results/throttle-report.md)):

| config | package W / °C | bogo‑ops/s | fan rpm |
|---|---|---|---|
| original setup (static 35 W, fan full, auto‑cpufreq, broken thermald) | 35.0 / 84.8 | 14 082 | 5 500 |
| ASUS Standard (ppd balanced) | 34.1 / 91.9 | 14 793 (+5 %) | 3 949 |
| ASUS Performance (ppd performance) | 37.8 / 93.8 | 15 458 (+10 %) | 4 902 |

- Removing auto‑cpufreq (it set `no_turbo=1` at times) raised burst throughput by about 15 %.
- In Standard the package stays on the TCC trip (~92 °C) because the EC's
  Standard fan curve can't remove 38 W. That is how the firmware is designed to
  work, but it means many throttle events.
- Performance gives +4–5 % on long compute runs. A clean V8 build takes the
  same time in both modes (27:03 vs 27:09).
- An extra 89 °C passive row in the policy (`thermald/vault-override.sh`) brought
  no measurable benefit. It stays in the repo as an opt‑in experiment.
- The default is the stock ASUS policy in Standard.

Known limitation: SEN1 (the skin sensor) reads a fixed 63.05 °C on Linux, so
the policy never reaches Standard_Turbo (45 W) and Whisper sits at 15–20 W.

## Repository layout

```
bin/        perf-control (UI), powermon
libexec/    perfctld (state daemon), perfctl-helper (pkexec fallback)
systemd/    perfctld.service
polkit/     polkit action for the helper
share/      desktop entry
thermald/   patched-thermald install, drop-in, policy override, PR notes
research/   STATUS.md, decoded GDDV policy and firmware dumps
tools/      GDDV dump/patch tools
bench/      measurement protocol and batch scripts
results/    raw and summarized benchmark runs
docs/       ROLLBACK.md
legacy/     the replaced static-limit and fan-daemon setup, kept for rollback
```

## Caveats

This was built for one laptop model and one firmware (GDDV `x1402_p28_0322`).
The scripts write to systemd units, polkit and RAPL/thermal settings as root.
Read them before running on other hardware.
