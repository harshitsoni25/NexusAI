"""Responsible target preflight: parsing robots.txt and surfacing guidance.

Preflight is about respecting a site's stated wishes, not defeating them. This
module parses a robots.txt document -- which the caller retrieves through approved
means -- extracts the directives that apply to a given user-agent, and reports
whether a path is allowed, along with any crawl delay and sitemap references. It
never circumvents a restriction and never claims that reading robots.txt confers
legal authorisation; it surfaces what the file says so an operator can act
responsibly.

The parser follows the conventional precedence: the most specific matching path
rule wins, and an explicit ``Disallow`` on a matching prefix blocks the path
unless a longer ``Allow`` overrides it. When robots.txt is absent or unparseable,
the result is permissive but flagged, because absence of a rule is not the same
as a considered decision.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True, kw_only=True)
class PreflightResult:
    """What preflight determined about a target.

    Attributes:
        target: The URL checked.
        allowed: Whether the target's path is permitted for the user-agent.
        crawl_delay: The requested delay between requests, if stated.
        sitemaps: Sitemap URLs declared in robots.txt.
        warnings: Caveats, such as a missing or unparseable robots.txt.
        robots_present: Whether a robots.txt was actually available.
    """

    target: str
    allowed: bool = True
    crawl_delay: float | None = None
    sitemaps: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    robots_present: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation."""
        return {
            "target": self.target,
            "allowed": self.allowed,
            "crawl_delay": self.crawl_delay,
            "sitemaps": list(self.sitemaps),
            "warnings": list(self.warnings),
            "robots_present": self.robots_present,
        }


@dataclass(frozen=True, slots=True)
class _Rule:
    allow: bool
    path: str


def parse_robots(robots_text: str, *, target: str, user_agent: str = "*") -> PreflightResult:
    """Parse ``robots_text`` and decide whether ``target``'s path is allowed.

    Args:
        robots_text: The contents of a robots.txt document.
        target: The URL to check.
        user_agent: The user-agent to evaluate rules for.
    """
    path = urlparse(target).path or "/"
    rules, crawl_delay, sitemaps, applies = _collect(robots_text, user_agent)

    matching = [rule for rule in rules if path.startswith(rule.path)]
    allowed = True
    if matching:
        # Longest matching path wins; Allow beats Disallow at equal length.
        best = max(matching, key=lambda rule: (len(rule.path), rule.allow))
        allowed = best.allow

    warnings: list[str] = []
    if not applies:
        warnings.append("no rules matched the user-agent; treating as allowed")
    return PreflightResult(
        target=target,
        allowed=allowed,
        crawl_delay=crawl_delay,
        sitemaps=tuple(sitemaps),
        warnings=tuple(warnings),
        robots_present=True,
    )


def absent_robots(target: str) -> PreflightResult:
    """Return a permissive-but-flagged result for a target with no robots.txt."""
    return PreflightResult(
        target=target,
        allowed=True,
        warnings=("robots.txt was not available; proceeding with default policy",),
        robots_present=False,
    )


def _collect(
    robots_text: str, user_agent: str
) -> tuple[list[_Rule], float | None, list[str], bool]:
    rules: list[_Rule] = []
    crawl_delay: float | None = None
    sitemaps: list[str] = []
    active = False
    applies = False
    ua_lower = user_agent.lower()

    for raw in robots_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            active = value == "*" or value.lower() == ua_lower
            if active:
                applies = True
        elif key == "sitemap":
            sitemaps.append(value)
        elif active and key == "disallow" and value:
            rules.append(_Rule(allow=False, path=value))
        elif active and key == "allow" and value:
            rules.append(_Rule(allow=True, path=value))
        elif active and key == "crawl-delay":
            with contextlib.suppress(ValueError):
                crawl_delay = float(value)
    return rules, crawl_delay, sitemaps, applies
