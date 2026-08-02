"""Source traceability value objects.

Provenance is a structural member of the record type rather than a side table
(ADR-0008), so a record without provenance is not representable. The record-level
and field-level provenance that composes these references arrives with the record
model in a later phase; these are the reusable roots.
"""

from __future__ import annotations

from nexusai.domain.provenance.source import ArtifactReference, SourceReference

__all__ = ["ArtifactReference", "SourceReference"]
