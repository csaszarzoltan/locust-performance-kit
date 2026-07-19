"""Request correlation and cascade failure detection for Locust tests.

Attaches to Locust's events.request to track request chains and identify
cascade failures — when a failed request causes downstream requests from
the same user/session to also fail within a configurable time window.

Public API:
    RequestCorrelator   — main correlator class
    CorrelatedEvent     — single request event with correlation metadata
    FailureChain        — root failure + its cascade dependents
    CorrelationSummary  — aggregate statistics
"""

from __future__ import annotations

import csv
import json
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CorrelatedEvent:
    """A single request event with correlation metadata.

    Attributes:
        timestamp: Unix timestamp of the request start.
        request_type: HTTP method (GET, POST, etc.).
        name: Request name (e.g. "GET /api/v1/profile").
        response_time: Response time in milliseconds.
        status_code: HTTP status code (0 if no response).
        exception: String representation of exception, or None if successful.
        user_id: User identifier from context, or None.
        correlation_id: Explicit correlation ID from context, or None.
        parent_request: Name of the previous request from the same user
            within the cascade window, or None.
        is_cascade_failure: True if this failure was caused by an upstream
            failure (i.e., a previous request from the same user also
            failed within the cascade window).
        chain_depth: 0 for root requests, 1+ for cascade dependents.
    """

    timestamp: float
    request_type: str
    name: str
    response_time: float
    status_code: int
    exception: str | None
    user_id: str | None
    correlation_id: str | None
    parent_request: str | None
    is_cascade_failure: bool
    chain_depth: int


@dataclass
class FailureChain:
    """A chain of failures starting from a root failure.

    Attributes:
        root_request: The initial failure that triggered the cascade.
        failed_dependents: List of subsequent failures caused by the root.
        cascade_count: Number of cascade failures in the chain.
        total_chain_length: Total number of requests in the chain
            (root + dependents).
    """

    root_request: CorrelatedEvent
    failed_dependents: list[CorrelatedEvent]
    cascade_count: int
    total_chain_length: int


@dataclass
class CorrelationSummary:
    """Summary statistics for correlated request events.

    Attributes:
        total_requests: Total number of recorded requests.
        total_failures: Total number of failed requests.
        cascade_failures: Failures caused by an upstream failure.
        root_failures: Failures that are not cascades (standalone or chain roots).
        top_failure_chains: Top 10 failure chains sorted by cascade_count.
        avg_chain_depth: Average chain depth across all events.
    """

    total_requests: int
    total_failures: int
    cascade_failures: int
    root_failures: int
    top_failure_chains: list[FailureChain]
    avg_chain_depth: float


class RequestCorrelator:
    """Track request chains and detect cascade failures from Locust events.

    Attaches to ``environment.events.request`` to capture every request with
    its context metadata. Identifies cascading failures when a failed request
    is followed by more failures from the same user/session within a time window.

    Example:
        correlator = RequestCorrelator()

        @events.init.add_listener
        def on_init(environment, **kwargs):
            correlator.register(environment)

        @events.quitting.add_listener
        def on_quitting(environment, **kwargs):
            correlator.export_csv("results/correlated_events.csv")
            print(correlator.get_summary())
    """

    def __init__(self, *, cascade_window_s: float = 5.0) -> None:
        """Initialize the correlator.

        Args:
            cascade_window_s: Time window in seconds for cascade detection.
                A failure is considered a cascade if a previous request from
                the same user failed within this window.
        """
        self._cascade_window_s = cascade_window_s
        self._events: list[CorrelatedEvent] = []
        self._user_history: dict[str, list[tuple[float, str, bool, int]]] = {}
        self._lock = threading.Lock()

    def register(self, environment: Any) -> None:
        """Attach to environment.events.request and environment.events.quitting.

        Args:
            environment: The Locust Environment instance.
        """
        environment.events.request.add_listener(self._on_request)
        environment.events.quitting.add_listener(self._on_quitting)

    def _on_request(
        self,
        *,
        request_type: str = "",
        name: str = "",
        response_time: float = 0.0,
        response_length: int = 0,
        exception: Any = None,
        response: Any = None,
        start_time: float | None = None,
        context: Any = None,
        url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle a Locust events.request event.

        Records the event with correlation metadata. Thread-safe via
        a single lock block for the entire method body.

        Args:
            request_type: HTTP method (GET, POST, etc.).
            name: Request name (e.g. "GET /api/v1/profile").
            response_time: Response time in milliseconds.
            response_length: Response body length in bytes.
            exception: Exception object if the request failed, else None.
            response: HTTP response object, or None on connection error.
            start_time: Unix timestamp of request start. Defaults to now.
            context: Locust request context dict (may contain user_id,
                correlation_id).
            url: Request URL.
        """
        ctx: dict[str, Any] = context or {}
        user_id: str | None = ctx.get("user_id") or ctx.get("correlation_id")
        correlation_id: str | None = ctx.get("correlation_id")
        failed = exception is not None
        status_code = self._extract_status_code(response, exception)
        ts = start_time if start_time is not None else time.time()

        is_cascade = False
        parent_request: str | None = None
        chain_depth = 0

        with self._lock:
            if user_id:
                history = self._user_history.get(user_id, [])
                # Scan backward through recent requests from same user
                for prev_ts, prev_name, prev_failed, prev_depth in reversed(history):
                    if ts - prev_ts > self._cascade_window_s:
                        break
                    # Set parent to the most recent request within window
                    parent_request = prev_name
                    if prev_failed:
                        # Cascade: previous failed and this one also fails
                        is_cascade = failed
                        chain_depth = prev_depth + 1
                    break  # Only consider the most recent request
                history.append((ts, name, failed, chain_depth))
                self._user_history[user_id] = history

            self._events.append(
                CorrelatedEvent(
                    timestamp=ts,
                    request_type=request_type,
                    name=name,
                    response_time=response_time,
                    status_code=status_code,
                    exception=str(exception) if exception else None,
                    user_id=user_id,
                    correlation_id=correlation_id,
                    parent_request=parent_request,
                    is_cascade_failure=is_cascade,
                    chain_depth=chain_depth,
                )
            )

    def _on_quitting(self, **kwargs: Any) -> None:
        """Handle events.quitting — no-op (explicit export is the primary pattern)."""
        pass

    def get_correlated_events(self) -> list[CorrelatedEvent]:
        """Return all recorded correlated events in chronological order."""
        with self._lock:
            return list(self._events)

    def get_failure_chains(self) -> list[FailureChain]:
        """Build and return failure chains from recorded events.

        A failure chain starts at a root failure (exception is not None,
        is_cascade_failure is False) and includes all subsequent cascade
        failures from the same user.

        Returns:
            List of FailureChain objects, sorted by cascade_count descending.
        """
        with self._lock:
            events = list(self._events)

        chains: list[FailureChain] = []
        # Group events by user_id
        by_user: dict[str, list[CorrelatedEvent]] = {}
        for ev in events:
            if ev.user_id is not None:
                by_user.setdefault(ev.user_id, []).append(ev)

        for user_events in by_user.values():
            i = 0
            while i < len(user_events):
                ev = user_events[i]
                # Root failure: failed but not a cascade
                if ev.exception is not None and not ev.is_cascade_failure:
                    dependents: list[CorrelatedEvent] = []
                    j = i + 1
                    while j < len(user_events):
                        next_ev = user_events[j]
                        if next_ev.exception is not None and next_ev.is_cascade_failure:
                            dependents.append(next_ev)
                            j += 1
                        else:
                            break
                    if dependents:
                        chains.append(
                            FailureChain(
                                root_request=ev,
                                failed_dependents=dependents,
                                cascade_count=len(dependents),
                                total_chain_length=1 + len(dependents),
                            )
                        )
                    i = j
                else:
                    i += 1

        # Sort by cascade_count descending
        chains.sort(key=lambda c: c.cascade_count, reverse=True)
        return chains

    def export_csv(self, path: str | Path) -> Path:
        """Export all correlated events to a CSV file.

        Args:
            path: Output file path.

        Returns:
            Resolved Path to the written file.
        """
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            events = list(self._events)

        headers = [
            "timestamp",
            "request_type",
            "name",
            "response_time",
            "status_code",
            "exception",
            "user_id",
            "correlation_id",
            "parent_request",
            "is_cascade_failure",
            "chain_depth",
        ]
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for ev in events:
                writer.writerow(
                    [
                        ev.timestamp,
                        ev.request_type,
                        ev.name,
                        ev.response_time,
                        ev.status_code,
                        ev.exception or "",
                        ev.user_id or "",
                        ev.correlation_id or "",
                        ev.parent_request or "",
                        ev.is_cascade_failure,
                        ev.chain_depth,
                    ]
                )
        return output.resolve()

    def export_json(self, path: str | Path, *, chains_only: bool = True) -> Path:
        """Export correlated data to a JSON file.

        Args:
            path: Output file path.
            chains_only: If True (default), export failure chains as a list
                of FailureChain dicts. If False, export all events as a
                flat list of CorrelatedEvent dicts.

        Returns:
            Resolved Path to the written file.
        """
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if chains_only:
            chains = self.get_failure_chains()
            data = [
                {
                    "root_request": asdict(c.root_request),
                    "failed_dependents": [asdict(d) for d in c.failed_dependents],
                    "cascade_count": c.cascade_count,
                    "total_chain_length": c.total_chain_length,
                }
                for c in chains
            ]
        else:
            with self._lock:
                events = list(self._events)
            data = [asdict(e) for e in events]

        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return output.resolve()

    def get_summary(self) -> CorrelationSummary:
        """Compute summary statistics from recorded events.

        Returns:
            CorrelationSummary with aggregate stats.
        """
        with self._lock:
            events = list(self._events)

        total_requests = len(events)
        total_failures = sum(1 for e in events if e.exception is not None)
        cascade_failures = sum(1 for e in events if e.is_cascade_failure)
        root_failures = sum(
            1 for e in events if e.exception is not None and not e.is_cascade_failure
        )

        if total_requests > 0:
            avg_chain_depth = sum(e.chain_depth for e in events) / total_requests
        else:
            avg_chain_depth = 0.0

        chains = self.get_failure_chains()
        top_chains = chains[:10]

        return CorrelationSummary(
            total_requests=total_requests,
            total_failures=total_failures,
            cascade_failures=cascade_failures,
            root_failures=root_failures,
            top_failure_chains=top_chains,
            avg_chain_depth=avg_chain_depth,
        )

    @staticmethod
    def _extract_status_code(response: Any, exception: Any) -> int:
        """Extract HTTP status code from a response object.

        Returns 0 when no response is available (connection error, etc.).
        Follows the same pattern as Locust's CsvRequestLogger.

        Args:
            response: HTTP response object or None.
            exception: Exception object or None.

        Returns:
            HTTP status code as int, or 0 if unavailable.
        """
        if exception is not None and response is None:
            return 0
        try:
            return int(response.status_code)
        except (AttributeError, TypeError, ValueError):
            return 0


__all__ = [
    "CorrelatedEvent",
    "CorrelationSummary",
    "FailureChain",
    "RequestCorrelator",
]
