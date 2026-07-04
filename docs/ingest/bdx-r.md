# Ingest — BDX-R (Isaac Lab + MjLab)  [§0.6]

Two upstream repos by the BDX-R project; **BDX-A is built on these** (operator
directive: reuse and IMPROVE, don't rebuild). Vendored read-only at pinned SHAs
via `scripts/fetch_upstream.sh`. Licenses cleared (MIT / Apache-2.0, see LICENSES).

## BDX-R-IsaacLab  (MIT, @62f0ba6)
- **Assets:** `data/Robots/BDXR/URDF.urdf` (77 links, 80 STL meshes — full printable
  BD-X: hip/knee/ankle motors, leg covers, head, ears, eyes, face, battery) +
  `BDX-R.usd`. This is the correctly-proportioned model (hips on the SIDES of a
  compact body — fixes our hand-built primitive's under-leg hips).
- **Kinematics:** 10 revolute DOF = 5/leg — `{L,R}_Hip_Yaw, _Hip_Roll, _Hip_Pitch,
  _Knee, _Ankle`. Matches the real BDX (no ankle roll). **Head is present in the
  mesh but NOT actuated** (README: "integration of a head is a future goal").
- **Actuators:** `DelayedPDActuatorCfg`, full-scale real-BDX values — stiffness
  ~79 (hip/knee) / ~16.6 (ankle), effort **42 N·m** (hip/knee) / 11.9 (ankle).
  → **Robstride-class, NOT STS3215.** Build budget < $3000, Jetson Orin Nano.
- **Scale:** base init z = 0.33 m, base-height reward target 0.30846 → ~0.66 m
  full-scale droid.
- **Training:** Isaac Lab manager-based `Bdxr-Velocity-Flat-v0`; obs (imu ang vel,
  gravity, cmd, joint pos/vel, prev action), `BDXRRewards` (termination -200,
  base-height L2, feet-air-time, tracking), friction/mass DR. Runs in the 2.3.2
  container. Install: `pip install -e source/BDXR`; `train.py --task=Bdxr-Velocity-Flat-v0 --headless`.

## BDX-R-MjLab  (Apache-2.0, @079acd2)
- **Assets:** `robots/bdxr/xmls/bdxr.xml` (full) + `bdxr_legs.xml` (legs). Native
  **MuJoCo** — runs on the Spark host, no container. Directly usable for our §5
  settle / §6.5 sim2sim / eval + on-host iteration.
- **Tasks:** `velocity`, `tracking`, and **`imitation` / `imitation_legs`**
  (reference-motion tracking). Imitation is the path to *movie-accurate motion*
  (learn to move like a reference gait), beyond plain velocity walking.
- Same 10-DOF legs kinematics + constants (`bdxr_constants.py`).

## How we reuse + improve (BDX-A)
- **Adopt** the BDX-R geometry/URDF-USD-MJCF (correct structure) + training
  pipelines (Isaac velocity, MjLab velocity/imitation) — subclass/extend in our
  tree, never edit vendored copies.
- **Improvements we add:** active 3-DOF neck (D-005 — both upstreams stub the
  head); full component integration (Jetson/battery/fan/sensors/cameras/wiring,
  Qi-15W wireless charging); print/QA + swap schedule; our orchestrator/gates.
- **OPEN DECISION (blocks actuator model + BOM + torque):** physical target —
  adopt BDX-R **full-scale + Robstride** (accurate/strong, ~$3k, long lead) vs the
  spec's **0.6x + STS3215** (D-001, ~$400, printable now). Scale-agnostic reuse
  (geometry, training structure) proceeds regardless; the actuator/scale finalise
  waits on this. See DECISIONS D-007 (to be logged once chosen).

## Rocky
No comparable upstream exists (operator confirmed). Rocky stays our own design —
we own it and IMPROVE independently (adding front-leg manipulators, D-008).
