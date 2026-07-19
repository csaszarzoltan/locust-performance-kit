"""Metrics collection for Locust performance tests.

Provides thread-safe metrics recording and percentile calculations
for analyzing load test results.
"""

import threading
import time
from collections import defaultdict


class MetricsCollector:
    """Thread-safe metrics collector for Locust load tests."""

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics: dict[str, list[dict]] = defaultdict(list)

    def record_request(
        self,
        name: str,
        response_time: float,
        status_code: int,
        success: bool,
    ) -> None:
        """Record a single request metric."""
        with self._lock:
            self._metrics[name].append(
                {
                    "response_time": response_time,
                    "status_code": status_code,
                    "success": success,
                    "timestamp": time.time(),
                }
            )

    def get_summary(self) -> dict[str, dict]:
        """Get summary statistics for all endpoints."""
        with self._lock:
            summary = {}
            for name, records in self._metrics.items():
                if not records:
                    continue
                response_times = [r["response_time"] for r in records]
                failures = sum(1 for r in records if not r["success"])
                summary[name] = {
                    "count": len(records),
                    "avg": sum(response_times) / len(response_times),
                    "min": min(response_times),
                    "max": max(response_times),
                    "failures": failures,
                }
            return summary

    def get_percentile(self, name: str, percentile: int) -> float:
        """Calculate percentile for a specific endpoint."""
        with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return 0.0
            response_times = sorted(
                [r["response_time"] for r in self._metrics[name]]
            )
            n = len(response_times)
            if n == 1:
                return response_times[0]
            # Linear interpolation percentile
            k = (percentile / 100) * (n - 1)
            f = int(k)
            c = f + 1
            if c >= n:
                return response_times[-1]
            d = k - f
            return response_times[f] + d * (response_times[c] - response_times[f])

    def get_error_rate(self, name: str) -> float:
        """Calculate error rate for a specific endpoint."""
        with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return 0.0
            records = self._metrics[name]
            failures = sum(1 for r in records if not r["success"])
            return failures / len(records)

    def reset(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self._metrics.clear()
