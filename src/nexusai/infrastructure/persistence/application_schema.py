"""SQLAlchemy tables for application-level state: jobs, checkpoints, schedules.

These rows persist the application layer's long-lived state through the same
metadata store and boundary discipline as the dataset schema: the rows are
infrastructure detail, and the repositories map them to and from domain value
objects so no SQLAlchemy type escapes. Job and schedule rows carry their small
free-form maps as JSON text, because their shape is caller-defined; checkpoints
store their fields explicitly so integrity can be recomputed on load.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from nexusai.infrastructure.persistence.schema import Base


class JobRow(Base):
    """One persisted job."""

    __tablename__ = "job"

    job_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    configuration_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_version: Mapped[str] = mapped_column(String(32), default="1")
    dataset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dataset_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checkpoint_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class CheckpointRow(Base):
    """One persisted checkpoint. Append-only; the latest by row id is current."""

    __tablename__ = "checkpoint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class ScheduleRow(Base):
    """One persisted schedule."""

    __tablename__ = "schedule"

    schedule_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run: Mapped[datetime | None] = mapped_column(nullable=True)
    last_run: Mapped[datetime | None] = mapped_column(nullable=True)
    interval_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
