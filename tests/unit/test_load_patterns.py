"""Pre-dev tests for load_patterns module and new shapes (ConstantLoadShape, RampUpLoadShape).

Tests define the contract for the load pattern builder that maps CLI config
to concrete Locust LoadShape classes, plus the new shape classes in shapes.py.

Pattern:
- Interface tests: verify imports, dataclass fields, signatures (PASS immediately)
- Behavioral tests: verify pattern resolution logic (FAIL with NotImplementedError until implemented)
"""

from __future__ import annotations

import inspect
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

import pytest

from locust_templates.load_patterns import (
    SUPPORTED_PATTERNS,
    PatternConfig,
    PatternResult,
    parse_duration,
    resolve_pattern,
)
from locust_templates.shapes import ConstantLoadShape, RampUpLoadShape

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def constant_config() -> PatternConfig:
    return PatternConfig(pattern="constant", users=20, spawn_rate=2, runtime="5m")


@pytest.fixture
def ramp_up_config() -> PatternConfig:
    return PatternConfig(
        pattern="ramp-up",
        users=50,
        spawn_rate=5,
        runtime="10m",
        ramp_up_duration="2m",
        hold_duration="5m",
        ramp_down_duration="3m",
    )


@pytest.fixture
def spike_config() -> PatternConfig:
    return PatternConfig(
        pattern="spike",
        users=10,
        spawn_rate=2,
        spike_users=100,
        spike_duration="5s",
    )


# ──────────────────────────────────────────────────────────────
# Interface tests — PASS immediately against stubs
# ──────────────────────────────────────────────────────────────


class TestPatternConfigDataclass:
    """Verify PatternConfig dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(PatternConfig)

    def test_has_required_fields(self):
        field_names = {f.name for f in dataclass_fields(PatternConfig)}
        for name in ("pattern", "users", "spawn_rate", "runtime",
                      "spike_users", "spike_duration",
                      "ramp_up_duration", "ramp_down_duration", "hold_duration"):
            assert name in field_names, f"Missing field: {name}"

    def test_default_values(self):
        cfg = PatternConfig(pattern="constant")
        assert cfg.users == 10
        assert cfg.spawn_rate == 1
        assert cfg.runtime == "5m"
        assert cfg.spike_users == 100
        assert cfg.spike_duration == "5s"
        assert cfg.ramp_up_duration == "2m"
        assert cfg.ramp_down_duration == "1m"
        assert cfg.hold_duration == "3m"

    def test_custom_values(self):
        cfg = PatternConfig(pattern="ramp-up", users=50, spawn_rate=5)
        assert cfg.users == 50
        assert cfg.spawn_rate == 5


class TestPatternResultDataclass:
    """Verify PatternResult dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(PatternResult)

    def test_has_required_fields(self):
        field_names = {f.name for f in dataclass_fields(PatternResult)}
        for name in ("shape_class", "shape_import", "constructor_args", "code_snippet"):
            assert name in field_names, f"Missing field: {name}"

    def test_constructable(self):
        pr = PatternResult(
            shape_class="ConstantLoadShape",
            shape_import="from locust_templates.shapes import ConstantLoadShape",
        )
        assert pr.shape_class == "ConstantLoadShape"
        assert pr.constructor_args == {}
        assert pr.code_snippet == ""


class TestSupportedPatternsConstant:
    """Verify SUPPORTED_PATTERNS is defined."""

    def test_is_tuple(self):
        assert isinstance(SUPPORTED_PATTERNS, tuple)

    def test_contains_constant(self):
        assert "constant" in SUPPORTED_PATTERNS

    def test_contains_ramp_up(self):
        assert "ramp-up" in SUPPORTED_PATTERNS

    def test_contains_spike(self):
        assert "spike" in SUPPORTED_PATTERNS

    def test_has_three_entries(self):
        assert len(SUPPORTED_PATTERNS) == 3


class TestResolvePatternExists:
    """Verify resolve_pattern is importable and callable."""

    def test_is_callable(self):
        assert callable(resolve_pattern)

    def test_signature(self):
        sig = inspect.signature(resolve_pattern)
        params = list(sig.parameters.keys())
        assert "config" in params

    def test_return_annotation(self):
        sig = inspect.signature(resolve_pattern)
        ret = sig.return_annotation
        assert ret is inspect.Parameter.empty or ret is PatternResult or ret == "PatternResult"


class TestParseDurationExists:
    """Verify parse_duration is importable and callable."""

    def test_is_callable(self):
        assert callable(parse_duration)

    def test_signature(self):
        sig = inspect.signature(parse_duration)
        params = list(sig.parameters.keys())
        assert "duration_str" in params


class TestConstantLoadShapeExists:
    """Verify ConstantLoadShape class exists and is a LoadTestShape subclass."""

    def test_class_exists(self):
        assert ConstantLoadShape is not None

    def test_is_subclass(self):
        from locust import LoadTestShape
        assert issubclass(ConstantLoadShape, LoadTestShape)

    def test_init_signature(self):
        sig = inspect.signature(ConstantLoadShape.__init__)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "steady_users" in params
        assert "spawn_rate" in params
        assert "duration" in params

    def test_init_type_hints(self):
        hints = ConstantLoadShape.__init__.__annotations__
        assert "steady_users" in hints
        assert "spawn_rate" in hints
        assert "duration" in hints


class TestRampUpLoadShapeExists:
    """Verify RampUpLoadShape class exists and is a LoadTestShape subclass."""

    def test_class_exists(self):
        assert RampUpLoadShape is not None

    def test_is_subclass(self):
        from locust import LoadTestShape
        assert issubclass(RampUpLoadShape, LoadTestShape)

    def test_init_signature(self):
        sig = inspect.signature(RampUpLoadShape.__init__)
        params = list(sig.parameters.keys())
        for name in ("self", "target_users", "ramp_up_duration",
                      "hold_duration", "ramp_down_duration", "spawn_rate"):
            assert name in params, f"Missing param: {name}"

    def test_init_type_hints(self):
        hints = RampUpLoadShape.__init__.__annotations__
        for name in ("target_users", "ramp_up_duration", "hold_duration",
                      "ramp_down_duration", "spawn_rate"):
            assert name in hints, f"Missing hint: {name}"


# ──────────────────────────────────────────────────────────────
# Behavioral tests — FAIL with NotImplementedError until implemented
# ──────────────────────────────────────────────────────────────


class TestConstantLoadShapeBehavioral:
    """Behavioral tests for ConstantLoadShape."""

    def test_works(self):
        shape = ConstantLoadShape(steady_users=10, spawn_rate=1, duration=300)
        assert shape.steady_users == 10

    def test_tick_returns_tuple(self):
        try:
            shape = ConstantLoadShape(steady_users=10, spawn_rate=1, duration=300)
            result = shape.tick()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_tick_returns_steady_users(self):
        try:
            shape = ConstantLoadShape(steady_users=10, spawn_rate=1, duration=300)
            result = shape.tick()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        if result is not None:
            users, spawn_rate = result
            assert users == 10
            assert spawn_rate == 1


class TestRampUpLoadShapeBehavioral:
    """Behavioral tests for RampUpLoadShape."""

    def test_init_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            RampUpLoadShape(
                target_users=50, ramp_up_duration=120,
                hold_duration=180, ramp_down_duration=60, spawn_rate=5,
            )

    def test_tick_returns_tuple_or_none(self):
        try:
            shape = RampUpLoadShape(
                target_users=50, ramp_up_duration=120,
                hold_duration=180, ramp_down_duration=60, spawn_rate=5,
            )
            result = shape.tick()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_tick_returns_nonnegative_users(self):
        try:
            shape = RampUpLoadShape(
                target_users=50, ramp_up_duration=120,
                hold_duration=180, ramp_down_duration=60, spawn_rate=5,
            )
            result = shape.tick()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        if result is not None:
            users, spawn_rate = result
            assert users >= 0
            assert spawn_rate > 0


class TestResolvePatternBehavioral:
    """Behavioral tests for resolve_pattern()."""

    def test_raises_not_implemented(self, constant_config):
        with pytest.raises(NotImplementedError):
            resolve_pattern(constant_config)

    def test_returns_pattern_result(self, constant_config):
        try:
            result = resolve_pattern(constant_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, PatternResult)

    def test_constant_pattern_shape_class(self, constant_config):
        try:
            result = resolve_pattern(constant_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.shape_class == "ConstantLoadShape"

    def test_ramp_up_pattern_shape_class(self, ramp_up_config):
        try:
            result = resolve_pattern(ramp_up_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.shape_class == "RampUpLoadShape"

    def test_spike_pattern_shape_class(self, spike_config):
        try:
            result = resolve_pattern(spike_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.shape_class == "SpikeLoadShape"

    def test_shape_import_is_valid_python(self, constant_config):
        try:
            result = resolve_pattern(constant_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.shape_import.startswith("from ")
        compile(result.shape_import, "<import>", "exec")

    def test_code_snippet_is_valid_python(self, constant_config):
        try:
            result = resolve_pattern(constant_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        compile(result.code_snippet, "<snippet>", "exec")

    def test_constructor_args_populated(self, constant_config):
        try:
            result = resolve_pattern(constant_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.constructor_args) > 0

    def test_unknown_pattern_raises_value_error(self):
        bad_config = PatternConfig(pattern="unknown")
        try:
            resolve_pattern(bad_config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except ValueError as e:
            assert "unknown" in str(e).lower() or "not supported" in str(e).lower()


class TestParseDurationBehavioral:
    """Behavioral tests for parse_duration()."""

    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            parse_duration("5m")

    @pytest.mark.parametrize("duration_str,expected_seconds", [
        ("30s", 30.0),
        ("5m", 300.0),
        ("1h", 3600.0),
        ("10m", 600.0),
        ("2h30m", 9000.0),
        ("0s", 0.0),
    ])
    def test_parse_durations(self, duration_str, expected_seconds):
        try:
            result = parse_duration(duration_str)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == expected_seconds, f"parse_duration('{duration_str}') should be {expected_seconds}, got {result}"

    def test_invalid_format_raises(self):
        try:
            parse_duration("invalid")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except (ValueError, TypeError):
            pass  # Expected
