"""Unit tests for soak test template."""

from locust_templates.soak import SoakUser


class TestSoakUser:
    """Test the SoakUser Locust user class."""

    def test_wait_time_between_2_and_8_seconds(self):
        wait_time = SoakUser.wait_time
        samples = [wait_time(None) for _ in range(100)]
        assert all(2.0 <= s <= 8.0 for s in samples)

    def test_has_typical_user_flow_task(self):
        assert hasattr(SoakUser, "typical_user_flow")

    def test_has_data_creation_task(self):
        assert hasattr(SoakUser, "data_creation")

    def test_has_read_heavy_task(self):
        assert hasattr(SoakUser, "read_heavy")

    def test_has_background_cleanup_task(self):
        assert hasattr(SoakUser, "background_cleanup")
