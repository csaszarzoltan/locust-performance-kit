"""CLI entry point for locust-gen.

Generates Locust load test scripts from OpenAPI/Swagger specifications.

Usage:
    locust-gen from-openapi spec.yaml --output locustfile.py
    locust-gen from-openapi spec.yaml --output locustfile.py --users 50 --spawn-rate 5
    locust-gen from-openapi spec.yaml --output locustfile.py --pattern ramp-up --runtime 10m
"""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    """Build the locust-gen argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="locust-gen",
        description="Generate Locust load test scripts from OpenAPI/Swagger specs",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.5.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # from-openapi subcommand
    openapi_parser = subparsers.add_parser(
        "from-openapi",
        help="Generate Locust script from an OpenAPI/Swagger spec file",
    )
    openapi_parser.add_argument("spec_file", help="Path to OpenAPI/Swagger spec file (JSON or YAML)")
    openapi_parser.add_argument(
        "-o", "--output",
        default="locustfile.py",
        help="Output file path (default: locustfile.py)",
    )
    openapi_parser.add_argument(
        "-u", "--users",
        type=int,
        default=10,
        help="Number of simulated users (default: 10)",
    )
    openapi_parser.add_argument(
        "-r", "--spawn-rate",
        type=int,
        default=1,
        help="Users spawned per second (default: 1)",
    )
    openapi_parser.add_argument(
        "-t", "--runtime",
        default="5m",
        help="Test runtime duration (default: 5m)",
    )
    openapi_parser.add_argument(
        "-p", "--pattern",
        default="constant",
        choices=["constant", "ramp-up", "spike"],
        help="Load pattern (default: constant)",
    )
    openapi_parser.add_argument(
        "--base-url",
        help="Override base URL for all requests",
    )
    openapi_parser.add_argument(
        "--auth-provider",
        help="Authentication provider (env, oauth2, etc.)",
    )
    openapi_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Generate script but don't write to file",
    )
    openapi_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )
    openapi_parser.add_argument(
        "--no-comments",
        action="store_true",
        default=False,
        help="Generate script without inline comments",
    )

    return parser


def cmd_from_openapi(args: argparse.Namespace) -> int:
    """Handle 'locust-gen from-openapi' subcommand."""
    from locust_templates.load_patterns import PatternConfig, resolve_pattern
    from locust_templates.locust_generator import GenerationConfig, generate_locust_script
    from locust_templates.openapi_parser import OpenAPIParseError, parse_spec

    try:
        spec = parse_spec(args.spec_file)
    except OpenAPIParseError as exc:
        print(f"Error parsing spec: {exc}", file=sys.stderr)
        return 1

    config = GenerationConfig(
        base_url=args.base_url,
        include_comments=not args.no_comments,
        auth_provider=args.auth_provider,
    )

    result = generate_locust_script(spec, config)

    # Append load pattern snippet if pattern is not default
    if args.pattern and args.pattern != "constant":
        pattern_config = PatternConfig(
            pattern=args.pattern,
            users=args.users,
            spawn_rate=args.spawn_rate,
            runtime=args.runtime,
        )
        try:
            pattern_result = resolve_pattern(pattern_config)
            result.source_code += "\n\n# ── Load Pattern ──\n"
            result.source_code += pattern_result.code_snippet + "\n"
        except ValueError as exc:
            print(f"Warning: {exc}", file=sys.stderr)

    if args.dry_run:
        print(result.source_code)
    else:
        output_path = args.output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.source_code)
        if args.verbose:
            print(f"Generated {output_path}")
            print(f"  Endpoints processed: {result.endpoints_processed}")
            print(f"  Auth schemes mapped: {result.auth_schemes_mapped}")
            for w in result.warnings:
                print(f"  Warning: {w}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0=success, 1=error)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "from-openapi":
        return cmd_from_openapi(args)

    parser.print_help()
    return 0
