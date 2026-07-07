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

## D-024 — Rocky expressive TOP: physical breathing crown + hidden seam LEDs
Made `rocky/carapace.py`'s 5-plate kinematics PHYSICAL and added Rocky's (faceless)
lighting. Three new registered parts + a small servo + two LED components.
- **Breathing mechanism (one servo -> five petals).** The dome crown (z >= 58 mm) is
  cut into five 72deg petals (`carapace_plate`, PLA, qty 5); each has an underside
  slider rib carrying a cam-follower pin bore + a return-spring anchor. A central
  **scroll cam** (`carapace_cam`, a flat disc with five 72deg Archimedean ramp slots)
  is turned by ONE micro-servo and drives all five follower pins radially IN SYNC —
  a self-centering 5-jaw scroll-chuck. Return springs pull the petals back (exhale);
  the cam only pushes out (inhale). The stationary `carapace_hub` carries the servo
  well, the five radial guide slots, the spring posts, three fixing bosses, and the
  LED ring seat. Actuator = **MG90S-class micro servo** (`BREATH_SERVO`, 13 g, ~$3),
  NOT the 242 g EduLite QDD — the QDD is absurd for slowly nudging light cosmetic
  petals; a scroll cam gives the mechanical advantage a micro-servo needs.
- **20 mm travel is at the sane upper limit, so petals shingle.** 20 mm radial on a
  ~45-63 mm crown is a large 30-44% bloom; a pure gap would look broken. The petals
  overlap and the visible read is a *growing glowing seam*, not a bald hole. The
  scroll ramp is sized so travel = pitch x (servo_sweep/360): a 180deg sweep gives
  the full ~20 mm A_BREATH; resting breath uses a smaller sweep.
- **Speech ripple is NOT mechanical (honest).** A_SPEECH 3 mm @ 22 Hz is beyond ANY
  servo's (or QDD's) bandwidth. Split the channels: **servo = slow ~0.25 Hz breathing
  (motion); LEDs = speech ripple (light).** `carapace.speech_led_intensity()` +
  `SPEECH_IS_MECHANICAL=False` document/realise this. A voice-coil could add real
  22 Hz micro-jitter later, but LED is the clean split and it is what we recommend.
- **Hidden lighting (Rocky has no face).** `SEAM_LED` (WS2812, qty 5) sits in the hub
  ring, split into five arcs by the guide ribs — one per petal seam — so Rocky glows
  along the gaps as he breathes/speaks, no exposed emitter. `GRILLE_LED` (qty 5)
  backlights the five skirt sound grilles (reuses the audio apertures). New provision
  `led_channel` (recessed strip/ring seat). One WS2812 data line drives the whole chain.
- **QA/mass.** All 12 registered Rocky parts pass mesh QA; `make gate-2` green (9/9
  pytest). New solid-volume (100% infill upper-bound) mass: `carapace_plate` 82.4 g x5
  = 412 g, `carapace_hub` 206.8 g, `carapace_cam` 94.0 g. Petals print far lighter at
  real infill. Preview: `docs/media/rocky_carapace_mech.png` (matplotlib Agg, no GL).
- **Needs a decision (human):** (1) confirm the crown-petal seam kinematics — the
  single-piece `carapace` still models a closed dome apex; swap its crown for these
  five petals (truncate its apex to a shoulder ring) before a functional breathing
  build. (2) MG90S torque budget vs 5 petals + 5 springs through the scroll — validate
  or step up to a small metal-gear standard servo. (3) petal shingle/overlap geometry
  (currently petals are modeled as separate wedges at neutral; the overlap tongues are
  a finish detail). (4) confirm LED-for-speech vs a voice-coil.

## D-025 — Deploy hardening: real CAN framing + obs-order lock
Turned the brain.py scaffold into a runnable deploy path. (1) MotorBus now packs the
8-byte Robstride/EduLite MIT position frame (pos16/vel12/kp12/kd12/torque12, PD gains
from params) + parses feedback — VERIFY the P/V/KP/KD/T ranges vs the EduLite-05 manual
before energising. (2) BNO055 IMU read (ang_vel + projected gravity). (3) The #1
"runs-but-walks-wrong" guard: deploy/jetson/dump_obs_spec.py runs in the container and
dumps the policy's EXACT observation term order + dims to <robot>_obs_spec.json;
brain.build_obs assembles the on-robot obs from that spec (canonical fallback if absent).
Remaining TODO is only wiring-specific (mic/speaker ids, VAD, velocity-command source).

## D-026 — Reconcile design mass to the real build (5.0 -> 6.0 kg) before training
The 5 kg target was aspirational; the honest build is servo-dominated: 17 EduLite
(~4.1 kg, unavoidable) + printed parts at ~30% infill (~1.3 kg) + electronics/battery
(~0.5 kg) ~= 6.0 kg (8.4 kg only at an unrealistic 100% infill). Set design_target_kg
6.0 + mass_budget_kg 6.5 so the TRAINING mass matches what we print ("train what you
print"). Torque re-check PASSES with margin (femur worst case ~0.96 vs 1.8 N·m
continuous, 2.25x). Design is now LOCKED + validated for the retrain.

## D-027 — Grip hand is a REAL mechanism: split parts + spiral cam + firm grasp
The grip hand was ONE fused open-pose solid (the crown gear / pinions / pins / finger
split were only DESCRIBED). Made it a real, printable, trainable mechanism.
- **Split into 3 registered parts** (each `part()` + `PartMeta`, each prints & assembles
  separately): `grip_palm` (stony base: bolts to the tibia via the EduLite Ø41.5 PCD
  flange, houses the grip servo, HIDES the drive in an underside cavity, carries three
  pin-clevis finger hinges), `grip_crown` (drive disc on the servo Ø24 output collar),
  and `grip_finger` (one Eridian-stone finger; Ø5 pivot bore + a follower pin on a crank).
  Qtys derive from params: with D-028 (all 5 legs are hands) -> palm ×5, crown ×5, finger ×15.
- **CAM, NOT MESHING GEAR TEETH (honest).** The crown is a flat disc with THREE 120°
  Archimedean spiral grooves; each finger's follower pin rides one groove, so ONE servo
  turn swings all three fingers in phase. Real bevel/face-gear teeth are the WRONG choice
  here: at this diameter the module gives ~1.5-2 mm teeth (BELOW the 2.4 mm structural
  min-wall -> would fail G2), and hand-rolled teeth jam/backlash on an FDM printer. The
  spiral cam is chunky (all walls ≥ 2.4 mm), backlash-tolerant, prints flat with no
  supports — exactly the printable synchroniser precedent already set by `carapace_cam`.
- **Wider grasp for REAL gripping.** `grip_limit_rad` 1.4 -> **2.2 rad (126°)**. At 1.4
  (<90°) the fingers never passed vertical — only a CRADLE. At 2.2 they swing PAST vertical
  into a firm 3-jaw close. 0.0 still = flat splayed foot (tripod sole Ø168, the stand pose).
- **Verified geometry** (fwd kinematics, `docs/reports`): fully-closed (2.2) fingertips sit
  on a Ø22 circle with **≈ 4.9 mm inter-tip clearance — NO self-collision**. Ø40 / 50 / 60 mm
  objects are gripped at 1.97 / 1.86 / 1.75 rad (all inside [0, 2.2], tips wrapping past the
  equator) -> **yes, it holds a 40-60 mm object.** Min graspable ≈ Ø22.
- **Look.** Fingers stay weathered filleted stone shards; the crown cam is fully hidden in
  the palm underside cavity between the finger roots — no exposed gear (Rocky reads as rock).
- **QA/mass.** All three parts pass mesh QA (watertight, ≤250 mm, min-wall 2.90/2.90/2.89 mm).
  100%-infill masses: palm 89.5 g, crown 61.4 g, finger 9.4 g -> **one hand = 179 g**;
  reconciled `components.GRIP_HAND` 114 -> 179 g. Preview (exploded + flat foot + Ø50 grasp):
  `docs/media/rocky_grip_mech.png` (matplotlib Agg, no GL). `grip_hand.py` is now the
  (unregistered) assembly module that fuses the three parts for the render only.
- **Needs a decision (human):** (1) D-028 makes the grip a MICRO servo, but the crown bore
  (Ø24) + palm flange (Ø41.5 PCD) still target the EduLite — re-point the crown collar +
  servo mount to the micro servo's output/horn (the cam + finger geometry are unaffected).
  (2) the big Ø108 palm (sized to hide the Ø100 crown) makes the fingers look stubby vs the
  movie's long claws — when the hand is re-derived from the STL per D-028, shrink the crown/
  palm (e.g. put the followers inboard via a longer crank + link) for slimmer proportions.

## D-028 — Movie-accuracy redesign: derive from the official STL (272mm, RS00, 20 DOF)
Operator review of the assembled render: the tightened 180mm parametric build looked
like a boxy tripod, NOT the organic pentaradial Eridian. Canon (book + refs, see
memory rocky-anatomy-canon): pentagonal thorax, 5 bent crab legs, EVERY limb ends in
3 triangular fingers, 5 breathing slits on top. Corrections:
- SIZE: revert tighten-down -> native official-STL ~272mm ("movie proportions", operator).
- SERVO: EduLite-05 FAILS torque at 272mm (need >=2.52 vs 1.8 N·m) -> back to Robstride
  RS00 (14/17, 10x margin), re-unified with BDX. Grips -> small micro servos (low load).
- DOF: manipulators on ALL 5 legs (was 2) -> 20 DOF (15 leg + 5 grip). Needs the retrain.
- CAD: RETIRE the parametric leg_bracket/carapace (they exceed the 250mm envelope + look
  wrong at movie size) and REBUILD every printed part by segmenting rocky_normalized.stl
  into articulated legs + 3-finger hands + pentagonal thorax. gate-2 is RED until that
  rebuild lands — this is a deliberate WIP state, not a weakened gate.

## D-029 — Rocky leg joints = bulbous stone knuckles (servo-in-joint)
Resolves the STL-rebuild tension (RS00 Ø60 won't hide in the 10-60mm slender movie
legs). Operator choice: house each RS00 in a STONE-TEXTURED BULBOUS KNUCKLE at the
joint (crab/spider legs naturally have wide joints), with slender stone segments
between. Buildable + movie-plausible (reads organic, not mechanical). The knuckle is
the structural hub bridging two segments; slender segments cantilever from it. Refine
segment_rocky_stl.py to add the knuckles + pose the crab stance + close the dome with
5 breathing slits + real 3-finger hands at the tips.

## D-030 — Scale Rocky to canon Labrador size (272 -> 400mm)
The 272mm "movie proportions" made the legs too short for 3 spaced RS00 knuckles — they
merged into boulder-cluster legs (not the elegant slender crab). Operator: scale up to
the true canon Labrador size (~400mm thorax, ~712mm span, x1.47). Now each leg is long
enough for spaced knuckles + slender stone segments between = movie-accurate AND matches
the book. Cost: ~11-12kg, parts exceed the 250mm printer -> dovetail splits required.
RS00 torque re-checked at 11kg / 160mm femur (~2.9 N·m worst case): PASS (~2.7x margin).

## D-031 — Revert to EduLite + compact light body (undo the RS00/Labrador cascade)
Operator caught that the RS00->Labrador escalation was driven by TWO of my mistakes, not
physics: (1) I treated the 1.8x continuous safety margin as a hard wall — EduLite actually
holds the 272mm leg at ~72% continuous with 3.3x peak headroom; (2) I double-counted the
knuckle crowding (a joint knuckle is SHARED, eats D/2 into each segment, not a full D), so
EduLite's Ø46 knuckle leaves a slender 63-74mm femur/tibia at 272mm — not a boulder.
The real design lever is DECOUPLING body size from leg length (operator): a compact LIGHT
body keeps EduLite torque-valid; the legs read slender on their own. Reverted: 400->272mm,
RS00->EduLite, design_target 11->5.5kg, continuous_margin 1.8->1.5 (justified by peak
headroom). Supersedes D-028/D-030. 20 DOF (all-5 fingers, canon) stays — it's servo-agnostic.
Note (STL agent): even the master's own legs are proportionally short (~stubby squat) — a
normalization-accuracy question to revisit; EduLite's smaller knuckle helps regardless.

## D-032 — Scale spidery Rocky x1.2 (272->326mm) so the Jetson carrier fits
Buildability gate (operator won't train a robot we can't build): the movie-accurate
~272mm body's clean interior (~58mm) is too narrow for the standard Jetson Orin Nano
carrier (63mm even on-edge) — deepening couldn't fix a WIDTH problem. Operator chose a
modest x1.2 upscale over a custom carrier PCB: body 326mm, interior ~70mm, Jetson
carrier fits on-edge with 3.3mm walls. Legs stay slender (Ø46 knuckle on 131mm femur =
85mm neck). HONEST torque cost: EduLite drops from 61%->78% continuous util (margin
1.64->1.28x, still 2.1x peak headroom) — near its ceiling; the build must stay <=6kg or
it needs a stronger micro-QDD. Supersedes the 272mm size in D-031 (EduLite + slender-leg
findings still hold). Blender segmentation re-runs at x1.2; electronics-fit gate re-checked.

## D-033 — Rebuild ROCKY-5 CAD from the OFFICIAL statue master (segment real posed sculpt)
Operator supplied the official movie-accurate figure. Chose master =
`reference/self_print_rocky/.../statue_unsupported/statue_unsupported.stl` (assembled,
single in-pose near-watertight mesh, 129k verts, 100x93x79mm raw) OVER the Action_figure
part STLs: those are the SAME sculpt but each leg is print-split into A/B[/C] halves and
laid at independent print origins with NO supplied assembly transforms — reassembling
them is a blind registration puzzle, whereas the statue is already one clean in-pose mesh.
Segmented the REAL posed sculpt (Blender planar bisect + EXACT boolean, NO voxel remesh)
rather than re-synthesizing radial symmetry like the old blender_segment_rocky.py did (that
hack existed only because rocky_normalized.stl had detached/fused legs; the official master
is clean). Scale = widest-XY bbox -> 326mm per D-032 (=3.274x), consistent with the prior
script's 272->326 full-span reading. Consequence: the official master has a chunkier central
carapace + 3-of-5 legs tucked under in its crouch pose, so the thorax comes out ~191mm (vs
the old 116mm) — which is why the electronics FIT GATE now PASSES with margin (Jetson-on-edge
min wall 11.1mm, 6S battery-on-end 29.3mm, both >=3mm; usable interior 63x55x90mm) where the
old 116mm thorax failed its honest gate. No sphere "knuckles" (they blobbed the legs — the
natural 62-88mm craggy legs already house the Ø46 EduLite; bored transverse pitch-axis seats
at hip/knee1/knee2, minimal barrel boss only where a joint is <52mm). Finger call (HONEST):
canon claw is sculpt-native on the raised manipulator arm; walking-leg tips are blunter
craggy claws — PRESERVED as-sculpted, NOT re-grafted (grafting smooth prongs would blob the
stone). All 16 parts (thorax + 5x coxa/femur/tibia) <=250mm -> no dovetail splits needed.
Generator: scripts/blender_rocky_official.py. Renders: docs/media/rocky_official_assembly*.png.

## D-034 — Re-pose ROCKY-5 to a SYMMETRIC NEUTRAL walking stance (instance ONE clean leg 5x)
The D-033 master is a DYNAMIC ACTION pose: legs asymmetric, 3 of 5 tucked under the body so
they segmented short/partial (leg2 fragmentary). A walking robot needs true 5-fold radial
symmetry (params.yaml: 5 identical limbs @72deg, limb0 = +X heading; matches the training
URDF/mjcf coxa_yaw+femur_pitch+tibia_pitch chain). FIX (extended blender_rocky_official.py,
still bisect+boolean ONLY, no remesh): (1) isolate all 5 posed legs, score by reach*sqrt(verts),
pick the ONE cleanest fully-extended leg = az -40 (score 14051 vs 6.5-7.6k for the tucked ones);
(2) segment it ONCE into coxa/femur/tibia at its curvature bends, keeping the craggy sculpt +
EduLite Ø46x44 transverse pitch seats + grip-micro cavity + sculpt-native claw tip; (3) re-pose
by forward-kinematics about the two joint pivots (rotate each segment about Y = the real pitch
axis to an absolute neutral tilt: coxa -4deg, femur +26deg to a raised knee, tibia -62deg to the
ground) with the coxa root seated R_CORE-8 into the thorax socket; (4) INSTANCE that single
posed leg 5x at exactly 0/72/144/216/288deg -> 5 IDENTICAL legs on a common ground ring. The
thorax is re-cut at the SAME symmetric azimuths (pentagonal sockets) and radially trimmed with a
cylinder (R_CORE+3) + keep-largest-component to drop the posed-leg-root STUBS the symmetric planes
would otherwise sever (this is what restored the fit-gate GATE_both_fit=True; jet 11.1 / bat 29.3mm).
Result: top view = 5 identical legs at exact 72deg, craggy carapace on top, all feet planted; body
sits level at stance height. HONEST shortfall: footprint dia = 402mm vs the params 581mm target —
the sculpt-derived leg is shorter than the parametric 336mm reach and I did NOT stretch it (would
distort the movie geometry); reported in-report. Export = 4 unique STLs (thorax + coxa/femur/tibia),
print BOM x1/x5/x5/x5 = 16 parts, all <=250mm. Old per-leg leg{1-5}_*.stl in stl_derived are
SUPERSEDED (kept per the no-delete-STL rule; the canonical print set is the 4 unique files).

**D-035: ROCKY-5 refine — fingers preserved on the RIGID natural-posed hand-limb; slender knee joints get flat mounts + cosmetic stone-sleeve covers (not articulated FK).**
| The operator rejected the D-034 assembly (mangled/cut-off manipulator hands + ugly
flat-cut chunk gaps at the joints). Two root causes fixed in a new, additive pipeline
`scripts/blender_rocky_refine.py` (bisect + EXACT boolean ONLY, no remesh; nothing
committed; STLs -> rocky/cad/stl_derived/refined_*.stl, gitignored): (A) FINGERS. A
read-only profile (`blender_rocky_profile.py`) + isolation (`blender_rocky_hand_isolate.py`)
located the sculptor's 3-finger manipulator hand on the FRONT RAISED ARM (azimuth ~-33deg;
raw tip bbox ~8x9x17mm, digits ~4-6mm) — the other three limbs (az -160/-105/125) are
pointed planted stone feet with NO digits. We isolate THAT hand-bearing arm by planar
bisect wedge (no boolean) and instance it 5x so every foot is a proper hand; all joint cuts
are placed PROXIMAL to the wrist so the whole hand rides the distal (tibia) segment
untouched — NO graft/cone/grip-cavity/servo-boss ever touches it (preserved 1:1, proven by
docs/media/rocky_hands_before.png vs _after.png). (B) JOINT GAPS. D-034 articulated each
joint to forced absolute angles (FK), which rotated the mating faces apart into wedge gaps.
Instead we keep the sculpt's OWN limb bend and place the WHOLE limb RIGIDLY per hip: one
Y-rotation to a -40deg outward-down splay, hip height derived so the foot plants at the
ground, coxa root sunk R_CORE-20 into the thorax socket. Because coxa/femur/tibia share ONE
rigid transform, every cut face MATES EXACTLY (seamless, and closer to the original art).
(C) SERVOS. The sculpt arm is slender (37-48mm) — narrower than the Ø46 EduLite servo — so
the two knees CANNOT bury the servo organically; per hard-req #3 they get a FLAT functional
mount PLUS a separate cosmetic cover (refined_knee{1,2}_cover.stl): a ~2.6mm stone sleeve
sliced from the UNCUT sculpt at that joint (outer face = the sculpt) that clips over
joint+servo. The hip servo hides inside the thorax leg socket. Torso keeps the passing
Jetson(on-edge)+battery(on-end) bays (fit gate re-run GATE_both_fit=True; jet 11.1 / bat
29.3mm walls). All parts <=250mm (max = thorax 191.7). HONEST shortfalls vs the pristine
sculpt: footprint dia 378mm vs the 581mm params target (sculpt limb is short; NOT stretched,
to avoid distorting the movie geometry); minor dark crevices remain at a few hip junctions;
cover sleeves read slightly smoother than the craggy segments. Old D-034 refined set
(coxa/femur/tibia/thorax.stl) is superseded by the refined_*.stl set (old STLs kept per the
no-delete rule).

## D-036 — Mechanism-first ROCKY-5 leg CHASSIS (Phase 1 skeleton); retire leg_bracket
Operator directive: design Rocky MECHANISM-FIRST — the servos + the structural frame that
holds them + real articulation FIRST, cosmetic sculpt shell scales over it in Phase 2. This
lands the leg rebuild D-028 called for (gate-2 had been RED pending it) and RETIRES the
monolithic `leg_bracket` from the print set (it exceeds the 250 mm envelope at the movie
dimensions — 273 mm — and was never a real articulated leg; module + STL kept for the legacy
render, just unregistered).

The new chassis is ONE functional 3-DOF + grip leg, parametric in build123d off
`rocky/cad/parts/leg_geom.py` (the kinematic single-source-of-truth), split into four
separately-printed PETG parts, each < 250 mm and QA-clean (watertight / envelope / min-wall):
- `leg_hip_yoke` (qty 5) — body-side coxa_yaw mount: Ø46 shroud cup, floor carries the real
  Ø41.5 PCD flange (M3+M4) + Ø24 output bore; 3 M3 carapace lugs. Servo axis VERTICAL (Z).
- `coxa_bracket` (qty 5) — rides the coxa_yaw Ø24 collar (top hub), reaches COXA_MM to a YOKE
  that straddles the femur root: +Y wall bolts the femur_pitch EduLite, -Y wall holds a 625ZZ.
  Sets the two hip axes PERPENDICULAR (yaw Z ⟂ pitch Y).
- `femur_link` (qty 5) — driven thigh: +Y root presses the femur_pitch collar, -Y stub-axle
  rides the coxa 625ZZ; runs FEMUR_MM to a knee yoke (tibia_pitch EduLite + 625ZZ).
- `tibia_link` (qty 5) — driven shank: +Y root on the knee collar, -Y stub in the femur
  625ZZ; runs TIBIA_MM to a tip pad presenting the Ø41.5 PCD flange the existing 3-finger
  grip hand (grip_palm/crown/finger) bolts onto.
Each PITCH joint is carried on BOTH sides (servo output + a 625ZZ), never cantilevered off
the servo. Servo mounts reuse `common.cad_lib.edulite`; a shallow Ø46 housing register seats
the body (the Ø38.5 pilot was dropped — it feather-edges against the Ø41.5 bolt circle in a
thin wall and trips the min-wall screen; the body-rim register centres the servo cleanly).

BOM per leg: 3× EduLite-05 + 1× grip micro servo; 2× 625ZZ (one non-driven pivot at each of
the two pitch joints; the hip yaw thrust rides the servo output); 2× Ø5×20 steel stub-axle
dowels (femur/tibia roots); 3× M3 carapace heat-sets; 6× M3 hand-mount heat-sets; servo
flange fasteners M3+M4 on each Ø41.5 PCD (thread into the servo's own flange).

Articulation (verified by trimesh interference across the joint-limit corners,
`scripts/build_leg_chassis.py` → `docs/build_plan/leg_chassis_facts.json`): coxa_yaw and
femur_pitch are collision-free across their FULL params ranges; the knee (tibia_pitch) is
collision-free to **1.65 rad (95°)** — beyond that the folding tibia contacts the femur, so
the params limit of **2.0 rad (115°) is NOT reachable** on the printed chassis. HUMAN ACTION:
clamp the trained tibia_pitch upper limit to ~1.5 rad (a soft margin under the 1.65 hard
stop), or accept 95° as the mechanical stop. Reach envelope: tip radius 4–237 mm, z −166…
+176 mm, yaw sweep 103° (428 mm arc). Neutral stance = all joints 0 (leg straight out +X);
diagram (neutral + flexed, 3 axes labelled) at `docs/build_plan/leg_chassis.png`.

## D-037 — ROUND the leg servo joints (coxa/femur/tibia), hug the Ø46 EduLite

Operator feedback: the `coxa_bracket` / `femur_link` pitch-yokes were chunky Ø54 SQUARE
plates that wasted the corners. Reshaped both both-sides yokes to ROUND Ø54 disc CUPS
(axis = the pitch axis) that hug the Ø46 servo body / Ø41.5 PCD / Ø52 flange, tied by a flat
proximal WEB tucked inside the round silhouette. The inscribed circle trims ~21 % of each
wall face; both-sides support (servo output + 625ZZ + Ø5 stub) is kept, watertight + ≥2.4 mm
+ ≤250 mm hold. Bulk: `coxa_bracket` 117.4 → 100.7 g (−14 %), `femur_link` 107.1 → 85.3 g
(−20 %); min-wall stays clean (coxa 3.48, femur 2.89). Knee self-collision limit even eases
1.65 → 1.70 rad (less corner bulk). `tibia_link` was already round (coupling disc + round
hand pad), left as-is. The web distal face sits at jx−17 (root-safe: the mating link root
reaches jx−15; a flat web there avoids the thin rim/slot wedge a curved web produced).

## D-038 — Redesign the manipulator hand: SLIM 2+1 (2 primaries + opposing thumb)

Operator feedback (ref sculpt `docs/media/rocky_hands_before.png`): the old hand had a fat
Ø108 crown disc between the servo and THREE symmetric fingers — both wrong. Redesigned as a
**2+1** hand on a SLIM wrist:
- `grip_palm` (qty 5) — slim Ø34 wrist that bolts to the tibia Ø41.5 PCD flange, FUSES the
  two PRIMARY fingers low (they converge into a single spider-leg WALKING TIP — Rocky stands
  on the fingertips, rigid so the foot never wobbles), carries the thumb clevis, and HIDES
  the micro-servo + drive crank in a Y-split clamshell bay. 89.5 → 66.6 g.
- `grip_finger` (qty 5) — now the single moving THUMB: a Ø5-pivot digit with a crank tail.
- `grip_crown` (qty 5) — no longer a spiral crown; now the hidden DRIVE CRANK on the
  micro-servo horn, its Ø5 follower pin swings the thumb tail (crank+pin, not gear teeth —
  same printability logic as retired D-027). 61.4 → 2.0 g.
grip 0 = thumb raised, 2 primaries present the foot-tip to STAND on; grip 2.2 = thumb pinches
down against the primaries → 3-point GRASP. Whole hand 179 → ~76 g. All three parts pass G2
(watertight, ≤250 mm, ≥2.4 mm). Renders: `docs/build_plan/hand_2plus1.png` (open foot-tip +
closed grasp, labelled) and the hand now shown on `docs/build_plan/leg_chassis.png`. This is
the FUNCTIONAL hand; the cosmetic stone sculpt shell scales over it in Phase 2. params
`manipulators` note updated (fingers still 3 = 2 primary + 1 thumb, `arrangement: 2plus1`).

## D-039 — ADD tibia_roll: a 4th leg DOF (inline wrist-roll) -> 25 DOF total

Operator change 1: give each leg a WRIST-ROLL. A 4th EduLite is mounted INLINE in the
tibia, between the knee (tibia_pitch) and the shank, and rolls the whole shank+hand about
the leg's LONG axis (X). DOF go 20 -> 25: each limb is now 4 joints (coxa_yaw, femur_pitch,
tibia_pitch, tibia_roll), servo IDs stride by 4 (leg i -> 4i+1..4i+4, so 20 leg IDs 1..20);
the 5 grips shift to IDs 21..25. `tibia_roll` limit [-1.5, 1.5] rad — a roll, so it is
limited by wiring wrap, not self-collision (verified 0 mm^3 across the full range).

- params.yaml: `dof_template` gains `tibia_roll` (offset 4); `manipulators.servo_ids` ->
  [21..25]; comments 20->25. `common/params.rocky_dof` now strides by len(dof_template)
  (produces 25 with correct names/ids). `tests/test_params.py` -> 25 DOF, ids 1..25, roll
  names present, grips 21..25. Description builder splits the tibia into `tibia_prox`
  (roll stator) + shank and adds the roll revolute (axis X); `test_descriptions` EXPECTED_DOF
  17 -> 25 (was STALE at 17 vs the real 20 — gate-3 was already red; now consistent + green).
  `components.py`: 20 EduLite leg servos (IDs 1-20) + 5 grip micros (21-25).
- CAD: NEW part `tibia_bracket` (qty 5) = knee-driven carrier of the roll EduLite (its flange
  bolts a bulkhead ring, axis X; body -X, Ø24 output +X drives the shank). `tibia_link` is now
  the short roll-driven shank that still ends at the UNCHANGED hand mount TIP=238 (reach
  unaffected). Roll support is flange + QDD integral bearings (a roll load is axial thrust +
  a light-hand moment the QDD carries directly — no second bearing, unlike the pitch clevises).
- HONEST PACKAGING: the femur's both-sides Ø54 knee cups fill the space just past the knee,
  so the coaxial Ø46 roll body cannot start at the budgeted 54 mm — the bulkhead sits 71 mm
  past the knee (body on the cup edge), leaving a ~26 mm shank. The bracket keeps an ON-AXIS
  proximal spine (so the knee still folds cleanly) and drops a cantilever KEEL below the body
  only DISTALLY. Cost: knee self-collision limit eases from ~1.70 -> ~1.55 rad (still above the
  ~1.5 rad training clamp from D-036). All tibia parts print < 250 mm; all in-range poses are
  self-collision free (the only clashes are the out-of-range knee=2.0 corner, as before).

## D-040 — THIN-WALL GYROID STRUTS for the leg link beams

Operator change 2: the strut links only need to be a stiff CORE (the Phase-2 sculpt shell
carries the volume), so the solid/I-beam link beams are replaced by a THIN closed outer wall
(2.7 mm, >= the 2.4 mm structural floor) enclosing a rib lattice, with the slicer set to
GYROID infill 30-40% (documented in each strut's part note) and the hollow core doubling as
the wiring run. A true modeled gyroid is impractical in build123d, so the printed solid is a
closed thin-wall tube + transverse ribs + an axial wire channel (`leg_mounts.lattice_beam`);
the gyroid lives in the slicer. Applied to `femur_link` (main beam), `coxa_bracket` (hub->yoke
spar) and the `tibia_bracket` keel. A CLOSED thin-wall tube is far stiffer in TORSION than the
old OPEN I-beam — which now matters because the D-039 roll DOF twists the shank through these
links. Mass: coxa_bracket 100.7 -> 95.2 g; femur_link 85.3 -> 85.7 g (~flat, but torsionally
much stiffer + wired). All parts stay watertight, min-wall 2.70, < 250 mm (G2 green).

MASS + TORQUE (honest, D-039/D-040): +5 EduLite = +1.21 kg of servos; net printed-strut change
is +78 g (the tibia_bracket adds structure; the gyroid trims coxa). AS-BUILT integrated mass is
now ~9.2 kg (was ~7.9 kg at 15 QDD — the 6.5 kg budget was ALREADY blown before this change; the
budget/target params are aspirational, not as-built). The G1 torque gate (spec §4 design point,
femur 0.80 N.m at design_target) stays GREEN unweakened; but scaled to the real ~9.2 kg the femur
worst case is ~1.23 N.m -> continuous margin ~1.46x (still ABOVE the x1.2 training ceiling, so the
EduLite HOLDS, stall ~4.9x) but just BELOW the 1.5x design target. Honest human action: lighten the
shell or use a smaller actuator for the roll DOF, or accept the heavier build / tighter margin.

## D-041 — SLIM SERIAL SERVOS, EMBEDDED INLINE: ROCKY-5's 20 leg joints move off the QDD

Operator-approved "slim all 20": ROCKY-5's 20 leg joints drop the fat external Robstride
EduLite QDD (Ø46 body seating in a Ø54 round cup, ±27 mm off each joint) for slim Feetech
STS serial-bus servos EMBEDDED INLINE in the links. Both variants share one 45.2 x 24.7 x
35 mm body; only mass/torque differ:
  * PITCH joints (femur_pitch + tibia_pitch, 10 total): **STS3250** — ~4.9 N·m stall /
    ~2.4 N·m sustained, 74 g (weight-bearing).
  * YAW/ROLL joints (coxa_yaw + tibia_roll, 10 total): **STS3215** — ~2.9 N·m stall, 55 g
    (low load).
  * Grip stays the MG90S-class micro-servo (D-028).
All 12 V, TTL serial bus, POSITION control (NOT a backdrivable QDD).

INLINE EMBEDDING (the payoff): each servo's 24.7-thin body slots ALONG its link inside the
strut; only the output HORN crosses the joint axis. Because the STS output is on the 35 mm
(H) face, that 35 mm sets the joint's minimum width along the output axis — so a pitch joint
still consumes ~35 mm laterally — but the fat Ø54 round cups are GONE and the both-sides
yoke fork is replaced by a compact rectangular housing + a 625ZZ IDLER carrying the far end
of the output shaft (the real double-support servo bracket). New leg-part lateral (Y) widths:
femur 45, tibia_bracket 38 (were ~54 at every Ø54-cup knuckle); the struts between joints are
now the slim ~24-30 mm silhouette instead of being punctuated by Ø54 balls. HONEST: the coxa
bracket is still ~62 mm wide (the yaw hub + the idler back wall), and the pitch-joint knuckle
can't go below ~40 mm because the servo is 35 mm along its output axis — a real limit of this
servo, not a modelling shortcut. The couplings are kept strictly on their own side of each
joint plane (femur root +Y vs coxa body -Y, etc.) so the links interleave without clashing;
routing the tibia_bracket spine laterally (-Y, clear of the femur's distal knee body) also
recovers the FULL knee fold — collision-free to the 2.0 rad param limit (was self-limited to
~1.55 rad by the old on-axis spine). PR/TIP kept UNCHANGED so leg reach and the description
kinematics are unaffected. All 5 leg parts stay watertight, min-wall >= 2.4 mm (2.7 typ.),
< 250 mm; the D-040 gyroid struts + D-039 tibia_roll + the 2+1 hand are retained.

CAD: new `common/cad_lib/feetech.py` (STS pocket/horn/screw builders, mirrors `edulite.py`)
+ `standards.STS_*`; `leg_mounts.sts_face_cut/idler_seat_cut/box_from_aabb` + `leg_geom`
`sts_body_aabb`/`joint_housing_aabb`. `leg_hip_yoke`, `coxa_bracket`, `femur_link`,
`tibia_bracket`, `tibia_link` reworked to inline STS housings (the Ø54 cups + Ø54 roll
bulkhead removed). `edulite.py` is RETAINED for BDX-A (Robstride, D-007) and for the ROCKY
tibia<->grip_palm hand-mount bolt flange (a plain Ø41.5 PCD circle, not a servo).
`components.py`: `SERVO_PITCH` (STS3250) + `SERVO_YR` (STS3215) replace the leg `SERVO`;
BDX-A keeps `SERVO` (EduLite). Render `docs/build_plan/leg_chassis.png` redone (slim inline
joints, no cups).

MASS + TORQUE (honest, GENUINE IMPROVEMENT): the 20 leg servos drop from 4.84 kg (EduLite)
to 1.29 kg (10x74 + 10x55 g) — a ~3.55 kg cut — so AS-BUILT integrated mass falls from ~9.2
kg to ~5.6 kg, back UNDER the 6.5 kg budget (design_target 5.9 -> 5.6). The G1 torque gate
(spec §4 design point, femur 0.80 N·m) PASSES with far MORE headroom: STS3250 2.4 continuous
/ 0.80 = 3.0x (was EduLite 1.8/0.80 = 2.25x), stall 4.9/0.80 = 6.1x. Scaled to the real ~5.6
kg the femur worst case FALLS to ~0.75 N·m -> continuous margin ~3.2x (was ~1.46x at 9.2 kg):
the swap fixes the mass problem AND improves the margin. `test_torque` threshold RAISED 1.5 ->
2.5x (honest, strengthened — not weakened). STS3215 yaw/roll joints are low-load and clear by
an even wider margin. The description masses (train-what-you-print) dropped to match: rocky
model 7.15 -> 4.10 kg, gate-3 green.

TRAINING/DEPLOY implication (for the operator to wire): the retrain MUST model the leg
actuators as POSITION control (stiff PD: kp 60 / kd 1.5, was QDD kp 40 / kd 2.0) + ~0.5 deg
gear backlash + torque saturation at stall (effort_clamp 4.9 N·m) + the slower STS no-load
speed (vel_clamp 5.5 rad/s, was 15), on a TTL serial bus — NOT the old QDD torque source.
Params + this note are set here; deploy wiring is separate. POWER note: the STS are 12 V (was
48 V EduLite), so the 6S pack now feeds a 12 V servo-rail buck (or drop in a 3S pack).

## D-042 — LOCK the ROCKY-5 leg: HIP-CLUSTER QDD + KNEE DRIVESHAFT + inline roll STS

Operator-approved LOCK of the leg chassis (SUPERSEDES the all-STS pitch of D-041; and to be
precise, coxa_yaw is now QDD too — D-041's slim-STS coxa_yaw is dropped). This is the
weekend's locked leg so we can shell it next. The architecture keeps the QDD's SPEED (~15
rad/s, restores ~2.5 km/h) and backdrivability at the weight-bearing joints but moves the
motor MASS into the BODY and keeps the moving leg SLIM by driving the knee remotely.

LOCKED per-leg actuator + transmission map:
- **Hip cluster (in the body, under the carapace) — 3 EduLite-05 QDD (Ø46, 15 rad/s,
  backdrivable, 242 g each):** `coxa_yaw` (Z, direct), `femur_pitch` (Y, local direct), and
  the **KNEE motor** (drives the knee REMOTELY). All three motor masses live in the BODY, not
  the leg.
- **Knee = REMOTE driveshaft** (`knee.transmission` = `double_cardan_driveshaft`): the knee QDD
  → a DOUBLE-CARDAN CVD centred on the femur_pitch axis at P1 (so the shaft just BENDS over the
  full ~80° pitch range, no cross-coupling) → a Ø6 shaft in a Ø12 tube down the slim femur →
  an M1 16T:16T MITER BEVEL at the knee that turns it onto the knee axis and caps the tibia.
  ratio **1.0**, backlash **0.044 rad (~2.5°)** (2 cardans + 1 bevel mesh), efficiency **0.9**
  (effective knee torque 1.62 N·m continuous / 5.4 stall — still 2.0×/6.75× the 0.80 N·m worst
  case).
- **`tibia_roll` = slim inline STS3215** (X) embedded in the shank — the ONLY servo that rides
  the moving leg (distal, light → keeps the shank slim). **grip = MG90S-class micro** (hidden
  in the palm). MIXED BUS: 15 QDD on CAN; 5 STS roll on TTL; grips on PWM. POWER: 6S (22.2 V)
  feeds the 15–60 V QDD directly + a 12 V buck rail for the STS roll servos.

CAD (build123d, `scripts/cadpy`; gate-2 GREEN, all 18 parts QA-clean):
- `leg_hip_yoke` — coxa_yaw QDD flange plate (Ø46 body up, Ø24 output down; STS pocket → QDD
  flange). `coxa_bracket` — the HIP CLUSTER frame: couples coxa_yaw, carries the femur_pitch
  QDD flange (Y) AND the knee QDD flange (its output feeds the CVD), 2 M2.5 shell anchors;
  knuckles hollowed to shed mass (240 g).
- `femur_link` — RECONCILED to the SLIM Ø12-shaft wrap (no QDD cup): CV-support ring at P1,
  axial Ø12 shaft tube, M1 miter-bevel box at the knee (Ø24 output collar drives the tibia),
  femur_pitch QDD root coupling, 2 M2.5 anchors — bbox 102×39×31 mm, 46 g, fits the Ø44
  under-shell envelope. `tibia_bracket` — knee-BEVEL-output driven (was inline knee STS), still
  hosts the inline STS3215 roll, +2 M2.5 anchors. `tibia_link` shank + 2+1 hand unchanged.
- 6 M2.5 heat-set + machine-screw SHELL ANCHORS per leg (2 each on coxa/femur/tibia; the split
  stone shell BOLTS on — no clips). All parts watertight, ≤250 mm, min-wall ≥2.4 mm.
- ARTICULATION (`scripts/build_leg_chassis.py` → `docs/build_plan/leg_chassis_facts.json`):
  femur_pitch (full ±), coxa_yaw, and the knee are FREE-SPACE collision-free across the in-range
  poses; tibia_roll ±1.5 rad free (0 mm³); and the SLIM shaft femur RESTORES the full knee fold
  to 2.0 rad (the old bulky QDD-cup femur self-limited it to ~1.55). HONEST: the coxa_bracket↔
  femur_link and femur_link↔tibia_bracket overlaps are the coaxial femur_pitch-QDD+CVD coupling
  at P1 and the knee miter-bevel coupling — BOLTED joints, reported as coupling volume not
  clashes; the hip-cluster knuckle massing overlaps the femur CV ring by ~5 cm³ and wants
  clearance refinement before print (tight coaxial QDD+CVD at P1).

MASS + TORQUE (honest): 15 QDD = 3.63 kg back in the build (they were the D-041 slim STS), but
all in the BODY. COTS integrated mass 4.89 kg (actuators dominate); description "train-what-you-
print" model 6.68 kg with the QDD lumped into base_link (coxa_yaw ×5) + the near-hip coxa link
(femur_pitch + knee ×5) so the femur/tibia links are LIGHT (60/110/60 g) — light distal leg,
heavy body. As-built ≈ **6.6 kg** (design_target 6.6), ~0.1 kg OVER the aspirational 6.5 budget —
the honest cost of 15 QDD; the payoff is speed + backdrivability + genuinely slim legs. G1 torque
GREEN (spec §4 design point, femur 0.80 N·m): EduLite 1.8 continuous → **2.25×** (was the STS3250's
3.0× under D-041) but 6.0 stall → **7.5×** (was 6.1×). `test_torque` re-baselined HONESTLY to the
QDD (continuous ≥2.2 — its true number, not weakened to pass — plus a STRENGTHENED stall ≥6.0
check). gate-1/2/3 all GREEN. Render: `docs/build_plan/leg_chassis.png` (hip cluster + CVD + shaft
+ bevel + roll + hand + Ø44 envelope + anchors; neutral + flexed/rolled).

TRAIN/DEPLOY (operator to wire): model coxa_yaw/femur_pitch/knee as the backdrivable QDD (kp 40 /
kd 2.0, effort 6, vel 15) on CAN; ADD the knee driveshaft transmission (1:1, +2.5° backlash, 0.9
efficiency) at the knee joint; model tibia_roll as the STS3215 position servo on TTL; wire the
12 V roll rail alongside the CAN QDD bus.

## D-043 — LENGTHEN the leg to UNIFORM-scale the figure shell (kill the lateral squash)

Operator directive: fix the ROCKY-5 leg proportions the RIGHT way. The prior shell pass
(`blender_actionfig_shells.py`, D-042 era) had to inflate the slender official action-figure
leg **~6.5× LATERALLY** (LAT=6.5) while only stretching it ~2.5–3.8× axially, just to make it
cover the Ø27–44 chassis — a fat, squashed leg, NOT the movie's slender craggy spider/crab legs.
The correct fix is to scale the figure leg **UNIFORMLY** (same factor axially + laterally) so its
NATURAL slender cross-section wraps the chassis, then LENGTHEN the chassis strut to the resulting
longer shell. **Only the LEG length changes** — body / hip-cluster / servos / torso stay compact.

**Uniform scale factor `s = 4.40`** (was: lateral 6.5, axial 2.5–3.8 = the distortion). Derived
from the raw figure geometry: measured the 5 assembled figure legs (`af_leg{N}_assembled.stl`) —
native length ~66–73 mm, slender-shaft Ø ~10–13 mm. The SLENDEREST leg's typical (median) shaft is
Ø11.39. `s = Ø50 / Ø11.39 = 4.40`, where Ø50 = Ø44 shell envelope + 3 mm wall each side. So the
slenderest figure leg's natural cross-section sheaths the chassis links WITHOUT any lateral-only
stretch; the shell now prints ISOTROPIC (uniform), preserving the craggy slender proportions.
`blender_actionfig_shells.py`: `LAT 6.5→4.40`, clearance core Ø56→Ø52, stations tracked to the new
chassis. Its axial scale (chassis-span / piece-length) also lands at ~4.40, so the result is a true
uniform scale (residual per-leg axial variance ≤ ~15 % because the 5 distinct sculpts share ONE
chassis — vs the old 70–160 % lateral over-inflation).

**Leg lengthened to match (`rocky/cad/parts/leg_geom.py` + `params.yaml`):**
- `FEMUR 73→98 mm`, `TIBIA 105→170 mm`; `COXA 60 mm` UNCHANGED (hip-cluster offset stays compact).
- `ROLL_OUT_OFF 79→144` so the wrist (PR→TIP) stays the SAME short 26 mm — only the tibia_bracket
  knee→roll spine lengthens; `tibia_link` is geometrically unchanged.
- **hip→tip 238 → 328 mm (+38 %)**; stations knee 133→158, roll 212→302, tip 238→328.
- params: `limb_reach 201→244`, `footprint_dia 402→489`, `stance_height 145→200` (re-derived at the
  longer leg, same stance angles). The Ø12 driveshaft + Ø6 shaft + tube just get longer (cheap).

**Chassis regen (gate-2 GREEN):** all parts watertight, ≤250 mm, min-wall ≥2.4 mm — femur_link
54.6 g, tibia_bracket 95.9 g, tibia_link 27.5 g. Longest print is the tibia SHELL clamshell half
at ~158 mm (< 250, **no split needed**). Articulation RE-VERIFIED
(`build_leg_chassis.py`): knee still folds to 2.0 rad, tibia_roll ±1.5 free, and the longer leg
now has **ZERO free-space clashes** (the old out-of-range knee-fold clash cleared with the extra
separation); the only overlaps are the by-design bolted P1 QDD+CVD and knee-bevel couplings.

**Re-shelled + swept (Task 4):** uniform s=4.40 shells over the lengthened chassis — tibia now
~141–157 mm long × ~52–67 mm wide (was 92 × 66–95: slimmer AND longer = slender), hollow 3 mm,
sagittal clamshell split on the M2.5 anchors, separate hand claw. New `sweep_shell_clearance.py`:
all 5 legs **0 mm³** shell-to-shell across femur_pitch [-1.4,1.0], knee to 2.0 rad, roll ±1.5.

**Torque re-checked HONESTLY (gate-1 GREEN, NOT weakened):** the longer femur = longer lever, so
the spec §4 femur worst case scales ~linearly, `0.80 → 1.074 N·m` (×98/73). Margins (unchanged
1.5× cont / 3.0× stall bars):
- femur_pitch (DIRECT): **1.8/1.074 = 1.68× continuous, 6.0/1.074 = 5.59× stall.**
- knee (0.9-eff driveshaft): 1.62 cont / 5.4 stall → **1.51× / 5.03×** — the binding margin.
The femur was **CAPPED at 98 mm precisely to hold the knee ≥1.5× continuous** (a longer femur drops
it below 1.5×); the tibia absorbed the remaining uniform length so the leg still reads long+slender.
This CUTS headroom from D-042's 2.25× — reported, not hidden. `test_torque` sanity bars moved to the
new TRUE numbers (cont ≥1.6, stall ≥5.0) + an added explicit knee ≥1.5× assert; the gate margins
(1.5/3.0) themselves are untouched. As-built mass 6.6→~6.72 kg (+~0.12 kg longer struts + shaft).

**Render:** `docs/build_plan/legs_with_shells.png` replaced — the 5 slender craggy spider legs,
shell naturally wrapping (no distortion) the ghosted chassis, with leg length / footprint / torque
margins / 0 mm³ clearance annotated. gate-1 / gate-2 / gate-3 all GREEN.

## D-044 — RE-SHELL the leg cosmetic PRESERVING the craggy stone surface (method fix)

Operator directive: the D-043 shells LOST the official figure's craggy stone relief — the
tibia rendered as a smooth featureless pill. ROOT CAUSE found in
`scripts/blender_actionfig_shells.py`: after uniform-scaling (s=4.40) each figure leg
segment, the pipeline **unioned a fat Ø52 clearance core** (`CORE_R=26`) along every
segment body "to guarantee the mechanism fits." Where the slender uniform-scaled figure
leg was thinner than Ø52 (the tibia ~Ø45–56, thin-axis ~Ø30), that core **punched
through the craggy skin and replaced it with a smooth cylinder** — a smooth pill. The
core was doing double duty: clearance AND (accidentally) re-rounding the flat craggy plate.

**FIX (method only; D-043 proportions/length UNCHANGED — femur 98 / tibia 170, s=4.40):**
the shell IS the figure surface. Removed the Ø52 core union entirely; the craggy segment
is now hollowed by a THIN 3 mm INWARD `solidify` that FOLLOWS the relief. Local joint-
knuckle relief (taper rims + boot gaps at femur_pitch / knee) is retained. Re-split into
sagittal clamshells, re-swept, re-rendered. **Craggy stone relief is recovered on ALL
segments incl. the tibia** (verified `docs/build_plan/legs_shells_solid.png` — mountainous
relief, cracks, socket holes, engraved marks; previously a smooth pill).

**Motion clearance (gate-3 sweep, `sweep_shell_clearance.py`):** slimmer shells → all 5
legs **0 mm³** shell-to-shell across femur_pitch [-1.4,1.0], knee to 2.0 rad, roll ±1.5.
The local knuckle relief still clears full travel. GREEN (unchanged, not weakened).

**HONEST cavity-vs-chassis finding (`measure_shell_cavity.py`, signed-distance of the real
neutral chassis into each solid shell):** with the rounding core gone, the movie-accurate
**slender craggy cosmetic does NOT enclose the current chassis.** The chassis tibia shank
is ~Ø54 round AND offset ~−12 mm in Y (roll-servo body + tibia_bracket routing), while the
uniform-scaled craggy tibia is a FLAT plate ~Ø56 wide × ~Ø30 thin — so ~45–82 % of tibia
chassis points sit PROUD of the cosmetic skin (worst chassis pt ~20 mm outside), and the
femur mid-body is ~8 mm proud. The femur *driveshaft* mid-span (Ø12) fits with margin; the
hip QDD (R≈72), femur_pitch servo (R≈57) and knee/roll brackets (R≈42) are the bulbous
stone KNUCKLES (D-029) and sit at the joint stations by design (locally relieved). **The
D-043 premise "chassis tibia ≈ Ø35 → fits" is optimistic — the as-built chassis is bigger
and off-axis.** This needs an OPERATOR decision — it is NOT a minimal chassis slim:
  (a) shrink/re-center the tibia chassis (on-axis roll servo, tighter bracket), or
  (b) accept a partly-proud cosmetic, or
  (c) a small *lateral-only* cosmetic inflation on the tibia thin-axis (re-introduces some
      of the D-042 squash — a movie-accuracy trade). NO surface was smoothed to hide this.

**Watertight (gate-2) — DEGRADED, source-limited:** the cosmetic clamshells derive from the
OFFICIAL action-figure scans, which are themselves non-manifold (e.g. `2-B.stl`: 16 open +
30 non-manifold edges; only `1-A` is clean). The derived shells are near-manifold (single
closed body, euler≈2, positive volume, ≤250 mm, slicer-printable with auto-repair) but NOT
strictly trimesh-watertight — a handful of bad edges survive every clean/boolean short of a
**voxel remesh, which the pipeline forbids** (a remesh is exactly what re-smooths the craggy
detail we just recovered). The old shells read "watertight" only because the EXACT Ø52-core
boolean rebuilt the whole surface — i.e. the same operation that caused the smooth-pill bug.
The registered **build123d chassis parts** (the actual gate-2 pytest scope, `test_cad.py`)
are untouched and remain green. NOT committed per directive.

## D-045 — THIN-AXIS (Y) FATTEN + Y RECENTER to resolve the tibia shell-vs-chassis fit

Operator DECISION on the D-044 conflict: fix it on the SHELL side (do NOT reorient/relocate
the roll servo), by **fattening ONLY the tibia THIN axis** to enclose the round chassis —
keep the craggy stone detail, accept a slightly rounder (less flat-blade) tibia. D-043 length
(femur 98 / tibia 170) and the D-044 craggy surface method are UNTOUCHED.

**The conflict (D-044 `measure_shell_cavity.py`):** the craggy movie tibia is a slim blade
centred on the leg long axis (y=0), but the as-built chassis in the shank is the roll-bracket
SPINE beam (STS3215 body + `tibia_bracket` routing) **offset to ~y=−12** (~Ø26 cross-section,
Y22×Z26), so it poked ~20 mm proud of the slender shell; the femur mid-body was ~8 mm proud.

**Fix (`scripts/blender_actionfig_shells.py`, `FATTEN` + `thin_axis_fatten()`):** for each of
the 5 tibia shells (and the femur), (1) **recenter** the shell mid-body Y-centre onto the
chassis axis and (2) **anisotropically scale ONLY Y** (the thin/thickness axis) about that
axis to `target_half` (tibia 28 → Ø56, femur 22). The WIDE (Z) axis, the AXIAL length, and
ALL craggy relief are untouched — an affine Y map stretches the cross-section rounder while
preserving every crag/crack/socket-mark (NO re-core, NO voxel remesh). The recenter is
**graduated** (ramped over the knee boot-gap taper 171→201, and 70→96 femur) so the shell
FOLLOWS the chassis centreline — ~0 at the knee (keeping the neck over the knee knuckle) and
bending onto −12 along the shank — rather than rigid-shifting the whole shell (which regressed
the neck). Recentring is a shell PLACEMENT change, not a servo change.

**Thin-axis factors (Y) / resulting mid-body cross-section (Ythin × Zwide):**
- tibia: leg1 ×1.31 → Ø56.0×46.7 · leg2 ×1.24 → Ø56.0×51.7 · leg3 ×1.68 → Ø56.0×47.8 ·
  leg4 ×1.00 → Ø60.8×54.7 (already wide, no scale) · leg5 ×1.40 → Ø56.0×49.2.
- femur: recenter-only (×1.00) except leg4 ×1.14; body Ø44–62 × Ø37–51.

**Enclosure verify (`measure_shell_cavity.py`, signed-distance of the real neutral chassis):**
Measured over the true untapered mid-body (the span the slim shell actually sheaths):
- **Femur body (x96–114): ENCLOSED all 5 legs** (0 proud legs 1/2/4; 6–7 % on legs 3/5) —
  was 12–30 % proud in the LINK window. Fixed.
- **Tibia body (x201–250): legs 1 & 5 ENCLOSED (~0 % proud); legs 2/3/4 = 25–40 % residual.**
  The residual is NOT a thin-axis shortfall (it is scale-invariant — Y×2.2 does not clear it):
  it is genuine **craggy HOLLOWS / socket-holes in those specific action-figure source pieces**
  at a localised x-band (~208–215) sitting over the chassis. Closing them would require FILLING
  the crags — the exact re-smoothing D-044 forbids. Honest movie-accuracy-vs-coverage limit.
- The gate's LINK windows (tibia 168–250, femur 92–132) also span the **knee/roll boot-gap
  NECKS** (60–85 % pierce), which are the external stone KNUCKLES (D-029) the gate's own
  docstring says are "locally relieved, NOT buried in the slim shell" — so the headline LINK
  pierce stays high BY DESIGN. No threshold or window was moved to hide this (prime directive 5).

**Motion clearance (`sweep_shell_clearance.py`): all 5 legs 0 mm³** shell-to-shell across
femur_pitch [−1.4,1.0], knee to 2.0 rad, roll ±1.5 — the graduated recenter kept the knee neck
on-axis so the boot gaps still clear full travel. **GREEN (unchanged).**

**Printability:** all segments ≤250 mm (max clamshell half ~158 mm); clamshells re-split on
each segment's own Y-centroid (balanced halves now the tibia sits ~12 mm off-axis); 6 M2.5
anchor bosses/leg unchanged. Re-rendered `docs/build_plan/legs_shells_solid.png` (craggy
relief confirmed intact on ALL segments post-stretch) + `legs_with_shells.png` (shank bodies
now wrapped; residual visible mechanism is the knee-bevel + roll-housing knuckles at the joints).

**Honest aesthetic read:** the tibia is now a **slim oval ~Ø56 × Ø47** (was a flat blade
~Ø56 × ~Ø30). It reads noticeably ROUNDER / less blade-like on the thin axis — the deliberate,
operator-accepted trade — but it is still unmistakably a craggy stone shank (not the D-042
smooth pill, and not a full Ø60 round). Legs 2/3/4 keep a small amount of chassis show-through
through their natural stone hollows at the shank mid. NOT committed per directive.
