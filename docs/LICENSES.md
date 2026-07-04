# LICENSES — upstream provenance (ROBOTS_SPEC.md §0.7)

Record every upstream license BEFORE reuse. No license file ⇒ all-rights-reserved
⇒ re-derive parametrically, copy nothing. Both robots are personal / non-commercial.
No Disney/Lucasfilm trade dress published.

| Upstream | URL | License | Reuse decision |
|---|---|---|---|
| BDX-R Isaac Lab | github.com/BDX-R/BDX-R-IsaacLab @ 62f0ba6 | **MIT** (Kayden Knapik, 2025) | **REUSE** — URDF/USD/meshes + Isaac Lab training, extended (not forked) for BDX-A. Attribute in NOTICE. |
| BDX-R MjLab | github.com/BDX-R/BDX-R-MjLab @ 079acd2 | **Apache-2.0** | **REUSE** — MuJoCo models + velocity/imitation tasks, host-native. Preserve NOTICE/attribution. |
| Open Duck Mini | github.com/apirrone/Open_Duck_Mini | _(fill at ingest)_ | STS3215 0.6x actuation/scale reference (D-001) |
| Open Duck Mini Runtime | github.com/apirrone/Open_Duck_Mini_Runtime | _(fill at ingest)_ | runtime-loop reference |
| Isaac Lab | github.com/isaac-sim/IsaacLab | BSD-3-Clause | container image 2.3.2 (D-004); env configs referenced |

Both BDX-R repos are permissively licensed and cleared for reuse. We EXTEND them
(subclass env/robot cfgs, reuse the URDF/USD/MJCF assets) rather than copy-edit —
attribution preserved. Vendored read-only via `scripts/fetch_upstream.sh`.

_Populated during the ingest stage (§0.6). Any fetch failure → Appendix A + D-###._
