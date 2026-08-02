"""Formula-injection defence for spreadsheet-bound exports.

A spreadsheet treats a cell beginning with ``=``, ``+``, ``-`` or ``@`` as a
formula, so an extracted value like ``=cmd|'/c calc'`` becomes executable when a
victim opens a CSV or XLSX in Excel. :func:`neutralise` prefixes such a value with
an apostrophe, which spreadsheets read as "this is text", defusing the value
while leaving it legible. Applied by the CSV and Excel exporters to every cell.
"""

from __future__ import annotations

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def neutralise(value: str) -> str:
    """Return ``value`` made safe against spreadsheet formula injection."""
    if value and value[0] in _DANGEROUS_PREFIXES:
        return "'" + value
    return value
