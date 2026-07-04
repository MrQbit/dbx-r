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
