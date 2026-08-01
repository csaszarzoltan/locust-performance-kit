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
    raise NotImplementedError("parse_spec not yet implemented")


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref pointer within the spec document."""
    raise NotImplementedError("_resolve_ref not yet implemented")


def _detect_version(spec: dict) -> tuple[str, str]:
    """Detect spec version. Returns ('openapi', '3.x.x') or ('swagger', '2.0')."""
    raise NotImplementedError("_detect_version not yet implemented")
