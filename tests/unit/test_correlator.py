"""Unit tests for RequestCorrelator — cascade failure detection from Locust events.

These tests define the acceptance contract for the RequestCorrelator feature.
They call ``_on_request()`` directly with keyword arguments matching Locust's
actual ``events.request`` handler signature (verified against locust 2.45.0 source).

Key: ``status_code`` is NOT a direct event parameter — it is extracted from the
``response`` object's ``status_code`` attribute.  Failed requests have
``exception`` set and ``response`` may be ``None``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import Mock

from locust_templates.correlator import (
    CorrelatedEvent,
    CorrelationSummary,
    FailureChain,
    RequestCorrelator,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _ok_response(status_code: int = 200) -> Mock:
    """Create a mock response object for a successful request."""
    r = Mock()
    r.status_code = status_code
    return r


def _fire(
    corr: RequestCorrelator,
    *,
    request_type: str = "GET",
    name: str = "GET /api/v1/test",
    response_time: float = 100.0,
    response_length: int = 1024,
    response: object | None = None,
    context: dict | None = None,
    exception: Exception | None = None,
    start_time: float = 1000.0,
    url: str | None = "http://localhost/api/v1/test",
) -> None:
    """Call _on_request with Locust-compatible keyword arguments."""
    corr._on_request(
        request_type=request_type,
        name=name,
        response_time=response_time,
        response_length=response_length,
        response=response,
        context=context,
        exception=exception,
        start_time=start_time,
        url=url,
    )


# ──────────────────────────────────────────────────────────────
# 1. Empty correlator
# ──────────────────────────────────────────────────────────────


class TestRequestCorrelator:
    """Acceptance tests for RequestCorrelator cascade detection."""

    def test_empty_correlator_no_events(self):
        """Empty correlator returns no events."""
        corr = RequestCorrelator()
        assert corr.get_correlated_events() == []

    def test_empty_correlator_summary_zeros(self):
        """Empty correlator summary has all-zero stats."""
        corr = RequestCorrelator()
        s = corr.get_summary()
        assert s.total_requests == 0
        assert s.total_failures == 0
        assert s.cascade_failures == 0
        assert s.root_failures == 0
        assert s.avg_chain_depth == 0.0

    def test_empty_correlator_no_chains(self):
        """Empty correlator returns no failure chains."""
        corr = RequestCorrelator()
        assert corr.get_failure_chains() == []

    # ──────────────────────────────────────────────────────────
    # 2. Single successful request
    # ──────────────────────────────────────────────────────────

    def test_single_successful_request(self):
        """One successful request: recorded with correct fields, no failures."""
        corr = RequestCorrelator()
        _fire(
            corr,
            request_type="GET",
            name="GET /api/v1/profile",
            response_time=150.0,
            response=_ok_response(200),
            context={"user_id": "user-1"},
            exception=None,
            start_time=1000.0,
        )
        events = corr.get_correlated_events()
        assert len(events) == 1
        ev = events[0]
        assert ev.request_type == "GET"
        assert ev.name == "GET /api/v1/profile"
        assert ev.response_time == 150.0
        assert ev.status_code == 200
        assert ev.exception is None
        assert ev.user_id == "user-1"
        assert ev.is_cascade_failure is False
        assert ev.chain_depth == 0
        assert ev.parent_request is None

    # ──────────────────────────────────────────────────────────
    # 3. Single failed request
    # ──────────────────────────────────────────────────────────

    def test_single_failed_request(self):
        """One failed request: recorded as failure, no cascade (no dependents)."""
        corr = RequestCorrelator()
        exc = ConnectionError("timeout")
        _fire(
            corr,
            request_type="GET",
            name="GET /api/v1/orders",
            response_time=5000.0,
            response=None,
            context={"user_id": "user-1"},
            exception=exc,
            start_time=1000.0,
        )
        events = corr.get_correlated_events()
        assert len(events) == 1
        ev = events[0]
        assert ev.exception is not None
        assert "timeout" in ev.exception
        assert ev.status_code == 0  # no response → 0
        assert ev.is_cascade_failure is False  # no prior failure to cascade from

    # ──────────────────────────────────────────────────────────
    # 4. Two sequential requests — parent/child relationship
    # ──────────────────────────────────────────────────────────

    def test_two_sequential_requests_same_user(self):
        """Two sequential requests from same user: second has parent_request set."""
        corr = RequestCorrelator()
        _fire(
            corr,
            name="GET /login",
            response=_ok_response(200),
            context={"user_id": "user-1"},
            start_time=1000.0,
        )
        _fire(
            corr,
            name="GET /profile",
            response=_ok_response(200),
            context={"user_id": "user-1"},
            start_time=1000.5,
        )
        events = corr.get_correlated_events()
        assert len(events) == 2
        # Second request should record parent_request pointing to first
        assert events[1].parent_request is not None
        assert events[1].parent_request == "GET /login"

    # ──────────────────────────────────────────────────────────
    # 5. Cascade failure — A fails → B fails within window → B is cascade
    # ──────────────────────────────────────────────────────────

    def test_cascade_failure(self):
        """A fails → B fails within window → B is marked as cascade failure."""
        corr = RequestCorrelator(cascade_window_s=5.0)
        _fire(
            corr,
            name="GET /profile",
            response=None,
            context={"user_id": "user-1"},
            exception=RuntimeError("500 error"),
            start_time=1000.0,
        )
        _fire(
            corr,
            name="GET /orders",
            response=None,
            context={"user_id": "user-1"},
            exception=ConnectionError("refused"),
            start_time=1001.0,  # within 5s window
        )
        events = corr.get_correlated_events()
        assert len(events) == 2
        assert events[0].is_cascade_failure is False  # root
        assert events[1].is_cascade_failure is True   # cascade
        assert events[1].parent_request == "GET /profile"

    # ──────────────────────────────────────────────────────────
    # 6. Cascade not triggered — A fails → B succeeds → cascade broken
    # ──────────────────────────────────────────────────────────

    def test_cascade_not_triggered_on_success(self):
        """A fails → B succeeds → B is NOT a cascade failure."""
        corr = RequestCorrelator(cascade_window_s=5.0)
        _fire(
            corr,
            name="GET /profile",
            response=None,
            context={"user_id": "user-1"},
            exception=RuntimeError("500 error"),
            start_time=1000.0,
        )
        _fire(
            corr,
            name="GET /orders",
            response=_ok_response(200),
            context={"user_id": "user-1"},
            exception=None,
            start_time=1001.0,
        )
        events = corr.get_correlated_events()
        assert events[1].is_cascade_failure is False
        assert events[1].exception is None

    # ──────────────────────────────────────────────────────────
    # 7. Cascade window expiry — A fails → B fails after window → NOT cascade
    # ──────────────────────────────────────────────────────────

    def test_cascade_window_expiry(self):
        """A fails → B fails AFTER window → B is NOT a cascade failure."""
        corr = RequestCorrelator(cascade_window_s=2.0)
        _fire(
            corr,
            name="GET /profile",
            response=None,
            context={"user_id": "user-1"},
            exception=RuntimeError("500 error"),
            start_time=1000.0,
        )
        _fire(
            corr,
            name="GET /orders",
            response=None,
            context={"user_id": "user-1"},
            exception=ConnectionError("refused"),
            start_time=1005.0,  # 5s later, beyond 2s window
        )
        events = corr.get_correlated_events()
        assert events[1].is_cascade_failure is False

    # ──────────────────────────────────────────────────────────
    # 8. Explicit correlation_id via context
    # ──────────────────────────────────────────────────────────

    def test_explicit_correlation_id(self):
        """correlation_id from context is captured on the event."""
        corr = RequestCorrelator()
        _fire(
            corr,
            name="GET /data",
            response=_ok_response(200),
            context={"user_id": "user-1", "correlation_id": "token-xyz"},
            start_time=1000.0,
        )
        events = corr.get_correlated_events()
        assert events[0].correlation_id == "token-xyz"

    # ──────────────────────────────────────────────────────────
    # 9. Multiple users with independent chains
    # ──────────────────────────────────────────────────────────

    def test_multiple_users_independent_chains(self):
        """User1's failure does not cascade to user2's request."""
        corr = RequestCorrelator(cascade_window_s=5.0)
        # user-1: login succeeds, profile fails
        _fire(
            corr,
            name="GET /profile",
            response=None,
            context={"user_id": "user-1"},
            exception=RuntimeError("500"),
            start_time=1000.0,
        )
        # user-2: makes a request at same time — should NOT be cascade
        _fire(
            corr,
            name="GET /orders",
            response=None,
            context={"user_id": "user-2"},
            exception=ConnectionError("refused"),
            start_time=1000.5,
        )
        events = corr.get_correlated_events()
        user2_ev = [e for e in events if e.user_id == "user-2"][0]
        assert user2_ev.is_cascade_failure is False

    # ──────────────────────────────────────────────────────────
    # 10. CSV export format
    # ──────────────────────────────────────────────────────────

    def test_csv_export_format(self, tmp_path):
        """CSV export has the 11 required columns and correct data."""
        corr = RequestCorrelator()
        _fire(
            corr,
            name="GET /profile",
            response=_ok_response(200),
            context={"user_id": "user-1", "correlation_id": "tok"},
            start_time=1000.0,
        )
        csv_path = corr.export_csv(tmp_path / "events.csv")
        assert csv_path.exists()
        with open(csv_path) as f:
            reader = csv.reader(f)
            header = next(reader)
            row = next(reader)
        expected_cols = [
            "timestamp", "request_type", "name", "response_time",
            "status_code", "exception", "user_id", "correlation_id",
            "parent_request", "is_cascade_failure", "chain_depth",
        ]
        assert header == expected_cols
        assert len(row) == 11
        assert row[1] == "GET"  # request_type
        assert row[2] == "GET /profile"  # name
        assert row[6] == "user-1"  # user_id
        assert row[7] == "tok"  # correlation_id

    # ──────────────────────────────────────────────────────────
    # 11. JSON export format
    # ──────────────────────────────────────────────────────────

    def test_json_export_format(self, tmp_path):
        """JSON export produces a list of FailureChain objects."""
        corr = RequestCorrelator(cascade_window_s=5.0)
        # Create a cascade: profile fails → orders fails
        _fire(
            corr,
            name="GET /profile",
            response=None,
            context={"user_id": "user-1"},
            exception=RuntimeError("500"),
            start_time=1000.0,
        )
        _fire(
            corr,
            name="GET /orders",
            response=None,
            context={"user_id": "user-1"},
            exception=ConnectionError("refused"),
            start_time=1001.0,
        )
        json_path = corr.export_json(tmp_path / "chains.json")
        assert json_path.exists()
        with open(json_path) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 1
        chain = data[0]
        assert "root_request" in chain
        assert "failed_dependents" in chain
        assert "cascade_count" in chain
        assert "total_chain_length" in chain
        assert chain["root_request"]["name"] == "GET /profile"
        assert chain["cascade_count"] >= 1

    # ──────────────────────────────────────────────────────────
    # 12. Summary statistics
    # ──────────────────────────────────────────────────────────

    def test_summary_statistics(self):
        """Summary stats: total_requests, total_failures, cascade_failures, etc."""
        corr = RequestCorrelator(cascade_window_s=5.0)
        # 3 requests: 1 success, 1 root failure, 1 cascade failure
        _fire(
            corr,
            name="GET /login",
            response=_ok_response(200),
            context={"user_id": "user-1"},
            start_time=1000.0,
        )
        _fire(
            corr,
            name="GET /profile",
            response=None,
            context={"user_id": "user-1"},
            exception=RuntimeError("500"),
            start_time=1000.5,
        )
        _fire(
            corr,
            name="GET /orders",
            response=None,
            context={"user_id": "user-1"},
            exception=ConnectionError("refused"),
            start_time=1001.0,
        )
        s = corr.get_summary()
        assert s.total_requests == 3
        assert s.total_failures == 2
        assert s.cascade_failures == 1
        assert s.root_failures >= 1
        assert isinstance(s.avg_chain_depth, float)
        assert s.avg_chain_depth > 0.0

    # ──────────────────────────────────────────────────────────
    # 13. Edge case: all requests succeed
    # ──────────────────────────────────────────────────────────

    def test_all_requests_succeed(self):
        """All-succeed scenario: no failures, no chains, summary zeros."""
        corr = RequestCorrelator()
        for i in range(5):
            _fire(
                corr,
                name=f"GET /api/v1/item-{i}",
                response=_ok_response(200),
                context={"user_id": "user-1"},
                start_time=1000.0 + i * 0.5,
            )
        s = corr.get_summary()
        assert s.total_requests == 5
        assert s.total_failures == 0
        assert s.cascade_failures == 0
        assert s.root_failures == 0
        assert s.avg_chain_depth == 0.0
        assert corr.get_failure_chains() == []

    # ──────────────────────────────────────────────────────────
    # 14. Edge case: all requests fail
    # ──────────────────────────────────────────────────────────

    def test_all_requests_fail(self):
        """All-fail scenario: at least 1 root, subsequent are cascades."""
        corr = RequestCorrelator(cascade_window_s=10.0)
        for i in range(4):
            _fire(
                corr,
                name=f"GET /api/v1/step-{i}",
                response=None,
                context={"user_id": "user-1"},
                exception=RuntimeError(f"err-{i}"),
                start_time=1000.0 + i * 0.5,  # all within 10s window
            )
        events = corr.get_correlated_events()
        s = corr.get_summary()
        assert s.total_requests == 4
        assert s.total_failures == 4
        # First is root, rest are cascades
        assert events[0].is_cascade_failure is False
        cascade_count = sum(1 for e in events if e.is_cascade_failure)
        assert cascade_count >= 1
        assert s.cascade_failures == cascade_count

    # ──────────────────────────────────────────────────────────
    # Fixture data validation
    # ──────────────────────────────────────────────────────────

    def test_sample_events_fixture(self):
        """Fixture file exists and has the expected cascade scenario."""
        fixture = FIXTURES_DIR / "sample_events.json"
        assert fixture.exists()
        with open(fixture) as f:
            data = json.load(f)
        assert "events" in data
        assert len(data["events"]) == 3
        # login succeeds, profile fails 500, orders fails connection error
        assert data["events"][0]["exception"] is None
        assert data["events"][0]["status_code"] == 200
        assert data["events"][1]["exception"] == "InternalServerError"
        assert data["events"][1]["status_code"] == 500
        assert data["events"][2]["exception"] == "ConnectionError"
        assert data["events"][2]["status_code"] == 0

    # ──────────────────────────────────────────────────────────
    # Dataclass existence
    # ──────────────────────────────────────────────────────────

    def test_dataclasses_exist(self):
        """CorrelatedEvent, FailureChain, CorrelationSummary are importable
        dataclasses."""
        from dataclasses import is_dataclass
        assert is_dataclass(CorrelatedEvent)
        assert is_dataclass(FailureChain)
        assert is_dataclass(CorrelationSummary)

    # ──────────────────────────────────────────────────────────
    # register() pattern
    # ──────────────────────────────────────────────────────────

    def test_register_attaches_to_events(self):
        """register() should attach to environment.events.request."""
        corr = RequestCorrelator()
        fake_env = Mock()
        fake_env.events.request.add_listener = Mock()
        fake_env.events.quitting.add_listener = Mock()
        corr.register(fake_env)
        fake_env.events.request.add_listener.assert_called_once()
        # Should also attach to quitting for cleanup (per CsvRequestLogger pattern)
        fake_env.events.quitting.add_listener.assert_called_once()
