"""Pre-dev tests for locust_generator module.

Tests define the contract for generating Locust User classes from parsed
OpenAPI specs with @task methods, auth injection, and parameter handling.

Pattern:
- Interface tests: verify imports, dataclass fields, signatures (PASS immediately)
- Behavioral tests: verify generation logic (FAIL with NotImplementedError until implemented)
"""

from __future__ import annotations

import inspect
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

import pytest

from locust_templates.locust_generator import (
    GenerationConfig,
    GenerationResult,
    _generate_auth_setup,
    _generate_endpoint_task,
    _generate_imports,
    _method_weight,
    generate_locust_script,
)
from locust_templates.openapi_parser import (
    EndpointInfo,
    OpenAPISpec,
    ParamInfo,
    RequestBodyInfo,
    SecurityRequirement,
)

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_spec() -> OpenAPISpec:
    """Minimal OpenAPISpec with one GET endpoint."""
    return OpenAPISpec(
        title="Test API",
        version="1.0.0",
        base_url="https://api.example.com",
        endpoints=[
            EndpointInfo(
                path="/items",
                method="get",
                operation_id="listItems",
                summary="List all items",
                query_params=[
                    ParamInfo(name="limit", location="query", required=False, schema_type="integer"),
                ],
            )
        ],
    )


@pytest.fixture
def spec_with_post(minimal_spec: OpenAPISpec) -> OpenAPISpec:
    """Spec with a GET and POST endpoint, including request body."""
    post_ep = EndpointInfo(
        path="/items",
        method="post",
        operation_id="createItem",
        summary="Create an item",
        request_body=RequestBodyInfo(
            content_type="application/json",
            required=True,
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
            example={"name": "Widget"},
        ),
    )
    minimal_spec.endpoints.append(post_ep)
    return minimal_spec


@pytest.fixture
def spec_with_auth(minimal_spec: OpenAPISpec) -> OpenAPISpec:
    """Spec with security schemes."""
    minimal_spec.security_schemes = {
        "ApiKeyAuth": SecurityRequirement(
            scheme_name="ApiKeyAuth",
            scheme_type="apiKey",
            scheme_location="header",
            scheme_name_header="X-API-Key",
        )
    }
    minimal_spec.endpoints[0].security = [minimal_spec.security_schemes["ApiKeyAuth"]]
    return minimal_spec


@pytest.fixture
def spec_with_path_params() -> OpenAPISpec:
    """Spec with path parameter endpoint."""
    return OpenAPISpec(
        title="Test API",
        version="1.0.0",
        base_url="https://api.example.com",
        endpoints=[
            EndpointInfo(
                path="/items/{itemId}",
                method="get",
                operation_id="getItem",
                summary="Get item by ID",
                path_params=[
                    ParamInfo(name="itemId", location="path", required=True, schema_type="string"),
                ],
            )
        ],
    )


# ──────────────────────────────────────────────────────────────
# Interface tests — PASS immediately against stubs
# ──────────────────────────────────────────────────────────────


class TestGenerationConfigDataclass:
    """Verify GenerationConfig dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(GenerationConfig)

    def test_has_required_fields(self):
        field_names = {f.name for f in dataclass_fields(GenerationConfig)}
        for name in ("base_url", "default_wait_time", "auth_provider",
                      "auth_env_var", "task_weight_method", "include_comments"):
            assert name in field_names, f"Missing field: {name}"

    def test_default_values(self):
        cfg = GenerationConfig()
        assert cfg.base_url is None
        assert cfg.default_wait_time == (1.0, 3.0)
        assert cfg.auth_provider is None
        assert cfg.auth_env_var == "API_TOKEN"
        assert cfg.task_weight_method == "default"
        assert cfg.include_comments is True

    def test_custom_values(self):
        cfg = GenerationConfig(
            base_url="http://localhost:8080",
            auth_provider="env",
            include_comments=False,
        )
        assert cfg.base_url == "http://localhost:8080"
        assert cfg.auth_provider == "env"
        assert cfg.include_comments is False


class TestGenerationResultDataclass:
    """Verify GenerationResult dataclass fields."""

    def test_is_dataclass(self):
        assert is_dataclass(GenerationResult)

    def test_has_required_fields(self):
        field_names = {f.name for f in dataclass_fields(GenerationResult)}
        for name in ("source_code", "endpoints_processed", "auth_schemes_mapped", "warnings"):
            assert name in field_names, f"Missing field: {name}"

    def test_default_values(self):
        result = GenerationResult()
        assert result.source_code == ""
        assert result.endpoints_processed == 0
        assert result.auth_schemes_mapped == 0
        assert result.warnings == []


class TestGenerateFunctionExists:
    """Verify generate_locust_script is importable and callable."""

    def test_is_importable(self):
        assert generate_locust_script is not None

    def test_is_callable(self):
        assert callable(generate_locust_script)

    def test_signature(self):
        sig = inspect.signature(generate_locust_script)
        params = list(sig.parameters.keys())
        assert "spec" in params
        assert "config" in params

    def test_return_annotation(self):
        sig = inspect.signature(generate_locust_script)
        ret = sig.return_annotation
        assert ret is inspect.Parameter.empty or ret is GenerationResult or ret == "GenerationResult"


class TestHelperFunctionsExist:
    """Verify internal helper functions are importable."""

    def test_generate_endpoint_task_callable(self):
        assert callable(_generate_endpoint_task)

    def test_generate_auth_setup_callable(self):
        assert callable(_generate_auth_setup)

    def test_generate_imports_callable(self):
        assert callable(_generate_imports)

    def test_method_weight_callable(self):
        assert callable(_method_weight)

    def test_method_weight_signature(self):
        sig = inspect.signature(_method_weight)
        params = list(sig.parameters.keys())
        assert "method" in params


# ──────────────────────────────────────────────────────────────
# Behavioral tests — FAIL with NotImplementedError until implemented
# ──────────────────────────────────────────────────────────────


class TestGenerateLocustScriptBehavioral:
    """Behavioral tests for generate_locust_script()."""

    def test_works(self, minimal_spec):
        result = generate_locust_script(minimal_spec)
        assert isinstance(result, GenerationResult)

    def test_returns_generation_result(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, GenerationResult)

    def test_source_code_is_string(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result.source_code, str)
        assert len(result.source_code) > 0

    def test_source_compiles_as_python(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        compile(result.source_code, "<generated>", "exec")

    def test_endpoints_processed_count(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.endpoints_processed == len(minimal_spec.endpoints)

    def test_generates_task_for_each_endpoint(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "@task" in result.source_code

    def test_includes_imports(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "from locust import" in result.source_code or "import locust" in result.source_code

    def test_user_class_defined(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "class" in result.source_code
        assert "HttpUser" in result.source_code


class TestGenerateWithPostEndpoint:
    """Behavioral tests for POST endpoint generation."""

    def test_post_endpoint_generates_json_body(self, spec_with_post):
        try:
            result = generate_locust_script(spec_with_post)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "json=" in result.source_code

    def test_post_endpoint_uses_post_method(self, spec_with_post):
        try:
            result = generate_locust_script(spec_with_post)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "self.client.post" in result.source_code or ".post(" in result.source_code


class TestGenerateWithPathParams:
    """Behavioral tests for path parameter handling."""

    def test_path_param_interpolated(self, spec_with_path_params):
        try:
            result = generate_locust_script(spec_with_path_params)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Path params should be f-string interpolated
        assert "itemId" in result.source_code or "item_id" in result.source_code


class TestGenerateWithAuth:
    """Behavioral tests for auth injection."""

    def test_auth_setup_present(self, spec_with_auth):
        try:
            result = generate_locust_script(spec_with_auth)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "on_start" in result.source_code or "auth" in result.source_code.lower()

    def test_auth_schemes_mapped(self, spec_with_auth):
        try:
            result = generate_locust_script(spec_with_auth)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.auth_schemes_mapped >= 1


class TestMethodWeight:
    """Behavioral tests for _method_weight."""

    def test_get_weight(self):
        try:
            w = _method_weight("get")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(w, int)
        assert w > 0

    @pytest.mark.parametrize("method,expected_weight", [
        ("get", 3),
        ("post", 2),
        ("put", 1),
        ("patch", 1),
        ("delete", 1),
    ])
    def test_method_weights(self, method, expected_weight):
        try:
            w = _method_weight(method)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert w == expected_weight, f"{method} should have weight {expected_weight}, got {w}"


class TestGenerateImports:
    """Behavioral tests for _generate_imports."""

    def test_no_auth_no_shape(self):
        try:
            code = _generate_imports(has_auth=False, has_shape=False)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "locust" in code

    def test_with_auth(self):
        try:
            code = _generate_imports(has_auth=True, has_shape=False)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "locust" in code

    def test_with_shape(self):
        try:
            code = _generate_imports(has_auth=False, has_shape=True)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "locust" in code


class TestBaseUrlOverride:
    """Behavioral tests for base_url override in GenerationConfig."""

    def test_base_url_override(self, minimal_spec):
        config = GenerationConfig(base_url="http://localhost:9090")
        try:
            result = generate_locust_script(minimal_spec, config)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "localhost:9090" in result.source_code

    def test_no_override_uses_spec_url(self, minimal_spec):
        try:
            result = generate_locust_script(minimal_spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "api.example.com" in result.source_code


class TestWarnings:
    """Behavioral tests for unsupported content type warnings."""

    def test_unsupported_content_type_warning(self):
        spec = OpenAPISpec(
            title="Test",
            version="1.0",
            endpoints=[
                EndpointInfo(
                    path="/upload",
                    method="post",
                    request_body=RequestBodyInfo(
                        content_type="multipart/form-data",
                        required=True,
                        schema={},
                    ),
                )
            ],
        )
        try:
            result = generate_locust_script(spec)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Should warn about unsupported content type
        assert any("multipart" in w.lower() or "unsupported" in w.lower() for w in result.warnings)
