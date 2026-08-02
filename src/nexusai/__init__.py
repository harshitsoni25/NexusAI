"""Nexus AI: a framework for collecting and assuring publicly available web data.

The public surface of the package is deliberately small. Consumers interact
with the framework through the command line interface, through the composition
root, or by implementing one of the published extension points.

Architecture layers (dependencies always point inward):

    presentation -> application -> domain <- infrastructure

See ``docs/architecture`` for the full design and ``docs/adr`` for the
decisions behind it.
"""

from __future__ import annotations

from nexusai.__about__ import __version__

__all__ = ["__version__"]
