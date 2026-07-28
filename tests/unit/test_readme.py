"""Pre-development tests for README multi-protocol documentation (TDD red phase).

Interface tests verify the README file and documentation files exist
(must pass immediately).
Behavioral tests define the expected multi-protocol section content
that the developer must add, raising NotImplementedError until then.

Run: pytest tests/unit/test_readme.py -v
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
README_PATH = REPO_ROOT / "README.md"


def readme_text() -> str:
    """Read and return the full README content."""
    return README_PATH.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify README and documentation files exist and are accessible."""

    def test_readme_exists(self):
        """README.md must exist in the repo root."""
        assert README_PATH.exists(), f"README not found at {README_PATH}"

    def test_readme_is_readable(self):
        """README.md must be a readable file."""
        text = readme_text()
        assert isinstance(text, str)
        assert len(text) > 0, "README.md is empty"

    def test_docs_directory_exists(self):
        """docs/ directory must exist."""
        docs_dir = REPO_ROOT / "docs"
        assert docs_dir.is_dir(), f"docs/ directory not found at {docs_dir}"

    def test_grpc_testing_doc_exists(self):
        """docs/grpc-testing.md must exist."""
        path = REPO_ROOT / "docs" / "grpc-testing.md"
        assert path.exists(), f"gRPC doc not found at {path}"

    def test_graphql_testing_doc_exists(self):
        """docs/graphql-testing.md must exist."""
        path = REPO_ROOT / "docs" / "graphql-testing.md"
        assert path.exists(), f"GraphQL doc not found at {path}"

    def test_websocket_testing_doc_exists(self):
        """docs/websocket-testing.md must exist."""
        path = REPO_ROOT / "docs" / "websocket-testing.md"
        assert path.exists(), f"WebSocket doc not found at {path}"


# ──────────────────────────────────────────────────────────────
# Behavioral tests — Multi-Protocol README section content
# ──────────────────────────────────────────────────────────────


class TestReadmeMultiProtocolSection:
    """Verifies the README contains a dedicated Multi-Protocol Templates section."""

    def test_has_multi_protocol_heading(self):
        """README must contain a heading with 'Multi-Protocol'."""
        text = readme_text()
        assert "Multi-Protocol" in text, (
            "README missing 'Multi-Protocol' in section heading"
        )

    def test_has_grpc_doc_link(self):
        """README must include a link to docs/grpc-testing.md."""
        text = readme_text()
        assert "docs/grpc-testing.md" in text, (
            "README missing link to docs/grpc-testing.md"
        )

    def test_has_graphql_doc_link(self):
        """README must include a link to docs/graphql-testing.md."""
        text = readme_text()
        assert "docs/graphql-testing.md" in text, (
            "README missing link to docs/graphql-testing.md"
        )

    def test_has_websocket_doc_link(self):
        """README must include a link to docs/websocket-testing.md."""
        text = readme_text()
        assert "docs/websocket-testing.md" in text, (
            "README missing link to docs/websocket-testing.md"
        )

    def test_mentions_grpc_user_class(self):
        """README multi-protocol section must mention GrpcUser."""
        text = readme_text()
        assert "GrpcUser" in text, (
            "README missing GrpcUser class name"
        )

    def test_mentions_graphql_user_class(self):
        """README multi-protocol section must mention GraphQLUser."""
        text = readme_text()
        assert "GraphQLUser" in text, (
            "README missing GraphQLUser class name"
        )

    def test_mentions_websocket_user_class(self):
        """README multi-protocol section must mention WebSocketUser."""
        text = readme_text()
        assert "WebSocketUser" in text, (
            "README missing WebSocketUser class name"
        )

    def test_has_grpc_install_command(self):
        """Multi-protocol section must include [grpc] install command."""
        text = readme_text()
        assert "[grpc]" in text, (
            "README missing [grpc] optional dep install command"
        )

    def test_has_websocket_install_command(self):
        """Multi-protocol section must include [websocket] install command."""
        text = readme_text()
        assert "[websocket]" in text, (
            "README missing [websocket] optional dep install command"
        )


class TestReadmeSectionOrdering:
    """Verifies the Multi-Protocol Templates section appears before Documentation."""

    def test_multi_protocol_before_documentation(self):
        """Multi-Protocol heading must appear before '## Documentation'."""
        text = readme_text()
        doc_pos = text.find("## Documentation")
        mp_pos = text.find("Multi-Protocol")
        assert mp_pos >= 0, (
            "Multi-Protocol section not found in README"
        )
        assert doc_pos >= 0, (
            "'## Documentation' heading not found in README"
        )
        assert mp_pos < doc_pos, (
            "Multi-Protocol section must appear before '## Documentation'"
        )


class TestReadmeLinkResolution:
    """Verifies all documentation links resolve to actual files."""

    def test_grpc_doc_link_resolves(self):
        """Link to docs/grpc-testing.md must resolve to an existing file."""
        readme = README_PATH.read_text(encoding="utf-8")
        assert "docs/grpc-testing.md" in readme, (
            "README must contain link to docs/grpc-testing.md"
        )
        linked = REPO_ROOT / "docs" / "grpc-testing.md"
        assert linked.exists(), f"Linked file does not exist: {linked}"

    def test_graphql_doc_link_resolves(self):
        """Link to docs/graphql-testing.md must resolve to an existing file."""
        readme = README_PATH.read_text(encoding="utf-8")
        assert "docs/graphql-testing.md" in readme, (
            "README must contain link to docs/graphql-testing.md"
        )
        linked = REPO_ROOT / "docs" / "graphql-testing.md"
        assert linked.exists(), f"Linked file does not exist: {linked}"

    def test_websocket_doc_link_resolves(self):
        """Link to docs/websocket-testing.md must resolve to an existing file."""
        readme = README_PATH.read_text(encoding="utf-8")
        assert "docs/websocket-testing.md" in readme, (
            "README must contain link to docs/websocket-testing.md"
        )
        linked = REPO_ROOT / "docs" / "websocket-testing.md"
        assert linked.exists(), f"Linked file does not exist: {linked}"
