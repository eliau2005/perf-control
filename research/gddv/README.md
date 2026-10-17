# ASUS X1402ZA DTT policy (GDDV `x1402_p28_0322`)

Source: `/sys/bus/platform/devices/INTC1041:00/data_vault` (3246 B). Decoded with
`tools/gddv_dump.py` → `x1402_p28_0322.txt`. ACPI `\_SB.IETM.GDDV` (SSDT8) returns
one of three vaults keyed on `\_SB.CPUW` (15/28/45 W SKU); ours is the 28 W one.

Format: ESIFDV v2 header, flags `0x40000000` = LZMA-alone compressed payload
(3098 B → 82998 B), containing a nested `dptf`/`KEYS` vault with the tables.

## Why thermald 2.5.11 rejects it

`/shared/export/itmt` is version 1 with **four** fields per entry
(`target, trip, pl1_min, pl1_max`) and is exactly 98 bytes. thermald's
`parse_itmt()` (`src/thd_gddv.cpp`) unconditionally reads a fifth string
(`unused`) and so reads past the 98-byte buffer; the heap garbage there has type
0 → `Found object of type 0, expecting 8` → `GDDV parsing failed`. Upstream
master (v2.5.13) adds bounds checks that turn the same read into a
`get_string ... out of bounds` exception, so it fails too; the fix is to make
the fifth field optional.

Everything else in the vault parses with thermald's layout assumptions
(verified element-by-element in `gddv_dump.py`, which mirrors `thd_gddv.cpp`).
Upstream issue intel/thermal_daemon#463 (Vivobook X1605ZA, same message) was
closed without a fix. Our fix lives in `~/GitHub/thermal_daemon` (master +
`parse_itmt` guard). Alternative for ≥ 2.5.12 without a rebuild: drop a repaired
vault at `/lib/firmware/intel/dtt/dtt_data_vault_<crc32s>.bin` and enable
`<DataVaultFromFileSystem>` in `/etc/thermald/thermald-features.xml`.

thermald's adaptive engine skips conditions it can't evaluate: `Screen_state`
(MS row) is ignored; `Oem0..5` map to `odvp0..5`, `Temperature_without_hysteresis`
reads the INT3403 zone. It parks the MSR PL1 at 200 W and controls the
`intel-rapl-mmio` zone; the UUID-scoped `/shared/export/<uuid>/…` sets are ignored
(only the un-scoped tables below are used).

## The policy (uuid-less `/shared/export/apat` + `apct`, what thermald reads)

Condition sets are evaluated in order, first match wins. `Oem0` = `ODVP0` =
`\ODV0`, which ACPI `\_SB.ATKD.FANL` sets from the ASUS WMI thermal-policy
write (`DEVS 0x00110019`) — i.e. Linux `platform_profile` / MyASUS fan mode.
SEN1 = INT3403 "TS0 Local Participant" (skin-side thermistor), °C = (x−2732)/10.

| # | target | condition | PL1 min–max | PL2 | TCC off | PSVT |
|---|--------|-----------|-------------|-----|---------|------|
| 39 | Check | Oem5 == 255 | 4–19 W | 19 W | 19 | 20220111 |
| 51 | HOT | SEN1 ≥ 80.0 °C | 10–15 W | 15 W | 30 | s1_ts0_52 |
| 52 | MS (screen off) | Screen_state == 0 | 10–15 W | 25 W | 11 | s1_ts0_52 |
| 59 | Whisper | Oem0 == 1 | 15–20 W | 45 W | 11 | s1_ts0_57 |
| 62 | Performance | Oem0 == 2 | 35–38 W | 45 W | 5 | s1_ts0_69 |
| 65 | Standard | SEN1 ≥ 63.0 °C | 28–38 W | 45 W | 8 | s1_ts0_63 |
| 66 | Standard_Turbo | SEN1 ≥ 0.0 °C (always) | 38–45 W | 45 W | 8 | s1_ts0_63 |
| 49 | Default | Default | 15–28 W | 50 W | 8 | s1_ts0_52 |

Targets 74/75/77 (`*_QC_SSD`) have no condition set in this table.

PSVT tables (passive policy; source TCPU, target sensor, priority, sample
period in 0.1 s, trip in 0.1 K, domain, knob 0x10000 = PL1, limit, step mW,
limit/unlimit coefficients):

| name | SEN1 trip | sample | step | extra rows |
|------|-----------|--------|------|------------|
| 20220111 | 56.0 °C | 5 s | 125 mW | — |
| s1_ts0_52 | 52.0 °C | 30 s | 250 mW | — |
| s1_ts0_57 | 57.0 °C | 20 s | 250 mW | STG0 68.0 °C |
| s1_ts0_63 | 63.0 °C | 10 s | 250 mW | STG0 68.0 °C, SEN6 85.0 °C → TCPU |
| s1_ts0_69 | 69.0 °C | 10 s | 250 mW | STG0 68.0 °C, SEN6 85.0 °C → TCPU |

`/participants/IETM.D0/psvt` (the firmware default) equals `s1_ts0_63`.

## Sensors on Linux (measured 2026-10-17, `results/*/monitor.csv`)

| zone | _STR | behaviour |
|------|------|-----------|
| SEN1 | TS0 Local Participant | **constant 63.05 °C** (= 3362 dK, exactly the Standard trip) at 44 °C idle and 93 °C load — EC returns a placeholder via `REBS(0x17, idx 0)`. Policy therefore always lands in *Standard* (never Standard_Turbo), Whisper throttles to its 15 W floor, HOT never triggers. |
| SEN2 | TS0 Remote Participant | live: 45–57 °C idle, max 76 / 81 / 83 °C in baseline / B4 Standard / B5 Performance. Not skin‑like: tracks package temperature with a 5 s lag (r = 0.87), +24 °C in the first 60 s of load, crosses 63 °C after 8 s and 80 °C after 48–157 s, cools 15 °C in 30 s. A chassis‑skin sensor has minute‑scale dynamics and never nears 80 °C — this is a heatsink/VRM thermistor. Replaying SEN1's conditions on the recorded SEN2 traces: Standard_Turbo (PL1 45 W) only for the first ~8 s (no gain: bursts are already PL2‑bound at 45 W), then Standard with the 63 °C PSVT pushing PL1 toward 28 W, then **HOT** (PL1 10–15 W, TCC 30 → 70 °C trip) after 1–3 min of sustained load. Strictly worse than today; not mapped. |
| SEN3/4/5 | TS1 Local/Remote, Thermistor Memory | 0.05 °C — unpopulated |
| SEN6/7/8 | Thermistor Memory | 42/38/37 idle → 59/46/43 °C under load; SEN6 is in the policy (85 °C → TCPU), never reached |

thermald's adaptive engine disables the XML parser (`parser_disabled = true`),
so a virtual-sensor override from `thermal-conf.xml` is not available in
adaptive mode; remapping would need a thermald change.

Other keys: `TCPU.D0/ppcc` = PL1 10–15 W (28–32 s), PL2 8–115 W, PL4 215 W —
the DTT "PPCC" override, overridden in turn by the APAT PL1MIN/PL1MAX targets.
ACPI `PPCC` method (what the kernel shows in
`/sys/bus/pci/devices/0000:00:04.0/power_limits/`) returns PL1 0.125–15 W,
PL2 25 W for cTDP level 0; `NPCC` static package is PL1 35–45 W, PL2 56.25 W.
`/shared/export/itmt`: SEN1 trip 62.0 °C, PL1 28000–35000 mW.
`/participants/TCPU.D0/trippoint/_ac0.._ac4` = 109.4/107.4/106.4/104.9/103.4 °C
(0.1 K; active-cooling trips, fan is EC controlled anyway); `_psv/_crt/_hot` =
110.4 °C.
