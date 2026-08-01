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

import re
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


def parse_duration(duration_str: str) -> float:
    """Parse duration string like '5m', '30s', '1h', '2h30m' into seconds."""
    if not duration_str or not duration_str.strip():
        raise ValueError(f"Invalid duration string: {duration_str!r}")

    duration_str = duration_str.strip()

    # Handle pure digits (assume seconds)
    if duration_str.isdigit():
        return float(duration_str)

    total = 0.0
    # Match groups of digits followed by a unit
    parts = re.findall(r"(\d+)([smhd])", duration_str.lower())
    if not parts:
        raise ValueError(f"Invalid duration format: {duration_str!r}")

    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    for value, unit in parts:
        total += int(value) * multipliers[unit]

    return total


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
    pattern = config.pattern.lower()

    if pattern == "constant":
        duration = parse_duration(config.runtime)
        args = {
            "steady_users": config.users,
            "spawn_rate": config.spawn_rate,
            "duration": duration,
        }
        snippet_lines = [
            "from locust_templates.shapes import ConstantLoadShape",
            "",
            "class TestShape(ConstantLoadShape):",
            "    pass",
            "",
            "environment.runner.shape_class = TestShape(",
            f"    steady_users={config.users},",
            f"    spawn_rate={config.spawn_rate},",
            f"    duration={duration},",
            ")",
        ]
        return PatternResult(
            shape_class="ConstantLoadShape",
            shape_import="from locust_templates.shapes import ConstantLoadShape",
            constructor_args=args,
            code_snippet="\n".join(snippet_lines),
        )

    elif pattern == "ramp-up":
        ramp_up = parse_duration(config.ramp_up_duration)
        hold = parse_duration(config.hold_duration)
        ramp_down = parse_duration(config.ramp_down_duration)
        args = {
            "target_users": config.users,
            "ramp_up_duration": ramp_up,
            "hold_duration": hold,
            "ramp_down_duration": ramp_down,
            "spawn_rate": config.spawn_rate,
        }
        snippet_lines = [
            "from locust_templates.shapes import RampUpLoadShape",
            "",
            "class TestShape(RampUpLoadShape):",
            "    pass",
            "",
            "environment.runner.shape_class = TestShape(",
            f"    target_users={config.users},",
            f"    ramp_up_duration={ramp_up},",
            f"    hold_duration={hold},",
            f"    ramp_down_duration={ramp_down},",
            f"    spawn_rate={config.spawn_rate},",
            ")",
        ]
        return PatternResult(
            shape_class="RampUpLoadShape",
            shape_import="from locust_templates.shapes import RampUpLoadShape",
            constructor_args=args,
            code_snippet="\n".join(snippet_lines),
        )

    elif pattern == "spike":
        spike_users = config.spike_users
        spike_dur = parse_duration(config.spike_duration)
        args = {
            "baseline_users": config.users,
            "spike_users": spike_users,
            "spike_duration": spike_dur,
            "spawn_rate": config.spawn_rate,
        }
        snippet_lines = [
            "from locust_templates.shapes import SpikeLoadShape",
            "",
            "class TestShape(SpikeLoadShape):",
            "    pass",
            "",
            "environment.runner.shape_class = TestShape(",
            f"    baseline_users={config.users},",
            f"    spike_users={spike_users},",
            f"    spike_duration={spike_dur},",
            ")",
        ]
        return PatternResult(
            shape_class="SpikeLoadShape",
            shape_import="from locust_templates.shapes import SpikeLoadShape",
            constructor_args=args,
            code_snippet="\n".join(snippet_lines),
        )

    else:
        raise ValueError(
            f"Unknown pattern '{config.pattern}'. "
            f"Supported patterns: {', '.join(SUPPORTED_PATTERNS)}"
        )
