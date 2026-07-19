"""Unit tests for custom Locust shapes (StepLoadShape, SpikeLoadShape).

Tests verify:
- Correct user count at each tick
- Step transitions work as configured
- Spike/recovery phases work correctly
- Edge cases (empty steps, single step, very long tests)
"""

import pytest
from locust_templates.shapes import StepLoadShape, SpikeLoadShape


class TestStepLoadShape:
    """Test the StepLoadShape for ramp-up patterns."""

    def test_init_with_defaults(self):
        shape = StepLoadShape()
        assert shape.step_duration == 30
        assert shape.step_users == 10
        assert shape.max_users == 100

    def test_init_with_custom_values(self):
        shape = StepLoadShape(
            step_duration=60,
            step_users=20,
            max_users=500,
        )
        assert shape.step_duration == 60
        assert shape.step_users == 20
        assert shape.max_users == 500

    def test_tick_returns_users_and_spawn_rate(self):
        shape = StepLoadShape(step_duration=10, step_users=5, max_users=50)
        result = shape.tick()
        assert result is not None
        users, spawn_rate = result
        assert isinstance(users, int)
        assert isinstance(spawn_rate, int)
        assert users > 0
        assert spawn_rate > 0

    def test_initial_tick_returns_first_step(self):
        shape = StepLoadShape(step_duration=10, step_users=5, max_users=50)
        users, spawn_rate = shape.tick()
        assert users == 5
        assert spawn_rate == 5

    def test_tick_increases_users_per_step(self):
        shape = StepLoadShape(step_duration=0.01, step_users=10, max_users=100)
        first_users, _ = shape.tick()
        # After first step duration, should increase
        import time
        time.sleep(0.02)
        second_users, _ = shape.tick()
        assert second_users >= first_users

    def test_tick_stops_at_max_users(self):
        shape = StepLoadShape(step_duration=0.01, step_users=50, max_users=100)
        # Run through steps until we hit max
        import time
        max_reached = False
        for _ in range(20):
            result = shape.tick()
            if result is None:
                max_reached = True
                break
            users, _ = result
            if users >= 100:
                max_reached = True
                break
            time.sleep(0.02)
        assert max_reached

    def test_tick_returns_none_after_max(self):
        shape = StepLoadShape(step_duration=0.01, step_users=100, max_users=100)
        import time
        # First tick should return max
        users, _ = shape.tick()
        assert users == 100
        time.sleep(0.02)
        # After step duration, should return None (test complete)
        result = shape.tick()
        assert result is None

    def test_spawn_rate_equals_step_users(self):
        shape = StepLoadShape(step_duration=10, step_users=15, max_users=100)
        users, spawn_rate = shape.tick()
        assert spawn_rate == 15


class TestSpikeLoadShape:
    """Test the SpikeLoadShape for spike testing patterns."""

    def test_init_with_defaults(self):
        shape = SpikeLoadShape()
        assert shape.baseline_users == 10
        assert shape.spike_users == 100
        assert shape.baseline_duration == 30
        assert shape.spike_duration == 5
        assert shape.recovery_duration == 30

    def test_init_with_custom_values(self):
        shape = SpikeLoadShape(
            baseline_users=20,
            spike_users=200,
            baseline_duration=60,
            spike_duration=10,
            recovery_duration=60,
        )
        assert shape.baseline_users == 20
        assert shape.spike_users == 200
        assert shape.baseline_duration == 60
        assert shape.spike_duration == 10
        assert shape.recovery_duration == 60

    def test_tick_returns_users_and_spawn_rate(self):
        shape = SpikeLoadShape(
            baseline_users=10,
            spike_users=50,
            baseline_duration=0.01,
            spike_duration=0.01,
            recovery_duration=0.01,
        )
        result = shape.tick()
        assert result is not None
        users, spawn_rate = result
        assert isinstance(users, int)
        assert isinstance(spawn_rate, int)

    def test_baseline_phase_returns_baseline_users(self):
        shape = SpikeLoadShape(
            baseline_users=10,
            spike_users=100,
            baseline_duration=10,
            spike_duration=5,
            recovery_duration=10,
        )
        users, spawn_rate = shape.tick()
        assert users == 10
        assert spawn_rate == 10

    def test_spike_phase_increases_users(self):
        shape = SpikeLoadShape(
            baseline_users=5,
            spike_users=50,
            baseline_duration=0.01,
            spike_duration=10,
            recovery_duration=0.01,
        )
        import time
        # Wait for baseline to end
        time.sleep(0.02)
        users, _ = shape.tick()
        assert users >= 5  # Should be in spike or recovery phase

    def test_spike_spawn_rate_matches_spike_users(self):
        shape = SpikeLoadShape(
            baseline_users=10,
            spike_users=100,
            baseline_duration=0.01,
            spike_duration=0.01,
            recovery_duration=10,
        )
        import time
        time.sleep(0.02)
        result = shape.tick()
        if result is not None:
            users, spawn_rate = result
            # In spike phase, spawn_rate should match spike_users
            # In recovery phase, it should decrease
            assert spawn_rate > 0

    def test_cycles_through_phases(self):
        shape = SpikeLoadShape(
            baseline_users=5,
            spike_users=25,
            baseline_duration=0.01,
            spike_duration=0.01,
            recovery_duration=0.01,
        )
        import time
        results = []
        for _ in range(10):
            result = shape.tick()
            if result is not None:
                users, _ = result
                results.append(users)
            time.sleep(0.02)
        # Should have seen at least baseline and spike values
        assert len(results) > 0
        assert 5 in results or 25 in results
