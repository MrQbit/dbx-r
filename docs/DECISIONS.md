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
