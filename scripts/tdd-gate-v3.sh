#!/bin/sh
set -eu
python -m pytest -q
! grep -R "NotImplementedError" -n src/locust_templates/run_import.py src/locust_templates/decision_artifact.py src/locust_templates/analysis_service.py
printf 'PASS tdd-gate-v3\n'
