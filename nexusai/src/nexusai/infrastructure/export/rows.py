"""Turning processed records into flat rows for tabular exporters.

Tabular formats -- CSV, Excel, Parquet -- need a flat, ordered set of columns.
This module derives a stable column order from the union of field names across
the dataset (sorted, so identical inputs produce identical schemas) and flattens
each record's processed values into that shape. Nested values are serialised to
JSON text so a tabular cell can hold them without silently dropping structure.

Provenance is preserved, not discarded for tidiness: an optional source column
carries the record's source URI, so a row in a CSV can still be traced to the
page it came from.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from nexusai.domain.model.processing import ProcessedDataset, ProcessedRecord
from nexusai.shared.types import JsonValue

SOURCE_COLUMN = "_source_uri"


def column_order(dataset: ProcessedDataset, *, include_source: bool = True) -> list[str]:
    """Return a deterministic column order for the dataset's records."""
    names: set[str] = set()
    for record in dataset.records:
        names.update(record.fields)
    ordered = sorted(names)
    if include_source:
        ordered.append(SOURCE_COLUMN)
    return ordered


def record_to_row(
    record: ProcessedRecord, columns: Sequence[str], *, null: str = ""
) -> dict[str, str]:
    """Flatten a record into a string-valued row keyed by ``columns``."""
    row: dict[str, str] = {}
    for column in columns:
        if column == SOURCE_COLUMN:
            row[column] = record.source.uri if record.source is not None else ""
            continue
        value = record.value(column)
        row[column] = _cell(value, null)
    return row


def _cell(value: JsonValue, null: str) -> str:
    if value is None:
        return null
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, sort_keys=True, default=str)
