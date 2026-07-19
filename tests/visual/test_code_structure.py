"""Visual regression tests for Locust templates.

These tests verify that template code structures match expected patterns
and that the CI/CD pipeline configuration is correct.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestTemplateCodeStructure:
    """Verify code structure patterns - no duplicated logic."""

    def test_api_load_no_duplicated_imports(self):
        from locust_templates import api_load
        source = Path(api_load.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        # Check no duplicate import statements
        assert len(import_lines) == len(set(import_lines))

    def test_stress_no_duplicated_imports(self):
        from locust_templates import stress
        source = Path(stress.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))

    def test_spike_no_duplicated_imports(self):
        from locust_templates import spike
        source = Path(spike.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))

    def test_soak_no_duplicated_imports(self):
        from locust_templates import soak
        source = Path(soak.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))

    def test_web_ui_no_duplicated_imports(self):
        from locust_templates import web_ui
        source = Path(web_ui.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))

    def test_shapes_no_duplicated_imports(self):
        from locust_templates import shapes
        source = Path(shapes.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))

    def test_config_no_duplicated_imports(self):
        from locust_templates import config
        source = Path(config.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))

    def test_runner_no_duplicated_imports(self):
        from locust_templates import runner
        source = Path(runner.__file__).read_text()
        import_lines = [
            line
            for line in source.split("\n")
            if line.startswith("from ") or line.startswith("import ")
        ]
        assert len(import_lines) == len(set(import_lines))


class TestNoDuplicatedLogic:
    """Verify each function appears only once across templates."""

    def test_unique_task_names_across_templates(self):
        """Each template should have distinct task names."""
        from locust_templates import api_load, soak, spike, stress, web_ui

        task_names = set()
        duplicates = []

        for mod in [api_load, stress, spike, soak, web_ui]:
            user_cls = getattr(
                mod,
                mod.__name__.split(".")[-1].replace("_", "")
                .title()
                .replace("User", "")
                + "User",
                None,
            )
            if user_cls is None:
                # Find the user class dynamically
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if isinstance(obj, type) and hasattr(obj, 'wait_time'):
                        user_cls = obj
                        break
            if user_cls:
                for method_name in dir(user_cls):
                    if (
                        not method_name.startswith("_")
                        and callable(getattr(user_cls, method_name))
                        and hasattr(
                            getattr(user_cls, method_name),
                            'locust_task_weight',
                        )
                    ):
                        full_name = f"{mod.__name__}.{method_name}"
                        if method_name in task_names:
                            duplicates.append(full_name)
                        task_names.add(method_name)

        # No duplicates expected
        assert duplicates == [], f"Found duplicate task names: {duplicates}"

    def test_metrics_collector_single_implementation(self):
        """MetricsCollector should be defined only in metrics module."""
        from locust_templates import metrics
        assert hasattr(metrics, "MetricsCollector")

        # Verify no other module re-implements it
        from locust_templates import api_load, soak, spike, stress, web_ui
        for mod in [api_load, stress, spike, soak, web_ui]:
            source = Path(mod.__file__).read_text()
            assert "class MetricsCollector" not in source, (
                f"MetricsCollector duplicated in {mod.__name__}"
            )


class TestCIWorkflow:
    """Verify CI/CD workflow configuration."""

    def test_workflow_file_exists(self):
        workflow_path = (
            Path(__file__).parent.parent.parent
            / ".github" / "workflows" / "performance-ci.yml"
        )
        assert workflow_path.exists(), "CI workflow file must exist"

    def test_workflow_uses_headless_mode(self):
        workflow_path = (
            Path(__file__).parent.parent.parent
            / ".github" / "workflows" / "performance-ci.yml"
        )
        content = workflow_path.read_text()
        assert "--headless" in content, "CI must use headless mode"

    def test_workflow_uploads_artifacts(self):
        workflow_path = (
            Path(__file__).parent.parent.parent
            / ".github" / "workflows" / "performance-ci.yml"
        )
        content = workflow_path.read_text()
        assert "upload-artifact" in content, "CI must upload test artifacts"


class TestDocumentation:
    """Verify documentation exists and is consistent."""

    def test_readme_exists(self):
        readme = Path(__file__).parent.parent.parent / "README.md"
        assert readme.exists()

    def test_getting_started_exists(self):
        doc = Path(__file__).parent.parent.parent / "docs" / "getting-started.md"
        assert doc.exists()

    def test_custom_scripts_exists(self):
        doc = Path(__file__).parent.parent.parent / "docs" / "custom-scripts.md"
        assert doc.exists()

    def test_readme_lists_all_templates(self):
        readme = Path(__file__).parent.parent.parent / "README.md"
        content = readme.read_text()
        for template in ["api_load", "stress", "spike", "soak", "web_ui"]:
            assert template in content, f"README must mention {template}"

    def test_readme_mentions_shapes(self):
        readme = Path(__file__).parent.parent.parent / "README.md"
        content = readme.read_text()
        assert (
            "shapes" in content.lower()
            or "StepLoadShape" in content
        ), "README must mention shapes module"

    def test_readme_mentions_config(self):
        readme = Path(__file__).parent.parent.parent / "README.md"
        content = readme.read_text()
        assert (
            "config" in content.lower()
            or "LoadTestConfig" in content
        ), "README must mention config module"
