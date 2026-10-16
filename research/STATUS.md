# Status — 2026‑10‑17 (overnight run)

Goal: make the X1402ZA (i7‑1260P) behave like Windows Intel DTT + MyASUS on Linux
(Ubuntu 26.04.1, kernel 7.0.0‑38), with measurements for every change.
Reference = the ASUS DTT policy decoded from the firmware GDDV (no Windows
numbers available).

## What was done

1. **App located and put under git** — `~/GitHub/perf-control` (commit `c56dca6` =
   exactly what was installed). Map in the first commit message and `docs/`.
2. **GDDV decoded** (`research/gddv/README.md`, `tools/gddv_dump.py`): ASUS ships
   a full DTT policy; `platform_profile` → asus‑wmi → ACPI `FANL` → `ODV0`
   (quiet=1 Whisper, balanced=0 Standard, performance=2 Performance — verified
   empirically, `results/odvp-probe-2.txt`, and from thermald's own
   "Condition Set matched" lines, `results/thermald-b3-switch.log`).
3. **thermald fixed** (`~/GitHub/thermal_daemon`, branch `asus-itmt-v1`, two commits):
   - `parse_itmt()` read a 5th field ASUS's 4‑field ITMT v1 row doesn't have →
     "type 0, expecting 8" / "GDDV parsing failed" (upstream #463, unfixed).
   - `set_adaptive_target(PL1MAX/PL1MIN)` never raised PL1, so the MSR domain
     stayed at the ACPI PPCC max (15 W) → package ran at **14 W** after PL2 expired;
     and each target switch started at PL1MIN and crept up 0.5 W / 4 s.
   Installed as `/usr/local/sbin/thermald` via a systemd drop‑in (`thermald/`),
   distro package untouched; rollback in `docs/ROLLBACK.md` §1.
4. **Conflicting actors**: `power-limits.service` (static 35/48 W) disabled;
   `perfctl-fand` switched to `auto` (it rewrote `platform_profile` — i.e. the
   DTT mode — by temperature); auto‑cpufreq pinned `turbo=always` (its auto mode
   set `no_turbo=1` → 2.1 GHz cap). Full removal of auto‑cpufreq + app install
   needs root → morning (§Open).
5. **App reworked** (not yet installed): profile selector via power‑profiles‑daemon
   D‑Bus (fallback pkexec helper), fan auto/full, monitoring of DTT target,
   PL1/PL2/TCC, SEN1/SEN2, throttle counter; `perfctld` root state daemon.
   `install.sh` removes the legacy pieces. Smoke‑tested standalone (8 s, no errors).
6. **Policy override prepared, not applied**: `tools/gddv_patch.py` +
   `research/gddv/x1402_p28_0322-cool89.bin` + `thermald/vault-override.sh`.

## Measurements (same protocol each run: 30 s idle → 10‑min all‑core
`stress-ng matrixprod` → 2‑min cooldown → 8×8 s bursts → 2‑min CPU+GPU;
`bench/summarize.py results/<run>` prints the full table)

| run | config | sustained W / °C / avg MHz / bogo‑s | %thermal‑limited | thermal trips (10 min) | bursts bogo‑s | mixed %thermal |
|---|---|---|---|---|---|---|
| baseline‑1 | static 35/48 W, auto‑cpufreq turbo auto, fan forced full, thermald broken | 35.6 / 84.6 (max 93) / 2709 / 14082 | 3 % (88 % PL1) | 5 928 | **15 329** (12.6k–17.5k, dips = no_turbo) | 37 % |
| b2‑turbo‑always | + `no_turbo` pinned 0 | 35.5 / 85.7 / 2732 / 14790 | 3 % | 8 724 | **17 565** (±150) | 49 % |
| b3‑thermald‑standard | + patched thermald, ASUS **Standard** (PL1 38 / PL2 45 / TCC 8), EC fan table (~3.9k rpm) | 34.5 / 91.8 (max 93) / 2617 / 14631 | **98 %** | **191 100** (362 s) | 17 031 | 93 % |
| b5‑performance‑usermode | ASUS **Performance** (PL1 38 / PL2 45 / TCC 5 → 95 °C), EC fan ~4.7k rpm; no power column (unprivileged) | _see results/b5-performance-usermode/summary.md_ | | | | |

Reading:
- The **turbo pin** is the clear win for responsiveness: +15 % mean burst
  throughput and no more 12.6k dips. Sustained is unaffected (PL1‑bound).
- The **ASUS policy itself does not raise sustained performance here**: its PL1
  (38 W) is above what the chassis can cool with the EC's Standard fan curve,
  so the package sits on the TCC trip (92 °C) at ~34.5 W. Windows with the same
  tables behaves the same way (modulo SEN1, below). In Performance mode the
  trip moves to 95 °C and the fan runs faster → higher clocks, hotter.
- **SEN1 is stuck at 63.05 °C** on Linux (EC placeholder); the policy therefore
  never reaches Standard_Turbo (45 W) and Whisper throttles to 15 W. SEN2 is a
  live VRM‑area thermistor (45→76 °C under load) — too hot to stand in for the
  skin sensor; not remapped (see `research/gddv/README.md`).
- "Zero thermal‑trip events" conflicts with Windows fidelity in Standard: the
  policy relies on the hardware TCC trip for CPU temperature. The prepared
  override adds a TCPU 89 °C passive row so thermald lowers PL1 ~3 °C before the
  trip; it costs a few W sustained and is opt‑in (`thermald/vault-override.sh`).

## Open (needs you / root)

1. A pkexec password dialog is waiting on screen from 02:3x — the queued command
   would switch to *performance* and start a 20‑min monitor into
   `results/b5-thermald-performance/`. **Cancel it** (B5 was re‑run unprivileged).
2. `pkexec bench/apply-b4.sh` — removes auto‑cpufreq, starts power‑profiles‑daemon,
   installs the new app (`install.sh`). Then verify ppd ↔ `platform_profile`
   mapping (`powerprofilesctl set power-saver` → quiet? → odvp0 1) and run
   `results/b4-*` with the protocol. Rollback: `docs/ROLLBACK.md` §4–6.
3. Optional: `pkexec thermald/vault-override.sh install research/gddv/x1402_p28_0322-cool89.bin`
   and measure (`b6`). Remove with `… remove`.
4. Suspend/resume and AC↔battery: confirm thermald re‑applies PL1/PL2/TCC
   (watch `journalctl -u thermald -f` and `results/…/monitor.csv`).
5. Remove `/etc/systemd/system/thermald.service.d/zz-debug.conf` once done
   (debug logging is verbose).
6. Upstream PR: branch `asus-itmt-v1` (2 commits) + `thermald/PR.md` are ready;
   fork/push/open on your word (outward‑facing, and the second commit changes
   behaviour for everyone).
7. Decide the default mode mapping for GNOME's power modes (ppd): Power Saver →
   Whisper (15 W on Linux because of SEN1!), Balanced → Standard, Performance →
   Performance.
