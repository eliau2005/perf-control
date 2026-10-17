# Throttle comparison

- **baseline-1**: config: platform_profile=performance fan.json={"mode": "curve", "curve": [50, 60, 63]} auto-cpufreq=active override=performance thermald=active power-limits.service=35/48W kernel=7.0.0-38-generic date=2026-10-17T01:09:00+03:00
- **tc-standard-stress**: config: throttle comparison, standard (ppd balanced), stock ASUS policy via patched thermald, 30 s idle + 600 s stress-ng matrixprod all cores. date=2026-10-17T17:35:14+03:00
- **tc-performance-stress**: config: throttle comparison, performance (ppd performance), stock ASUS policy via patched thermald, 30 s idle + 600 s stress-ng matrixprod all cores. date=2026-10-17T17:58:33+03:00

## 10-min all-core stress (stable window = minutes 3–10)

| metric | baseline-1 | tc-standard-stress | tc-performance-stress |
|---|---|---|---|
| profile / PL1 mmio W / TCC | balanced,performance,quiet / 35 / 8 | balanced / 38 / 8 | performance / 38 / 5 |
| package throttle events (Δ over 10 min) | 5,928 | 152,979 | 97,775 |
| core throttle events, all cores (Δ) | 1,572 (cpu0 only) | 333,578 | 200,700 |
| package throttle time ms (Δ) | 14,624 | 394,679 | 227,283 |
| % time thermal/TCC-limited | 3 | 98 | 30 |
| % time PL1-limited | 88 | 0 | 81 |
| % time PL2-limited | 4 | 2 | 3 |
| % time PROCHOT | 0 | 0 | 0 |
| % time unlimited | 6 | 0 | 0 |
| PkgWatt (RAPL / turbostat) | 35.0 / 35.0 | 34.1 / 34.1 | 37.8 / 37.8 |
| PkgTmp °C avg (max in run) | 84.8 (93) | 91.9 (93) | 93.8 (97) |
| Bzy_MHz (turbostat) / avg MHz (sysfs) | 2,706 / 2,706 | 2,621 / 2,619 | 2,754 / 2,750 |
| bogo-ops/s | 14,082 | 14,793 | 15,458 |
| fan rpm | 5,500 | 3,949 | 4,902 |

Per-minute throttle events (package / core-all):

| minute | baseline-1 | tc-standard-stress | tc-performance-stress |
|---|---|---|---|
| 1 | 5,105 / 1,507 | 9,000 / 17,870 | 9,454 / 29,446 |
| 2 | 823 / 65 | 8,665 / 17,296 | 15,603 / 31,200 |
| 3 | 0 / 0 | 11,884 / 30,394 | 12,179 / 23,446 |
| 4 | 0 / 0 | 18,434 / 42,218 | 12,115 / 22,164 |
| 5 | 0 / 0 | 19,182 / 38,948 | 9,155 / 17,850 |
| 6 | 0 / 0 | 16,749 / 39,890 | 10,962 / 21,090 |
| 7 | 0 / 0 | 14,170 / 32,104 | 9,893 / 18,938 |
| 8 | 0 / 0 | 16,581 / 33,124 | 7,643 / 15,032 |
| 9 | 0 / 0 | 18,794 / 39,636 | 5,136 / 10,172 |
| 10 | 0 / 0 | 17,216 / 36,855 | 4,129 / 8,256 |

## Clean V8 build

- **tc-standard-build**: config: throttle comparison, standard (ppd balanced), clean V8 build: gn clean + ninja -j16 d8 in /home/user/GitHub/v8-root/v8/out/x64.release (a8260afcc21). date=2026-10-17T18:21:54+03:00
- **tc-performance-build**: config: throttle comparison, performance (ppd performance), clean V8 build: gn clean + ninja -j16 d8 in /home/user/GitHub/v8-root/v8/out/x64.release (a8260afcc21). date=2026-10-17T19:16:25+03:00

| metric | tc-standard-build | tc-performance-build |
|---|---|---|
| wall time | 27.1 min (mm:ss or m:ss): 27:02.99, rc 0) | 27.1 min (mm:ss or m:ss): 27:08.52, rc 0) |
| package throttle events (Δ) | 418,217 | 34,156 |
| core throttle events, all cores (Δ) | 976,352 | 76,658 |
| % time thermal / PL1 / PL2 / none | 99 / 0 / 1 / 0 | 10 / 91 / 1 / 0 |
| PkgWatt (RAPL / turbostat) | 33.5 / 33.5 | 34.7 / 34.7 |
| PkgTmp °C avg (max) | 91.6 (93) | 91.4 (100) |
| Bzy_MHz / avg MHz | 2,518 / 2,512 | 2,602 / 2,595 |
| fan rpm | 3,936 | 4,690 |

