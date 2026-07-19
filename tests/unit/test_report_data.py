"""Tests for ReportData dataclass and from_csv() parsing (TDD).

These tests define the contract for the new ReportData model that decouples
CSV parsing from report rendering. They will FAIL until report_data.py is
implemented.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from locust_templates.report_data import (
    EndpointStats,
    ExceptionRecord,
    FailureRecord,
    ReportData,
    ReportMetadata,
    ReportSummary,
    ThresholdConfig,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestReportDataInterface:
    """Verify that ReportData and sub-dataclasses exist with correct fields."""

    def test_report_data_is_importable(self):
        """ReportData should be importable."""
        assert ReportData is not None

    def test_report_data_is_dataclass(self):
        """ReportData should be a dataclass."""
        import dataclasses

        assert dataclasses.is_dataclass(ReportData)

    def test_sub_dataclasses_importable(self):
        """All sub-dataclasses should be importable."""
        assert ReportMetadata is not None
        assert ReportSummary is not None
        assert ThresholdConfig is not None
        assert EndpointStats is not None
        assert FailureRecord is not None
        assert ExceptionRecord is not None


# ──────────────────────────────────────────────────────────────
# from_csv() parsing tests
# ──────────────────────────────────────────────────────────────


class TestFromCsvParsing:
    """Tests for ReportData.from_csv() — fail until implemented."""

    @pytest.mark.unit
    def test_from_csv_parses_stats(self):
        """from_csv() should parse _stats.csv and populate endpoints."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert len(data.endpoints) > 0
        names = [e.name for e in data.endpoints]
        assert "/api/items" in names

    @pytest.mark.unit
    def test_from_csv_excludes_aggregated_row(self):
        """Aggregated row should not appear in endpoints[]."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        names = [e.name for e in data.endpoints]
        assert "Aggregated" not in names

    @pytest.mark.unit
    def test_from_csv_parses_failures(self):
        """from_csv() should parse _failures.csv and populate failures list."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert len(data.failures) > 0
        assert isinstance(data.failures[0], FailureRecord)
        assert data.failures[0].method == "POST"
        assert data.failures[0].name == "/api/orders"

    @pytest.mark.unit
    def test_from_csv_parses_exceptions(self):
        """from_csv() should parse _exceptions.csv and populate exceptions list."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert len(data.exceptions) > 0
        assert isinstance(data.exceptions[0], ExceptionRecord)
        assert "ConnectionError" in data.exceptions[0].exception

    @pytest.mark.unit
    def test_from_csv_missing_exceptions_file(self):
        """Missing _exceptions.csv should result in empty exceptions list."""
        # Use a prefix that has _stats.csv and _failures.csv but no _exceptions.csv
        # Create temp files for this test
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "nostats"
            # Copy stats and failures but not exceptions
            stats_src = FIXTURES_DIR / "sample_stats.csv"
            failures_src = FIXTURES_DIR / "sample_failures.csv"
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (Path(f"{prefix}_failures.csv")).write_text(
                failures_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            assert data.exceptions == []

    @pytest.mark.unit
    def test_from_csv_missing_failures_file(self):
        """Missing _failures.csv should result in empty failures list."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "nofailures"
            stats_src = FIXTURES_DIR / "sample_stats.csv"
            (Path(f"{prefix}_stats.csv")).write_text(
                stats_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            data = ReportData.from_csv(str(prefix))
            assert data.failures == []

    @pytest.mark.unit
    def test_from_csv_missing_stats_file_raises(self):
        """Missing _stats.csv should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ReportData.from_csv("/nonexistent/path/prefix")

    @pytest.mark.unit
    def test_from_csv_accepts_path_object(self):
        """from_csv() should accept a Path object as csv_prefix."""
        data = ReportData.from_csv(FIXTURES_DIR / "sample")
        assert len(data.endpoints) > 0

    @pytest.mark.unit
    def test_from_csv_accepts_str(self):
        """from_csv() should accept a string as csv_prefix."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert len(data.endpoints) > 0

    @pytest.mark.unit
    def test_from_csv_computes_summary(self):
        """Summary fields should be computed correctly from endpoint data."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert data.summary.total_requests == 5000
        assert data.summary.total_failures == 30
        assert data.summary.endpoint_count == 4
        assert data.summary.total_rps == pytest.approx(83.6, abs=0.1)

    @pytest.mark.unit
    def test_from_csv_summary_failure_rate(self):
        """Failure rate should be total_failures / total_requests."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert data.summary.failure_rate == pytest.approx(0.006, abs=0.001)

    @pytest.mark.unit
    def test_from_csv_metadata_populated(self):
        """Metadata should have generated_at, tool, version, csv_prefix."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        assert data.metadata is not None
        assert data.metadata.tool == "locust-performance-kit"
        assert data.metadata.version == "1.2.0"
        assert data.metadata.csv_prefix != ""

    @pytest.mark.unit
    def test_from_csv_metadata_iso8601(self):
        """metadata.generated_at should be ISO 8601 format."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        # Should contain 'T' separator and 'Z' suffix (UTC)
        assert "T" in data.metadata.generated_at
        assert data.metadata.generated_at.endswith("Z")

    @pytest.mark.unit
    def test_from_csv_endpoint_stats_types(self):
        """EndpointStats fields should have correct Python types."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        endpoint = data.endpoints[0]
        assert isinstance(endpoint.request_count, int)
        assert isinstance(endpoint.failure_count, int)
        assert isinstance(endpoint.average_response_time_ms, float)
        assert isinstance(endpoint.requests_per_sec, float)
        assert isinstance(endpoint.percentile_95, float)

    @pytest.mark.unit
    def test_from_csv_threshold_status_pass(self):
        """Thresholds set and endpoint within limits → threshold_status='PASS'."""
        data = ReportData.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 500.0, "p99": 1000.0},
        )
        # /api/items has p95=250, p99=450 → should PASS
        items = [e for e in data.endpoints if e.name == "/api/items"]
        assert len(items) == 1
        assert items[0].threshold_status == "PASS"

    @pytest.mark.unit
    def test_from_csv_threshold_status_fail(self):
        """Thresholds set and endpoint exceeds → threshold_status='FAIL'."""
        data = ReportData.from_csv(
            str(FIXTURES_DIR / "sample"),
            thresholds={"p95": 100.0, "p99": 200.0},
        )
        # /api/items has p95=250 → should FAIL
        items = [e for e in data.endpoints if e.name == "/api/items"]
        assert len(items) == 1
        assert items[0].threshold_status == "FAIL"

    @pytest.mark.unit
    def test_from_csv_threshold_status_skip(self):
        """No thresholds set → threshold_status='SKIP'."""
        data = ReportData.from_csv(str(FIXTURES_DIR / "sample"))
        for endpoint in data.endpoints:
            assert endpoint.threshold_status == "SKIP"

    @pytest.mark.unit
    def test_from_csv_invalid_threshold_keys_raises(self):
        """Thresholds dict with invalid keys should raise ValueError."""
        with pytest.raises(ValueError):
            ReportData.from_csv(
                str(FIXTURES_DIR / "sample"),
                thresholds={"p50": 100.0},
            )


# ──────────────────────────────────────────────────────────────
# Encoding tests
# ──────────────────────────────────────────────────────────────


class TestFromCsvEncoding:
    """Tests for UTF-8 encoding handling in from_csv()."""

    @pytest.mark.unit
    def test_from_csv_encodes_utf8(self):
        """Non-ASCII endpoint names should be parsed correctly with UTF-8."""
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
            assert len(data.endpoints) == 1
            assert data.endpoints[0].name == "/api/café"
