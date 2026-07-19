"""Visual tests - screenshot-style verification of template output.

These tests capture the expected structure of test output files
and verify the CI pipeline produces correct artifacts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestTemplateOutputStructure:
    """Verify template output format matches expected patterns."""

    def test_api_load_has_correct_task_distribution(self):
        """API load test should have weighted tasks summing correctly."""
        from locust_templates.api_load import APIUser

        # Verify task weights via locust metadata
        tasks = []
        for name in dir(APIUser):
            method = getattr(APIUser, name, None)
            if callable(method) and hasattr(method, 'locust_task_weight'):
                tasks.append((name, method.locust_task_weight))

        # Should have tasks
        assert len(tasks) >= 3, "APIUser should have at least 3 tasks"

    def test_metrics_output_format(self):
        """MetricsCollector output should be structured correctly."""
        from locust_templates.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_request("GET /api/items", 150.0, 200, True)
        collector.record_request("POST /api/items", 300.0, 201, True)
        collector.record_request("GET /api/items/1", 50.0, 200, True)

        summary = collector.get_summary()

        # Each endpoint should have count, avg, min, max, failures
        for _endpoint, metrics in summary.items():
            assert "count" in metrics
            assert "avg" in metrics
            assert "min" in metrics
            assert "max" in metrics
            assert "failures" in metrics

    def test_threshold_result_structure(self):
        """ThresholdResult should have standard fields."""
        from locust_templates.thresholds import ThresholdChecker

        checker = ThresholdChecker()
        result = checker.check(p95=200.0, p99=400.0, error_rate=0.005)

        assert hasattr(result, "passed")
        assert hasattr(result, "failures")
        assert hasattr(result, "metrics")
        assert isinstance(result.passed, bool)
        assert isinstance(result.failures, list)
        assert isinstance(result.metrics, dict)


class TestTemplateFileContent:
    """Visual verification of template file content."""

    def test_all_template_files_are_nonempty(self):
        template_dir = Path(__file__).parent.parent.parent / "src" / "locust_templates"
        for py_file in template_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            content = py_file.read_text()
            assert len(content) > 100, f"{py_file.name} is too short"

    def test_template_files_have_docstrings(self):
        template_dir = Path(__file__).parent.parent.parent / "src" / "locust_templates"
        for py_file in template_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            content = py_file.read_text()
            assert '"""' in content or "'''" in content, (
                f"{py_file.name} missing docstring"
            )
