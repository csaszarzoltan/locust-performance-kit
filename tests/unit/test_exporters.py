"""Tests for report exporters: HTML, JSON, Markdown, JUnit XML (TDD).

These tests define the contract for the Strategy-pattern exporters that
render ReportData into various formats. They will FAIL until exporters.py
is implemented.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from locust_templates.exporters import (
    HTMLExporter,
    JSONExporter,
    JUnitXMLExporter,
    MarkdownExporter,
    ReportExporter,
)
from locust_templates.report_data import ReportData

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestExporterInterface:
    """Verify that exporter classes exist and follow the Strategy interface."""

    def test_report_exporter_is_importable(self):
        """ReportExporter ABC should be importable."""
        assert ReportExporter is not None

    def test_html_exporter_is_importable(self):
        """HTMLExporter should be importable."""
        assert HTMLExporter is not None

    def test_json_exporter_is_importable(self):
        """JSONExporter should be importable."""
        assert JSONExporter is not None

    def test_markdown_exporter_is_importable(self):
        """MarkdownExporter should be importable."""
        assert MarkdownExporter is not None

    def test_junit_xml_exporter_is_importable(self):
        """JUnitXMLExporter should be importable."""
        assert JUnitXMLExporter is not None

    def test_all_exporters_subclass_report_exporter(self):
        """All concrete exporters should subclass ReportExporter."""
        assert issubclass(HTMLExporter, ReportExporter)
        assert issubclass(JSONExporter, ReportExporter)
        assert issubclass(MarkdownExporter, ReportExporter)
        assert issubclass(JUnitXMLExporter, ReportExporter)


# ──────────────────────────────────────────────────────────────
# Shared fixture
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def report_data():
    """Load ReportData from sample fixtures."""
    return ReportData.from_csv(str(FIXTURES_DIR / "sample"))


@pytest.fixture
def report_data_with_thresholds():
    """Load ReportData with thresholds set."""
    return ReportData.from_csv(
        str(FIXTURES_DIR / "sample"),
        thresholds={"p95": 500.0, "p99": 1000.0},
    )


# ──────────────────────────────────────────────────────────────
# HTMLExporter tests
# ──────────────────────────────────────────────────────────────


class TestHTMLExporter:
    """Tests for HTMLExporter — fail until implemented."""

    @pytest.mark.unit
    def test_html_export_creates_file(self, report_data, tmp_path):
        """export() should create an HTML file at the specified path."""
        output = tmp_path / "report.html"
        result = HTMLExporter().export(report_data, str(output))
        assert Path(result).exists()

    @pytest.mark.unit
    def test_html_export_returns_absolute_path(self, report_data, tmp_path):
        """export() should return the absolute path as a string."""
        output = tmp_path / "report.html"
        result = HTMLExporter().export(report_data, str(output))
        assert isinstance(result, str)
        assert Path(result).is_absolute()

    @pytest.mark.unit
    def test_html_export_is_valid_html(self, report_data, tmp_path):
        """Output should contain <html>, </html>, and <!DOCTYPE>."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "<html" in content.lower()
        assert "</html>" in content.lower()
        assert "<!doctype" in content.lower() or "<!DOCTYPE" in content

    @pytest.mark.unit
    def test_html_export_is_self_contained(self, report_data, tmp_path):
        """Output should have no external CSS/JS dependencies."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert 'href="http' not in content
        assert 'src="http' not in content

    @pytest.mark.unit
    def test_html_export_contains_endpoints(self, report_data, tmp_path):
        """Endpoint names should appear in the output."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "/api/items" in content

    @pytest.mark.unit
    def test_html_export_contains_summary(self, report_data, tmp_path):
        """Summary metrics should appear in the output."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "5000" in content or "5,000" in content  # total requests
        assert "83" in content  # RPS

    @pytest.mark.unit
    def test_html_export_threshold_pass_shows_green(
        self, report_data_with_thresholds, tmp_path
    ):
        """PASS indicator should appear with green CSS class."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data_with_thresholds, str(output))
        content = output.read_text(encoding="utf-8")
        assert "pass" in content.lower()

    @pytest.mark.unit
    def test_html_export_threshold_fail_shows_red(self, tmp_path):
        """FAIL indicator should appear with red CSS class."""
        data = ReportData.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 100.0, "p99": 200.0},
        )
        output = tmp_path / "report.html"
        HTMLExporter().export(data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "fail" in content.lower()

    @pytest.mark.unit
    def test_html_export_creates_parent_dirs(self, report_data, tmp_path):
        """Nested output path should have parent directories created."""
        output = tmp_path / "a" / "b" / "report.html"
        HTMLExporter().export(report_data, str(output))
        assert output.exists()

    @pytest.mark.unit
    def test_html_export_under_500kb(self, report_data, tmp_path):
        """Output file should be under 500KB with typical test data."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        size = output.stat().st_size
        assert size < 500 * 1024, f"HTML file is {size} bytes, expected < 500KB"

    @pytest.mark.unit
    def test_html_export_non_ascii_endpoint(self, tmp_path):
        """Non-ASCII endpoint name should render correctly in UTF-8."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "unicode"
            stats_content = (
                '"Type","Name","Request Count","Failure Count",'
                '"Median Response Time","Average Response Time",'
                '"Min Response Time","Max Response Time",'
                '"Average Content Size","Requests/s",'
                '"50%","66%","75%","80%","90%","95%","98%","99%",'
                '"99.9%","99.99%","100%"\n'
                '"GET","/api/café","100","0","50","55","20","200",'
                '"128","10.0","50","60","65","70","80","90","120","150",'
                '"200","200","200"\n'
            )
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_content, encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            output = tmp_path / "report.html"
            HTMLExporter().export(data, str(output))
            content = output.read_text(encoding="utf-8")
            assert "café" in content


# ──────────────────────────────────────────────────────────────
# JSONExporter tests
# ──────────────────────────────────────────────────────────────


class TestJSONExporter:
    """Tests for JSONExporter — fail until implemented."""

    @pytest.mark.unit
    def test_json_export_creates_file(self, report_data, tmp_path):
        """export() should create a JSON file at the specified path."""
        output = tmp_path / "report.json"
        result = JSONExporter().export(report_data, str(output))
        assert Path(result).exists()

    @pytest.mark.unit
    def test_json_export_valid_json(self, report_data, tmp_path):
        """Output should be valid JSON parseable with json.loads()."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    @pytest.mark.unit
    def test_json_export_has_metadata(self, report_data, tmp_path):
        """JSON should have metadata with tool, version, generated_at."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "metadata" in parsed
        assert "tool" in parsed["metadata"]
        assert "version" in parsed["metadata"]
        assert "generated_at" in parsed["metadata"]

    @pytest.mark.unit
    def test_json_export_has_summary(self, report_data, tmp_path):
        """JSON should have summary with total_requests and failure_rate."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "summary" in parsed
        assert parsed["summary"]["total_requests"] == 5000
        assert "failure_rate" in parsed["summary"]

    @pytest.mark.unit
    def test_json_export_has_endpoints(self, report_data, tmp_path):
        """JSON should have endpoints[] with snake_case field names."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "endpoints" in parsed
        assert len(parsed["endpoints"]) == 4
        ep = parsed["endpoints"][0]
        assert "name" in ep
        assert "request_count" in ep
        assert "p95" in ep

    @pytest.mark.unit
    def test_json_export_excludes_aggregated(self, report_data, tmp_path):
        """No endpoint with name 'Aggregated' should appear in endpoints[]."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        names = [e["name"] for e in parsed["endpoints"]]
        assert "Aggregated" not in names

    @pytest.mark.unit
    def test_json_export_has_failures(self, report_data, tmp_path):
        """JSON should have failures[] populated from _failures.csv."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "failures" in parsed
        assert len(parsed["failures"]) == 3

    @pytest.mark.unit
    def test_json_export_has_exceptions(self, report_data, tmp_path):
        """JSON should have exceptions[] (populated or empty array)."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "exceptions" in parsed
        assert isinstance(parsed["exceptions"], list)

    @pytest.mark.unit
    def test_json_export_threshold_status(self, report_data_with_thresholds, tmp_path):
        """Each endpoint should have threshold_status: PASS/FAIL/SKIP."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data_with_thresholds, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        for ep in parsed["endpoints"]:
            assert ep["threshold_status"] in ("PASS", "FAIL", "SKIP")

    @pytest.mark.unit
    def test_json_export_iso8601_timestamp(self, report_data, tmp_path):
        """metadata.generated_at should match ISO 8601 with Z suffix."""
        output = tmp_path / "report.json"
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        parsed = json.loads(content)
        ts = parsed["metadata"]["generated_at"]
        assert "T" in ts
        assert ts.endswith("Z")

    @pytest.mark.unit
    def test_json_export_preserves_non_ascii(self, tmp_path):
        """Non-ASCII endpoint names should be preserved (ensure_ascii=False)."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "unicode"
            stats_content = (
                '"Type","Name","Request Count","Failure Count",'
                '"Median Response Time","Average Response Time",'
                '"Min Response Time","Max Response Time",'
                '"Average Content Size","Requests/s",'
                '"50%","66%","75%","80%","90%","95%","98%","99%",'
                '"99.9%","99.99%","100%"\n'
                '"GET","/api/café","100","0","50","55","20","200",'
                '"128","10.0","50","60","65","70","80","90","120","150",'
                '"200","200","200"\n'
            )
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_content, encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            output = tmp_path / "report.json"
            JSONExporter().export(data, str(output))
            content = output.read_text(encoding="utf-8")
            assert "café" in content  # not escaped

    @pytest.mark.unit
    def test_json_export_creates_parent_dirs(self, report_data, tmp_path):
        """Parent directories should be created for nested output paths."""
        output = tmp_path / "x" / "y" / "report.json"
        JSONExporter().export(report_data, str(output))
        assert output.exists()


# ──────────────────────────────────────────────────────────────
# MarkdownExporter tests
# ──────────────────────────────────────────────────────────────


class TestMarkdownExporter:
    """Tests for MarkdownExporter — fail until implemented."""

    @pytest.mark.unit
    def test_md_export_creates_file(self, report_data, tmp_path):
        """export() should create a Markdown file at the specified path."""
        output = tmp_path / "report.md"
        result = MarkdownExporter().export(report_data, str(output))
        assert Path(result).exists()

    @pytest.mark.unit
    def test_md_export_has_title(self, report_data, tmp_path):
        """First line should be '# Locust Performance Report'."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "# Locust Performance Report" in content

    @pytest.mark.unit
    def test_md_export_has_summary_table(self, report_data, tmp_path):
        """Summary section should have a GFM table with | separators."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "## Summary" in content
        assert "|" in content
        assert "Total Requests" in content

    @pytest.mark.unit
    def test_md_export_has_endpoint_table(self, report_data, tmp_path):
        """Per-Endpoint Metrics table should appear in the output."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "/api/items" in content
        assert "|" in content

    @pytest.mark.unit
    def test_md_export_has_threshold_table(self, report_data_with_thresholds, tmp_path):
        """Threshold Results table should appear when thresholds are set."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data_with_thresholds, str(output))
        content = output.read_text(encoding="utf-8")
        assert "Threshold" in content

    @pytest.mark.unit
    def test_md_export_threshold_pass_emoji(
        self, report_data_with_thresholds, tmp_path
    ):
        """✅ PASS should appear in threshold table for passing endpoints."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data_with_thresholds, str(output))
        content = output.read_text(encoding="utf-8")
        assert "✅" in content or "PASS" in content

    @pytest.mark.unit
    def test_md_export_threshold_fail_emoji(self, tmp_path):
        """❌ FAIL should appear in threshold table for failing endpoints."""
        data = ReportData.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 100.0, "p99": 200.0},
        )
        output = tmp_path / "report.md"
        MarkdownExporter().export(data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "❌" in content or "FAIL" in content

    @pytest.mark.unit
    def test_md_export_threshold_skip_no_table(self, report_data, tmp_path):
        """No threshold table when no thresholds are set."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        # Should not have a threshold results section
        assert "Threshold Results" not in content

    @pytest.mark.unit
    def test_md_export_has_failures_table(self, report_data, tmp_path):
        """Failures table should appear when failures exist."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "## Failures" in content
        assert "HTTPError" in content

    @pytest.mark.unit
    def test_md_export_no_failures_section(self, tmp_path):
        """No failures section when failures list is empty."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "nofail"
            stats_src = FIXTURES_DIR / "sample_stats.csv"
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            output = tmp_path / "report.md"
            MarkdownExporter().export(data, str(output))
            content = output.read_text(encoding="utf-8")
            assert "## Failures" not in content

    @pytest.mark.unit
    def test_md_export_has_exceptions_section(self, report_data, tmp_path):
        """Exceptions section should appear when exceptions exist."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "Exception" in content

    @pytest.mark.unit
    def test_md_export_excludes_aggregated(self, report_data, tmp_path):
        """No 'Aggregated' row should appear in endpoint table."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        # Aggregated should not be a table row
        lines = content.split("\n")
        table_lines = [line for line in lines if "|" in line and "Aggregated" in line]
        assert len(table_lines) == 0

    @pytest.mark.unit
    def test_md_export_comma_separated_counts(self, report_data, tmp_path):
        """Large counts should be formatted with commas (e.g. '1,500')."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "1,500" in content

    @pytest.mark.unit
    def test_md_export_creates_parent_dirs(self, report_data, tmp_path):
        """Parent directories should be created for nested output paths."""
        output = tmp_path / "a" / "b" / "report.md"
        MarkdownExporter().export(report_data, str(output))
        assert output.exists()


# ──────────────────────────────────────────────────────────────
# JUnitXMLExporter tests
# ──────────────────────────────────────────────────────────────


class TestJUnitXMLExporter:
    """Tests for JUnitXMLExporter — fail until implemented."""

    @pytest.mark.unit
    def test_junit_export_creates_file(self, report_data, tmp_path):
        """export() should create an XML file at the specified path."""
        output = tmp_path / "junit.xml"
        result = JUnitXMLExporter().export(report_data, str(output))
        assert Path(result).exists()

    @pytest.mark.unit
    def test_junit_export_valid_xml(self, report_data, tmp_path):
        """Output should be valid XML parseable with ElementTree."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root is not None

    @pytest.mark.unit
    def test_junit_export_has_testsuites(self, report_data, tmp_path):
        """Root element should be <testsuites>."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root.tag == "testsuites"

    @pytest.mark.unit
    def test_junit_export_has_testsuite(self, report_data, tmp_path):
        """Output should contain a <testsuite> element."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suites = root.findall("testsuite")
        assert len(suites) >= 1

    @pytest.mark.unit
    def test_junit_export_test_count(self, report_data, tmp_path):
        """tests attribute should equal endpoint count."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        assert int(suite.get("tests")) == 4

    @pytest.mark.unit
    def test_junit_export_failure_count(self, tmp_path):
        """failures attribute should equal count of threshold violations."""
        data = ReportData.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 100.0, "p99": 200.0},
        )
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        # All 4 endpoints exceed p95=100 → 4 failures
        assert int(suite.get("failures")) == 4

    @pytest.mark.unit
    def test_junit_export_testcase_per_endpoint(self, report_data, tmp_path):
        """One <testcase> per endpoint should appear."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        testcases = suite.findall("testcase")
        assert len(testcases) == 4

    @pytest.mark.unit
    def test_junit_export_failure_element_on_threshold_breach(self, tmp_path):
        """<failure> element should appear when threshold is exceeded."""
        data = ReportData.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 100.0, "p99": 200.0},
        )
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        failures = suite.findall("testcase/failure")
        assert len(failures) > 0

    @pytest.mark.unit
    def test_junit_export_system_out_on_pass(
        self, report_data_with_thresholds, tmp_path
    ):
        """<system-out> with metrics should appear for passing testcases."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data_with_thresholds, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        system_outs = suite.findall("testcase/system-out")
        assert len(system_outs) > 0

    @pytest.mark.unit
    def test_junit_export_no_thresholds_all_pass(self, report_data, tmp_path):
        """No <failure> elements when no thresholds set."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        failures = suite.findall("testcase/failure")
        assert len(failures) == 0

    @pytest.mark.unit
    def test_junit_export_has_properties(self, report_data, tmp_path):
        """<properties> should contain total_requests, total_failures, rps."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        props = suite.find("properties")
        assert props is not None
        prop_names = {p.get("name") for p in props.findall("property")}
        assert "total_requests" in prop_names

    @pytest.mark.unit
    def test_junit_export_excludes_aggregated(self, report_data, tmp_path):
        """No testcase with name containing 'Aggregated'."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        suite = root.find("testsuite")
        for tc in suite.findall("testcase"):
            assert "Aggregated" not in (tc.get("name") or "")

    @pytest.mark.unit
    def test_junit_export_xml_declaration(self, report_data, tmp_path):
        """Output should start with <?xml version=\"1.0\" encoding=\"UTF-8\"?>."""
        output = tmp_path / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert content.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")

    @pytest.mark.unit
    def test_junit_export_creates_parent_dirs(self, report_data, tmp_path):
        """Parent directories should be created for nested output paths."""
        output = tmp_path / "a" / "b" / "junit.xml"
        JUnitXMLExporter().export(report_data, str(output))
        assert output.exists()


# ──────────────────────────────────────────────────────────────
# Cross-platform path tests
# ──────────────────────────────────────────────────────────────


class TestCrossPlatformPaths:
    """Tests for cross-platform path handling in exporters."""

    @pytest.mark.unit
    def test_export_with_relative_path(self, report_data, tmp_path, monkeypatch):
        """Relative output path should work (resolved against cwd)."""
        monkeypatch.chdir(tmp_path)
        output = "report.json"
        result = JSONExporter().export(report_data, output)
        assert Path(result).exists()

    @pytest.mark.unit
    def test_export_with_absolute_path(self, report_data, tmp_path):
        """Absolute output path should work."""
        output = tmp_path / "report.json"
        result = JSONExporter().export(report_data, str(output.resolve()))
        assert Path(result).exists()

    @pytest.mark.unit
    def test_export_nested_directories(self, report_data, tmp_path):
        """Deeply nested output path should create all parent dirs."""
        output = tmp_path / "a" / "b" / "c" / "report.json"
        JSONExporter().export(report_data, str(output))
        assert output.exists()

    @pytest.mark.unit
    def test_export_path_with_spaces(self, report_data, tmp_path):
        """Output path containing spaces should work."""
        output = tmp_path / "my reports" / "report.json"
        JSONExporter().export(report_data, str(output))
        assert output.exists()

    @pytest.mark.unit
    def test_export_overwrites_existing_file(self, report_data, tmp_path):
        """Existing file at output path should be overwritten."""
        output = tmp_path / "report.json"
        output.write_text("old content", encoding="utf-8")
        JSONExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert content != "old content"

    @pytest.mark.unit
    def test_export_accepts_path_object(self, report_data, tmp_path):
        """export() should accept a Path object (not just str)."""
        output = tmp_path / "report.json"
        result = JSONExporter().export(report_data, output)
        assert Path(result).exists()

    @pytest.mark.unit
    def test_from_csv_relative_prefix(self, monkeypatch):
        """Relative CSV prefix should resolve against cwd."""
        monkeypatch.chdir(FIXTURES_DIR)
        data = ReportData.from_csv("sample")
        assert len(data.endpoints) > 0

    @pytest.mark.unit
    def test_from_csv_absolute_prefix(self):
        """Absolute CSV prefix should work."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert len(data.endpoints) > 0
