#!/bin/sh
set -eu
python -m pytest -q tests/integration/test_run_import_flow.py tests/test_trust_workflow.py tests/unit/test_product_workspace.py
python - <<'PY'
from locust_templates.workspace_views import inbox
s=inbox([], {})
assert '<main' in s and 'Skip to content' in s and 'aria-label="Workspace"' in s
PY
printf 'PASS ui-gate\n'
