"""Unit tests for stress test template."""

from locust_templates.stress import StressUser


class TestStressUser:
    """Test the StressUser Locust user class."""

    def test_wait_time_between_1_and_5_seconds(self):
        wait_time = StressUser.wait_time
        samples = [wait_time(None) for _ in range(100)]
        assert all(1.0 <= s <= 5.0 for s in samples)

    def test_has_ramp_up_task(self):
        assert hasattr(StressUser, "ramp_up_request")

    def test_has_sustained_load_task(self):
        assert hasattr(StressUser, "sustained_request")

    def test_has_spike_request_task(self):
        assert hasattr(StressUser, "spike_request")

    def test_has_on_start_method(self):
        assert hasattr(StressUser, "on_start")

    def test_has_on_stop_method(self):
        assert hasattr(StressUser, "on_stop")
