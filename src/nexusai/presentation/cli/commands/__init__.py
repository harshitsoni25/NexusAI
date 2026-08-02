"""Command implementations.

Each command is a thin translation between user input and a use case. A command
that grows conditional logic about what the system should do is a signal that
the logic belongs in the application layer, where a future REST API can reach it
too.

Only commands that are fully implemented are registered. The Master
Specification forbids placeholders, so business commands appear in the phases
that implement them rather than as stubs that accept input and do nothing.
"""

from __future__ import annotations
