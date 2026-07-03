# PROJECT DUET — Master Build Specification **v2.0 (UNATTENDED-RUN EDITION)**
## BDX-A (bipedal, BDX-R–derived) and ROCKY-5 (pentaradial Eridian, 50% scale)

**Spec version:** 2.1 (DGX Spark edition) · **Date:** 2026-07-02 · Supersedes v1.0/v2.0 entirely.
**Executor:** Claude Code (Sonnet), fully autonomous — see companion `CLAUDE.md`.
**Human:** Martin. Human touches the system ONLY at the pre-flight checklist (`WEEKEND_RUNBOOK.md`) and at printer plate swaps. **No stage in this spec may block on human input.**

---

# 0. EXECUTION CONTRACT

0.1 **Unattended mode.** The entire pipeline runs from one command: `make weekend`. Every decision that v1.0 deferred to a human is now DECIDED in this document. The agent MUST NOT prompt, MUST NOT wait, MUST NOT leave `TODO(HUMAN)` in any file consumed by the pipeline. If genuinely stuck after the retry policy (§9), it isolates the failing track, logs `FAILURE-<track>.md`, and continues the other track.

0.2 **Determinism of interpretation.** Where this spec gives a number, that number is law. Where it gives a fallback table (Appendix A), the fallback is authoritative the moment a network fetch or repo ingest fails — no judgment calls. Where two sections conflict, the higher section number wins (later = more specific).

0.3 **Everything is code.** No GUI CAD, no manual mesh edits, no notebook-only steps. Fresh clone + `make all` reproduces every artifact except trained checkpoints and sliced 3MFs (Bambu Studio step is human, but its inputs — STL + `print_manifest.yaml` — are generated).

0.4 **Decision log.** Any deviation → `docs/DECISIONS.md`, format `D-###: what | why | impact`. Deviations may not weaken a MUST.

0.5 **Compute topology (DECIDED — resolves the Jetson question):**
- **Training host: NVIDIA DGX Spark** (GB10 Grace Blackwell, **aarch64**, 128 GB unified memory, DGX OS, driver 580.95.05+, **CUDA 13**). ≥ 150 GB free disk. ALL generation + training happens here. Consequences the agent MUST respect: cu13 PyTorch wheels only; no x86-only pip packages; some Isaac Lab features are unsupported on Spark (none we need — locomotion RL is supported); export `LD_PRELOAD=$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1` for every Isaac process.
- **Robot compute:** **NVIDIA Jetson Orin Nano 8 GB (JetPack 6.x)**, one per robot when operated simultaneously; a **single** Orin Nano may serve both robots alternately — the runtime is one image with two hardware profiles selected by `ROBOT=bdx_a|rocky` env var. The **legacy 2019 Jetson Nano is NOT supported** (Python 3.6 / JetPack 4 cannot run our ONNX runtime stack); if only legacy Nanos are on hand, this is a pre-flight FAIL, not something to engineer around.
- Inference cost is trivial (MLP ≤ 0.2 M params @ 50 Hz); the Orin also hosts Rocky's audio engine. GPU on Jetson unused in v1 — CPU ONNX Runtime (aarch64) is REQUIRED for portability.

0.6 **Ingest step (bounded, non-blocking).** Before P1, spend ≤ 45 min total fetching and summarizing: BDX-R repos (`github.com/BDX-R/BDX-R-IsaacLab`, `.../BDX-R-MjLab`), `kaydenknapik.com/report.pdf`, arXiv 2501.05204, `github.com/apirrone/Open_Duck_Mini` (+ `_Runtime`). Write `docs/ingest/<name>.md` (≤ 150 lines each, numbers cited). Any fetch failure → use Appendix A and log D-###. Ingest may REFINE Appendix A values; it may not add new blocking work.

0.7 **Licensing.** Record every upstream license in `docs/LICENSES.md` before reuse. No license file ⇒ all-rights-reserved ⇒ re-derive parametrically, copy nothing. Both robots: personal, non-commercial. No Disney/Lucasfilm trade dress published.

---

# 1. TOOLCHAIN — DGX Spark / aarch64 (install via `scripts/setup_env.sh`, idempotent, asserts every version)

**Primary install path (DECIDED): Isaac Lab official multi-arch Docker image, ARM variant, pinned to the newest 2.3.x tag available at setup time** (record exact tag + digest in `docs/DECISIONS.md`). The repo is bind-mounted into the container; all Isaac/RL stages run inside it. This is chosen over source builds for unattended determinism.
**Fallback (only if the image pull fails or is broken): NVIDIA dgx-spark-playbook source path** — GCC 11 via update-alternatives, git-lfs, clone Isaac Sim, `build.sh` → `_build/linux-aarch64/release` (~10–15 min), symlink `_isaac_sim` into an Isaac Lab clone pinned to the matching `release/2.3.x` branch, `./isaaclab.sh --install rsl_rl`. Verify with a headless smoke launch. Log D-### with the failure reason.

| Component | Pin | Notes |
|---|---|---|
| Train host OS | DGX OS (as shipped) | do NOT dist-upgrade during the run |
| CUDA / driver | CUDA 13, driver ≥ 580.95.05 | pre-flight assert via `nvidia-smi` |
| Python | as required by Isaac Lab 2.3.x (in-container) | outside container: 3.11 via `uv` for CAD/audio/tests |
| Isaac Sim | version bundled with the pinned Isaac Lab 2.3.x image | `OMNI_KIT_ACCEPT_EULA=YES` + privacy consent file |
| Isaac Lab | **2.3.x** (newest patch tag at setup; frozen after G0) | Spark-supported since 2.3.0 |
| RL | rsl_rl as vendored by Isaac Lab 2.3.x (3.x API) | PPO only; use the vendored API, do not pin an older rsl_rl |
| Env vars (every Isaac process) | `LD_PRELOAD=$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1`, `--headless` | plus asset caching enabled to avoid re-downloads |
| MuJoCo | newest 3.x with a linux-aarch64 wheel (record pin) | sim2sim |
| CAD | build123d 0.9.x + trimesh 4.x + numpy-stl | **aarch64 contingency (ordered, automatic):** (1) pip wheels; (2) if `cadquery-ocp` has no linux-aarch64 wheel → micromamba env with conda-forge `ocp` + pip build123d on top; (3) if both fail → degrade CAD backend to `manifold3d`+trimesh CSG (dovetails and rock displacement still work; log D-###, mark cosmetic fidelity DEGRADED) |
| URDF→MJCF | `urdf2mjcf` (pin latest release at setup, record hash) | plus hand-written actuator defaults |
| URDF→USD | Isaac Lab `convert_urdf.py` script, headless | |
| Export | ONNX opset 17, onnxruntime 1.18+ (x86) / onnxruntime aarch64 wheel (Jetson) | |
| Jetson | JetPack 6.x, Python 3.10 | deploy stage generates `deploy/jetson_install.sh` |
| Version-check gate | `make gate-0` runs `scripts/verify_env.py`: imports each package, launches Isaac Sim headless smoke (`--headless`, create+destroy stage, < 5 min timeout) | |

Version rule: whatever Isaac Lab 2.3.x patch + image digest G0 records is FROZEN for the weekend. No mid-run upgrades, no jumping major versions, even to fix a bug — work around or degrade instead. Note the train host and Jetson are both aarch64: the exact onnxruntime wheel and `ObsSpec` path used in `mujoco_eval` can be smoke-tested on the Spark and shipped to the Jetson unchanged.

---

# 2. REPOSITORY LAYOUT (create exactly; unchanged from v1 except `orchestrator/` and no `runtime` split by board)

```
duet/
├── Makefile                        # all, weekend, gate-0..gate-9, clean
├── CLAUDE.md                       # agent operating manual (companion file)
├── WEEKEND_RUNBOOK.md              # human pre-flight + swap schedule
├── orchestrator/
│   ├── weekend.py                  # DAG runner (§9): stages, timeouts, retries, resume
│   └── stages.yaml                 # the DAG definition (single source of truth)
├── docs/{DECISIONS.md, LICENSES.md, ingest/, assembly/, bom/, reports/}
├── common/{cad_lib/, description_gen/, export/, runtime_core/}
├── bdx_a/{design/params.yaml, cad/, description/, isaac/, mujoco_eval/, print/}
├── rocky/{design/params.yaml, cad/, description/, isaac/, mujoco_eval/, audio/, print/}
├── runtime/                        # ONE Jetson image for both robots (profiles: bdx_a, rocky)
│   ├── profiles/{bdx_a.yaml, rocky.yaml}
│   └── deploy/jetson_install.sh
└── tests/                          # pytest suites gate every stage
```

---

# 3. ROBOT A — **BDX-A** (DECIDED: single tier, buildable this weekend)

## 3.1 Decision D-001 (pre-made)
v1's Tier 1 (Robstride, ~$2–3k, long lead time) is **deferred to v2 hardware**. **BDX-A v1 = 0.6× scale, 10× Feetech STS3215 (12 V) bus servos** — the Open-Duck-proven class of build, printable and affordable now. All geometry is parametric from `params.yaml`; the Robstride upgrade later is a params + actuator-model change, no re-architecture. This is the single largest judgment call in this spec — Martin may override it **before** launch by editing `bdx_a/design/params.yaml: tier: robstride`; after launch it is frozen.

## 3.2 Canonical dimensions (0.6× values — these are what gets built; all in `params.yaml`)
| Param | Value |
|---|---|
| Standing height (legs extended, incl. static head) | 420 mm |
| Hip yaw-axis spacing | 108 mm |
| Thigh (hip-pitch→knee) | 96 mm |
| Shin (knee→ankle) | 96 mm |
| Foot L×W | 84 × 42 mm, 3 mm TPU sole |
| Total mass budget | ≤ 2.6 kg incl. battery |
| Battery (DECIDED) | 3S Li-ion 11.1 V ≥ 2600 mAh with BMS + XT30; bay sized 70×38×20 mm with ±2 mm foam tolerance |

## 3.3 DOF (10) — joint names are law; order below = obs order = action order = servo IDs 1–10
`l_hip_yaw, l_hip_roll, l_hip_pitch, l_knee, l_ankle_pitch, r_hip_yaw, r_hip_roll, r_hip_pitch, r_knee, r_ankle_pitch`
Limits (rad): hip_yaw ±0.6 · hip_roll ±0.5 · hip_pitch −1.6…0.6 · knee 0.0…2.2 · ankle ±1.0.
Torque check (generated `docs/reports/torque_bdx_a.md`): worst-case single support, CoM offset 30 mm, knee 60°; STS3215 continuous ≈ 1.2 N·m, stall ≈ 2.9 N·m @ 12 V — requirement: continuous ≥ 1.8× static, stall ≥ 3×. If CAD mass makes this fail → reduce shell mass (infill/walls) first, then shorten links 5% steps; log D-###.

## 3.4 Head/torso: static shells v1; 2-DOF neck stubbed as `fixed` joints in URDF (names `neck_pitch`, `neck_yaw`) so v2 needs no mesh rework. Eye LEDs: 2× WS2812 on a 3-pin lead, driven by Jetson GPIO — cosmetic, non-blocking (skip on any driver issue, log D-###).

## 3.5 Electronics (identical bus architecture for both robots)
Jetson Orin Nano 8 GB → **Waveshare Bus Servo Adapter (A) via USB** (`/dev/ttyUSB0`, 1 Mbps) → STS3215 daisy chain (IDs per §3.3) · **BNO055** IMU on Jetson I²C bus 7 (pins 3/5), mounted at torso CoM, +X forward — orientation constant lives in ONE file: `runtime/profiles/*.yaml` · Power: 3S → servo rail (fused 10 A, physical E-stop switch) + 5 V/5 A buck → Jetson (barrel) · INA219 on servo rail for current logs. Netlist in `runtime/profiles/bdx_a.yaml`; wiring SVG generated from it.

---

# 4. ROBOT B — **ROCKY-5** (pentaradial Eridian, 50% scale) — unchanged geometry from v1, restated as law

Radially symmetric, 5 identical limbs at 72°, no eyes, mineral carapace, chord voice. 50% of a Labrador-scale reference:
carapace circumscribed Ø **160 mm**, dome height **110 mm**, limb reach **180 mm** (coxa 40 / femur 70 / tibia 70), neutral stance height **130 mm**, footprint Ø **310 mm**, mass ≤ **2.2 kg** incl. battery (same 3S pack as §3.2).

**DOF (15):** per limb i∈0..4 (limb 0 = heading): `leg{i}_coxa_yaw` ±0.9 · `leg{i}_femur_pitch` −1.4…1.0 · `leg{i}_tibia_pitch` −0.3…2.0. Servo IDs = 3i+1, 3i+2, 3i+3. One printed limb design, qty 5 — the URDF generator instances limb 0 at 72° increments; a symmetry unit test asserts identical link inertias across limbs.

**Structure:** pentagonal PETG core plate (5 coxa pockets, Jetson tray with 15 mm clearance + vent slots, battery bay per §3.2, IMU at centroid) · 2-piece PLA carapace with procedural simplex-noise rock displacement (amp 1.2 mm, freq 0.08 /mm, applied to outer faces only, re-meshed, must still pass watertight QA) · TPU 95A hemispherical feet Ø 18 mm · 5 slotted sound grilles in skirt over 40 mm full-range driver + MAX98357A I2S amp (Jetson I2S pins per profile) · INMP441 mic reserved v2.

Torque: femur worst case ≈ 0.52 N·m vs STS3215 ≥ 1.2 N·m continuous → PASS by construction; report still generated.

---

# 4.5 CAD AUTHORING RULES & GENERATED DELIVERABLES (both robots)
1. One Python file per printable part in `<robot>/cad/parts/`, exporting `part() -> build123d.Part` + `PartMeta` (name, material, qty, print-orientation quaternion, insert list, mating clearances). Assemblies composed in `cad/assembly.py`; interference check (trimesh boolean, tolerance 0.05 mm) is a G2 test.
2. Fits, inserts, bearings, walls, fillets: Appendix A.4 — constants imported from `common/cad_lib/standards.py`, never re-typed.
3. Generated deliverables (G2): `docs/bom/<robot>.csv` (printed parts + COTS with qty, est. unit cost, link column left blank for human), `docs/assembly/<robot>.md` step guides with exploded-view PNG renders (build123d/trimesh offscreen), wiring SVG from the profile netlist, mass-properties report.

# 5. DESCRIPTION PIPELINE (`common/description_gen`) — deterministic, tested

`params.yaml` → dataclasses → **URDF** (visual meshes: decimated STL ≤ 20 k tris/link; collision: primitives ONLY — boxes/capsules/spheres; never trimesh) → **MJCF** (converter + injected `<default>` actuator blocks) → **USD** (Isaac Lab headless converter). Inertias from CAD mass properties (build123d, material densities: PETG 1.27, PLA 1.24, TPU 1.21 g/cm³, servo modeled as 60 g box 45.2×24×32 mm with datasheet CoM).
Tests (gate G3): URDF loads in `yourdfpy`, MuJoCo, Isaac; all inertia tensors positive-definite and within 10× of a uniform-density estimate; 5 s zero-command settle in MuJoCo ends with |base lin vel| < 0.05 m/s and no self-collision penetration > 1 mm.

---

# 6. RL — Isaac Lab v2.1.0, manager-based envs, 50 Hz policies

## 6.1 Tasks
`Duet-BdxA-Flat-v0`, `Duet-BdxA-Rough-v0`, `Duet-Rocky-Flat-v0`, `Duet-Rocky-Rough-v0`. Pattern: Isaac Lab `Velocity-Flat-H1-v0` (BDX-A) and `Velocity-Flat-Anymal-C-v0` (ROCKY-5) reference configs, with our robots and reward mods. sim dt 1/200 s, decimation 4. Envs: start 4096. Memory is not the constraint on Spark (128 GB unified) — GPU throughput is. After 200 warm-up iters, the orchestrator measures steps/sec at 4096 and once at 8192; keep whichever is faster in wall-clock terms and log it. On OOM or driver fault, fall back 4096→2048→1024 (§9).

## 6.2 Obs/Action (both robots; N=10 / N=15)
Obs: base ang vel (3) ×0.25 · projected gravity (3) · velocity command (3) · joint pos − default (N) · joint vel (N) ×0.05 · previous action (N). Noise: Appendix A.
Action: q_target = q_default + 0.25 × a. Actuator model (STS3215): implicit PD kp 17, kd 0.5, effort clamp 2.5 N·m, vel clamp 5 rad/s (ingest may refine ±30%; outside that, keep Appendix A).

## 6.3 Rewards — exact terms and weights in Appendix A (fallback-authoritative). Character shaping:
- **BDX-A:** stage 1 plain walking (Appendix A.1). Stage 2 (auto-starts when stage-1 success metric holds for 500 consecutive iters): add gait-phase strut reward w=0.3, feet-air-time target 0.35 s.
- **ROCKY-5:** Appendix A.2 = tracking core + pentapod wave-gait phase reward (5 oscillators, offsets 2πi/5, w=0.6) + height-hold 130±10 mm (w=0.4) + doubled flat-orientation penalty (gliding carapace) + 2nd-order action-rate −0.005 + omnidirectional commands (vx,vy uniform on 0.35 m/s disk, ωz ±1.0).
- DR (both): friction 0.4–1.1, base mass ±15%, motor strength 0.85–1.15, obs latency 0–20 ms, pushes Δv≤0.4 m/s every 5–10 s, restitution 0–0.1.

## 6.4 PPO (rsl_rl): MLP [512,256,128] ELU · rollout 24 · adaptive lr 1e-3 (KL 0.01) · γ .99 λ .95 · clip .2 · entropy .005 · 5 epochs / 4 minibatches · checkpoint every 250 iters, keep last 5 + best.
**Budgets (hard, orchestrator-enforced):** each flat run ≤ 6 h wall or 15 k iters; each rough run ≤ 10 h or 30 k iters. **Success:** mean lin-vel tracking error ≤ 15% at |v|≤0.5 m/s (Rocky ≤0.35) over 20 s eval, falls < 1% per 1000-env batch. **If budget expires below success:** keep best checkpoint, mark track `DEGRADED`, continue pipeline (a degraded policy still gates sim2sim and deploy packaging).

## 6.5 Sim2sim & export: ONNX export + parity test (MSE < 1e-5 vs torch on 1000 random obs) → MuJoCo replay 60 s × 3 command settings without fall (DEGRADED policies: 30 s standing counts). One shared `ObsSpec` module is imported by sim, eval, and runtime — obs construction exists in exactly one place.

## 6.6 Runtime (Jetson, `runtime/`): 50 Hz loop: read BNO055 + servo positions → ObsSpec → onnxruntime → clamp → bus write. Watchdog: torque-off if loop > 40 ms, |roll|/|pitch| > 50°, servo temp > 65 °C, or E-stop. Boot to idle-safe (torque off) always. Calibration CLI writes per-servo zero offsets to `calib.yaml`. First-motion protocol (human, post-weekend): tethered stand → in-place steps → slow walk; both torsos get a printed tether hook.

---

# 7. ROCKY VOICE — unchanged from v1, now with hard numbers
Additive synth: partials [1, .5, .33, .2], inharmonicity +0.3%/partial, ADSR 30/80/0.7/150 ms, vibrato 5 Hz ±6 cents, register G2–G4, 22.05 kHz mono. Codec: A-minor pentatonic ×2 octaves (10 pitches); glyph = 2–4-note chord + duration ∈{120,240,480 ms}; gaps 180/600 ms; mapping = SHA-1(token) indexed tables in `codec.yaml`; reserved motifs: greeting (ascending triad), query (rising fifth), alarm (tritone ×3), "Amaze" (fixed 4-note figure, documented). Tests (G7): encode→FFT-decode round trip ≥ 99% at SNR 20 dB (synthetic noise); render 5 demo WAVs to `docs/reports/audio/`; on-Jetson latency test deferred to deploy (not weekend-blocking).

---

# 8. PRINT PACKAGE — Bambu P2S Combo (human loads plates; everything else generated)

- Safe envelope **250×250×250 mm**; QA (`common/export/qa.py`) asserts watertight, positive volume, envelope fit, min-wall (2.4 structural / 1.6 cosmetic), and auto-splits oversize shells with generated dovetails. QA failure fails G2 — never discovered at the slicer.
- Materials: structural PETG (0.2 mm, 4 walls, 40% gyroid) · shells PLA Matte (0.16 mm, 3 walls, 12%) · feet TPU 95A (100% ≤3 mm; **external spool**, not AMS).
- `print/print_manifest.yaml` per robot: for each STL — qty, material, color, orientation quaternion, supports (type), plate group, **estimated minutes** (from trimesh volume × material factor; label ±30%), and a **plate sequence** ordered so the two longest plates land on Friday-night and Saturday-night unattended windows. Include `coupons` plate (servo pocket + insert boss + bearing seat fit tests, < 60 min) as plate #1.
- Honesty constraint the schedule must encode: one P2S cannot print both robots fully in one weekend. Priority order (DECIDED): coupons → ROCKY-5 complete → BDX-A legs/torso structure → BDX-A shells. The manifest computes expected completion per plate and writes `print/SWAP_SCHEDULE.md` for the human.

---

# 9. ORCHESTRATOR — `make weekend` (this is what runs unattended)

`orchestrator/weekend.py` executes `stages.yaml` as a DAG with per-stage: `cmd`, `timeout_min`, `retries` (default 2, exponential backoff), `on_fail` (`halt_track` | `degrade` | `skip`), `artifacts` (existence-checked), `resume_key` (stage skipped if artifacts valid — safe re-runs). Global rules: fully non-interactive (`DEBIAN_FRONTEND=noninteractive`, EULA env vars, `--headless`, `--yes` everywhere); disk guard (abort new training if < 40 GB free); GPU guard (env-count fallback §6.1); heartbeat line to `orchestrator/heartbeat.log` every 60 s; final `docs/reports/WEEKEND_REPORT.md` (per-stage status, metrics, checkpoints, next human actions).

**DAG (summary; stages.yaml is normative):**
G0 env-setup(240m) → ingest(45m, on_fail:degrade→AppendixA) → [bdx_a-track ∥ rocky-track], each: cad(60m) → mesh-qa(15m) → descriptions(30m) → sim-settle-test(20m) → print-package(30m) → train-flat(360m/§6.4) → train-rough(600m) → export-onnx(15m) → mujoco-eval(30m) → package-deploy(20m). Tracks are independent: one halting never stops the other. GPU stages serialize (lock file); order: bdx_a-flat, rocky-flat, bdx_a-rough, rocky-rough — flat policies for BOTH robots exist before any rough training spends budget.

# 10. GATES (unchanged numbering; all are `make gate-N`, all machine-checkable, none human)
G0 env · G1 params complete & frozen (zero TODO, torque PASS) · G2 CAD+QA+BOM+renders · G3 descriptions+settle · G4 training success-or-DEGRADED with artifacts · G5 ONNX parity+MuJoCo · G6 runtime HIL **stub** (loopback against a servo-bus simulator; real-bench HIL is post-weekend) · G7 audio · G8 print package + swap schedule · G9 weekend report complete.

# 11. NON-GOALS (v1): vision, autonomy, BDX-A neck articulation, Rocky manipulation, outdoor terrain, speech understanding, Robstride tier, mic input, on-Jetson training.

---

# APPENDIX A — FALLBACK-AUTHORITATIVE NUMBERS (used verbatim if ingest fails/underspecifies)

**A.0 Obs noise:** ang-vel σ 0.2 · gravity 0.05 · joint pos 0.01 · joint vel 1.5 · latency DR 0–20 ms.
**A.1 BDX-A rewards:** track_lin_vel_xy exp(σ=0.25) w=1.5 · track_ang_vel_z exp w=0.75 · lin_vel_z L2 −2.0 · ang_vel_xy L2 −0.05 · torques L2 −1e-5 · action_rate −0.01 · feet_air_time w=0.5 (target 0.35 s) · undesired_contacts (thigh, torso) −1.0 · flat_orientation −2.5 · joint_limit −5.0 · termination −200 (base contact or |roll/pitch|>1.2 rad).
**A.2 ROCKY-5 rewards:** A.1 core with flat_orientation −5.0, plus wave-gait phase w=0.6 · height-hold (130±10 mm) w=0.4 · action_rate_2nd −0.005; commands per §6.3; termination adds carapace contact.
**A.3 STS3215 model:** kp 17, kd 0.5, effort 2.5 N·m, vel 5 rad/s, armature 0.01, friction 0.03.
**A.4 Fits:** press 0.10 / slide 0.20 / loose 0.35 mm per side · M3 heat-set boss Ø4.0×5.8 mm · M2 shells · 625ZZ bearings at passive pivots · min walls 2.4/1.6 mm · fillets ≥ R2 on load paths.
