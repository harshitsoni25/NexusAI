"""Retention policy and retention service behaviour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nexusai.application.downstream import RetentionService
from nexusai.domain.model.persistence import ArtifactMetadata, ArtifactType
from nexusai.domain.policy.retention import RetentionClass, RetentionPolicy


def _artifact(kind: ArtifactType, age_days: float) -> ArtifactMetadata:
    return ArtifactMetadata(
        artifact_id=f"a-{kind.value}",
        artifact_type=kind,
        locator="memory://a",
        media_type="application/octet-stream",
        size_bytes=1,
        content_hash="sha256:x",
        created_at=datetime.now(UTC) - timedelta(days=age_days),
    )


class TestRetentionPolicy:
    def test_reports_are_audit_class(self) -> None:
        assert RetentionPolicy().classify(ArtifactType.REPORT) is RetentionClass.AUDIT

    def test_audit_is_never_deletable(self) -> None:
        assert not RetentionPolicy().may_delete(ArtifactType.REPORT, 10**9)

    def test_old_reproducibility_is_deletable(self) -> None:
        assert RetentionPolicy().may_delete(ArtifactType.SCREENSHOT, 40 * 86400)

    def test_fresh_reproducibility_is_kept(self) -> None:
        assert not RetentionPolicy().may_delete(ArtifactType.SCREENSHOT, 100)

    def test_future_timestamp_never_deletes(self) -> None:
        assert not RetentionPolicy().may_delete(ArtifactType.OTHER, -5)


class TestRetentionService:
    def test_plan_separates_deletable_from_retained(self) -> None:
        service = RetentionService(RetentionPolicy())
        plan = service.plan(
            [
                _artifact(ArtifactType.SCREENSHOT, 40),
                _artifact(ArtifactType.REPORT, 400),
                _artifact(ArtifactType.SCREENSHOT, 1),
            ]
        )
        assert len(plan.deletable) == 1
        assert len(plan.retained) == 2

    def test_execute_only_deletes_the_deletable(self) -> None:
        service = RetentionService(RetentionPolicy())
        plan = service.plan([_artifact(ArtifactType.SCREENSHOT, 40)])
        deleted: list[str] = []
        count = service.execute(plan, lambda a: deleted.append(a.artifact_id))
        assert count == 1
        assert deleted

    def test_audit_never_reaches_execute(self) -> None:
        service = RetentionService(RetentionPolicy())
        plan = service.plan([_artifact(ArtifactType.REPORT, 10000)])
        touched: list[str] = []
        service.execute(plan, lambda a: touched.append(a.artifact_id))
        assert not touched
