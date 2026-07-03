#!/usr/bin/env python3
"""PROJECT DUET orchestrator — runs stages.yaml as a DAG (ROBOTS_SPEC.md §9).

Design guarantees (see CLAUDE.md prime directives):
  * Never blocks on input — every stage command is non-interactive.
  * Fail small — a `halt_track` failure stops only its own track; the other
    track keeps running. `degrade`/`skip` never stop anything.
  * Idempotent — a stage whose `resume_key` artifacts already exist is skipped,
    so a killed run resumes by re-invocation.
  * Observable — a heartbeat line lands in orchestrator/heartbeat.log every 60 s
    and full state is persisted to orchestrator/stages.state.json after every
    stage transition (the orchestrator can crash and resume from it).

This module owns scheduling only; the real work is in each stage's `cmd`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
HEARTBEAT = HERE / "heartbeat.log"
STATE = HERE / "stages.state.json"
DISK_GUARD_GB = 40  # abort NEW training below this (§9)

# Stage lifecycle states.
PENDING, RUNNING, DONE, DEGRADED, SKIPPED, HALTED, BLOCKED = (
    "pending", "running", "done", "degraded", "skipped", "halted", "blocked",
)


class Orchestrator:
    def __init__(self, config: Path):
        raw = yaml.safe_load(config.read_text())
        self.defaults = raw.get("defaults", {})
        self.stages = {name: self._with_defaults(name, s) for name, s in raw["stages"].items()}
        self.state: dict[str, str] = self._load_state()
        self.halted_tracks: set[str] = set()
        self.gpu_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self._stop_heartbeat = threading.Event()
        self._current: dict[str, str] = {}  # thread-name -> stage id, for heartbeat

    # --- config / state ----------------------------------------------------
    def _with_defaults(self, name: str, s: dict) -> dict:
        merged = {
            "retries": self.defaults.get("retries", 2),
            "on_fail": self.defaults.get("on_fail", "halt_track"),
            "track": "common",
            "needs": [],
            "timeout_min": 60,
            "gpu": False,
        }
        merged.update(s)
        merged["name"] = name
        return merged

    def _load_state(self) -> dict[str, str]:
        if STATE.exists():
            return json.loads(STATE.read_text())
        return {}

    def _save_state(self):
        with self.state_lock:
            STATE.write_text(json.dumps(self.state, indent=2, sort_keys=True))

    def _set(self, name: str, status: str):
        with self.state_lock:
            self.state[name] = status
        self._save_state()

    # --- guards ------------------------------------------------------------
    def _free_gb(self) -> float:
        return shutil.disk_usage(ROOT).free / 1e9

    def _artifacts_valid(self, stage: dict) -> bool:
        keys = stage.get("resume_key")
        if not keys:
            return False
        return all((ROOT / p).exists() for p in keys)

    # --- heartbeat ---------------------------------------------------------
    def _heartbeat_loop(self):
        while not self._stop_heartbeat.wait(60):
            self._emit_heartbeat()

    def _emit_heartbeat(self):
        with self.state_lock:
            running = [v for v in self._current.values() if v]
            counts = {}
            for st in self.state.values():
                counts[st] = counts.get(st, 0) + 1
        # No wall-clock source in-loop beyond time.time(); fine for a heartbeat.
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        line = f"{stamp} running={running or '-'} free={self._free_gb():.0f}GB {counts}\n"
        with HEARTBEAT.open("a") as fh:
            fh.write(line)

    # --- execution ---------------------------------------------------------
    def run(self) -> int:
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        for name in self.stages:
            self.state.setdefault(name, PENDING)
        self._save_state()
        hb = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb.start()
        self._emit_heartbeat()
        try:
            self._schedule()
        finally:
            self._stop_heartbeat.set()
            self._emit_heartbeat()
        # Exit non-zero only if a track HALTED (degrade/skip are acceptable).
        return 1 if any(v == HALTED for v in self.state.values()) else 0

    def _ready(self) -> list[str]:
        ready = []
        for name, stage in self.stages.items():
            if self.state.get(name) != PENDING:
                continue
            if stage["track"] in self.halted_tracks:
                self._set(name, BLOCKED)
                continue
            deps = stage["needs"]
            dep_states = [self.state.get(d) for d in deps]
            if any(d in (HALTED, BLOCKED) for d in dep_states):
                self._set(name, BLOCKED)
                continue
            if all(d in (DONE, DEGRADED, SKIPPED) for d in dep_states):
                ready.append(name)
        return ready

    def _schedule(self):
        max_workers = 4  # tracks are few; GPU stages serialize via the lock
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            inflight: dict = {}
            while True:
                for name in self._ready():
                    self._set(name, RUNNING)
                    inflight[pool.submit(self._run_stage, name)] = name
                if not inflight:
                    if any(self.state.get(n) == PENDING for n in self.stages):
                        time.sleep(0.2)  # waiting on a running dep
                        continue
                    break
                done = [f for f in list(inflight) if f.done()]
                if not done:
                    time.sleep(0.2)
                    continue
                for fut in done:
                    inflight.pop(fut)
                    fut.result()  # re-raise scheduler bugs (not stage failures)

    def _run_stage(self, name: str):
        stage = self.stages[name]
        tname = threading.current_thread().name
        with self.state_lock:
            self._current[tname] = name
        try:
            if self._artifacts_valid(stage):
                self._set(name, SKIPPED)
                return
            if stage["gpu"] and self._free_gb() < DISK_GUARD_GB:
                self._fail(stage, reason=f"disk guard: {self._free_gb():.0f} GB < {DISK_GUARD_GB}")
                return
            ok = self._attempt(stage)
            if ok:
                self._set(name, DONE)
            else:
                self._fail(stage, reason="retries exhausted")
        finally:
            with self.state_lock:
                self._current[tname] = ""

    def _attempt(self, stage: dict) -> bool:
        gpu = stage["gpu"]
        attempts = stage["retries"] + 1
        for i in range(attempts):
            if gpu:
                self.gpu_lock.acquire()
            try:
                rc = self._exec(stage)
            finally:
                if gpu:
                    self.gpu_lock.release()
            if rc == 0:
                if not self._check_artifacts(stage):
                    return False
                return True
            if i < attempts - 1:
                time.sleep(min(60 * (2 ** i), 600))  # exponential backoff, capped
        return False

    def _exec(self, stage: dict) -> int:
        try:
            proc = subprocess.run(
                stage["cmd"], shell=True, cwd=ROOT,
                timeout=stage["timeout_min"] * 60,
            )
            return proc.returncode
        except subprocess.TimeoutExpired:
            return 124

    def _check_artifacts(self, stage: dict) -> bool:
        return all((ROOT / p).exists() for p in stage.get("artifacts", []))

    def _fail(self, stage: dict, reason: str):
        name = stage["name"]
        mode = stage["on_fail"]
        self._write_failure(stage, reason)
        if mode == "degrade":
            self._set(name, DEGRADED)
        elif mode == "skip":
            self._set(name, SKIPPED)
        else:  # halt_track
            self._set(name, HALTED)
            self.halted_tracks.add(stage["track"])

    def _write_failure(self, stage: dict, reason: str):
        path = ROOT / f"FAILURE-{stage['track']}.md"
        path.write_text(
            f"# FAILURE — track {stage['track']}\n\n"
            f"- **Stage:** `{stage['name']}`\n"
            f"- **Reason:** {reason}\n"
            f"- **on_fail:** {stage['on_fail']}\n"
            f"- **Resume:** `python orchestrator/weekend.py --config orchestrator/stages.yaml` "
            f"(idempotent; completed stages are skipped)\n"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=HERE / "stages.yaml")
    args = ap.parse_args()
    return Orchestrator(args.config).run()


if __name__ == "__main__":
    raise SystemExit(main())
