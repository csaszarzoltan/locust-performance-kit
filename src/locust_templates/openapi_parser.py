"""OpenAPI/Swagger specification parser.

Parses OpenAPI 3.x JSON/YAML and Swagger 2.0 specs into a normalized
internal model (OpenAPISpec dataclass) that can be consumed by the
locust_generator and load_patterns modules.

Public API:
    EndpointInfo           — normalized endpoint representation
    ParamInfo              — parameter metadata (path, query, header)
    RequestBodyInfo        — request body schema
    SecurityRequirement    — security scheme reference
    OpenAPISpec            — fully parsed spec
    OpenAPIParseError      — parse/validation error
    parse_spec(source)     — main entry point
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────


@dataclass
class ParamInfo:
    """Parameter metadata (path, query, header)."""
    name: str
    location: str          # "path" | "query" | "header"
    required: bool
    schema_type: str       # "string", "integer", "number", "boolean", "array"
    example: str | None = None
    enum: list[str] | None = None


@dataclass
class RequestBodyInfo:
    """Request body schema."""
    content_type: str      # "application/json", etc.
    required: bool
    schema: dict = field(default_factory=dict)
    example: dict | None = None


@dataclass
class SecurityRequirement:
    """Security scheme reference."""
    scheme_name: str
    scheme_type: str       # "http", "apiKey", "oauth2", "openIdConnect"
    scheme_location: str | None = None
    scheme_name_header: str | None = None


@dataclass
class EndpointInfo:
    """Normalized representation of a single API endpoint."""
    path: str
    method: str
    operation_id: str | None = None
    summary: str | None = None
    path_params: list[ParamInfo] = field(default_factory=list)
    query_params: list[ParamInfo] = field(default_factory=list)
    headers: list[ParamInfo] = field(default_factory=list)
    request_body: RequestBodyInfo | None = None
    response_schema: dict | None = None
    security: list[SecurityRequirement] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class OpenAPISpec:
    """Fully parsed and normalized OpenAPI specification."""
    title: str
    version: str
    base_url: str | None = None
    endpoints: list[EndpointInfo] = field(default_factory=list)
    security_schemes: dict[str, SecurityRequirement] = field(default_factory=dict)
    raw_spec: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────────────────────


class OpenAPIParseError(Exception):
    """Raised when spec parsing fails."""


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────


def _detect_version(spec: dict) -> tuple[str, str]:
    """Detect spec version. Returns ('openapi', '3.x.x') or ('swagger', '2.0')."""
    if "openapi" in spec:
        return ("openapi", str(spec["openapi"]))
    if "swagger" in spec:
        return ("swagger", str(spec["swagger"]))
    raise OpenAPIParseError("Unable to detect spec version: missing 'openapi' or 'swagger' key")


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref pointer within the spec document.

    Supports JSON Pointer syntax like '#/components/schemas/Pet'.
    """
    if not ref.startswith("#/"):
        raise OpenAPIParseError(f"External $ref not supported: {ref}")
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise OpenAPIParseError(f"Cannot resolve $ref '{ref}': key '{part}' not found")
    if not isinstance(node, dict):
        raise OpenAPIParseError(f"$ref '{ref}' does not point to a dict")
    return node


def _extract_security_schemes(spec: dict, kind: str) -> dict[str, SecurityRequirement]:
    """Extract security schemes from OpenAPI 3.x or Swagger 2.0 spec."""
    schemes: dict[str, SecurityRequirement] = {}
    if kind == "openapi":
        schemes_raw = (
            spec.get("components", {}).get("securitySchemes", {})
        )
        for name, definition in schemes_raw.items():
            schemes[name] = SecurityRequirement(
                scheme_name=name,
                scheme_type=definition.get("type", ""),
                scheme_location=definition.get("in"),
                scheme_name_header=definition.get("name"),
            )
    elif kind == "swagger":
        schemes_raw = spec.get("securityDefinitions", {})
        for name, definition in schemes_raw.items():
            schemes[name] = SecurityRequirement(
                scheme_name=name,
                scheme_type=definition.get("type", ""),
                scheme_location=definition.get("in"),
                scheme_name_header=definition.get("name"),
            )
    return schemes


def _extract_endpoint(
    path: str,
    method: str,
    operation: dict,
    spec: dict,
    spec_version: str,
    global_security: list[dict],
    security_schemes: dict[str, SecurityRequirement],
) -> EndpointInfo:
    """Extract a normalized EndpointInfo from an operation object."""
    # Resolve any $ref in the operation
    if "$ref" in operation:
        operation = _resolve_ref(spec, operation["$ref"])

    endpoint = EndpointInfo(
        path=path,
        method=method.lower(),
        operation_id=operation.get("operationId"),
        summary=operation.get("summary"),
        tags=operation.get("tags", []),
    )

    # Parameters (OpenAPI 3.x: in path/query/header; Swagger 2.0: same but also body)
    for param in operation.get("parameters", []):
        if "$ref" in param:
            param = _resolve_ref(spec, param["$ref"])

        location = param.get("in", "query")
        schema = param.get("schema", {})

        # Swagger 2.0: type is directly on the parameter, not nested in schema
        if spec_version == "swagger" and not schema:
            schema_type = param.get("type", "string")
        else:
            schema_type = schema.get("type", "string")

        param_info = ParamInfo(
            name=param.get("name", ""),
            location=location,
            required=param.get("required", False),
            schema_type=schema_type,
            example=param.get("example"),
            enum=schema.get("enum"),
        )

        if location == "path":
            endpoint.path_params.append(param_info)
        elif location == "query":
            endpoint.query_params.append(param_info)
        elif location == "header":
            endpoint.headers.append(param_info)

    # Request body (OpenAPI 3.x only; Swagger 2.0 uses body parameter above)
    if "requestBody" in operation:
        body = operation["requestBody"]
        if "$ref" in body:
            body = _resolve_ref(spec, body["$ref"])
        content = body.get("content", {})
        # Prefer application/json
        content_type = "application/json"
        if content_type not in content and content:
            content_type = next(iter(content))
        body_schema = content.get(content_type, {})
        endpoint.request_body = RequestBodyInfo(
            content_type=content_type,
            required=body.get("required", False),
            schema=body_schema.get("schema", {}),
            example=body_schema.get("example"),
        )

    # Response schema (first 2xx response)
    responses = operation.get("responses", {})
    for code in sorted(responses.keys()):
        if code.startswith("2"):
            resp = responses[code]
            if "$ref" in resp:
                resp = _resolve_ref(spec, resp["$ref"])
            # Try to get JSON schema from response content
            content = resp.get("content", {})
            if "application/json" in content:
                endpoint.response_schema = content["application/json"].get("schema", {})
            break

    # Security
    op_security = operation.get("security", global_security)
    for sec in op_security:
        for scheme_name in sec:
            if scheme_name in security_schemes:
                endpoint.security.append(security_schemes[scheme_name])

    return endpoint


def _extract_base_url(spec: dict, spec_version: str) -> str | None:
    """Extract base URL from the spec."""
    if spec_version == "openapi":
        servers = spec.get("servers", [])
        if servers:
            return servers[0].get("url")
    elif spec_version == "swagger":
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        scheme = (spec.get("schemes") or ["https"])[0]
        if host:
            return f"{scheme}://{host}{base_path}"
    return None


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────


def parse_spec(source: str | Path) -> OpenAPISpec:
    """
    Parse an OpenAPI 3.x JSON/YAML or Swagger 2.0 spec.

    Args:
        source: File path or URL string to the spec.

    Returns:
        OpenAPISpec with normalized endpoint data.

    Raises:
        OpenAPIParseError: On invalid spec, unsupported version, or I/O error.
    """
    path = Path(source)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError) as exc:
        raise OpenAPIParseError(f"Cannot read spec file: {source}") from exc

    # Parse JSON or YAML
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            spec = json.loads(raw_text)
        else:
            import yaml
            spec = yaml.safe_load(raw_text)
    except Exception as exc:
        raise OpenAPIParseError(f"Failed to parse spec: {exc}") from exc

    if not isinstance(spec, dict):
        raise OpenAPIParseError("Spec root must be a JSON/YAML object")

    # Detect version
    kind, version = _detect_version(spec)

    # Extract metadata
    info = spec.get("info", {})
    title = info.get("title", "")
    spec_version_str = info.get("version", "")
    base_url = _extract_base_url(spec, kind)

    # Extract security schemes
    security_schemes = _extract_security_schemes(spec, kind)

    # Global security
    global_security = spec.get("security", [])

    # Extract endpoints
    endpoints: list[EndpointInfo] = []
    paths = spec.get("paths", {})
    for path_str, path_item in paths.items():
        if "$ref" in path_item:
            path_item = _resolve_ref(spec, path_item["$ref"])

        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method in path_item:
                endpoint = _extract_endpoint(
                    path=path_str,
                    method=method,
                    operation=path_item[method],
                    spec=spec,
                    spec_version=kind,
                    global_security=global_security,
                    security_schemes=security_schemes,
                )
                endpoints.append(endpoint)

    return OpenAPISpec(
        title=title,
        version=spec_version_str,
        base_url=base_url,
        endpoints=endpoints,
        security_schemes=security_schemes,
        raw_spec=spec,
    )
