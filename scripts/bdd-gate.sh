#!/bin/sh
set -eu
python -m pytest -q tests/unit/test_run_import.py tests/unit/test_workspace_runs.py tests/unit/test_decision_artifact.py tests/integration/test_run_import_flow.py
for id in 001 002 003 004 005 006; do grep -Rq "us$id" tests || { echo "FAIL missing US-$id"; exit 1; }; done
printf 'PASS bdd-gate\n'
