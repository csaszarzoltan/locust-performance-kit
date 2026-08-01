"""CLI entry point for locust-gen.

Generates Locust load test scripts from OpenAPI/Swagger specifications.

Usage:
    locust-gen from-openapi spec.yaml --output locustfile.py
    locust-gen from-openapi spec.yaml --output locustfile.py --users 50 --spawn-rate 5
    locust-gen from-openapi spec.yaml --output locustfile.py --pattern ramp-up --runtime 10m
"""

from __future__ import annotations

import argparse


def _build_parser() -> argparse.ArgumentParser:
    """Build the locust-gen argument parser with subcommands."""
    raise NotImplementedError("_build_parser not yet implemented")


def cmd_from_openapi(args: argparse.Namespace) -> int:
    """Handle 'locust-gen from-openapi' subcommand."""
    raise NotImplementedError("cmd_from_openapi not yet implemented")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0=success, 1=error)."""
    raise NotImplementedError("main not yet implemented")
