"""Job lifecycle management.

Holds the job manager: the single component through which jobs are created and
through which every state change passes, always via the state-machine policy.
"""

from __future__ import annotations

from nexusai.application.jobs.manager import JobManager

__all__ = ["JobManager"]
