# ROCKY-5 cosmetic-shell pipeline (the "puppet skin")

Turns the official *Project Hail Mary* action-figure pieces (copyrighted — gitignored under
`reference/self_print_rocky/`, downloaded by the builder, see `docs/LICENSES.md`) into the
craggy cosmetic shells that dress the D-042/D-043 leg chassis. Derived STLs are gitignored
(regenerable); **these scripts + the transform JSONs are the source of truth.**

Run everything via `scripts/cadpy <script>` (micromamba `duet-cad`: trimesh/scipy/numpy/
open3d/pyransac3d/manifold3d) or `blender --background --python <script>` where noted.

## Pipeline (operator-approved recipe, one leg at a time)

0. **Canonical assembly** (`reglib.py`, `reg_all.py`, `reg_thighs.py`, `finalize.py`,
   `fit_joints_raw.py`, `final_build.py`): register each raw figure piece onto the sculptor's
   assembled statue (`statue_unsupported.stl`) — Open3D FPFH global RANSAC + manual
   point-to-plane ICP (o3d's built-in ICP segfaults on this aarch64 build). The 5 near-identical
   legs are disambiguated by physical constraints (each thigh on a distinct hip, adjacent to its
   own foot). Result: `transforms/toy_assembled_o3d.json` (piece -> 4x4, 99.3% of the statue
   surface within 1mm, zero interpenetration). **Never hand-guess piece orientations — every
   hand-rolled attempt failed; register against the statue.**
1. **Align** (`build_align.py` = leg2 template; `legN_align.py`): assembled leg (A+B, pegs kept)
   -> extend the knee straight -> per-piece similarity onto the chassis skeleton stations
   HIP 0 / KNEE 158 / TOE 328 (o3d roll preserved). Output `legN_aligned_*.stl` +
   `transforms/legN_aligned.json` (joint residuals are 0 by construction).
2. **Enclose** (`enc_build.py` template; `enc3_*/enc5_*/leg4_enc_*` adaptations): detect chassis
   protrusions, stretch the craggy shell radially (smooth falloff — the crag rides along, NO
   remesh/smoothing) to enclose +4mm. Hip-cluster QDD stays proud (carapace shroud's job).
3. **Toe/hand boot** (`fc_toe_build.py`; `leg4_fc_toe_build.py`, `fc3_toe_build.py`,
   `leg5_toe_build.py`): the REAL distal sculpt region of that leg's own foot = the boot,
   hollowed over the foot-core/collar (+1.5mm), carved for the thumb sweep (grip 0-2.2 rad).
4. **Finger gloves** (`fc_build_covers3.py`; per-leg `*_build_covers*.py`): 3 distinct snap-fit
   gloves — 2 THICK FLAT primaries (outers grafted from the leg's own prong/blade geometry,
   >=1.5mm visible cleft) + 1 smaller thinner thumb. Functional: 0.20mm slide cavities +
   detent retention, >=3mm tip walk pads, low-crag inner grip faces; grip stays free to
   ~2.0 rad (bare mech stalls ~2.15), aperture ~65-66mm.
5. **Verify/render** (`fc_verify2.py`, `fc_render2.py`, `fc_montage2.py` + per-leg variants):
   numbers first (fit, retention, pads, articulation, watertight), montage for review.

## Hard-won rules (do not relearn these the expensive way)
- **NO voxel remesh / smoothing** on the craggy surfaces — it blocks the stone into stairs.
  Hollowing that preserves crag = manifold-repair (no smoothing) + `manifold3d` erosion.
- Judge results on SOLID renders + mesh validation tables, not point clouds; the STL is the
  deliverable (watertight, 1-body, <=250mm print pieces).
- The toy tips are FLAT blades / 2-prong clefts; covers are per-finger "gloves", never a ball.
- Chassis: coxa 60 / femur 98 / tibia 170 (hip->tip 328), D-043. Whole-creature scale x6 (D-049).
