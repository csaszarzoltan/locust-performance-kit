"""Locust script generator from parsed OpenAPI specs.

Converts OpenAPISpec data into complete, runnable locustfile.py source code
with @task-decorated methods, auth injection, and parameter handling.

Public API:
    GenerationConfig      — generation options (base_url, auth, weights)
    GenerationResult      — output (source_code, metadata, warnings)
    generate_locust_script(spec, config) — main entry point
"""

from __future__ import annotations

from dataclasses import dataclass, field

from locust_templates.openapi_parser import OpenAPISpec, SecurityRequirement

# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────


@dataclass
class GenerationConfig:
    """Configuration for Locust script generation."""
    base_url: str | None = None
    default_wait_time: tuple[float, float] = (1.0, 3.0)
    auth_provider: str | None = None
    auth_env_var: str = "API_TOKEN"
    task_weight_method: str = "default"  # "default" | "equal" | "custom"
    include_comments: bool = True


@dataclass
class GenerationResult:
    """Output of Locust script generation."""
    source_code: str = ""
    endpoints_processed: int = 0
    auth_schemes_mapped: int = 0
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────


def generate_locust_script(
    spec: OpenAPISpec,
    config: GenerationConfig | None = None,
) -> GenerationResult:
    """
    Generate a complete locustfile.py from a parsed OpenAPI spec.

    Args:
        spec: Parsed OpenAPI specification from parse_spec().
        config: Optional generation configuration overrides.

    Returns:
        GenerationResult with source code and metadata.
    """
    raise NotImplementedError("generate_locust_script not yet implemented")


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────


def _generate_endpoint_task(ep: object, auth_header: str | None) -> str:
    """Generate a single @task method for an endpoint."""
    raise NotImplementedError("_generate_endpoint_task not yet implemented")


def _generate_auth_setup(schemes: dict[str, SecurityRequirement]) -> str:
    """Generate on_start() auth initialization code."""
    raise NotImplementedError("_generate_auth_setup not yet implemented")


def _generate_imports(has_auth: bool, has_shape: bool) -> str:
    """Generate the import block for the locustfile."""
    raise NotImplementedError("_generate_imports not yet implemented")


def _method_weight(method: str) -> int:
    """Return default task weight for an HTTP method."""
    raise NotImplementedError("_method_weight not yet implemented")
