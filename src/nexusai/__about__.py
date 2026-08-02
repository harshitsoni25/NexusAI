"""Single source of truth for the package version.

The build backend reads ``__version__`` from this module, so the version is
declared in exactly one place and never drifts between the distribution
metadata and the runtime package.
"""

from __future__ import annotations

__version__ = "0.1.0"
