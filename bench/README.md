# Bench protocol

Every configuration is measured with the same script so runs are comparable:

```sh
OUT=results/<name>; mkdir -p $OUT; echo "config: …" > $OUT/config.txt
pkexec bench/start-monitor.sh $OUT 1250      # root: 1 Hz sysfs/MSR CSV + turbostat (self-tests first)
bench/run-workloads.sh $OUT 600 120           # user: waits for monitor.csv, then the phases
python3 bench/summarize.py $OUT               # per-phase table -> $OUT/summary.md
```

Phases (`markers.csv`): 30 s idle → 600 s all‑core `stress-ng --cpu 0 --cpu-method matrixprod`
→ 120 s cooldown → 8 × (8 s burst, 22 s idle) → 120 s mixed (`stress-ng --cpu 4` +
`glmark2-wayland --run-forever` 800×600). Throughput = stress‑ng bogo‑ops/s
(real time); GPU = glmark2 FPS.

`monitor.csv` columns: package watts (RAPL energy, root), package/hottest core °C,
max/avg MHz, fan rpm, platform_profile, pwm1_enable, no_turbo, EPP, governor,
PL1/PL2 (MSR and MMIO), TCC offset, core/package throttle counters and time,
GT MHz, AC, `PERF_LIMIT_REASONS` low 16 bits (0x400 PL1, 0x800 PL2, 0x2 thermal,
0x1 PROCHOT), SEN1..SEN8. Without root the power/MSR/turbostat columns are empty.

Other scripts: `odvp-probe.sh` (profile → ODVP0 mapping; stop `perfctl-fand`
first if it is in curve mode), `apply-b3.sh` / `apply-b4.sh` (configuration steps,
root), `monitor.py` (can run unprivileged).

Unattended runs: `wait-and-run.sh OUT` (user side) waits until a root monitor
writes `OUT/monitor.csv`, then runs the workloads; `night-batch.sh` (B4 + first
B6 attempt) and `b6-batch.sh` (override vault measurement) are the root side,
launched once with `pkexec` so one password covers configure + measure + revert.
