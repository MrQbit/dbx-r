# CLAUDE.md — Agent Operating Manual for PROJECT DUET

You are Claude Code executing `ROBOTS_SPEC.md` v2.1 **fully unattended for ~60 hours**. The human is asleep, away, or watching a printer. Behave accordingly.

## Prime directives (ordered; earlier wins)
1. **Never block.** No prompts, no confirmations, no waiting on input. Every command non-interactive (`--yes`, `--headless`, `DEBIAN_FRONTEND=noninteractive`, `OMNI_KIT_ACCEPT_EULA=YES`).
2. **The spec is law; Appendix A is the tiebreaker.** If information is missing, use the spec's fallback. If the spec is silent, make the smallest reasonable choice, log `D-###` in `docs/DECISIONS.md`, continue. Do not redesign.
3. **Fail small.** A failing stage retries per `stages.yaml`, then degrades or halts ITS TRACK only. Write `FAILURE-<track>.md` (symptom, last log lines, hypothesis, exact resume command) and keep working the other track.
4. **Idempotence.** Every stage safe to re-run. Check `resume_key` artifacts before redoing work. Never delete checkpoints, logs, or exported STLs.
5. **Honesty in reports.** DEGRADED means degraded. Never mark a gate green by weakening its test.

## Working rules
- **Read lazily.** Load only the spec sections needed for the current stage (section anchors in the spec header). Keep context small; re-read rather than remember.
- **Test-first per gate.** Each gate's checks exist as pytest before the stage that must satisfy them.
- **Commits:** conventional commits, one per green stage minimum: `feat(rocky): cad parts pass QA [gate-2]`. Commit locally only; never push, never create remotes.
- **Long jobs:** launch training via the orchestrator only (it owns timeouts, OOM env fallback 4096→2048→1024, GPU lock). Tail metrics every 15 min; if reward is NaN or entropy collapses < 1e-4 for 300 iters, kill, halve lr once, restart from last checkpoint, log D-###.
- **Network:** allowed for pip/git/datasheets during G0–ingest only. After ingest, run offline-tolerant; any later fetch failure → Appendix A.
- **Forbidden:** `sudo` outside `scripts/setup_env.sh`; editing generated files by hand (fix the generator); touching printer/slicer settings beyond writing manifests; modifying gate thresholds; upgrading/downgrading the Isaac Lab image after G0 freezes its digest; any x86-only pip package (host is aarch64 — check wheel availability before adding ANY dependency); any interaction with real servos this weekend (G6 uses the bus simulator).

## DGX Spark specifics (aarch64, CUDA 13)
- All Isaac/RL work runs inside the pinned Isaac Lab 2.3.x ARM container; CAD/audio/tests run on host in the uv venv (with the conda-forge OCP contingency from spec §1 if wheels are missing).
- Export `LD_PRELOAD=$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1` for every Isaac process.
- PyTorch must be a cu13 aarch64 build; never install a cu12/x86 wheel to "fix" an import error.
- Enable Isaac Lab asset caching at G0 so training stages tolerate network loss.

## Machine limits & hygiene
- Disk guard 40 GB (abort new training below it; prune only `runs/*/tb_events` older than best+last-5 checkpoints).
- Write heartbeat + current stage to `orchestrator/heartbeat.log` every 60 s.
- On any crash of the orchestrator itself: restart it; it resumes from `stages.state.json`.

## Definition of done (weekend)
`docs/reports/WEEKEND_REPORT.md` exists and lists per track: gate statuses, best checkpoint paths + eval metrics, ONNX artifacts, print manifests + swap schedule, all D-### entries, and a ranked "human next actions" list. If both tracks halted, the report plus FAILURE files ARE the deliverable — write them well.
