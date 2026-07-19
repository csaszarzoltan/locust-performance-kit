"""Tests for failure hotspots in HTML and Markdown reports.

Failure hotspots = endpoints sorted by failure rate, showing the
worst offenders first so triage can focus on them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from locust_templates.exporters import HTMLExporter, MarkdownExporter
from locust_templates.report_data import ReportData

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def report_data():
    return ReportData.from_csv(str(FIXTURES_DIR / "sample"))


# ──────────────────────────────────────────────────────────────
# ReportData.get_failure_hotspots()
# ──────────────────────────────────────────────────────────────


class TestFailureHotspotsData:
    """Test the failure hotspots computation on ReportData."""

    def test_get_failure_hotspots_returns_list(self, report_data):
        hotspots = report_data.get_failure_hotspots()
        assert isinstance(hotspots, list)

    def test_hotspots_sorted_by_failure_rate_desc(self, report_data):
        """Hotspots should be sorted by failure rate descending."""
        hotspots = report_data.get_failure_hotspots()
        assert len(hotspots) > 0
        for i in range(len(hotspots) - 1):
            assert hotspots[i]["failure_rate"] >= hotspots[i + 1]["failure_rate"]

    def test_hotspots_exclude_zero_failure_endpoints(self, report_data):
        """Endpoints with 0 failures should not appear in hotspots."""
        hotspots = report_data.get_failure_hotspots()
        for h in hotspots:
            assert h["failure_rate"] > 0

    def test_hotspot_fields(self, report_data):
        """Each hotspot should have name, failure_count, request_count, failure_rate."""
        hotspots = report_data.get_failure_hotspots()
        if hotspots:
            h = hotspots[0]
            assert "name" in h
            assert "failure_count" in h
            assert "request_count" in h
            assert "failure_rate" in h

    def test_hotspots_with_no_failures(self, tmp_path):
        """When no endpoint has failures, hotspots should be empty."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "nofail"
            stats_content = (
                '"Type","Name","Request Count","Failure Count",'
                '"Median Response Time","Average Response Time",'
                '"Min Response Time","Max Response Time",'
                '"Average Content Size","Requests/s",'
                '"50%","66%","75%","80%","90%","95%","98%","99%",'
                '"99.9%","99.99%","100%"\n'
                '"GET","/api/ok","100","0","50","55","20","200",'
                '"128","10.0","50","60","65","70","80","90","120","150",'
                '"200","200","200"\n'
            )
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_content, encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            assert data.get_failure_hotspots() == []


# ──────────────────────────────────────────────────────────────
# HTMLExporter — failure hotspots section
# ──────────────────────────────────────────────────────────────


class TestHTMLFailureHotspots:
    """Test that HTMLExporter includes failure hotspots."""

    @pytest.mark.unit
    def test_html_has_failure_hotspots_section(self, report_data, tmp_path):
        """HTML report should include a Failure Hotspots section."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "Failure Hotspots" in content or "failure hotspots" in content.lower()

    @pytest.mark.unit
    def test_html_hotspots_show_endpoint_names(self, report_data, tmp_path):
        """Hotspot endpoint names should appear in the HTML."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        # /api/orders has 10/500 = 2% failure rate, /api/items 15/1500 = 1%
        assert "/api/orders" in content

    @pytest.mark.unit
    def test_html_hotspots_show_failure_rate(self, report_data, tmp_path):
        """Failure rate should appear in the hotspots section."""
        output = tmp_path / "report.html"
        HTMLExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        # Should show percentage or rate
        assert "%" in content

    @pytest.mark.unit
    def test_html_no_hotspots_section_when_no_failures(self, tmp_path):
        """When no failures, hotspots section should be absent or empty."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "nofail"
            stats_content = (
                '"Type","Name","Request Count","Failure Count",'
                '"Median Response Time","Average Response Time",'
                '"Min Response Time","Max Response Time",'
                '"Average Content Size","Requests/s",'
                '"50%","66%","75%","80%","90%","95%","98%","99%",'
                '"99.9%","99.99%","100%"\n'
                '"GET","/api/ok","100","0","50","55","20","200",'
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
            assert "Failure Hotspots" not in content


# ──────────────────────────────────────────────────────────────
# MarkdownExporter — failure hotspots section
# ──────────────────────────────────────────────────────────────


class TestMarkdownFailureHotspots:
    """Test that MarkdownExporter includes failure hotspots."""

    @pytest.mark.unit
    def test_md_has_failure_hotspots_section(self, report_data, tmp_path):
        """Markdown report should include a Failure Hotspots section."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "Failure Hotspots" in content

    @pytest.mark.unit
    def test_md_hotspots_show_endpoint_names(self, report_data, tmp_path):
        """Hotspot endpoint names should appear in the Markdown."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "/api/orders" in content

    @pytest.mark.unit
    def test_md_hotspots_table_format(self, report_data, tmp_path):
        """Hotspots should be in a Markdown table format."""
        output = tmp_path / "report.md"
        MarkdownExporter().export(report_data, str(output))
        content = output.read_text(encoding="utf-8")
        assert "## Failure Hotspots" in content
        assert "|" in content

    @pytest.mark.unit
    def test_md_no_hotspots_when_no_failures(self, tmp_path):
        """When no failures, hotspots section should be absent."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "nofail"
            stats_content = (
                '"Type","Name","Request Count","Failure Count",'
                '"Median Response Time","Average Response Time",'
                '"Min Response Time","Max Response Time",'
                '"Average Content Size","Requests/s",'
                '"50%","66%","75%","80%","90%","95%","98%","99%",'
                '"99.9%","99.99%","100%"\n'
                '"GET","/api/ok","100","0","50","55","20","200",'
                '"128","10.0","50","60","65","70","80","90","120","150",'
                '"200","200","200"\n'
            )
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_content, encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            output = tmp_path / "report.md"
            MarkdownExporter().export(data, str(output))
            content = output.read_text(encoding="utf-8")
            assert "## Failure Hotspots" not in content
