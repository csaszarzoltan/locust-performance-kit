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
# Internal helpers
# ──────────────────────────────────────────────────────────────


def _method_weight(method: str) -> int:
    """Return default task weight for an HTTP method."""
    weights = {
        "get": 3,
        "post": 2,
        "put": 1,
        "patch": 1,
        "delete": 1,
    }
    return weights.get(method.lower(), 1)


def _generate_imports(has_auth: bool, has_shape: bool) -> str:
    """Generate the import block for the locustfile."""
    lines = ["from locust import HttpUser, task, between"]
    if has_shape:
        lines.append("from locust import LoadTestShape")
    if has_auth:
        lines.append("import os")
    return "\n".join(lines) + "\n"


def _generate_auth_setup(schemes: dict[str, SecurityRequirement]) -> str:
    """Generate on_start() auth initialization code."""
    lines = ["    def on_start(self):"]
    for name, scheme in schemes.items():
        if scheme.scheme_type == "http" and scheme.scheme_location is None:
            # Bearer token from env var
            lines.append(
                f'        self.headers = {{"Authorization": f"Bearer '
                f'{{os.environ.get(\'{name.upper()}_TOKEN\', os.environ.get(\'API_TOKEN\', \'\''))}}"}}'
            )
        elif scheme.scheme_type == "apiKey" and scheme.scheme_location == "header":
            header_name = scheme.scheme_name_header or "X-API-Key"
            lines.append(
                f'        self.headers = self.headers if hasattr(self, "headers") else {{}}'
            )
            lines.append(
                f'        self.headers["{header_name}"] = os.environ.get(\'{name.upper()}_KEY\', '
                f'os.environ.get(\'API_KEY\', \'\'))'
            )
    lines.append("        return self.headers")
    return "\n".join(lines)


def _generate_endpoint_task(ep: object, auth_header: str | None) -> str:
    """Generate a single @task method for an endpoint."""
    # Build method name from operation_id or path
    if hasattr(ep, "operation_id") and ep.operation_id:
        op_id = ep.operation_id
        # camelCase to snake_case
        import re
        method_name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op_id).lower()
    else:
        path_part = ep.path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
        method_name = f"{ep.method}_{path_part}"

    method_name = method_name or f"{ep.method}_endpoint"
    weight = _method_weight(ep.method)

    lines = [f"    @task({weight})"]
    lines.append(f"    def {method_name}(self):")

    if hasattr(ep, "summary") and ep.summary:
        lines.append(f'        """{ep.summary}"""')

    # Build URL with path parameter interpolation
    url = ep.path
    has_path_params = hasattr(ep, "path_params") and ep.path_params
    if has_path_params:
        # Convert {paramName} to f-string interpolation
        for pp in ep.path_params:
            # snake_case the param name for the variable
            import re
            snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", pp.name).lower()
            url = url.replace(f"{{{pp.name}}}", f"{{{snake}}}")
        url = f'f"{url}"'
    else:
        url = f'"{url}"'

    # Build the request
    http_method = ep.method.lower()
    request_args = [f"        resp = self.client.{http_method}({url}"]

    # Query params
    if hasattr(ep, "query_params") and ep.query_params:
        qp_parts = []
        for qp in ep.query_params:
            qp_parts.append(f'"{qp.name}": None')
        request_args.append(f"            params={{{', '.join(qp_parts)}}},")

    # Request body
    if hasattr(ep, "request_body") and ep.request_body:
        body = ep.request_body
        if body.content_type == "application/json":
            # Try to use example data from schema
            example = body.example
            if not example and body.schema:
                # Generate a minimal example from schema properties
                props = body.schema.get("properties", {})
                example = {k: f"<{v.get('type', 'string')}>" for k, v in props.items()}
            if example:
                request_args.append(f"            json={example},")
        else:
            # Unsupported content type — no body generated

    # Close the call
    request_args.append("        )")
    lines.extend(request_args)

    return "\n".join(lines)


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
    if config is None:
        config = GenerationConfig()

    warnings: list[str] = []
    has_auth = bool(spec.security_schemes)
    has_shape = False  # Could be set if user requests a pattern

    # Determine base URL
    base_url = config.base_url or spec.base_url or "http://localhost:8080"

    # Collect all security schemes referenced by endpoints
    auth_schemes: dict[str, SecurityRequirement] = {}
    for ep in spec.endpoints:
        for sec in ep.security:
            auth_schemes[sec.scheme_name] = sec

    # Check for unsupported content types
    for ep in spec.endpoints:
        if ep.request_body and ep.request_body.content_type != "application/json":
            warnings.append(
                f"Unsupported content type '{ep.request_body.content_type}' "
                f"for {ep.method.upper()} {ep.path} — body will be ignored"
            )

    # Build source code
    parts: list[str] = []

    # Imports
    parts.append(_generate_imports(has_auth, has_shape))
    parts.append("")

    # Class definition
    class_name = spec.title.replace(" ", "").replace("-", "") + "User"
    parts.append(f"class {class_name}(HttpUser):")
    parts.append(f'    """Locust user class generated from {spec.title} {spec.version}."""')
    parts.append(f"    wait_time = between({config.default_wait_time[0]}, {config.default_wait_time[1]})")
    parts.append(f'    host = "{base_url}"')
    parts.append("")

    # Auth setup
    if auth_schemes:
        parts.append(_generate_auth_setup(auth_schemes))
        parts.append("")

    # Task methods for each endpoint
    for ep in spec.endpoints:
        parts.append(_generate_endpoint_task(ep, auth_header=None))
        parts.append("")

    source_code = "\n".join(parts)

    return GenerationResult(
        source_code=source_code,
        endpoints_processed=len(spec.endpoints),
        auth_schemes_mapped=len(auth_schemes),
        warnings=warnings,
    )
