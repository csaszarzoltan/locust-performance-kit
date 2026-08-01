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
            recovery_elapsed = (
                cycle_position - self.baseline_duration - self.spike_duration
            )
            recovery_progress = recovery_elapsed / self.recovery_duration
            current_users = int(
                self.spike_users
                - (self.spike_users - self.baseline_users) * recovery_progress
            )
            return max(current_users, self.baseline_users), self.baseline_users


class ConstantLoadShape(LoadTestShape):
    """Constant user count for the entire test duration.

    Attributes:
        steady_users: Fixed number of concurrent users.
        spawn_rate: Users spawned per second to reach steady state.
        duration: Total test duration in seconds.
    """

    def __init__(self, steady_users: int, spawn_rate: int, duration: float):
        super().__init__()
        self.steady_users = steady_users
        self.spawn_rate = spawn_rate
        self.duration = duration
        self._start_time = time.time()

    def tick(self):
        """Return (users, spawn_rate) for the current tick, or None to stop."""
        run_time = time.time() - self._start_time
        if run_time >= self.duration:
            return None
        return self.steady_users, self.spawn_rate


class RampUpLoadShape(LoadTestShape):
    """Gradual ramp from 0 to max_users, hold, then ramp down.

    Attributes:
        target_users: Maximum concurrent users at peak.
        ramp_up_duration: Seconds to reach target_users.
        hold_duration: Seconds to hold at peak.
        ramp_down_duration: Seconds to ramp back to 0.
        spawn_rate: Users spawned/despawned per second.
    """

    def __init__(
        self, target_users: int, ramp_up_duration: float,
        hold_duration: float, ramp_down_duration: float, spawn_rate: int,
    ):
        super().__init__()
        self.target_users = target_users
        self.ramp_up_duration = ramp_up_duration
        self.hold_duration = hold_duration
        self.ramp_down_duration = ramp_down_duration
        self.spawn_rate = spawn_rate
        self._start_time = time.time()

    def tick(self):
        """Return (users, spawn_rate) for the current tick, or None to stop."""
        run_time = time.time() - self._start_time

        if run_time < self.ramp_up_duration:
            # Ramp-up phase: linear interpolation from 0 to target_users
            progress = run_time / self.ramp_up_duration
            current_users = max(1, int(self.target_users * progress))
            return current_users, self.spawn_rate
        elif run_time < self.ramp_up_duration + self.hold_duration:
            # Hold phase
            return self.target_users, self.spawn_rate
        elif run_time < self.ramp_up_duration + self.hold_duration + self.ramp_down_duration:
            # Ramp-down phase: linear interpolation from target_users to 0
            elapsed_in_ramp_down = run_time - self.ramp_up_duration - self.hold_duration
            progress = elapsed_in_ramp_down / self.ramp_down_duration
            current_users = max(0, int(self.target_users * (1 - progress)))
            if current_users == 0:
                return None
            return current_users, self.spawn_rate
        else:
            # Test complete
            return None
