"""Responsible target preflight: robots.txt parsing and crawl guidance."""

from __future__ import annotations

from nexusai.infrastructure.preflight.robots import (
    PreflightResult,
    absent_robots,
    parse_robots,
)

__all__ = ["PreflightResult", "absent_robots", "parse_robots"]
