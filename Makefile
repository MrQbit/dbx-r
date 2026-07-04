# PROJECT DUET — top-level entrypoints (ROBOTS_SPEC.md §2, §9, §10).
# Host tools run in ./.venv (Python 3.11, uv). Isaac/RL stages run inside the
# pinned Isaac Lab 2.3.x ARM container via the orchestrator. Everything is
# non-interactive by construction (Prime Directive #1: never block).

SHELL := /bin/bash
PY := ./.venv/bin/python
PYTEST := $(PY) -m pytest
CADPY := ./scripts/cadpy         # CAD interpreter (micromamba duet-cad; §1 contingency)
ROBOT ?=
export DEBIAN_FRONTEND := noninteractive
export OMNI_KIT_ACCEPT_EULA := YES

.DEFAULT_GOAL := help
.PHONY: help all weekend clean regen-cad \
        gate-0 gate-1 gate-2 gate-3 gate-4 gate-5 gate-6 gate-7 gate-8 gate-9

help:  ## List targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## --- Unattended entrypoints ------------------------------------------------
weekend:  ## Run the full DAG unattended (orchestrator owns timeouts/retries/resume)
	$(PY) orchestrator/weekend.py --config orchestrator/stages.yaml

all: gate-0 gate-1 gate-2 gate-3 gate-5 gate-7 gate-8  ## Reproduce host-side artifacts (no long RL)

regen-cad:  ## Regenerate CAD after the one sanctioned clearance edit (RUNBOOK step 2)
	$(PY) -m common.description_gen.regen_cad || echo "regen-cad: not yet implemented"

## --- Gates (all machine-checkable, none human; §10) ------------------------
gate-0:  ## Environment: versions + Isaac Sim headless smoke
	$(PY) scripts/verify_env.py

gate-1: ## Params complete & frozen (zero TODO, torque PASS)
	$(PY) scripts/gen_reports.py
	$(PYTEST) tests/test_params.py tests/test_torque.py

_cad:  ## (internal) generate one robot's parts: STL + QA + BOM + mass
	$(CADPY) scripts/gen_cad.py $(ROBOT)

gate-2: _cad  ## CAD + mesh QA + BOM + mass (runs in the CAD env via cadpy)
	$(CADPY) -m pytest tests/test_cad.py tests/test_qa.py

_desc:  ## (internal) generate URDF + MJCF for one/both robots
	$(PY) scripts/gen_descriptions.py $(ROBOT)

gate-3: _desc  ## Descriptions load (yourdfpy/mujoco) + inertia + 5 s settle
	$(PYTEST) tests/test_descriptions.py

gate-4:  ## Training success-or-DEGRADED with artifacts (orchestrator-driven)
	$(PYTEST) tests/test_training_artifacts.py

gate-5:  ## ONNX parity + MuJoCo replay
	$(PYTEST) tests/test_export.py

gate-6:  ## Runtime HIL stub (servo-bus simulator loopback)
	$(PYTEST) tests/test_runtime_hil.py

gate-7:  ## Audio codec round-trip
	$(PYTEST) tests/test_audio.py

gate-8:  ## Print package + swap schedule
	$(PYTEST) tests/test_print_package.py

gate-9:  ## Weekend report complete
	$(PYTEST) tests/test_weekend_report.py

## --- Housekeeping ----------------------------------------------------------
clean:  ## Remove caches (NEVER checkpoints, logs, or exported STLs — Directive #4)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
