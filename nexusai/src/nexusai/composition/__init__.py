"""The composition root.

This is the only package permitted to import both ``application`` and
``infrastructure``. Concentrating that knowledge in one place is what allows
every other module to depend on abstractions alone.

The initialiser deliberately re-exports nothing. ``container`` imports
``factories``, so a re-export here would make the package initialiser and its own
submodule mutually dependent -- a cycle, and one the architecture tests reject.
Import from ``nexusai.composition.container`` directly.
"""

from __future__ import annotations
