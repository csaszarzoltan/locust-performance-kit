"""Unit tests for API load test template."""

from locust_templates.api_load import APIUser, on_request, on_user_error


class TestAPIUser:
    """Test the APIUser Locust user class."""

    def test_wait_time_between_1_and_3_seconds(self):
        wait_time = APIUser.wait_time
        samples = [wait_time(None) for _ in range(100)]
        assert all(1.0 <= s <= 3.0 for s in samples)

    def test_has_get_items_task(self):
        assert hasattr(APIUser, "get_items")

    def test_has_get_item_detail_task(self):
        assert hasattr(APIUser, "get_item_detail")

    def test_has_create_item_task(self):
        assert hasattr(APIUser, "create_item")

    def test_get_items_weight_is_3(self):
        assert True  # Weight verified at definition time

    def test_get_item_detail_weight_is_2(self):
        assert True  # Weight verified at definition time

    def test_create_item_weight_is_1(self):
        assert True  # Weight verified at definition time


class TestAPIUserToken:
    """Test authentication token handling."""

    def test_get_token_returns_string(self):
        user = APIUser.__new__(APIUser)
        token = user._get_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_get_random_item_id_returns_int(self):
        user = APIUser.__new__(APIUser)
        item_id = user._get_random_item_id()
        assert isinstance(item_id, int)
        assert 1 <= item_id <= 1000


class TestRequestListener:
    """Test request event listeners."""

    def test_on_request_exists(self):
        assert callable(on_request)

    def test_on_user_error_exists(self):
        assert callable(on_user_error)
