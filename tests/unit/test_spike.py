"""Unit tests for spike test template."""

from locust_templates.spike import SpikeUser


class TestSpikeUser:
    """Test the SpikeUser Locust user class."""

    def test_wait_time_between_1_and_2_seconds(self):
        wait_time = SpikeUser.wait_time
        samples = [wait_time(None) for _ in range(100)]
        assert all(1.0 <= s <= 2.0 for s in samples)

    def test_has_normal_request_task(self):
        assert hasattr(SpikeUser, "normal_request")

    def test_has_burst_request_task(self):
        assert hasattr(SpikeUser, "burst_request")

    def test_has_recovery_request_task(self):
        assert hasattr(SpikeUser, "recovery_request")
