"""The innermost architectural layer: enterprise rules and contracts.

This package depends on the Python standard library and ``nexusai.shared``
and on nothing else -- not Pydantic, not Loguru, not SQLAlchemy, not httpx. The
restriction is enforced mechanically by ``tests/unit/architecture``.

Keeping the domain free of third-party dependencies is what makes business
logic testable without network access, a browser, or a filesystem, as required
by section 37 of the Master Specification.
"""

from __future__ import annotations
