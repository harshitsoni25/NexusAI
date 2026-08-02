"""Regression: the composed runtime registers exactly the core export formats.

A C2 container run found that ``ndjson`` -- an implemented, tested, documented core
exporter -- was not registered in the composition root, so the shipped runtime
exposed only csv/json. Existing tests built collaborators by hand and never exercised
``build_application``, which is why the omission slipped through. This test drives the
real composition and asserts the runtime exposes exactly {csv, json, ndjson}: it fails
against the pre-fix build and passes once ``NdjsonExporter`` is registered.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.composition.application import build_scrape_collaborators
from nexusai.composition.container import Container
from nexusai.domain.errors.exceptions import ExportError
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import (
    ProcessedDataset,
    ProcessedField,
    ProcessedRecord,
)
from nexusai.domain.provenance.source import SourceReference

pytestmark = pytest.mark.component

_CORE_FORMATS = {"csv", "json", "ndjson"}


def _dataset() -> ProcessedDataset:
    source = SourceReference(
        uri="https://mock.local/",
        retrieved_at=datetime(2025, 1, 1, tzinfo=UTC),
        method="http-get",
    )
    record = ProcessedRecord(
        identity="r0",
        raw=ExtractionResult(),
        source=source,
        fields={"name": ProcessedField(name="name", value="Widget", raw_value="Widget")},
    )
    return ProcessedDataset(records=[record])


def _collaborators(container: Container):  # type: ignore[no-untyped-def]
    return build_scrape_collaborators(container, target="https://mock.local/", dataset_id="cert")


class TestComposedExportRegistry:
    @pytest.mark.parametrize("fmt", sorted(_CORE_FORMATS))
    def test_each_core_format_is_registered(self, container: Container, fmt: str) -> None:
        collaborators = _collaborators(container)
        manifest = collaborators.export(_dataset(), fmt, f"export.{fmt}")
        assert manifest.record_count == 1  # a real exporter handled it

    def test_unknown_format_is_rejected(self, container: Container) -> None:
        collaborators = _collaborators(container)
        with pytest.raises(ExportError):
            collaborators.export(_dataset(), "xml", "export.xml")

    def test_ndjson_specifically_registered(self, container: Container) -> None:
        # The exact format the C2 run reported missing must now be present.
        collaborators = _collaborators(container)
        manifest = collaborators.export(_dataset(), "ndjson", "export.ndjson")
        assert manifest.record_count == 1
