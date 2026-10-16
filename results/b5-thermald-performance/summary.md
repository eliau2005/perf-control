## b5-thermald-performance

```
config: B5 = B3 but platform_profile=performance (odvp0=2 -> DTT target 62 Performance: PL1 35-38 W, PL2 45 W, TCC 5 -> 95 C; EC Performance fan table). auto-cpufreq active turbo=always. Root monitor started 02:37 (after the queued pkexec was authenticated): power data covers the last ~7 min of sustained, the bursts and mixed.
```

| phase | s | PkgW | PkgW(ts) | pkg°C avg/max | hot°C max | SEN1 avg/max | MHz max/avg | fan | PL1 mmio | %PL1 | %PL2 | %therm | pkg_thr | core_thr | thr ms | bogo/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cooldown | 120 | 10.8 | 11.0 | 66.2/95 | 95 | 63.0/63 | 4019/1363 | 3211 | 38 | 0 | 0 | 3 | 93 | 23 | 420 | – |
| burst1 | 8 | 42.2 | 43.3 | 88.1/91 | 91 | 63.0/63 | 3375/3041 | 2700 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 17138 |
| burst2 | 8 | 42.0 | 44.0 | 87.8/90 | 93 | 63.0/63 | 3350/3038 | 3025 | 38 | 0 | 100 | 0 | 1 | 1 | 2 | 17030 |
| burst3 | 8 | 41.8 | 44.4 | 86.6/93 | 93 | 63.0/63 | 3360/3055 | 3125 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 17117 |
| burst4 | 8 | 41.6 | 45.0 | 89.1/93 | 93 | 63.0/63 | 3365/3058 | 3025 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 17097 |
| burst5 | 8 | 41.6 | 41.1 | 85.6/92 | 92 | 63.0/63 | 3375/3067 | 3100 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 17109 |
| burst6 | 8 | 41.4 | 41.5 | 87.5/92 | 92 | 63.0/63 | 3378/3073 | 3112 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 17129 |
| burst7 | 8 | 41.4 | 42.3 | 86.0/93 | 93 | 63.0/63 | 3378/3072 | 3038 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 16922 |
| burst8 | 8 | 41.2 | 42.8 | 88.8/93 | 92 | 63.0/63 | 3349/3045 | 2962 | 38 | 0 | 100 | 0 | 0 | 0 | 0 | 17079 |
| mixed | 120 | 35.6 | 35.7 | 94.2/96 | 96 | 63.0/63 | 3374/2331 | 4275 | 38 | 0 | 0 | 88 | 9046 | 8611 | 92653 | 9237 · glmark2 3938 fps (12 scenes) · GT 405 MHz · GFXW 2.07 |

bursts bogo/s: mean 17078, min 16922, max 17138 (17138, 17030, 17117, 17097, 17109, 17129, 16922, 17079)

profiles seen: ['performance']; no_turbo values: [0.0]; PL1/PL2 msr: [(200.0, 48.0)]; mmio: [(38.0, 45.0)]; tcc: [5.0]
