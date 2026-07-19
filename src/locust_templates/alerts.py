"""Configurable threshold alerts for real-time performance monitoring.

Alert rules are evaluated against live metrics during a running test.
When a metric breaches a threshold, an Alert is recorded with timestamp,
severity, and a human-readable message.

Public API:
    AlertRule   — a single threshold rule (metric, operator, threshold)
    Alert       — a fired alert with value, timestamp, message
    AlertEngine — evaluates rules against metrics, manages alert history
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

# ──────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────


@dataclass
class AlertRule:
    """A single threshold alert rule.

    Attributes:
        name: Human-readable rule name (e.g. "p95-high").
        metric: Metric key to check (e.g. "p95", "error_rate", "throughput").
        operator: Comparison operator: ">", ">=", "<", "<=", "==".
        threshold: Threshold value to compare against.
        severity: Alert severity — "warning" (default) or "critical".
    """

    name: str
    metric: str
    operator: str
    threshold: float
    severity: str = "warning"

    def evaluate(self, value: float) -> Alert | None:
        """Evaluate this rule against a metric value.

        Args:
            value: The current metric value.

        Returns:
            An Alert if the threshold is breached, else None.
        """
        breached = _compare(value, self.operator, self.threshold)
        if not breached:
            return None
        return Alert(
            rule_name=self.name,
            metric=self.metric,
            value=value,
            threshold=self.threshold,
            operator=self.operator,
            severity=self.severity,
            timestamp=time.time(),
            message=(
                f"{self.metric} {value} {self.operator} {self.threshold}"
            ),
        )


@dataclass
class Alert:
    """A fired alert.

    Attributes:
        rule_name: Name of the AlertRule that fired.
        metric: Metric that breached.
        value: The metric value at time of breach.
        threshold: The threshold that was breached.
        operator: Comparison operator.
        severity: "warning" or "critical".
        timestamp: Unix timestamp when the alert fired.
        message: Human-readable alert message.
    """

    rule_name: str
    metric: str
    value: float
    threshold: float
    operator: str
    severity: str
    timestamp: float
    message: str


# ──────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────


class AlertEngine:
    """Evaluate alert rules against live metrics.

    Example:
        rules = [AlertRule("p95-high", "p95", ">", 500.0)]
        engine = AlertEngine(rules=rules, dedup=True)
        alerts = engine.check({"p95": 600.0})
        if alerts:
            for a in alerts:
                print(a.message)
    """

    def __init__(
        self,
        rules: list[AlertRule] | None = None,
        *,
        dedup: bool = False,
    ) -> None:
        """Initialize the alert engine.

        Args:
            rules: Initial list of alert rules.
            dedup: If True, suppress duplicate alerts for the same rule
                while the metric remains in breach. A new alert fires
                only after the metric returns below threshold and then
                breaches again.
        """
        self._rules: list[AlertRule] = list(rules) if rules else []
        self._dedup = dedup
        self._alerts: list[Alert] = []
        # Track which rules are currently in breach (for dedup)
        self._active: set[str] = set()

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule to the engine."""
        self._rules.append(rule)

    def check(self, metrics: dict[str, float]) -> list[Alert]:
        """Evaluate all rules against the given metrics.

        Args:
            metrics: Dict of metric name → value (e.g. {"p95": 600.0}).

        Returns:
            List of newly fired Alerts (may be empty).
        """
        fired: list[Alert] = []
        for rule in self._rules:
            value = metrics.get(rule.metric)
            if value is None:
                # Metric not provided — skip
                if self._dedup:
                    self._active.discard(rule.name)
                continue

            alert = rule.evaluate(value)
            if alert is not None:
                if self._dedup:
                    if rule.name in self._active:
                        # Already in breach — suppress duplicate
                        continue
                    self._active.add(rule.name)
                self._alerts.append(alert)
                fired.append(alert)
            else:
                if self._dedup:
                    self._active.discard(rule.name)
        return fired

    def get_alerts(self) -> list[Alert]:
        """Return all alerts fired since the last clear."""
        return list(self._alerts)

    def clear_alerts(self) -> None:
        """Clear all recorded alerts and reset dedup state."""
        self._alerts.clear()
        self._active.clear()

    @classmethod
    def from_config(cls, config: list[dict[str, Any]]) -> AlertEngine:
        """Create an AlertEngine from a list of config dicts.

        Each dict should have keys: name, metric, operator, threshold,
        and optionally severity.

        Args:
            config: List of rule config dicts.

        Returns:
            Configured AlertEngine instance.
        """
        rules = [
            AlertRule(
                name=rule["name"],
                metric=rule["metric"],
                operator=rule["operator"],
                threshold=float(rule["threshold"]),
                severity=rule.get("severity", "warning"),
            )
            for rule in config
        ]
        return cls(rules=rules)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _compare(value: float, operator: str, threshold: float) -> bool:
    """Compare value to threshold using the given operator."""
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "==":
        return value == threshold
    raise ValueError(
        f"Invalid operator '{operator}'. "
        f"Valid operators: >, >=, <, <=, =="
    )


__all__ = [
    "Alert",
    "AlertEngine",
    "AlertRule",
]
