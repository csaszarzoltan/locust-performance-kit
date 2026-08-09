#!/bin/sh
set -eu
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
  tests/unit/test_run_import.py tests/unit/test_decision_artifact.py \
  tests/unit/test_comparison_view.py tests/unit/test_workspace_runs.py \
  tests/unit/test_analysis_service.py -p pytest_cov \
  --cov=locust_templates.run_import \
  --cov=locust_templates.decision_artifact \
  --cov=locust_templates.comparison_view \
  --cov=locust_templates.analysis_service \
  --cov-report=term-missing --cov-fail-under=90
coverage report --include='*/run_import.py,*/decision_artifact.py' --fail-under=95
printf 'PASS coverage-gate\n'
