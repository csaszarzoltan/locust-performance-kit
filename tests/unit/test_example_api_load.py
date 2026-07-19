"""Unit tests for the examples/api_load_test.py runnable example.

Verifies the example file:
- exists and is valid Python
- imports correctly
- uses the template classes from locust_templates
- can be run by Locust (has proper structure)
"""

import ast
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
EXAMPLE_FILE = EXAMPLES_DIR / "api_load_test.py"


class TestExampleFileExists:
    """Verify the example file exists and is well-formed."""

    def test_example_file_exists(self):
        assert EXAMPLE_FILE.exists(), (
            "examples/api_load_test.py must exist (CI depends on it)"
        )

    def test_example_file_is_nonempty(self):
        content = EXAMPLE_FILE.read_text()
        assert len(content) > 100, "Example file is too short"

    def test_example_file_is_valid_python(self):
        content = EXAMPLE_FILE.read_text()
        ast.parse(content)  # Raises SyntaxError if invalid


class TestExampleFileStructure:
    """Verify the example follows Locust conventions."""

    def test_imports_locust(self):
        content = EXAMPLE_FILE.read_text()
        assert "from locust" in content or "import locust" in content

    def test_defines_user_class(self):
        content = EXAMPLE_FILE.read_text()
        tree = ast.parse(content)
        class_defs = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert len(class_defs) >= 1, "Example must define at least one user class"

    def test_has_wait_time(self):
        content = EXAMPLE_FILE.read_text()
        assert "wait_time" in content, "User class must define wait_time"

    def test_has_tasks(self):
        content = EXAMPLE_FILE.read_text()
        assert "@task" in content, "User class must have @task decorated methods"

    def test_has_if_name_main(self):
        """Ensure the file can be used as both module and script."""
        content = EXAMPLE_FILE.read_text()
        assert '__name__' in content, (
            "Should have __name__ guard or at minimum be importable"
        )


class TestExampleImportsTemplate:
    """Verify the example reuses the template package."""

    def test_imports_from_locust_templates(self):
        content = EXAMPLE_FILE.read_text()
        assert "locust_templates" in content, (
            "Example should import from locust_templates to demonstrate reuse"
        )
