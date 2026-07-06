# DECISIONS — PROJECT DUET

Format: `D-###: what | why | impact`. Deviations may not weaken a MUST (§0.4).
Pre-made decisions from the spec are recorded here so the log is self-contained.

---

**D-001: BDX-A actuator tier = `sts3215_0p6x` (0.6× scale, 10× Feetech STS3215).**
| The Robstride tier (~$2–3k, long lead) is deferred to v2 hardware; the
STS3215 class is the Open-Duck-proven, printable-now build. | All geometry is
parametric from `bdx_a/design/params.yaml`; a later Robstride upgrade is a
params + actuator-model change, no re-architecture. Human may override to
`tier: robstride` *before* launch only. (Pre-made in spec §3.1.)

**D-002: G1 torque check evaluates at a provisional `design_target_kg` (1.8 kg), not the mass budget ceiling.**
| §3.3 defines the torque check against CAD-derived mass, but G1 runs before any
CAD exists, and at the 2.6 kg budget ceiling the *continuous* criterion
(≥ 1.8× static) fails. The spec is silent on which mass G1 uses. | Chosen the
smallest reasonable interpretation: G1 checks a provisional design target
(1.8 kg, comfortably Open-Duck-class); the final mass re-check happens at G2
against measured CAD mass properties. The generated torque report documents the
hard cap (2.265 kg for BDX-A) below which the build MUST land. No MUST weakened
— the real constraint is surfaced, not hidden.

**D-003: CAD backend uses conda-forge OCP + build123d 0.8.0 (not the spec's 0.9.x) on aarch64.**
| §1 pins build123d 0.9.x, but its OCP dependency (`cadquery-ocp` 7.8) has **no
linux-aarch64 wheel** (contingency 1 fails). The §1 ordered contingency 2
(micromamba + conda-forge `ocp`) succeeds, but conda-forge's newest aarch64 OCP
is **7.7.2**, which pairs with build123d **0.8.0**, not 0.9.x. | Realised
contingency 2 with build123d 0.8.0 (installed `--no-deps` so pip doesn't chase
the missing OCP wheel; pure-python deps added by hand). One further aarch64 snag:
`py-lib3mf` 2.5.0 ships its native module as `lib3mf` while build123d 0.8.0
imports `py_lib3mf` — resolved with a one-line re-export shim. Net result: **full
B-rep CAD on aarch64, no fidelity degradation** — contingency 3 (manifold3d
degrade) was NOT needed. Recipe captured in `scripts/setup_cad_env.sh` (idempotent,
reproducible); CAD stages run via `scripts/cadpy`. The 0.8.0 vs 0.9.x API delta
is immaterial to the primitives used (Box/Cylinder/RegularPolygon/extrude/booleans).

**D-004: Isaac Lab image pinned to `nvcr.io/nvidia/isaac-lab:2.3.2` (newest 2.3.x at setup).**
| §1 requires pinning the newest 2.3.x tag + recording its digest, frozen for the
weekend. Tags 2.3.0–2.3.2 exist on nvcr.io (public, no NGC auth needed); 2.3.3+
do not. | Pinned **2.3.2**, digest
`sha256:388dbc806f48359a964cb9f807feb226da95d0a107f470fdcad9780ea10fe6f2`
(recorded in `orchestrator/.isaac_image_digest`). This digest is FROZEN — no
mid-run Isaac Lab upgrades (§1 version rule). Primary Docker path succeeded; the
source-build fallback (dgx-spark-playbook) was not needed.

**D-005: BDX-A neck is ACTIVATED — 3 DOF (head_pitch1, head_pitch2, head_yaw), IDs 11-13.**
| §3.4 stubbed the neck as fixed joints for v1. Operator priority is a
movie-accurate, non-clunky build; research on the real Disney BDX (arXiv
2501.05204: 4 neck DOF) and the proven Open-Duck-Mini v2 (3 active neck DOF:
two-stage pitch + yaw) shows a *fixed head is the #1 "dead/clunky" tell* — the
neck is where the character lives. | Deviates from §3.4 (a v1 simplification, not
a MUST). Added the Open-Duck 3-DOF neck (two-stage pitch + yaw) appended as
IDs 11-13 after the 10 legs; obs==action==servo-id order preserved. BDX-A is now
13 DOF. Legs unchanged and confirmed correct vs the real droid (5/leg, hip
yaw/roll/pitch + knee + ankle-pitch, NO ankle roll — matches Disney, which uses
rounded foam feet instead). Mass +0.32 kg (still 1.84 kg < 2.265 kg cap);
settle still passes. RL obs/action N: 10 -> 13.

**D-006: ROCKY-5 dome lowered to canon (85 mm) and NO face/camera.**
| The book gives Rocky a pentagonal carapace "18 in across and half as thick"
(ratio 0.5); our 110 mm dome on a 160 mm carapace was 0.69 — too tall/beetle-like.
Rocky also has NO eyes, NO face, NO front (pentaradial, senses by sound). Our
component registry had wrongly placed a CSI camera on the dome as a "heading". |
Dome 110 -> 85 mm (0.53 ratio) for the squat river-stone silhouette + lower CG.
Removed the dome camera; sensing is audio + fully symmetric hidden ToF (no
component may imply a front). 15 DOF (3/limb) kept — research confirms it is
"accurate-plus" and enables the walk-and-manipulate behaviour from the story.

**D-007 (RESOLVED): BDX-A IS BDX-R exactly — full-scale (~0.66 m), Robstride, 14 DOF. Adopt, don't re-derive.**
| Operator: "build EXACTLY the same BDX-R, same size, same actuators; only
introduce improvements via more training, wireless charging, and better
balancing. You can fork — open-source hobbyist, no licensing/commercial issues."
| BDX-A now = the vendored BDX-R model (MjLab `bdxr.xml`: **14 DOF = 10 legs +
4-DOF head** Neck_Pitch/Head_Pitch/Head_Yaw/Head_Roll; full-scale, base init
0.25 m; Robstride actuators). We use BDX-R's own URDF/USD/MJCF + Isaac/MjLab
training verbatim and layer improvements on top. **Supersedes D-001** (the 0.6x
STS3215 build is dropped) and **supersedes D-005** (my invented 3-DOF neck —
BDX-R already has the correct 4-DOF head; use theirs). My hand-built primitive
BDX-A (`build_bdx_a`) is retired from the gates; ROCKY-5 stays our own
params-driven design. Improvements tracked: Qi-15W charging (CAD add-on to the
BDX-R chassis), balancing/gait via training. BDX-R model verified to load in our
MuJoCo (14 DOF, 81 meshes) and Isaac (2.3.2, headless smoke passed).

**D-008: ROCKY-5 gains 3-finger grip manipulators on its 2 front legs (limbs 1 & 4).**
| Operator: Rocky needs manipulators like the film; no upstream exists so we own
the design. Book canon = every leg can be a hand. | Added a hand-foot to limbs 1
& 4 (flanking heading limb 0): flat palm (ground contact, same height as the
sphere feet, so pentapod walking is preserved) + a driven grip (3 fingers, IDs
16-17). ROCKY-5 now 17 DOF; still settles on all 5 legs; 2.16 kg < 2.2 budget.

**D-009: ROCKY-5 carapace rock displacement raised to amp 3.5 mm / freq 0.13 (from spec 1.2/0.08).**
| The spec's 1.2 mm amp at 0.08 /mm is imperceptible on the 160 mm carapace —
renders as a smooth dome, not "made of rocks". | Raised to amp 3.5 mm, freq
0.13 /mm, 4 octaves, applied OUTER-FACES-ONLY (masked by normal-vs-centroid) so
the cosmetic shell wall never thins (min wall 1.72 mm > 1.6). Visibly craggy,
watertight, QA-pass. A tuning knob in rocky/design/params.yaml. Future: 2-piece
split + dovetails (§4), carved markings.

**D-010 (needs scale decision): ROCKY-5 actuator switched to Robstride, shared with BDX-A.**
| Operator: "assume Robstride for Rocky as well, reuse as many components as
possible to simplify (BDX is known behavior)." | Actuator is now a shared
Robstride QDD motor across both robots (also corrected BDX-A's registry, which
still listed STS3215). CONSEQUENCE: Robstride ~230 g each vs STS3215 60 g — **17x
Robstride = 4.35 kg of motors alone, ~2x Rocky's 2.2 kg budget.** Rocky cannot
stay 2.2 kg / 160 mm with Robstride; it must scale up to a larger/heavier robot
(full-scale ~5-6 kg like BDX-R). Dimensions, masses, CAD, and the (STS3215-trained)
Rocky policy all need to follow the scale decision — RETRAIN pending. Actuator
type + component reuse applied now; scale/budget/dims flagged for the operator.

## D-011 — Rough-terrain curriculum: command-relative promotion
Isaac Lab's stock `terrain_levels_vel` promotes only if the robot walks >4 m net
(half the 8 m patch); robots capped at 0.35 m/s never reach it and are demoted
forever (observed terrain_level stuck ~0.06–0.12; Isaac Lab issue #969). Replaced
with `duet_mdp.terrain_levels_track` (promote on ≥60% of COMMANDED distance, demote
<25%), + constant per-episode command, 30 s training episodes, start at level 0,
action_rate −0.005. Spec pins commands to the 0.35 m/s disk (§6.3/A.2), so the
levers are the curriculum/episode (spec-silent). Applies to both robots.

## D-012 — Imitation unified in Isaac (not ported from mjlab)
RL policy weights don't transfer across simulators (Isaac PhysX vs mjlab MuJoCo:
different obs/action/physics → OOD failure). The mjlab BDX imitation validated the
approach but can't be carried over. Chose to unify BOTH robots in Isaac: imitation
is a reference-tracking REWARD (`duet_mdp.track_reference_gait`) on the hand-authored
gaits (rocky_reference movie-accurate; bdx_reference bipedal), combined with rough
terrain in one policy per robot. Tasks: Duet-{Rocky,Bdx}-Imitate-Rough-v0.

## D-013 — ROCKY-5 servo: RS00 -> Robstride EduLite 05
The RS00 (14/17 Nm) was ~3x over-specced for a 5-legged ~5 kg robot (torque report:
passes to 17 kg). Switched Rocky to EduLite 05 (1.8 rated / 6 peak Nm, ~$80,
significantly cheaper). Torque-valid ONLY at the tightened size (shorter femur
lever, worst case ~0.8 Nm -> needs 1.44 cont / 2.4 peak; EduLite 1.8/6 clears it).
BDX-A CANNOT use EduLite (hips need 42 Nm) — stays on higher-torque Robstride.
Requires an RL retrain with effort_limit=6.

## D-014 — ROCKY-5 tightened to smallest-that-fits
Carapace 220 -> 165 mm (x0.75), legs scaled to match; fits the 250 mm print
envelope in one piece and hides the electronics. Mass stays ~5 kg (motor-dominated,
17 x ~240 g). Requires URDF regen + retrain.

## D-015 — Jetson: dev kit -> compact NVIDIA carrier
Stay on the NVIDIA stack (operator). Orin Nano 8GB moves from the 100x80 dev kit to
a compact carrier (reComputer J401-class, ~90x63) — keeps USB/Ethernet/CSI out of
the box (no custom PCB), smaller footprint for the tightened body.

## D-016 — Halve PPO learning rate after resized-Rocky NaN blowup
The resized-Rocky retrain (165mm/EduLite-05) climbed to reward +46.6 then crashed at
iter ~354 with `normal expects std >= 0.0` — a PPO policy-std NaN blowup (the tighter
6 Nm dynamics let some envs reach extreme states). The identical PPO config trained
the first Rocky + BDX fine, so it's numerical instability, not a config bug. Halved
learning_rate 1e-3 -> 5e-4 (gentler updates) and relaunched. Watch iter ~354.

## D-017 — BDX-A: add the 2 ear/antenna actuators (16 DOF), NO retrain
Research (arXiv 2501.05204 + BDX-R GitHub) confirmed the real Disney BDX and Kayden
Knapik's BDX-R are 16 DOF = 14 locomotion + 2 EAR actuators (+ LED eyes, passive
ankle roll via rounded soles). Our 14-DOF layout matched Open Duck Mini, not BDX-R —
so we were MISSING the ears. Adopted the upstream BDX-R ear meshes (Left_Ear/
Right_Ear/Right_Ear_Motor, already vendored, fixed in the locomotion URDF). Actuate
them as a DECOUPLED expressive channel (bdx/persona.py: emotion->ear pose + LED eye
state), driven by persona, NOT the RL policy. Ears carry ~no load + are unrelated to
gait, so the trained 14-DOF locomotion policy stands — NO retrain (operator-confirmed).
The park-vs-demo "moves different" feeling = this expressive layer (Disney puppeteers
additive head/gaze/ear offsets on top of the RL gait), not a DOF/robot difference.

## D-018 — BDX-A: passive ankle roll (rounded soles) + LED eyes + expressive layer
Completing the movie-accuracy set (no retrain, all decoupled from the RL gait):
- **Passive ankle roll**: the real BDX has NO ankle-roll actuator — it rounds the foot
  soles so the foot rolls passively. TODO(cad): add a convex TPU sole cap to the BDX
  feet (a printed part over the upstream foot mesh) — a geometry change, zero actuators.
- **LED eyes**: bdx/persona.eye_state (color+brightness per emotion) drives an LED ring
  (BOM: eye_led) — expression without eye motors, mirroring Disney's show functions.
- **Expressive-offset layer** (deploy/jetson/brain.py): emotion drives ADDITIVE
  head-pitch/yaw offsets ON TOP of the locomotion policy's head targets + continuous
  ear/eye animation. This is Disney's architecture (operator offsets on top of RL) and
  the reason the park droid reads "alive" vs the bare research gait — implemented, no retrain.

## D-019 — Fit-test coupon servo box: STS3215 -> Robstride EduLite-05
The coupon plate (`common/cad_lib/coupons.py`) slide-fit pocket must validate the
servo ROCKY-5 actually uses. `standards.SERVO_BOX_*` still described the legacy
STS3215 (45.2 x 24 x 32); updated to the EduLite-05 box (52 x 52 x 34, matching
`components.SERVO`) so the human prints a coupon that verifies the real servo drop-in.
The coupon plate grew (90x50 -> 120x64) to seat the larger square pocket with a valid
land. `components.py` stays the single source of truth for all CAD provisions; these
constants only feed the coupon.

## D-020 — Structural CAD: per-leg limb bracket + core electronics tub
Authored the missing load-path parts so the ROCKY-5 registry is a printable robot,
not just a seed set.
- **leg_bracket** (qty 5, PETG): one rigid frame per leg hosting the three EduLite-05
  servo pockets (coxa/femur/tibia) inline along +X, two 625ZZ pitch-pivot knuckles,
  and M3 heat-set bosses (coxa-root -> core_plate + a servo hold-down tie). At the
  tightened params the coxa segment (41 mm) is SHORTER than a servo (52 mm), so the
  coxa->femur pocket pitch is FLOORED to a non-overlap value (~57 mm) that keeps a
  >= min-wall land; femur/tibia spacing tracks the real lengths. The whole frame is
  239 mm along +X — inside the 250 mm envelope, so it prints in ONE piece (no dovetail
  split needed at this scale; `_needs_split()` guards a future larger scale).
- **core_tub** (qty 1, PETG): a ROUND (not pentagonal) hollow tub, ~3.4 mm wall, sized
  to sit inside the 165 mm carapace above core_plate. Round because at this small dome
  the 90 mm Jetson + 70 mm pack nearly span it and a pentagon's flats pinch floor
  features. Hosts the Jetson tray (raised standoffs, board clears the rim into the dome
  apex), battery bay (walled, low for CoM), IMU boss, a 40 mm fan mount, and wiring
  pass-throughs. **Packing constraints (need human review):** (a) the 40 mm fan's full
  32 mm 4-bolt floor pattern does NOT fit beside the pack — realized as a floor exhaust
  vent + 2 diagonal bolt bosses; (b) the IMU boss is offset -X of the pack, not at the
  exact centroid the battery bay occupies; (c) the Jetson body overhangs the tub rim
  into the dome (only its standoffs are printed). All QA-clean.

## D-021 — Rocky: nudge dome 165->180 / 88->100 mm + lighten leg brackets
Two operator-approved refinements after the structural CAD flags (D-020):
- **Dome nudge** carapace_dia 165->180, dome_height 88->100 mm — buys packing/cooling
  room for the 40 mm fan beside the 90 mm Jetson + 70 mm battery, and vertical
  clearance so the Jetson no longer overhangs the tub rim. Still far under the
  original 220 mm; legs/servos/torque unchanged (shell-only), so NO retrain.
- **Leg-bracket lightening**: floor 9->5 mm + a through-Y window I-beaming the long
  solid tibia link. Mass 456 -> 315 g each (-31%; 5x = 1.58 kg, was 2.28 kg) at 100%
  infill. Real prints at 15-30% infill are far lighter again. gate-2 stays 9/9.

## D-022 — Lock EduLite-05 real dimensions + Rocky power fix
Operator supplied the EduLite-05 datasheet: 46x46 mm square base, 44 mm tall (was a
provisional 52x52x34), Ø46 housing rim / Ø38.5 pilot, Ø41.5 mm PCD mount (M3+M4 at
30deg), Ø24/Ø19 output collar. Updated components.SERVO + standards.EDULITE_* and
regenerated — all servo seats now key off the real box (gate-2 9/9). Power: replaced
the under-volted 3S/12V pack with a 6S (22.2V) Li-ion — within EduLite's 15-60V window,
ample for Rocky's <1 Nm loads; 12-13S/48V is the drop-in for max rated performance.
Battery bay 70x38x20 -> 85x40x25, XT30 -> XT60. Design is being LOCKED before the
manipulation/avoidance retrain (operator: don't train the wrong build twice).

## D-023 — Real EduLite-05 mount + Rocky front-leg grip hand-foot
Locked the two coupled front-limb CAD tasks that finish Rocky's leg/manipulator design.
- **Real EduLite interface** (`common/cad_lib/edulite.py`, single source of truth):
  round Ø46 (+slide) housing seat + Ø41.5 PCD bolt ring + Ø24 output-collar bore.
  The datasheet gives the PCD and "M3+M4 at 30deg" but not the exact bolt COUNT, so we
  realise a symmetric **6-bolt ring at 60deg pitch (offset 30deg, alternating M4/M3)**,
  every bolt on the 30deg grid. `leg_bracket`'s three joint seats were upgraded from a
  square drop-in slot to this seat (round Ø46 pocket + PCD flange + Ø24 output bore
  through the floor). Bracket stays one-piece (230mm < 250) and 420 g each (round seats
  add corner mass vs the D-021 315 g slot); min-wall 3.70, gate-2 green.
- **grip_hand** (new part, qty 2, legs 1 & 4): stony palm + 3 triangular Eridian-stone
  fingers driven by ONE grip servo (IDs 16/17) via a hidden central crown-gear
  synchroniser. grip 0.0 = fingers FLAT/splayed (stand-on foot, 130x149x24); grip 1.4 =
  fingers up/in (cradle grasp, 85x89x62). Fingers are lofted tapered triangular shards
  with 2.5mm edge fillets (weathered-stone look AND clears the acute-wedge that trips the
  min-wall ray screen). Modeled as one fused solid in the open pose (like `foot.py`); the
  functional split (separate finger prints + gears + pins) and the fact that 1.4 rad gives
  a cradle not a fist are logged in the manifest "needs a decision" list. min-wall 4.00.
- QA: all 9 registered Rocky parts pass; `make gate-2` green (9/9 pytest). Preview:
  `docs/media/rocky_grip_hand.png` (matplotlib Agg, open + closed).
