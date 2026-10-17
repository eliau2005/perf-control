# Status — 2026‑10‑17 (overnight run + morning batch)

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
4. **Conflicting actors removed** (B4, `bench/apply-b4.sh`, 10:59): auto‑cpufreq
   uninstalled (it rewrote governor/EPP every 3 s and set `no_turbo=1` → 2.1 GHz
   cap); `power-limits.service` (static 35/48 W) and `perfctl-fand` (rewrote
   `platform_profile` by temperature) removed; power‑profiles‑daemon 0.30
   (Ubuntu's default, tuned‑ppd not installed) unmasked and owns
   `platform_profile` + EPP. Mapping measured (`results/ppd-mapping.txt`):
   power‑saver → quiet/Whisper (PL1 20 W, TCC 11, EPP power), balanced →
   Standard (38 W, TCC 8, balance_performance), performance → Performance
   (38 W, TCC 5, EPP performance). thermald re‑targets within one 4 s poll.
5. **App reworked and installed** (`/usr/local/bin/perf-control`, `perfctld`):
   profile selector via ppd D‑Bus (fallback pkexec helper), fan auto/full,
   monitoring of DTT target, PL1/PL2/TCC, SEN1/SEN2, throttle counter. No direct
   PL/TCC writes anywhere in the app. Old instance replaced at 11:42; old code
   stays at commit `c56dca6`.
6. **Policy override** (`tools/gddv_patch.py`, `research/gddv/x1402_p28_0322-cool89.bin`,
   `thermald/vault-override.sh`): first attempt (B6, 11:19) was **rejected by
   thermald** — Python's LZMA‑alone writer leaves the uncompressed size as
   "unknown" and thermald's decoder requires a real size → "Unable to parse
   GDDV" → thermald silently dropped `--adaptive` and ran its generic engine.
   Fixed (size written into the header; verified with a harness built from
   thermald's own `thd_lzma_dec.cpp`), and `vault-override.sh` now rolls the
   vault back automatically if thermald falls out of adaptive mode. Re‑run
   queued (`bench/b6-batch.sh`).

## Measurements (same protocol each run: 30 s idle → 10‑min all‑core
`stress-ng matrixprod` → 2‑min cooldown → 8×8 s bursts → 2‑min CPU+GPU;
`bench/summarize.py results/<run>` prints the full table)

| run | config | sustained W / °C / avg MHz / bogo‑s | %thermal‑limited | thermal trips (10 min) | bursts bogo‑s | mixed bogo‑s / %thermal |
|---|---|---|---|---|---|---|
| baseline‑1 | static 35/48 W, auto‑cpufreq turbo auto, fan forced full, thermald broken | 35.6 / 84.6 (max 93) / 2709 / 14082 | 3 % (88 % PL1) | 5 928 | **15 329** (12.6k–17.5k, dips = no_turbo) | 37 % |
| b2‑turbo‑always | + `no_turbo` pinned 0 | 35.5 / 85.7 / 2732 / 14790 | 3 % | 8 724 | **17 565** (±150) | 49 % |
| b3‑thermald‑standard | + patched thermald, ASUS **Standard** (PL1 38 / PL2 45 / TCC 8), EC fan table (~3.9k rpm) | 34.5 / 91.8 (max 93) / 2617 / 14631 | **98 %** | **191 100** (362 s) | 17 031 | 93 % |
| b5‑performance‑usermode (+ root tail in b5‑thermald‑performance) | ASUS **Performance** (PL1 38 / PL2 45 / TCC 5 → 95 °C), EC fan ~4.8k rpm | ~38 (turbostat) / **93.5 (max 96)** / 2826 / **15 384** | n/a (no MSR) | 46 779 (135 s) | 17 078 | 9 237 / 88 % |
| **b4‑ppd‑standard** | B3 + auto‑cpufreq removed, **ppd balanced**, new app + perfctld, legacy units gone | 34.5 / 91.8 (max 93) / 2640 / **14 878** | 98 % | 190 552 (416 s) | 16 935 | 8 716 / 91 % |
| b6a‑thermald‑default‑engine (accidental) | B4 but thermald in its **non‑adaptive** engine (rejected vault): PPCC‑style PL1 stepping, MMIO 35 W, `no_turbo` toggled twice | 31.8 / 87.0 (max 93) / 2529 / 14 261 | 10 % (88 % PL1) | 25 992 | 16 849 | 8 397 / 65 % |
| **b6‑override‑cool89** (15:36) | B4 + TCPU 89 °C passive row (500 mW / 2 s) in every PSVT, override vault, thermald adaptive | 34.7 / 90.9 (max 93) / 2636 / 14 785 | 70 % (34 % PL1) | 186 430 (263 s) | 16 837 | 8 679 / 82 % |

Reading:
- **B4 = B3 within noise** (sustained +1.7 %, bursts −0.6 %): removing
  auto‑cpufreq and handing the profile to ppd costs nothing; ppd's EPP
  `balance_performance` vs auto‑cpufreq's `performance` makes no measurable
  difference under load. The system now has exactly two actors: ppd
  (profile/EPP) and thermald (PL1/PL2/TCC from the ASUS tables).
- The **turbo pin** is the clear win for responsiveness: +15 % mean burst
  throughput and no more 12.6k dips (auto‑cpufreq is gone, so nothing sets
  `no_turbo` any more; B4 saw it set only for 4 s, at 11:20:54 — thermald's
  generic engine during the rejected‑vault restart).
- The **ASUS policy itself does not raise sustained performance here**: its PL1
  (38 W) is above what the chassis can cool with the EC's Standard fan curve,
  so the package sits on the TCC trip (92 °C) at ~34.5 W. Windows with the same
  tables behaves the same way (modulo SEN1, below). In Performance mode the
  trip moves to 95 °C and the fan runs faster → higher clocks, hotter.
- **b6a is a useful accident**: it shows what plain thermald does on this
  machine without the ASUS tables — 3 W less sustained for 4 % less throughput,
  far fewer trips, but it also toggles `no_turbo` and steps PL1 blindly. Not a
  candidate.
- **SEN1 is stuck at 63.05 °C** on Linux (EC placeholder); the policy therefore
  never reaches Standard_Turbo (45 W) and Whisper throttles to 15–20 W. SEN2 is
  a live VRM‑area thermistor (45→76 °C under load) — too hot to stand in for
  the skin sensor; not remapped (see `research/gddv/README.md`).
- "Zero thermal‑trip events" conflicts with Windows fidelity in Standard: the
  policy relies on the hardware TCC trip for CPU temperature. The override adds
  a TCPU 89 °C passive row so thermald lowers PL1 before the trip.
- **B6 shows the override buys nothing as tuned**: thermald did act (MMIO PL1
  walked 38 → 28 W and back in 125–500 mW steps, PL1‑bound 34 % of the time),
  but the package still spent 70 % of the run on the TCC trip, trip events fell
  only 2 % (186k vs 190k), average temperature 0.9 °C, throughput −0.6 %,
  bursts −0.6 %, mixed −0.4 %. A 2 s / 500 mW passive loop is far slower than
  the 28 s PL1 time window and the firmware trip at 92 °C; the real limiter is
  the EC's Standard fan curve (~3.9k rpm ≈ 34 W of cooling at 92 °C). Making
  the row aggressive enough to stop trips (≈85 °C or multi‑watt steps) would
  just trade throughput for a lower number. **Recommendation: keep the stock
  ASUS policy as default**; the override stays in the repo as an opt‑in
  experiment (`thermald/vault-override.sh`), not installed.

Performance mode reading: +4 % sustained throughput over Standard/B2 at
93–96 °C; the TCC trip (95 °C) is still the governor. Bursts are identical
across B2/B3/B4/B5 (PL2‑bound). Mixed CPU+GPU is best in Performance but 88 %
thermally limited.

B6 took three attempts: `b6a-thermald-default-engine` (vault rejected, LZMA size
field), `b6b-override-idle-only` (root‑owned results dir, workloads could not
write), then the real run at 15:36. Both failure modes are fixed in the scripts.
Nothing is queued any more.

## Current system state

- thermald: `/usr/local/sbin/thermald --adaptive` (patched), firmware vault,
  info‑level logging (debug drop‑in removed), Standard target on balanced.
- power‑profiles‑daemon active, `balanced`; auto‑cpufreq, `power-limits.service`,
  `perfctl-fand`, `set-power-limits` removed. `no_turbo=0`, governor powersave,
  EPP balance_performance.
- `perfctld` active (`/run/perfctl/state.json`), new `perf-control` UI running.
- Rollback for each piece: `docs/ROLLBACK.md`.

## Transitions (`bench/transition-check.sh`, 16:55–17:02)

- **Suspend/resume** (`results/suspend-1`): two s2idle cycles (16:56:59→16:57:19,
  16:57:19→16:57:40). Before and after: profile balanced, MMIO PL1/PL2 38/45 W,
  MSR PL1 parked at 200 W, TCC 8, `no_turbo` 0, EPP balance_performance — the
  limits survive s2idle on this platform, thermald kept polling (Standard target,
  no re‑init needed), `perfctld` state live after resume.
- **AC↔battery** (`results/battery-1`): unplug at 16:59:23 → ppd switched EPP to
  `balance_power` within one sample; PL1/PL2/TCC and the DTT target unchanged
  (the ASUS APCT has no power‑source condition; Standard stays 38/45/8 on
  battery, as on Windows). Replug 17:00:27 → `balance_performance` again. No
  `no_turbo` change, no thermald re‑target. Result: pass.

## Open (needs you)

1. ~~Suspend/resume and AC↔battery~~ — done, see above.
2. Upstream PR: branch `asus-itmt-v1` (2 commits) + `thermald/PR.md` ready;
   fork/push/open on your word (outward‑facing; the second commit changes
   behaviour for everyone).
3. Confirm the default: stock ASUS Standard (recommended after B6 — the
   override measured no benefit). Nothing to do if you agree; it is already
   the installed state.
4. GNOME power‑mode mapping via ppd: Power Saver → Whisper is **15–20 W** on
   Linux (SEN1 stuck); fine for battery, surprising if chosen on AC.
