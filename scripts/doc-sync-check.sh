#!/bin/sh
set -eu
grep -q 'performance-decision/v1' src/locust_templates/decision_artifact.py
grep -q 'performance-decision/v1' README.md docs/baseline-decisions.md
grep -q -- '--decision-json' src/locust_templates/cli_analyze.py README.md
printf 'PASS doc-sync-check\n'
