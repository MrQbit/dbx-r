# WEEKEND_RUNBOOK.md — Human pre-flight & swap schedule (Martin)

## T-0 pre-flight checklist (Friday morning, ~30 min) — ALL must pass before `make weekend`
- [ ] Train host = DGX Spark: `nvidia-smi` shows driver ≥ 580.95.05 and CUDA 13; `uname -m` = aarch64; ≥ 150 GB free on the repo volume.
- [ ] Docker works and can pull from NVIDIA registries (`docker run --rm --gpus all` smoke) — the pipeline's primary path is the Isaac Lab 2.3.x ARM container.
- [ ] Spark set to never sleep; on wired ethernet if possible (Isaac assets + container pull are tens of GB).
- [ ] Internet OK; NVIDIA pip index reachable (setup script will verify, but a dead network at hour 0 wastes the weekend).
- [ ] Power/thermals: machine set to never sleep; GPU fans unobstructed; UPS if you have one.
- [ ] Printer: P2S updated, PEI plate clean (IPA), nozzle 0.4 hardened; AMS 2 Pro loaded — Slot1 PETG (structural color), Slot2 PLA Matte Ash Grey, Slot3 spare PETG; TPU on EXTERNAL spool holder; AMS drying ON for PETG.
- [ ] Filament stock: ≥ 3 kg PETG, ≥ 2 kg PLA Matte, ≥ 0.5 kg TPU 95A.
- [ ] Bambu Handy notifications ON (you are the print-failure watchdog; the agent cannot see the printer).
- [ ] Hardware NOT needed this weekend (order now for next week): 25× Feetech STS3215 12 V (10+15), 2× Waveshare bus servo adapter, 2× BNO055, 1–2× Jetson Orin Nano 8 GB (**legacy 2019 Jetson Nano will NOT work** — spec §0.5), MAX98357A + 40 mm driver, 2× 3S ≥2600 mAh packs, XT30s, M2/M3 heat-set inserts, 625ZZ bearings ×~14, buck converters 5 V/5 A ×2, INA219 ×2.
- [ ] Optional override window closes now: `bdx_a/design/params.yaml: tier` (default `sts3215_0p6x`).

## Launch
```
git clone https://github.com/MrQbit/dbx-r.git duet && cd duet
nohup make weekend > weekend.out 2>&1 &
tail -f orchestrator/heartbeat.log
```

## Printing (the only human loop)
1. When `gate-2` goes green (expect Friday afternoon), slice per `*/print/print_manifest.yaml` in Bambu Studio and start **plate #1 = coupons** (<1 h).
2. Check coupon fits (servo drops in snug, insert boss OK, bearing press-fit). If off: edit ONE number in `common/cad_lib/standards.py` clearances, run `make regen-cad`, re-print coupons. (This is the single sanctioned human edit.)
3. Then follow `print/SWAP_SCHEDULE.md`: Rocky plates first, longest plates queued at ~22:00 Fri/Sat/Sun so overnight windows are used. Realistic expectation: **Rocky fully printed + BDX-A structure by Monday; BDX-A shells spill into next week.** One P2S cannot print both robots in 60 h — the schedule optimizes, it doesn't defy physics.

## Monitoring from your phone (optional, 2 min/day)
`tail -20 orchestrator/heartbeat.log` via SSH; TensorBoard on `:6006` if you care. Do not intervene in software otherwise — every stage self-retries and resumes.

## Monday
Read `docs/reports/WEEKEND_REPORT.md` → follow its "human next actions". First-motion protocol (tethered stand → steps → walk) happens only after hardware arrives and bench HIL passes; it is deliberately NOT part of the unattended weekend.
