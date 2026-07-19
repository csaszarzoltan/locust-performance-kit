"""Tests for CLI entry point locust-report (TDD).

These tests define the contract for the argparse-based CLI that generates
reports from Locust CSV output. They will FAIL until cli.py is implemented.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from locust_templates.cli import main

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestCLIInterface:
    """Verify that cli.main() exists and is callable."""

    def test_main_is_importable(self):
        """cli.main should be importable."""
        assert main is not None
        assert callable(main)


# ──────────────────────────────────────────────────────────────
# Format tests
# ──────────────────────────────────────────────────────────────


class TestCLIFormat:
    """Tests for CLI --format option."""

    @pytest.mark.unit
    def test_cli_html_format_default(self, tmp_path):
        """No --format → HTML output by default."""
        output = tmp_path / "report.html"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--output", str(output),
        ])
        assert result == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<html" in content.lower()

    @pytest.mark.unit
    def test_cli_json_format(self, tmp_path):
        """--format json → JSON output file."""
        output = tmp_path / "report.json"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "json",
            "--output", str(output),
        ])
        assert result == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "metadata" in parsed

    @pytest.mark.unit
    def test_cli_markdown_format(self, tmp_path):
        """--format markdown → Markdown output file."""
        output = tmp_path / "report.md"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "markdown",
            "--output", str(output),
        ])
        assert result == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "# Locust Performance Report" in content

    @pytest.mark.unit
    def test_cli_junit_format(self, tmp_path):
        """--format junit → JUnit XML output file."""
        output = tmp_path / "junit.xml"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "junit",
            "--output", str(output),
        ])
        assert result == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert content.startswith("<?xml")

    @pytest.mark.unit
    def test_cli_output_path(self, tmp_path):
        """--output PATH should write to the specified path."""
        output = tmp_path / "custom" / "report.json"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "json",
            "--output", str(output),
        ])
        assert result == 0
        assert output.exists()

    @pytest.mark.unit
    def test_cli_stdout_json(self, capsys):
        """No --output with --format json → writes to stdout."""
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "metadata" in parsed

    @pytest.mark.unit
    def test_cli_stdout_markdown(self, capsys):
        """No --output with --format markdown → writes to stdout."""
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "markdown",
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "# Locust Performance Report" in captured.out

    @pytest.mark.unit
    def test_cli_stdout_dash(self, capsys):
        """--output - → writes to stdout for any format."""
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "json",
            "--output", "-",
        ])
        assert result == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "metadata" in parsed


# ──────────────────────────────────────────────────────────────
# Threshold tests
# ──────────────────────────────────────────────────────────────


class TestCLIThresholds:
    """Tests for CLI --p95-threshold and --p99-threshold options."""

    @pytest.mark.unit
    def test_cli_p95_threshold(self, tmp_path):
        """--p95-threshold 500 should set p95 threshold."""
        output = tmp_path / "report.json"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "json",
            "--output", str(output),
            "--p95-threshold", "500",
        ])
        assert result == 0
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["thresholds"]["p95"] == 500

    @pytest.mark.unit
    def test_cli_p99_threshold(self, tmp_path):
        """--p99-threshold 800 should set p99 threshold."""
        output = tmp_path / "report.json"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "json",
            "--output", str(output),
            "--p99-threshold", "800",
        ])
        assert result == 0
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["thresholds"]["p99"] == 800

    @pytest.mark.unit
    def test_cli_exit_code_success(self, tmp_path):
        """Valid run with passing thresholds → exit 0."""
        output = tmp_path / "report.html"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--output", str(output),
            "--p95-threshold", "1000",
            "--p99-threshold", "2000",
        ])
        assert result == 0

    @pytest.mark.unit
    def test_cli_exit_code_threshold_violation(self, tmp_path):
        """Threshold exceeded → exit code 2."""
        output = tmp_path / "report.html"
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--output", str(output),
            "--p95-threshold", "50",
            "--p99-threshold", "100",
        ])
        assert result == 2

    @pytest.mark.unit
    def test_cli_exit_code_file_not_found(self, tmp_path):
        """Missing CSV prefix → exit code 1."""
        result = main([
            "/nonexistent/path/prefix",
            "--format", "json",
        ])
        assert result == 1

    @pytest.mark.unit
    def test_cli_exit_code_invalid_format(self, tmp_path):
        """Unsupported format → exit code 1."""
        result = main([
            str(FIXTURES_DIR / "sample"),
            "--format", "xml",
        ])
        assert result == 1


# ──────────────────────────────────────────────────────────────
# Help / version tests
# ──────────────────────────────────────────────────────────────


class TestCLIHelpVersion:
    """Tests for CLI --help and --version."""

    @pytest.mark.unit
    def test_cli_version(self, capsys):
        """--version should print version string."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "1.2" in captured.out

    @pytest.mark.unit
    def test_cli_help(self, capsys):
        """--help should print usage information."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "csv_prefix" in captured.out.lower() or "format" in captured.out.lower()

    @pytest.mark.unit
    def test_cli_no_args_exits_error(self, capsys):
        """No arguments → exit code 1 with usage message."""
        result = main([])
        assert result == 1
