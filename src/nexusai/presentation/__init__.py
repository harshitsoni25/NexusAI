"""User-facing surfaces.

Translates user input into DTOs, invokes a use case and renders the result. It
contains no business logic; a command that grows conditional logic about what
the system should do is a signal that the logic belongs in a use case, which is
also what keeps a future REST API from duplicating it.
"""

from __future__ import annotations
