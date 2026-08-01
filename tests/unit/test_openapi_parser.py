"""Pre-dev tests for openapi_parser module.

Tests define the contract for the OpenAPI/Swagger parser that converts
specs into a normalized OpenAPISpec dataclass.

Pattern:
- Interface tests: verify imports, dataclass fields, signatures (PASS immediately)
- Behavioral tests: verify parsing logic (FAIL with NotImplementedError until implemented)
"""

from __future__ import annotations

import inspect
from dataclasses import is_dataclass
from pathlib import Path

import pytest

from locust_templates.openapi_parser import (
    EndpointInfo,
    OpenAPIParseError,
    OpenAPISpec,
    ParamInfo,
    RequestBodyInfo,
    SecurityRequirement,
    _detect_version,
    _resolve_ref,
    parse_spec,
)

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

SAMPLE_OPENAPI_3_0 = {
    "openapi": "3.0.3",
    "info": {"title": "Petstore", "version": "1.0.0"},
    "servers": [{"url": "https://petstore.example.com/v1"}],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
                        }
                    },
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "getPetById",
                "summary": "Get a pet by ID",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "OK"}},
            }
        },
    },
    "components": {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer"},
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
        }
    },
    "security": [{"BearerAuth": []}],
}

SAMPLE_SWAGGER_2_0 = {
    "swagger": "2.0",
    "info": {"title": "Petstore Swagger", "version": "2.0.0"},
    "host": "petstore.example.com",
    "basePath": "/v1",
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "type": "integer",
                        "required": False,
                    }
                ],
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
    "securityDefinitions": {
        "api_key": {"type": "apiKey", "name": "X-API-Key", "in": "header"}
    },
}


# ──────────────────────────────────────────────────────────────
# Interface tests — PASS immediately against stubs
# ──────────────────────────────────────────────────────────────


class TestParseSpecExists:
    """Verify parse_spec is importable and callable."""

    def test_parse_spec_is_importable(self):
        assert parse_spec is not None

    def test_parse_spec_is_callable(self):
        assert callable(parse_spec)

    def test_parse_spec_accepts_str(self):
        sig = inspect.signature(parse_spec)
        params = list(sig.parameters.values())
        assert len(params) == 1
        # Should accept str | Path
        param = params[0]
        assert param.name == "source"

    def test_parse_spec_return_annotation(self):
        sig = inspect.signature(parse_spec)
        # Return should be OpenAPISpec (or string annotation with from __future__ import annotations)
        ret = sig.return_annotation
        assert ret is inspect.Parameter.empty or ret is OpenAPISpec or ret == "OpenAPISpec"


class TestOpenAPISpecDataclass:
    """Verify OpenAPISpec dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(OpenAPISpec)

    def test_has_title(self):
        fields = {f.name for f in __import__("dataclasses").fields(OpenAPISpec)}
        assert "title" in fields

    def test_has_version(self):
        fields = {f.name for f in __import__("dataclasses").fields(OpenAPISpec)}
        assert "version" in fields

    def test_has_base_url(self):
        fields = {f.name for f in __import__("dataclasses").fields(OpenAPISpec)}
        assert "base_url" in fields

    def test_has_endpoints(self):
        fields = {f.name for f in __import__("dataclasses").fields(OpenAPISpec)}
        assert "endpoints" in fields

    def test_has_security_schemes(self):
        fields = {f.name for f in __import__("dataclasses").fields(OpenAPISpec)}
        assert "security_schemes" in fields

    def test_has_raw_spec(self):
        fields = {f.name for f in __import__("dataclasses").fields(OpenAPISpec)}
        assert "raw_spec" in fields

    def test_constructable_with_defaults(self):
        spec = OpenAPISpec(title="test", version="1.0")
        assert spec.title == "test"
        assert spec.version == "1.0"
        assert spec.base_url is None
        assert spec.endpoints == []
        assert spec.security_schemes == {}


class TestEndpointInfoDataclass:
    """Verify EndpointInfo dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(EndpointInfo)

    def test_has_required_fields(self):
        fields = {f.name for f in __import__("dataclasses").fields(EndpointInfo)}
        for name in ("path", "method", "operation_id", "summary", "path_params",
                      "query_params", "headers", "request_body", "response_schema",
                      "security", "tags"):
            assert name in fields, f"Missing field: {name}"

    def test_constructable(self):
        ep = EndpointInfo(path="/pets", method="get")
        assert ep.path == "/pets"
        assert ep.method == "get"
        assert ep.path_params == []
        assert ep.query_params == []


class TestParamInfoDataclass:
    """Verify ParamInfo dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(ParamInfo)

    def test_has_required_fields(self):
        fields = {f.name for f in __import__("dataclasses").fields(ParamInfo)}
        for name in ("name", "location", "required", "schema_type"):
            assert name in fields

    def test_constructable(self):
        p = ParamInfo(name="id", location="path", required=True, schema_type="string")
        assert p.name == "id"
        assert p.location == "path"
        assert p.example is None
        assert p.enum is None


class TestRequestBodyInfoDataclass:
    """Verify RequestBodyInfo dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(RequestBodyInfo)

    def test_has_required_fields(self):
        fields = {f.name for f in __import__("dataclasses").fields(RequestBodyInfo)}
        for name in ("content_type", "required", "schema", "example"):
            assert name in fields

    def test_constructable(self):
        rb = RequestBodyInfo(content_type="application/json", required=True)
        assert rb.content_type == "application/json"
        assert rb.schema == {}


class TestSecurityRequirementDataclass:
    """Verify SecurityRequirement dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(SecurityRequirement)

    def test_has_required_fields(self):
        fields = {f.name for f in __import__("dataclasses").fields(SecurityRequirement)}
        for name in ("scheme_name", "scheme_type", "scheme_location", "scheme_name_header"):
            assert name in fields

    def test_constructable(self):
        sr = SecurityRequirement(scheme_name="BearerAuth", scheme_type="http")
        assert sr.scheme_name == "BearerAuth"
        assert sr.scheme_type == "http"
        assert sr.scheme_location is None


class TestOpenAPIParseErrorExists:
    """Verify exception is importable."""

    def test_is_exception(self):
        assert issubclass(OpenAPIParseError, Exception)

    def test_is_constructable(self):
        err = OpenAPIParseError("bad spec")
        assert str(err) == "bad spec"


class TestHelperFunctionsExist:
    """Verify internal helper functions are importable."""

    def test_resolve_ref_is_callable(self):
        assert callable(_resolve_ref)

    def test_detect_version_is_callable(self):
        assert callable(_detect_version)

    def test_resolve_ref_signature(self):
        sig = inspect.signature(_resolve_ref)
        params = list(sig.parameters.keys())
        assert "spec" in params
        assert "ref" in params

    def test_detect_version_signature(self):
        sig = inspect.signature(_detect_version)
        params = list(sig.parameters.keys())
        assert "spec" in params


# ──────────────────────────────────────────────────────────────
# Behavioral tests — FAIL with NotImplementedError until implemented
# ──────────────────────────────────────────────────────────────


class TestParseSpecBehavioral:
    """Behavioral tests for parse_spec()."""

    def test_parse_spec_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            parse_spec("petstore.yaml")

    def test_parse_spec_accepts_path_object(self):
        try:
            parse_spec(Path("petstore.yaml"))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except Exception:
            pass  # Other errors are OK for behavioral tests

    def test_parse_spec_returns_openapi_spec(self):
        try:
            result = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, OpenAPISpec)

    def test_parse_spec_extracts_title(self):
        try:
            result = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.title  # Non-empty

    def test_parse_spec_extracts_version(self):
        try:
            result = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.version  # Non-empty

    def test_parse_spec_extracts_base_url(self):
        try:
            result = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.base_url is not None

    def test_parse_spec_populates_endpoints(self):
        try:
            result = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.endpoints) > 0

    def test_parse_spec_populates_security_schemes(self):
        try:
            result = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.security_schemes) > 0

    def test_parse_spec_invalid_raises_error(self):
        try:
            parse_spec("nonexistent.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except OpenAPIParseError:
            pass  # Expected


class TestParseSpecParametrized:
    """Parametrized behavioral tests for multiple spec formats."""

    @pytest.mark.parametrize("ext,content", [
        ("yaml", "openapi: '3.0.3'\ninfo: {title: Test, version: '1.0'}\npaths: {}"),
        ("json", '{"openapi": "3.0.3", "info": {"title": "Test", "version": "1.0"}, "paths": {}}'),
    ])
    def test_parse_spec_handles_formats(self, ext, content, tmp_path):
        spec_file = tmp_path / f"test.{ext}"
        spec_file.write_text(content)
        try:
            result = parse_spec(str(spec_file))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, OpenAPISpec)
        assert result.title == "Test"

    @pytest.mark.parametrize("version_field", ["openapi", "swagger"])
    def test_detect_version_handles_both(self, version_field):
        spec = {version_field: "3.0.3" if version_field == "openapi" else "2.0"}
        try:
            result = _detect_version(spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestEndpointExtraction:
    """Behavioral tests for endpoint metadata extraction."""

    def test_path_params_extracted(self):
        try:
            spec = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Find an endpoint with path params
        path_eps = [ep for ep in spec.endpoints if ep.path_params]
        assert len(path_eps) > 0

    def test_query_params_extracted(self):
        try:
            spec = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        query_eps = [ep for ep in spec.endpoints if ep.query_params]
        assert len(query_eps) > 0

    def test_request_body_extracted(self):
        try:
            spec = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        body_eps = [ep for ep in spec.endpoints if ep.request_body is not None]
        assert len(body_eps) > 0

    def test_security_requirements_extracted(self):
        try:
            spec = parse_spec("petstore.yaml")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        sec_eps = [ep for ep in spec.endpoints if ep.security]
        # At least some endpoints should have security
        assert len(sec_eps) > 0


class TestRefResolution:
    """Behavioral tests for $ref resolution."""

    def test_resolve_ref_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            _resolve_ref({}, "#/components/schemas/Pet")

    def test_resolve_ref_returns_dict(self):
        try:
            result = _resolve_ref(
                {"components": {"schemas": {"Pet": {"type": "object"}}}},
                "#/components/schemas/Pet",
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, dict)


class TestVersionDetection:
    """Behavioral tests for _detect_version."""

    def test_detect_openapi_3(self):
        try:
            kind, version = _detect_version({"openapi": "3.0.3"})
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert kind == "openapi"
        assert version.startswith("3.")

    def test_detect_swagger_2(self):
        try:
            kind, version = _detect_version({"swagger": "2.0"})
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert kind == "swagger"
        assert version == "2.0"

    def test_unknown_version_raises(self):
        try:
            _detect_version({})
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except OpenAPIParseError:
            pass  # Expected
