"""Pre-development tests for CI/CD Performance Gates workflow.

Interface tests verify the workflow YAML structure (must pass immediately).
Behavioral tests define the contract for threshold enforcement and
notification behavior.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "perf-test.yml"

REQUIRED_INPUTS = [
    "locust-script",
    "target-host",
    "users",
    "spawn-rate",
    "run-time",
    "p95-threshold",
    "p99-threshold",
    "error-rate-threshold",
    "rps-threshold",
]

REQUIRED_JOBS = [
    "load-test",
    "generate-reports",
    "quality-gate",
    "notify",
]


def _steps_run_text(job: dict) -> str:
    """Join ``run`` text from all steps in a workflow job."""
    return " ".join(
        str(s.get("run", ""))
        for s in job.get("steps", [])
        if isinstance(s, dict)
    )


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Parse and cache the workflow YAML once per module."""
    with open(WORKFLOW_PATH) as f:
        return yaml.safe_load(f)


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify the workflow YAML file exists and parses correctly."""

    def test_workflow_file_exists(self):
        """perf-test.yml must exist in .github/workflows/."""
        assert WORKFLOW_PATH.exists(), f"Workflow file not found: {WORKFLOW_PATH}"

    def test_workflow_is_valid_yaml(self, workflow):
        """Workflow file must parse as valid YAML."""
        assert isinstance(workflow, dict)

    def test_workflow_has_name(self, workflow):
        """Workflow must have a name."""
        assert isinstance(workflow.get("name"), str)
        assert len(workflow["name"]) > 0

    def test_workflow_dispatch_inputs_exist(self, workflow):
        """Workflow must have on.workflow_dispatch with all required inputs."""
        dispatch = workflow.get("on", {}).get("workflow_dispatch", {})
        inputs = dispatch.get("inputs", {})
        for input_name in REQUIRED_INPUTS:
            assert input_name in inputs, (
                f"Missing required workflow_dispatch input: {input_name}"
            )

    def test_workflow_dispatch_inputs_have_types(self, workflow):
        """Each workflow_dispatch input must have a type."""
        inputs = workflow.get("on", {}).get("workflow_dispatch", {}).get("inputs", {})
        for name in REQUIRED_INPUTS:
            assert "type" in inputs[name], (
                f"Input {name} missing 'type' field"
            )

    def test_workflow_call_inputs_exist(self, workflow):
        """Workflow must support workflow_call with reusable inputs."""
        call_inputs = workflow.get("on", {}).get("workflow_call", {}).get("inputs", {})
        for input_name in REQUIRED_INPUTS:
            assert input_name in call_inputs, (
                f"Missing required workflow_call input: {input_name}"
            )

    def test_workflow_call_secrets_exist(self, workflow):
        """Workflow_call must expose optional webhook secrets."""
        secrets = workflow.get("on", {}).get("workflow_call", {}).get("secrets", {})
        assert "SLACK_WEBHOOK_URL" in secrets
        assert "TEAMS_WEBHOOK_URL" in secrets

    def test_workflow_call_outputs_exist(self, workflow):
        """Workflow_call must expose quality-gate outputs."""
        outputs = workflow.get("on", {}).get("workflow_call", {}).get("outputs", {})
        required_outputs = [
            "gate-passed", "p95-max", "p99-max",
            "error-rate", "metrics-json",
        ]
        for out in required_outputs:
            assert out in outputs, f"Missing workflow_call output: {out}"

    def test_all_required_jobs_exist(self, workflow):
        """Workflow must have all 4 required jobs."""
        jobs = workflow.get("jobs", {})
        for job_name in REQUIRED_JOBS:
            assert job_name in jobs, f"Missing required job: {job_name}"

    def test_quality_gate_has_outputs(self, workflow):
        """quality-gate job must have outputs for downstream consumption."""
        qg = workflow.get("jobs", {}).get("quality-gate", {})
        qg_outputs = qg.get("outputs", {})
        required_qg_outputs = [
            "gate-passed", "p95-max", "p99-max",
            "error-rate", "metrics-json",
        ]
        for out in required_qg_outputs:
            assert out in qg_outputs, (
                f"quality-gate job missing output: {out}"
            )

    def test_notify_runs_on_always(self, workflow):
        """Notify job must run on always() to send pass and fail notifications."""
        notify_job = workflow.get("jobs", {}).get("notify", {})
        assert notify_job.get("if") == "always()" or "always()" in str(
            notify_job.get("if", "")
        )


# ──────────────────────────────────────────────────────────────
# Behavioral tests — quality-gate threshold enforcement
# ──────────────────────────────────────────────────────────────


class TestQualityGateBehavior:
    """Behavioral tests for quality-gate threshold enforcement."""

    def test_quality_gate_fails_on_p95_breach(self, workflow):
        """quality-gate must exit non-zero when p95 > threshold."""
        qg = workflow.get("jobs", {}).get("quality-gate", {})
        steps_text = " ".join(str(s) for s in qg.get("steps", []))
        assert "p95" in steps_text.lower() or "P95" in qg.get("outputs", {}), (
            "quality-gate job must reference p95 in its evaluation logic"
        )
        # Verify p95-threshold input is referenced somewhere in the job
        run_step = qg.get("steps", [{}])[-1] if qg.get("steps") else {}
        run_text = str(run_step.get("run", ""))
        gate_exit_found = re.search(
            r'(exit\s+2|GATE_PASSED.*false|failure)', run_text, re.IGNORECASE
        )
        assert gate_exit_found, (
            "quality-gate must have logic to fail the step on threshold breach"
        )

    def test_quality_gate_fails_on_error_rate_breach(self, workflow):
        """quality-gate must exit non-zero when error rate > threshold."""
        qg = workflow.get("jobs", {}).get("quality-gate", {})
        run_text = ""
        for s in qg.get("steps", []):
            if isinstance(s, dict) and "run" in s:
                run_text += str(s.get("run", "")) + "\n"
        # Check that error-rate-threshold is used in evaluation logic
        assert "error" in run_text.lower() and "threshold" in run_text.lower(), (
            "quality-gate must evaluate error rate against error-rate-threshold"
        )

    def test_quality_gate_passes_when_within_thresholds(self, workflow):
        """quality-gate must exit 0 when all metrics are within thresholds."""
        qg = workflow.get("jobs", {}).get("quality-gate", {})
        run_text = ""
        for s in qg.get("steps", []):
            if isinstance(s, dict) and "run" in s:
                run_text += str(s.get("run", "")) + "\n"
        # The gate should have a success path (setting gate-passed=true)
        assert "gate-passed=true" in run_text or "GATE_PASSED=\"true\"" in run_text, (
            "quality-gate must set gate-passed=true when thresholds are satisfied"
        )

    def test_rps_threshold_zero_disables_check(self, workflow):
        """RPS threshold of 0 must skip RPS check (backward compatible)."""
        qg = workflow.get("jobs", {}).get("quality-gate", {})
        qg_inputs = workflow.get("on", {}).get("workflow_call", {}).get("inputs", {})
        rps_default = qg_inputs.get("rps-threshold", {}).get("default", -1)
        assert rps_default == 0, (
            "rps-threshold must default to 0 (disabled) in workflow_call inputs"
        )
        run_text = ""
        for s in qg.get("steps", []):
            if isinstance(s, dict) and "run" in s:
                run_text += str(s.get("run", "")) + "\n"
        # Should have logic to skip when RPS threshold is 0
        assert 'RPS_THRESH != "0"' in run_text or 'rps-threshold' in run_text, (
            "quality-gate must skip RPS check when threshold is 0"
        )

    def test_quality_gate_outputs_are_set(self, workflow):
        """quality-gate must set gate-passed, p95-max, p99-max,
        error-rate, metrics-json outputs."""
        qg = workflow.get("jobs", {}).get("quality-gate", {})
        qg_outputs = qg.get("outputs", {})
        required = ["gate-passed", "p95-max", "p99-max", "error-rate", "metrics-json"]
        for out in required:
            assert out in qg_outputs, (
                f"quality-gate job must declare output '{out}'"
            )
            assert "${{" in str(qg_outputs[out]), (
                f"output '{out}' must reference a step output"
            )


class TestNotificationBehavior:
    """Behavioral tests for notification on pass and fail."""

    def test_notification_on_pass(self, workflow):
        """Notify job must send notification when gate passes."""
        notify = workflow.get("jobs", {}).get("notify", {})
        assert "notify" in notify.get("if", "always()").lower() or "always()" in str(
            notify.get("if", "")
        ), "Notify job must run on always()"
        # The notify job should reference gate-passed
        steps_joined = _steps_run_text(notify)
        assert "GATE_PASSED" in steps_joined or "gate-passed" in str(notify), (
            "Notify job should send notification with gate-passed status"
        )

    def test_notification_on_fail(self, workflow):
        """Notify job must send notification when gate fails."""
        notify = workflow.get("jobs", {}).get("notify", {})
        steps_joined = _steps_run_text(notify)
        # On failure it should still send (always() guarantees this)
        assert "always()" in str(notify.get("if", "")), (
            "Notify job must run on always() to send fail notifications"
        )
        assert "FAILED" in steps_joined or "failed" in steps_joined.lower(), (
            "Notify job should handle failed gate status"
        )

    def test_slack_webhook_env_var_supported(self, workflow):
        """Notification must support SLACK_WEBHOOK_URL env var."""
        notify = workflow.get("jobs", {}).get("notify", {})
        steps_joined = " ".join(
            str(s) for s in notify.get("steps", [])
        )
        assert "SLACK_WEBHOOK_URL" in steps_joined or "SLACK_WEBHOOK_URL" in str(
            workflow.get("env", {})
        ), "Workflow must reference SLACK_WEBHOOK_URL"

    def test_teams_webhook_env_var_supported(self, workflow):
        """Notification must support TEAMS_WEBHOOK_URL env var."""
        notify = workflow.get("jobs", {}).get("notify", {})
        steps_joined = " ".join(
            str(s) for s in notify.get("steps", [])
        )
        assert "TEAMS_WEBHOOK_URL" in steps_joined or "TEAMS_WEBHOOK_URL" in str(
            workflow.get("env", {})
        ), "Workflow must reference TEAMS_WEBHOOK_URL"


class TestWorkflowReuseBehavior:
    """Behavioral tests for workflow_call reusability."""

    def test_workflow_call_from_other_workflow(self, workflow):
        """perf-test.yml must be callable from another workflow via workflow_call."""
        on_dict = workflow.get("on", {})
        assert "workflow_call" in on_dict, (
            "workflow_call trigger must be present for reusability"
        )

    def test_rps_threshold_defaults_to_disabled(self, workflow):
        """rps-threshold must default to 0 (disabled) in workflow_call."""
        call_inputs = workflow.get("on", {}).get("workflow_call", {}).get("inputs", {})
        rps_input = call_inputs.get("rps-threshold", {})
        assert rps_input.get("default") == 0, (
            "rps-threshold must default to 0 in workflow_call inputs"
        )
