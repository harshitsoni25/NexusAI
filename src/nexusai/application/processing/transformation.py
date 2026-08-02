"""The transformation engine.

Given an extraction result and a plan mapping each field to an ordered list of
transformer names, the engine applies each chain and produces
:class:`ProcessedField`s that keep both the raw value and the transformed one.
The raw :class:`ExtractionResult` is never touched; the engine reads from it and
writes a new record beside it, which is how the framework's raw-immutability
guarantee is met in practice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from nexusai.domain.errors.exceptions import TransformationError
from nexusai.domain.model.extraction import ExtractionResult
from nexusai.domain.model.processing import ProcessedField, ProcessedRecord
from nexusai.domain.ports.processing import Transformer
from nexusai.shared.registry import Registry
from nexusai.shared.types import JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationPlan:
    """A declarative plan mapping fields to ordered transformer chains.

    Attributes:
        chains: A mapping from field name to the transformer names to apply, in
            order. A field absent from the plan is carried through untransformed.
        identity_field: The field whose transformed value identifies the record
            for change detection. When ``None`` or absent, a content hash of the
            values is used.
    """

    chains: Mapping[str, Sequence[str]] = field(default_factory=dict)
    identity_field: str | None = None


class TransformationEngine:
    """Applies transformer chains to extracted values, preserving the raw."""

    def __init__(self, transformers: Registry[Transformer]) -> None:
        self._transformers = transformers

    def transform(self, extraction: ExtractionResult, plan: TransformationPlan) -> ProcessedRecord:
        """Transform ``extraction`` under ``plan`` into a processed record.

        Raises:
            TransformationError: If a plan names a transformer that is not
                registered.
        """
        fields: dict[str, ProcessedField] = {}
        for name, extracted in extraction.fields.items():
            raw_value = extracted.value
            chain = plan.chains.get(name, ())
            value, applied = self._apply_chain(raw_value, chain)
            fields[name] = ProcessedField(
                name=name, value=value, raw_value=raw_value, transformations=applied
            )
        identity = _identity_for(fields, plan.identity_field)
        return ProcessedRecord(identity=identity, raw=extraction, fields=fields)

    def _apply_chain(
        self, value: JsonValue, chain: Sequence[str]
    ) -> tuple[JsonValue, tuple[str, ...]]:
        current = value
        applied: list[str] = []
        for transformer_name in chain:
            transformer = self._transformers.get_or_none(transformer_name)
            if transformer is None:
                raise TransformationError("No such transformer", transformer=transformer_name)
            current = transformer.transform(current)
            applied.append(transformer_name)
        return current, tuple(applied)


def _identity_for(fields: Mapping[str, ProcessedField], identity_field: str | None) -> str:
    if identity_field and identity_field in fields:
        return str(fields[identity_field].value)
    import hashlib
    import json

    payload = json.dumps(
        {name: processed.value for name, processed in sorted(fields.items())},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
