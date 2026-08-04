"""Pre-development TDD suite for locust-kit analyze CLI (v1.6.0).

Interface tests (parser structure, flags, pyproject entry point) PASS
immediately against the stub's ``_build_parser``. Behavioral tests (exit codes
0/1/2, formats, output files, baseline resolution) FAIL with NotImplementedError
during the RED phase and become active once ``cli_analyze.main`` is implemented
per analysis/analysis-brief.md §4.2.
"""

from __future__ import annotations

import argparse
import inspect
import json
import shutil
from pathlib import Path

import pytest
import tomllib

from locust_templates.cli_analyze import _build_parser, main

REPO_ROOT = Path(__file__).parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "intelligence"
RUN_A = str(FIXTURES / "run_a" / "run_a")
RUN_B = str(FIXTURES / "run_b" / "run_b")


# ──────────────────────────────────────────────────────────────
# Interface tests — PASS immediately
# ──────────────────────────────────────────────────────────────


class TestCLIInterface:
    """locust-kit analyze parser contract and packaging."""

    def test_main_importable_and_callable(self):
        assert main is not None
        assert callable(main)

    def test_main_signature(self):
        sig = inspect.signature(main)
        assert "argv" in sig.parameters
        assert sig.parameters["argv"].default is None
        # annotation is a string under `from __future__ import annotations`
        assert "int" in str(sig.return_annotation)

    def test_module_version(self):
        from locust_templates import cli_analyze

        assert cli_analyze.__version__ == "1.6.0"

    def test_build_parser_returns_argument_parser(self):
        parser = _build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_analyze_subcommand(self):
        args = _build_parser().parse_args(["analyze", "--csv", "some_prefix"])
        assert args.command == "analyze"
        assert args.csv == "some_prefix"

    def test_parser_no_subcommand_is_not_fatal(self):
        args = _build_parser().parse_args([])
        assert args.command is None

    def test_parser_slo_is_repeatable(self):
        args = _build_parser().parse_args(
            ["analyze", "--csv", "x", "--slo", "p95=500", "--slo", "error_rate=0.01"]
        )
        assert args.slo == ["p95=500", "error_rate=0.01"]

    def test_parser_slo_default_empty(self):
        assert _build_parser().parse_args(["analyze", "--csv", "x"]).slo == []

    def test_parser_baseline_default_none(self):
        assert _build_parser().parse_args(["analyze", "--csv", "x"]).baseline is None

    def test_parser_format_default_markdown(self):
        assert _build_parser().parse_args(["analyze", "--csv", "x"]).format == "markdown"

    def test_parser_output_default_dash(self):
        assert _build_parser().parse_args(["analyze", "--csv", "x"]).output == "-"

    def test_parser_llm_default_false_and_store_true(self):
        parser = _build_parser()
        assert parser.parse_args(["analyze", "--csv", "x"]).llm is False
        assert parser.parse_args(["analyze", "--csv", "x", "--llm"]).llm is True

    def test_parser_version_flag_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            _build_parser().parse_args(["analyze", "--version"])
        assert getattr(excinfo.value, "code", None) == 0
        assert "locust-kit 1.6.0" in capsys.readouterr().out

    def test_pyproject_entry_point_and_version(self):
        with open(REPO_ROOT / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        assert pyproject["project"]["version"] == "1.6.0"
        assert pyproject["project"]["scripts"]["locust-kit"] == "locust_templates.cli_analyze:main"


# ──────────────────────────────────────────────────────────────
# Behavioral tests — RED phase (NotImplementedError → skip)
# ──────────────────────────────────────────────────────────────


def _main(argv):
    """Call main(), skipping during RED when the stub raises."""
    try:
        return main(argv)
    except NotImplementedError:
        pytest.skip("cli_analyze.main not implemented yet — RED phase")


class TestCLIExitCodesBehavior:
    """Exit-code contract: 0 OK, 1 usage/IO/parse error, 2 measured SLO violation."""

    pytestmark = pytest.mark.unit

    def test_no_subcommand_prints_help_exit_one(self, capsys):
        assert _main([]) == 1
        assert "usage" in capsys.readouterr().out.lower()

    def test_missing_csv_exit_one(self, capsys):
        assert _main(["analyze"]) == 1
        assert "--csv" in capsys.readouterr().err

    def test_stats_file_not_found_exit_one(self, capsys):
        assert _main(["analyze", "--csv", "/nonexistent/prefix_xyz"]) == 1

    def test_invalid_slo_key_exit_one(self, capsys):
        assert _main(["analyze", "--csv", RUN_A, "--slo", "bogus=1"]) == 1

    def test_invalid_slo_value_exit_one(self):
        assert _main(["analyze", "--csv", RUN_A, "--slo", "p95=abc"]) == 1

    def test_unknown_format_exit_one(self, capsys):
        assert _main(["analyze", "--csv", RUN_A, "--format", "xml"]) == 1

    def test_output_path_is_directory_exits_one(self, tmp_path, capsys):
        """--output pointing at a directory → clean 'error:' + exit 1 (review #5)."""
        target = tmp_path / "adir"
        target.mkdir()
        rc = _main(["analyze", "--csv", RUN_A, "--output", str(target)])
        assert rc == 1
        assert "error:" in capsys.readouterr().err

    def test_unresolvable_baseline_exit_one(self, capsys):
        assert _main(["analyze", "--csv", RUN_A, "--baseline", "no-such-baseline"]) == 1

    def test_run_a_clean_exit_zero(self):
        assert _main(["analyze", "--csv", RUN_A]) == 0

    def test_run_a_with_passed_slo_exit_zero(self):
        assert _main(["analyze", "--csv", RUN_A, "--slo", "p95=500"]) == 0

    def test_run_b_violated_slo_exit_two(self):
        assert _main(["analyze", "--csv", RUN_B, "--slo", "p95=500"]) == 2

    def test_run_b_without_slo_is_advisory_exit_zero(self):
        assert _main(["analyze", "--csv", RUN_B]) == 0

    def test_version_flag_exits_zero(self, capsys):
        try:
            rc = main(["analyze", "--version"])
        except NotImplementedError:
            pytest.skip("cli_analyze.main not implemented yet — RED phase")
        except SystemExit as excinfo:
            assert getattr(excinfo, "code", None) == 0
            assert "locust-kit 1.6.0" in capsys.readouterr().out
            return
        assert rc == 0


class TestCLIFormatBehavior:
    """markdown (default) and json output, stdout and file targets."""

    pytestmark = pytest.mark.unit

    def test_default_markdown_stdout(self, capsys):
        rc = _main(["analyze", "--csv", RUN_A])
        assert rc == 0
        assert "# AI Performance Intelligence Report" in capsys.readouterr().out

    def test_json_format_stdout(self, capsys):
        rc = _main(["analyze", "--csv", RUN_B, "--slo", "p95=500", "--format", "json"])
        assert rc == 2
        data = json.loads(capsys.readouterr().out)
        assert data["exit_code"] == 2
        assert data["slo_results"][0]["status"] == "violated"
        assert data["ai_insights"] is None

    def test_json_format_contract_keys(self, capsys):
        _main(["analyze", "--csv", RUN_A, "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        for key in ("csv_prefix", "generated_at", "tool", "version", "baseline",
                    "summary", "slo_results", "anomalies", "bottlenecks",
                    "capacity_projections", "insights", "ai_insights", "exit_code"):
            assert key in data, f"missing {key}"

    def test_markdown_output_file(self, tmp_path):
        out = tmp_path / "report.md"
        rc = _main(["analyze", "--csv", RUN_A, "--output", str(out)])
        assert rc == 0
        assert out.exists()
        assert "# AI Performance Intelligence Report" in out.read_text(encoding="utf-8")

    def test_json_output_file(self, tmp_path):
        out = tmp_path / "report.json"
        rc = _main(["analyze", "--csv", RUN_B, "--slo", "p95=500",
                    "--format", "json", "--output", str(out)])
        assert rc == 2
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["exit_code"] == 2

    def test_output_parent_dirs_created(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "report.md"
        rc = _main(["analyze", "--csv", RUN_A, "--output", str(out)])
        assert rc == 0
        assert out.exists()

    def test_markdown_lists_violation_and_sections(self, capsys):
        rc = _main(["analyze", "--csv", RUN_B, "--slo", "p95=500"])
        assert rc == 2
        out = capsys.readouterr().out
        assert "## SLO Results" in out
        assert "violated" in out
        assert "## Anomalies" in out
        assert "## Insights" in out


class TestCLIBaselineBehavior:
    """--baseline resolution: prior-run CSV prefix, then .baselines/<name>.json."""

    pytestmark = pytest.mark.unit

    def test_baseline_prior_run_prefix(self):
        rc = _main(["analyze", "--csv", RUN_B, "--baseline", RUN_A])
        assert rc == 0  # no SLOs → advisory

    def test_baseline_prior_run_prefix_with_slo(self):
        rc = _main(["analyze", "--csv", RUN_B, "--baseline", RUN_A, "--slo", "p95=500"])
        assert rc == 2

    def test_baseline_stored_json(self, tmp_path, monkeypatch, capsys):
        (tmp_path / ".baselines").mkdir()
        (tmp_path / ".baselines" / "prod.json").write_text(
            json.dumps({
                "name": "prod",
                "created_at": "2026-01-01T00:00:00+00:00",
                "endpoints": [
                    {"name": "/api/items", "type": "GET", "request_count": 15000,
                     "failure_count": 15, "avg_response_time": 68.0, "p50": 60.0,
                     "p95": 95.0, "p99": 120.0, "rps": 15.0},
                ],
            }),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        rc = _main(["analyze", "--csv", RUN_A, "--baseline", "prod"])
        assert rc == 0

    def test_baseline_stored_json_missing_endpoint_maps(self, tmp_path, monkeypatch):
        """Stored baseline with no endpoints must still resolve cleanly."""
        (tmp_path / ".baselines").mkdir()
        (tmp_path / ".baselines" / "empty.json").write_text(
            json.dumps({"name": "empty", "created_at": "2026-01-01T00:00:00+00:00", "endpoints": []}),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        assert _main(["analyze", "--csv", RUN_A, "--baseline", "empty"]) == 0

    def test_stats_only_prefix_with_baseline_exits_cleanly(self, tmp_path, capsys):
        """Stats-only prefix + baseline: clean exit, no traceback (review #1)."""
        shutil.copy(FIXTURES / "run_b" / "run_b_stats.csv", tmp_path / "stats_only_stats.csv")
        rc = _main(["analyze", "--csv", str(tmp_path / "stats_only"), "--baseline", RUN_A])
        assert rc == 0
        assert "Traceback" not in capsys.readouterr().err


class TestCLILLMBehavior:
    """--llm opt-in: unconfigured/failing provider → statistical fallback."""

    pytestmark = pytest.mark.unit

    def test_llm_flag_unconfigured_falls_back(self, monkeypatch, capsys):
        monkeypatch.delenv("LOCUST_KIT_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        rc = _main(["analyze", "--csv", RUN_A, "--llm"])
        assert rc == 0  # fallback never changes the exit code
        out = capsys.readouterr().out
        assert "# AI Performance Intelligence Report" in out
        assert "## AI Insights" not in out  # no LLM section on fallback
