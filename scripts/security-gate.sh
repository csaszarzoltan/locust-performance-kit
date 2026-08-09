#!/bin/sh
set -eu
python -m pytest -q tests/unit/test_run_import.py tests/test_trust_workflow.py
! grep -R -E "(AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH) PRIVATE KEY)" src tests docs
printf 'PASS security-gate\n'
