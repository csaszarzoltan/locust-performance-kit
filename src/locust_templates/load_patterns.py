"""Load pattern builder for OpenAPI-to-Locust conversion.

Maps CLI pattern config (--pattern constant/ramp-up/spike) to concrete
Locust LoadShape classes and generates embeddable code snippets.

Public API:
    PatternConfig          — user-specified pattern configuration
    PatternResult          — resolved shape class + constructor args
    resolve_pattern(config) — main entry point
    parse_duration(s)      — parse "5m" / "30s" / "1h" into seconds
    SUPPORTED_PATTERNS     — tuple of supported pattern names
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

SUPPORTED_PATTERNS: tuple[str, ...] = ("constant", "ramp-up", "spike")


# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────


@dataclass
class PatternConfig:
    """Load pattern configuration."""
    pattern: str
    users: int = 10
    spawn_rate: int = 1
    runtime: str = "5m"
    # Spike-specific
    spike_users: int = 100
    spike_duration: str = "5s"
    # Ramp-specific
    ramp_up_duration: str = "2m"
    ramp_down_duration: str = "1m"
    hold_duration: str = "3m"


@dataclass
class PatternResult:
    """Resolved pattern: shape class name + constructor args."""
    shape_class: str
    shape_import: str
    constructor_args: dict[str, int | float] = field(default_factory=dict)
    code_snippet: str = ""


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────


def resolve_pattern(config: PatternConfig) -> PatternResult:
    """
    Resolve a pattern config into a concrete shape + code snippet.

    Args:
        config: User-specified pattern configuration.

    Returns:
        PatternResult with import, class name, and constructor code.

    Raises:
        ValueError: On unknown pattern name or invalid parameters.
    """
    raise NotImplementedError("resolve_pattern not yet implemented")


def parse_duration(duration_str: str) -> float:
    """Parse duration string like '5m', '30s', '1h' into seconds."""
    raise NotImplementedError("parse_duration not yet implemented")
