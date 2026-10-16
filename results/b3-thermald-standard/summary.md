## b3-thermald-standard

```
config: B3 = B2 + patched thermald 2.5.13 (parse_itmt + PL1MAX fixes) in --adaptive running ASUS GDDV policy; power-limits.service disabled; perfctl-fand mode=auto (no profile rewriting, pwm1_enable=2 EC fan table); platform_profile=balanced (odvp0=0 -> Standard, SEN1 stuck 63.05 so never Standard_Turbo); auto-cpufreq still active with turbo=always, governor performance. Limits at start: MSR PL1 200 W, MMIO PL1 38 W PL2 45 W TCC 8. kernel=7.0.0-38-generic date=2026-10-17T02:03:33+03:00
```

| phase | s | PkgW | PkgW(ts) | pkg°C avg/max | hot°C max | SEN1 avg/max | MHz max/avg | fan | PL1 mmio | %PL1 | %PL2 | %therm | pkg_thr | core_thr | thr ms | bogo/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| idle | 30 | 10.0 | 9.9 | 57.1/71 | 71 | 63.0/63 | 3744/1136 | 2390 | 38 | 0 | 0 | 0 | 0 | 0 | 0 | – |
| sustained | 600 | 34.5 | 34.5 | 91.8/93 | 93 | 63.0/63 | 2828/2617 | 3932 | 38 | 0 | 2 | 98 | 191100 | 78228 | 362317 | 14631 |
| cooldown | 120 | 12.6 | 12.6 | 67.9/93 | 93 | 63.0/63 | 3876/1414 | 3502 | 38 | 0 | 0 | 12 | 407 | 58 | 2162 | – |
| burst1 | 8 | 41.9 | 42.7 | 90.4/93 | 93 | 63.0/63 | 3325/3025 | 2925 | 38 | 0 | 88 | 12 | 817 | 157 | 2857 | 16775 |
| burst2 | 8 | 41.6 | 42.9 | 87.0/93 | 93 | 63.0/63 | 3338/3032 | 3562 | 38 | 0 | 62 | 38 | 755 | 181 | 2986 | 17013 |
| burst3 | 8 | 41.8 | 43.7 | 89.2/93 | 93 | 63.0/63 | 3357/2980 | 3512 | 38 | 0 | 88 | 12 | 684 | 137 | 2217 | 17095 |
| burst4 | 8 | 41.6 | 44.3 | 86.0/92 | 93 | 63.0/63 | 3358/3016 | 3450 | 38 | 0 | 88 | 12 | 595 | 78 | 2430 | 17132 |
| burst5 | 8 | 41.4 | 44.9 | 87.5/92 | 93 | 63.0/63 | 3338/3005 | 3250 | 38 | 0 | 88 | 12 | 852 | 304 | 2133 | 16991 |
| burst6 | 8 | 41.4 | 41.1 | 87.1/92 | 92 | 63.0/63 | 3338/3029 | 3425 | 38 | 0 | 88 | 12 | 679 | 224 | 1577 | 17025 |
| burst7 | 8 | 41.4 | 41.6 | 86.9/92 | 92 | 63.0/63 | 3362/3053 | 3338 | 38 | 0 | 88 | 12 | 866 | 269 | 1396 | 17064 |
| burst8 | 8 | 41.4 | 42.3 | 90.1/93 | 93 | 63.0/63 | 3400/3088 | 3300 | 38 | 0 | 62 | 25 | 678 | 189 | 1519 | 17147 |
| mixed | 120 | 32.4 | 32.4 | 91.3/93 | 93 | 63.0/63 | 3199/2280 | 3958 | 38 | 0 | 0 | 93 | 46072 | 23318 | 58877 | 8748 · glmark2 3920 fps (12 scenes) · GT 404 MHz · GFXW 2.02 |

bursts bogo/s: mean 17031, min 16775, max 17147 (16775, 17013, 17095, 17132, 16991, 17025, 17064, 17147)

profiles seen: ['balanced']; no_turbo values: [0.0]; PL1/PL2 msr: [(200.0, 48.0)]; mmio: [(38.0, 45.0)]; tcc: [8.0]
