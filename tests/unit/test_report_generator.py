"""Smoke tests for HTML report generator (TASK-4).

Interface tests verify API surface. Behavioral tests define the contract
for CSV parsing and HTML report generation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from locust_templates.report_generator import HTMLReportGenerator

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that HTMLReportGenerator exists with correct methods."""

    def test_class_exists(self):
        """HTMLReportGenerator should be importable."""
        assert HTMLReportGenerator is not None

    def test_has_from_csv_classmethod(self):
        """from_csv should be a classmethod."""
        assert hasattr(HTMLReportGenerator, "from_csv")

    def test_has_generate_method(self):
        """generate should be an instance method."""
        assert hasattr(HTMLReportGenerator, "generate")

    def test_init_accepts_stats_failures_thresholds(self):
        """__init__ should accept stats, failures, thresholds."""
        gen = HTMLReportGenerator(
            stats=[{"Name": "/api/items", "Request Count": 100}],
            failures=[],
            thresholds={"p95": 500.0, "p99": 1000.0},
        )
        assert gen.stats == [{"Name": "/api/items", "Request Count": 100}]
        assert gen.failures == []
        assert gen.thresholds["p95"] == 500.0


# ──────────────────────────────────────────────────────────────
# Behavioral pre-state tests (fail until implementation)
# ──────────────────────────────────────────────────────────────


class TestFromCsv:
    """Behavioral tests for from_csv() — fail until implemented."""

    @pytest.mark.unit
    def test_from_csv_parses_stats(self):
        """from_csv() should parse the _stats.csv file and populate stats list."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        assert len(gen.stats) > 0
        # Should have parsed the endpoint rows
        names = [s.get("Name", s.get("name", "")) for s in gen.stats]
        assert any("/api/items" in str(n) for n in names)

    @pytest.mark.unit
    def test_from_csv_parses_failures(self):
        """from_csv() should parse the _failures.csv file if it exists."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        # Failures may be empty if file doesn't exist, but shouldn't crash
        assert isinstance(gen.failures, list)


class TestGenerate:
    """Behavioral tests for generate() — fail until implemented."""

    @pytest.mark.unit
    def test_generate_creates_html_file(self, tmp_path):
        """generate() should create an HTML file at the given path."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        result_path = gen.generate(str(output))
        assert Path(result_path).exists()
        assert tmp_path.exists()

    @pytest.mark.unit
    def test_generated_html_is_valid(self, tmp_path):
        """Generated HTML should contain key report sections."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        gen.generate(str(output))
        content = output.read_text()
        assert "<html" in content.lower()
        assert "</html>" in content.lower()
        # Should contain endpoint names
        assert "/api/items" in content or "api" in content.lower()

    @pytest.mark.unit
    def test_generated_html_has_summary_stats(self, tmp_path):
        """HTML should include total requests, failures, p95, p99."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        gen.generate(str(output))
        content = output.read_text()
        # Should mention some performance metrics
        assert "p95" in content.lower() or "95%" in content

    @pytest.mark.unit
    def test_generated_html_is_self_contained(self, tmp_path):
        """HTML should have no external CSS/JS dependencies."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        gen.generate(str(output))
        content = output.read_text()
        # No external stylesheet links
        assert 'href="http' not in content
        assert 'src="http' not in content

    @pytest.mark.unit
    def test_generated_html_under_500kb(self, tmp_path):
        """HTML file should be under 500KB for typical test results."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        gen.generate(str(output))
        size = output.stat().st_size
        assert size < 500 * 1024, f"HTML file is {size} bytes, expected < 500KB"

    @pytest.mark.unit
    def test_threshold_pass_fail_indicators(self, tmp_path):
        """HTML should show green/red for threshold pass/fail."""
        gen = HTMLReportGenerator.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 500.0, "p99": 1000.0},
        )
        output = tmp_path / "report.html"
        gen.generate(str(output))
        content = output.read_text()
        # Should have some pass/fail indication
        lowered = content.lower()
        assert (
            "pass" in lowered
            or "fail" in lowered
            or "green" in lowered
            or "red" in lowered
        )


# ──────────────────────────────────────────────────────────────
# Backward compatibility tests (v1.2.0 shim)
# ──────────────────────────────────────────────────────────────


class TestBackwardCompat:
    """Verify HTMLReportGenerator backward compatibility after v1.2.0 refactor."""

    @pytest.mark.unit
    def test_backward_compat_from_csv_signature(self):
        """from_csv(prefix, thresholds=...) should work unchanged."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        assert gen is not None
        gen2 = HTMLReportGenerator.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 500.0, "p99": 1000.0},
        )
        assert gen2 is not None

    @pytest.mark.unit
    def test_backward_compat_generate_signature(self, tmp_path):
        """generate('report.html') should return str path."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        result = gen.generate(str(output))
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_backward_compat_init_stats_failures_thresholds(self):
        """HTMLReportGenerator(stats=..., failures=..., thresholds=...) works."""
        gen = HTMLReportGenerator(
            stats=[{"Name": "/api/items", "Request Count": 100}],
            failures=[
            {"Method": "GET", "Name": "/api/items", "Type": "ERR", "Error": "oops"}
        ],
            thresholds={"p95": 500.0, "p99": 1000.0},
        )
        assert gen is not None

    @pytest.mark.unit
    def test_backward_compat_generate_still_produces_html(self, tmp_path):
        """generate() should still produce valid HTML after refactor."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.html"
        gen.generate(str(output))
        content = output.read_text(encoding="utf-8")
        assert "<html" in content.lower()
        assert "</html>" in content.lower()


# ──────────────────────────────────────────────────────────────
# New convenience methods (v1.2.0)
# ──────────────────────────────────────────────────────────────


class TestNewMethods:
    """Tests for new to_json(), to_markdown(), to_junit() methods (v1.2.0)."""

    @pytest.mark.unit
    def test_new_to_json_method(self, tmp_path):
        """to_json() should write valid JSON file."""
        import json

        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.json"
        result = gen.to_json(str(output))
        assert Path(result).exists()
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "metadata" in parsed

    @pytest.mark.unit
    def test_new_to_markdown_method(self, tmp_path):
        """to_markdown() should write valid Markdown file."""
        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "report.md"
        result = gen.to_markdown(str(output))
        assert Path(result).exists()
        content = output.read_text(encoding="utf-8")
        assert "# Locust Performance Report" in content

    @pytest.mark.unit
    def test_new_to_junit_method(self, tmp_path):
        """to_junit() should write valid JUnit XML file."""
        import xml.etree.ElementTree as ET

        gen = HTMLReportGenerator.from_csv(str(FIXTURES_DIR / "sample"))
        output = tmp_path / "junit.xml"
        result = gen.to_junit(str(output))
        assert Path(result).exists()
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root.tag == "testsuites"
