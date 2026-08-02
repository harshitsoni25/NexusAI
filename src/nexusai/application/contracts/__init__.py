"""Extension point contracts that plugin authors program against.

The generic plugin contract lives in ``domain.ports.plugins``. Category-specific
contracts -- exporter, extractor, storage provider and the rest -- are published
by the phase that introduces the engine consuming them, so that a contract and
its first consumer arrive together.
"""

from __future__ import annotations

from nexusai.application.contracts.extension_points import (
    ExtensionPointDescription,
    describe_extension_points,
)

__all__ = ["ExtensionPointDescription", "describe_extension_points"]
