"""Pre-dev tests for cli_gen module (locust-gen CLI).

Tests define the contract for the argparse-based CLI that generates
Locust load test scripts from OpenAPI/Swagger specifications.

Pattern:
- Interface tests: verify imports, function signatures (PASS immediately)
- Behavioral tests: verify CLI behavior (FAIL with NotImplementedError until implemented)
"""

from __future__ import annotations

import argparse
import inspect

import pytest

from locust_templates.cli_gen import _build_parser, cmd_from_openapi, main

# ──────────────────────────────────────────────────────────────
# Interface tests — PASS immediately against stubs
# ──────────────────────────────────────────────────────────────


class TestMainExists:
    """Verify main() is importable and callable."""

    def test_main_is_importable(self):
        assert main is not None

    def test_main_is_callable(self):
        assert callable(main)

    def test_main_accepts_argv(self):
        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_main_argv_default_none(self):
        sig = inspect.signature(main)
        param = sig.parameters["argv"]
        assert param.default is None

    def test_main_return_annotation(self):
        sig = inspect.signature(main)
        ret = sig.return_annotation
        assert ret is inspect.Parameter.empty or ret is int or ret == "int"


class TestBuildParserExists:
    """Verify _build_parser() is importable and callable."""

    def test_is_callable(self):
        assert callable(_build_parser)

    def test_returns_argument_parser(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(parser, argparse.ArgumentParser)


class TestCmdFromOpenapiExists:
    """Verify cmd_from_openapi() is importable and callable."""

    def test_is_callable(self):
        assert callable(cmd_from_openapi)

    def test_signature_has_args(self):
        sig = inspect.signature(cmd_from_openapi)
        params = list(sig.parameters.keys())
        assert "args" in params

    def test_return_annotation(self):
        sig = inspect.signature(cmd_from_openapi)
        ret = sig.return_annotation
        assert ret is inspect.Parameter.empty or ret is int or ret == "int"


# ──────────────────────────────────────────────────────────────
# Behavioral tests — FAIL with NotImplementedError until implemented
# ──────────────────────────────────────────────────────────────


class TestMainBehavioral:
    """Behavioral tests for main()."""

    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            main()

    def test_returns_int_on_success(self, tmp_path):
        try:
            code = main(["from-openapi", "petstore.yaml"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(code, int)

    def test_help_flag(self):
        try:
            main(["--help"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except SystemExit as e:
            # argparse --help raises SystemExit(0)
            assert e.code == 0

    def test_version_flag(self):
        try:
            main(["--version"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except SystemExit as e:
            assert e.code == 0


class TestBuildParserBehavioral:
    """Behavioral tests for _build_parser()."""

    def test_returns_parser(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(parser, argparse.ArgumentParser)

    def test_has_from_openapi_subcommand(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Parse with subcommand — should not raise
        args = parser.parse_args(["from-openapi", "spec.yaml"])
        assert hasattr(args, "spec_file") or hasattr(args, "func")

    def test_has_output_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "-o", "out.py"])
        assert args.output == "out.py" or getattr(args, "output", None) == "out.py"

    def test_has_users_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "-u", "50"])
        assert args.users == 50 or getattr(args, "users", None) == 50

    def test_has_spawn_rate_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "-r", "5"])
        assert args.spawn_rate == 5 or getattr(args, "spawn_rate", None) == 5

    def test_has_runtime_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "-t", "10m"])
        assert args.runtime == "10m" or getattr(args, "runtime", None) == "10m"

    def test_has_pattern_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "-p", "ramp-up"])
        assert args.pattern == "ramp-up" or getattr(args, "pattern", None) == "ramp-up"

    def test_has_base_url_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "--base-url", "http://localhost:8080"])
        assert args.base_url == "http://localhost:8080" or getattr(args, "base_url", None) == "http://localhost:8080"

    def test_has_auth_provider_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "--auth-provider", "env"])
        assert args.auth_provider == "env" or getattr(args, "auth_provider", None) == "env"

    def test_has_dry_run_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "--dry-run"])
        assert getattr(args, "dry_run", None) is True

    def test_has_verbose_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "-v"])
        assert getattr(args, "verbose", None) is True

    def test_has_no_comments_flag(self):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml", "--no-comments"])
        assert getattr(args, "no_comments", None) is True


class TestCmdFromOpenapiBehavioral:
    """Behavioral tests for cmd_from_openapi()."""

    def test_raises_not_implemented(self):
        args = argparse.Namespace(spec_file="petstore.yaml")
        with pytest.raises(NotImplementedError):
            cmd_from_openapi(args)

    def test_returns_int(self, tmp_path):
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("openapi: '3.0.3'\ninfo: {title: Test, version: '1.0'}\npaths: {}")
        args = argparse.Namespace(
            spec_file=str(spec_file),
            output=str(tmp_path / "locustfile.py"),
            users=10, spawn_rate=1, runtime="5m", pattern="constant",
            base_url=None, auth_provider=None, dry_run=False,
            verbose=False, no_comments=False,
        )
        try:
            code = cmd_from_openapi(args)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(code, int)


class TestEndToEndFlags:
    """Parametrized behavioral tests for CLI flag combinations."""

    @pytest.mark.parametrize("flags,expected_attrs", [
        (["--dry-run"], {"dry_run": True}),
        (["-v"], {"verbose": True}),
        (["--no-comments"], {"no_comments": True}),
        (["--pattern", "ramp-up"], {"pattern": "ramp-up"}),
        (["--users", "100"], {"users": 100}),
        (["--spawn-rate", "10"], {"spawn_rate": 10}),
        (["--runtime", "30m"], {"runtime": "30m"}),
        (["--base-url", "http://localhost:8080"], {"base_url": "http://localhost:8080"}),
        (["--auth-provider", "oauth2"], {"auth_provider": "oauth2"}),
    ])
    def test_flag_parsing(self, flags, expected_attrs):
        try:
            parser = _build_parser()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        args = parser.parse_args(["from-openapi", "spec.yaml"] + flags)
        for attr, expected in expected_attrs.items():
            assert getattr(args, attr, None) == expected, f"Flag {attr} should be {expected}"
