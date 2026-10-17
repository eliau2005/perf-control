# Upstream PR draft — intel/thermal_daemon

**Opened 2026-10-17 as https://github.com/intel/thermal_daemon/pull/609** (fork `eliau2005/thermal_daemon`, branch `asus-itmt-v1`, both commits). The text below is the draft it was built from.

**Title:** gddv: tolerate ITMT v1 entries without the trailing string

**Body:**

Fixes #463.

On ASUS Vivobook laptops with Alder Lake (observed: X1402ZA, i7-1260P, INT3400
`INTC1041`, data vault `x1402_p28_0322`; #463 is an X1605ZA with the same
message) `thermald --adaptive` fails with

```
Found object of type 0, expecting 8
GDDV parsing failed
```

(2.5.11) or, with the bounds checks added in 2.5.12,

```
GDDV: get_string type read out of bounds (off=98 len=98)
```

The vault itself is fine: a v2 ESIFDV header, `ESIF_SERVICE_CONFIG_COMPRESSED`,
LZMA-alone payload (3098 → 82998 bytes) with a nested `dptf`/KEYS repository
holding PPCC, six PSVTs, APAT/APCT and trip points, all of which parse. The
single key that breaks is `/shared/export/itmt`, a 98-byte ITMT **version 1**
table with one entry of four fields:

```
00: 04 00 00 00  01 00 00 00 00 00 00 00                 u64 version = 1
0c: 08 00 00 00  1a 00 .. 00  "\_SB_.PC00.LPCB.EC0_.SEN1\0"   str target
31: 04 00 00 00  18 0d 00 00 00 00 00 00                 u64 trip = 3352 (62.0 °C)
3d: 08 00 00 00  06 00 .. 00  "28000\0"                   str pl1_min
4f: 08 00 00 00  06 00 .. 00  "35000\0"                   str pl1_max
62:                                                       (end, len = 98)
```

`cthd_gddv::parse_itmt()` reads a fifth string (`unused`) for every entry and
then skips 12 bytes for v1, so for this layout it reads at offset 98 == len.
Before 2.5.12 that read 4 bytes of adjacent heap (zero → "type 0"); now it
throws from the bounds check. Either way the exception propagates out of
`parse_gddv_key()` and the whole adaptive engine is abandoned, although none
of the APAT targets even reference ITMT.

This change only consumes the trailing string when one is present (type tag 8
at the current offset, within bounds). Tables that do carry the fifth field
are parsed exactly as before.

Tested on the X1402ZA: the vault now parses, `odvp0` (set by the ASUS WMI fan
mode) selects the Whisper/Standard/Performance APAT targets, and thermald
applies PL1MIN/PL1MAX/PL2PowerLimit/TccOffset and the mode's PSVT.

**Attach:** `research/gddv/x1402_p28_0322.bin` (3246 B) as evidence; mention
`tools/gddv_dump.py` output if useful.

---

# Second commit (same PR or a follow-up): cdev_rapl PL1MAX/PL1MIN

With parsing fixed, the adaptive engine on this machine still ran the
package at 14 W: the ACPI PPCC reports PL1 0.125–15 W, `update()` writes that
maximum to *both* RAPL devices, and `set_adaptive_target("PL1MAX")` only ever
lowers PL1 — so the "Disable rapl-msr interface and use rapl-mmio"
PL1MAX=200000 call wrote nothing and the MSR stayed at 15 W (the effective
limit is min(MSR, MMIO)). PL1MIN had the mirror problem: `curr_state` is 0 at
startup, which compares "below" the floor, so each target switch first wrote
PL1MIN and the zones then crept up 0.5 W per poll. Commit message in
`~/GitHub/thermal_daemon` (`git log asus-itmt-v1`) has the full write-up;
evidence: `results/thermald-b3-start.log` (before) and
`results/thermald-b3-switch.log` (after).
