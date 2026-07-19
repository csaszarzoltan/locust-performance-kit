"""Unit tests for web UI test template."""

from locust_templates.web_ui import WebUIUser


class TestWebUIUser:
    """Test the WebUIUser Locust user class."""

    def test_wait_time_between_2_and_10_seconds(self):
        wait_time = WebUIUser.wait_time
        samples = [wait_time(None) for _ in range(100)]
        assert all(2.0 <= s <= 10.0 for s in samples)

    def test_has_homepage_task(self):
        assert hasattr(WebUIUser, "browse_homepage")

    def test_has_search_task(self):
        assert hasattr(WebUIUser, "search_items")

    def test_has_detail_page_task(self):
        assert hasattr(WebUIUser, "view_detail_page")

    def test_has_add_to_cart_task(self):
        assert hasattr(WebUIUser, "add_to_cart")

    def test_has_checkout_task(self):
        assert hasattr(WebUIUser, "checkout_flow")
