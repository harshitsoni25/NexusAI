"""Checkpoint creation and safe resume.

Holds the checkpoint manager, which writes checkpoints during a run and, on
resume, proves a checkpoint's integrity and compatibility before continuing.
"""

from __future__ import annotations

from nexusai.application.checkpoint.manager import (
    CheckpointManager,
    ResumeError,
    ResumePlan,
)

__all__ = ["CheckpointManager", "ResumeError", "ResumePlan"]
