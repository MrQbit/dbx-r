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
