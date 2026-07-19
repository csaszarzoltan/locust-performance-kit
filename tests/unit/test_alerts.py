"""Unit tests for configurable threshold alerts.

Tests the AlertRule, Alert, and AlertEngine classes that fire alerts
when metrics exceed configured thresholds during a running test.
"""

from __future__ import annotations

import time

from locust_templates.alerts import Alert, AlertEngine, AlertRule

# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that the alerts module has the correct public API."""

    def test_alert_rule_is_dataclass(self):
        import dataclasses

        assert dataclasses.is_dataclass(AlertRule)

    def test_alert_is_dataclass(self):
        import dataclasses

        assert dataclasses.is_dataclass(Alert)

    def test_alert_engine_is_class(self):
        assert isinstance(AlertEngine, type)

    def test_alert_rule_fields(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        assert rule.name == "p95-high"
        assert rule.metric == "p95"
        assert rule.operator == ">"
        assert rule.threshold == 500.0

    def test_alert_rule_default_severity(self):
        rule = AlertRule(name="err", metric="error_rate", operator=">", threshold=0.01)
        assert rule.severity == "warning"

    def test_alert_rule_custom_severity(self):
        rule = AlertRule(
            name="crit",
            metric="p99",
            operator=">",
            threshold=1000.0,
            severity="critical",
        )
        assert rule.severity == "critical"

    def test_alert_fields(self):
        now = time.time()
        alert = Alert(
            rule_name="p95-high",
            metric="p95",
            value=600.0,
            threshold=500.0,
            operator=">",
            severity="warning",
            timestamp=now,
            message="p95 600.0 > 500.0",
        )
        assert alert.rule_name == "p95-high"
        assert alert.value == 600.0
        assert alert.severity == "warning"

    def test_alert_engine_init(self):
        engine = AlertEngine()
        assert engine.get_alerts() == []

    def test_alert_engine_init_with_rules(self):
        rules = [AlertRule(name="r1", metric="p95", operator=">", threshold=500.0)]
        engine = AlertEngine(rules=rules)
        assert len(engine._rules) == 1

    def test_alert_engine_add_rule(self):
        engine = AlertEngine()
        rule = AlertRule(name="r1", metric="p95", operator=">", threshold=500.0)
        engine.add_rule(rule)
        assert len(engine._rules) == 1


# ──────────────────────────────────────────────────────────────
# Behavioral tests — AlertRule evaluation
# ──────────────────────────────────────────────────────────────


class TestAlertRuleEvaluation:
    """Test AlertRule._evaluate() logic."""

    def test_gt_operator_fires(self):
        rule = AlertRule(name="r", metric="p95", operator=">", threshold=500.0)
        alert = rule.evaluate(600.0)
        assert alert is not None
        assert alert.rule_name == "r"
        assert alert.value == 600.0

    def test_gt_operator_no_fire(self):
        rule = AlertRule(name="r", metric="p95", operator=">", threshold=500.0)
        assert rule.evaluate(400.0) is None

    def test_gt_equal_no_fire(self):
        """Strict >: equal does not fire."""
        rule = AlertRule(name="r", metric="p95", operator=">", threshold=500.0)
        assert rule.evaluate(500.0) is None

    def test_ge_operator_fires_on_equal(self):
        rule = AlertRule(name="r", metric="p95", operator=">=", threshold=500.0)
        assert rule.evaluate(500.0) is not None

    def test_ge_operator_no_fire(self):
        rule = AlertRule(name="r", metric="p95", operator=">=", threshold=500.0)
        assert rule.evaluate(499.9) is None

    def test_lt_operator_fires(self):
        rule = AlertRule(name="r", metric="throughput", operator="<", threshold=100.0)
        assert rule.evaluate(50.0) is not None

    def test_lt_operator_no_fire(self):
        rule = AlertRule(name="r", metric="throughput", operator="<", threshold=100.0)
        assert rule.evaluate(150.0) is None

    def test_le_operator_fires_on_equal(self):
        rule = AlertRule(name="r", metric="throughput", operator="<=", threshold=100.0)
        assert rule.evaluate(100.0) is not None

    def test_eq_operator_fires(self):
        rule = AlertRule(name="r", metric="status", operator="==", threshold=500)
        assert rule.evaluate(500) is not None

    def test_eq_operator_no_fire(self):
        rule = AlertRule(name="r", metric="status", operator="==", threshold=500)
        assert rule.evaluate(200) is None

    def test_invalid_operator_raises(self):
        rule = AlertRule(name="r", metric="p95", operator="~=", threshold=500.0)
        try:
            rule.evaluate(600.0)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass

    def test_alert_message_format(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        alert = rule.evaluate(600.0)
        assert alert is not None
        assert "p95" in alert.message
        assert "600" in alert.message
        assert "500" in alert.message


# ──────────────────────────────────────────────────────────────
# Behavioral tests — AlertEngine
# ──────────────────────────────────────────────────────────────


class TestAlertEngine:
    """Test AlertEngine.check() and alert management."""

    def test_check_no_rules(self):
        engine = AlertEngine()
        alerts = engine.check({"p95": 600.0})
        assert alerts == []

    def test_check_fires_on_threshold_breach(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        alerts = engine.check({"p95": 600.0})
        assert len(alerts) == 1
        assert alerts[0].rule_name == "p95-high"

    def test_check_no_fire_within_threshold(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        alerts = engine.check({"p95": 400.0})
        assert alerts == []

    def test_check_missing_metric_no_fire(self):
        """If the metric is not in the metrics dict, no alert fires."""
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        alerts = engine.check({"throughput": 100.0})
        assert alerts == []

    def test_check_multiple_rules(self):
        rules = [
            AlertRule(name="p95", metric="p95", operator=">", threshold=500.0),
            AlertRule(name="err", metric="error_rate", operator=">", threshold=0.01),
            AlertRule(name="rps", metric="throughput", operator="<", threshold=100.0),
        ]
        engine = AlertEngine(rules=rules)
        alerts = engine.check({"p95": 600.0, "error_rate": 0.05, "throughput": 150.0})
        assert len(alerts) == 2
        names = {a.rule_name for a in alerts}
        assert names == {"p95", "err"}

    def test_get_alerts_returns_all_fired(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        engine.check({"p95": 600.0})
        engine.check({"p95": 700.0})
        all_alerts = engine.get_alerts()
        assert len(all_alerts) == 2

    def test_clear_alerts(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        engine.check({"p95": 600.0})
        assert len(engine.get_alerts()) == 1
        engine.clear_alerts()
        assert engine.get_alerts() == []

    def test_alert_has_timestamp(self):
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        before = time.time()
        engine.check({"p95": 600.0})
        after = time.time()
        alerts = engine.get_alerts()
        assert before <= alerts[0].timestamp <= after

    def test_check_dedup_not_enabled_by_default(self):
        """Without dedup, the same breach fires on every check call."""
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        engine.check({"p95": 600.0})
        engine.check({"p95": 600.0})
        assert len(engine.get_alerts()) == 2

    def test_check_dedup_enabled(self):
        """With dedup=True, repeated breaches of the same rule are deduplicated."""
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule], dedup=True)
        engine.check({"p95": 600.0})
        engine.check({"p95": 600.0})
        assert len(engine.get_alerts()) == 1

    def test_check_dedup_resets_when_clear(self):
        """After clearing, the same breach fires again even with dedup."""
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule], dedup=True)
        engine.check({"p95": 600.0})
        engine.clear_alerts()
        engine.check({"p95": 600.0})
        assert len(engine.get_alerts()) == 1

    def test_check_dedup_resets_when_value_returns_below(self):
        """When metric returns below threshold, then breaches again,
        a new alert fires."""
        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule], dedup=True)
        engine.check({"p95": 600.0})
        engine.check({"p95": 400.0})  # below threshold
        engine.check({"p95": 700.0})  # breaches again
        assert len(engine.get_alerts()) == 2


# ──────────────────────────────────────────────────────────────
# Factory tests
# ──────────────────────────────────────────────────────────────


class TestAlertEngineFactory:
    """Test AlertEngine.from_config() factory."""

    def test_from_config_dict(self):
        config = [
            {
                "name": "p95-high",
                "metric": "p95",
                "operator": ">",
                "threshold": 500.0,
            },
            {
                "name": "err-high",
                "metric": "error_rate",
                "operator": ">",
                "threshold": 0.01,
            },
        ]
        engine = AlertEngine.from_config(config)
        assert len(engine._rules) == 2
        assert engine._rules[0].name == "p95-high"

    def test_from_config_empty(self):
        engine = AlertEngine.from_config([])
        assert len(engine._rules) == 0

    def test_from_config_with_severity(self):
        config = [
            {
                "name": "crit-p99",
                "metric": "p99",
                "operator": ">",
                "threshold": 1000.0,
                "severity": "critical",
            },
        ]
        engine = AlertEngine.from_config(config)
        assert engine._rules[0].severity == "critical"
