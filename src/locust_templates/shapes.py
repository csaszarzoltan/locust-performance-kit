"""Custom Locust shapes for advanced load testing patterns.

Provides reusable shape classes for step-load and spike testing
that can be used alongside any Locust user class.

Usage:
    from locust_templates.shapes import StepLoadShape

    # In your locust file:
    shape = StepLoadShape(step_duration=30, step_users=10, max_users=100)
    environment.runner.shape_class = shape
"""

import time

from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    """Step-load shape for gradual ramp-up testing.

    Increases user count in discrete steps at regular intervals,
    useful for finding breaking points incrementally.

    Attributes:
        step_duration: Seconds to maintain each step before increasing.
        step_users: Number of users to add at each step.
        max_users: Maximum user count (test ends after reaching this).
    """

    def __init__(
        self,
        step_duration: float = 30.0,
        step_users: int = 10,
        max_users: int = 100,
    ):
        super().__init__()
        self.step_duration = step_duration
        self.step_users = step_users
        self.max_users = max_users
        self._start_time = time.time()

    def tick(self):
        """Return (users, spawn_rate) for the current tick, or None to stop."""
        run_time = time.time() - self._start_time
        current_step = int(run_time // self.step_duration) + 1
        target_users = min(current_step * self.step_users, self.max_users)

        if target_users >= self.max_users and run_time > self.step_duration:
            return None

        return target_users, self.step_users


class SpikeLoadShape(LoadTestShape):
    """Spike load shape for burst and recovery testing.

    Alternates between a baseline user count and a spike user count
    to test system recovery behavior.

    Attributes:
        baseline_users: Normal user count during baseline/recovery.
        spike_users: User count during spike phase.
        baseline_duration: Seconds for each baseline phase.
        spike_duration: Seconds for each spike phase.
        recovery_duration: Seconds for recovery after spike.
    """

    def __init__(
        self,
        baseline_users: int = 10,
        spike_users: int = 100,
        baseline_duration: float = 30.0,
        spike_duration: float = 5.0,
        recovery_duration: float = 30.0,
    ):
        super().__init__()
        self.baseline_users = baseline_users
        self.spike_users = spike_users
        self.baseline_duration = baseline_duration
        self.spike_duration = spike_duration
        self.recovery_duration = recovery_duration
        self._start_time = time.time()
        self._cycle_duration = baseline_duration + spike_duration + recovery_duration

    def tick(self):
        """Return (users, spawn_rate) based on current phase."""
        run_time = time.time() - self._start_time
        cycle_position = run_time % self._cycle_duration

        if cycle_position < self.baseline_duration:
            # Baseline phase
            return self.baseline_users, self.baseline_users
        elif cycle_position < self.baseline_duration + self.spike_duration:
            # Spike phase
            return self.spike_users, self.spike_users
        else:
            # Recovery phase - gradually decrease
            recovery_elapsed = cycle_position - self.baseline_duration - self.spike_duration
            recovery_progress = recovery_elapsed / self.recovery_duration
            current_users = int(
                self.spike_users - (self.spike_users - self.baseline_users) * recovery_progress
            )
            return max(current_users, self.baseline_users), self.baseline_users
