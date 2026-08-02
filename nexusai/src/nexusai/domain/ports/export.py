"""The Exporter and StorageProvider contracts.

Storage and export are deliberately separate contracts (ADR-0010). A storage
provider must support write *and* read-back, because the dataset it holds is
queried later by quality assessment, export and reporting. An exporter is
write-only and terminal: it consumes a stream and produces an artefact that
nothing reads back through the framework.

Fusing them would force every exporter to implement query methods it has no use
for, and every storage provider to be streamable in a way it need not be. Keeping
them apart lets each implementer satisfy only the obligations it actually has.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, TypeVar, runtime_checkable

from nexusai.domain.model.metadata import Metadata

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)


@runtime_checkable
class Exporter(Protocol[T_contra]):
    """Consumes a stream of items and produces a terminal artefact.

    Write-only by design. An exporter is handed an iterable and writes it out; it
    is never asked to read anything back. It consumes an ``Iterable`` rather than
    a materialised sequence so that a large dataset can be exported without being
    held in memory.
    """

    @property
    def name(self) -> str:
        """A stable identifier, also the format name where that applies."""
        ...

    @property
    def media_type(self) -> str:
        """The media type of the artefact this exporter produces."""
        ...

    def export(self, items: Iterable[T_contra], destination: str) -> Metadata:
        """Write ``items`` to ``destination`` and return export metadata.

        The returned metadata carries what a manifest needs -- item count, size,
        a provenance summary -- so that an exported artefact remains
        self-describing after it leaves the framework.
        """
        ...


@runtime_checkable
class StorageProvider(Protocol[T]):
    """Persists items durably and supports reading them back.

    The read-back obligation is what distinguishes a storage provider from an
    exporter: a stored dataset is iterated later by quality assessment, export and
    reporting, so a provider that could only write would not satisfy the
    contract.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the provider."""
        ...

    def store(self, items: Iterable[T]) -> int:
        """Persist ``items`` and return how many were stored."""
        ...

    def read_all(self) -> Iterable[T]:
        """Yield every stored item, streaming rather than materialising."""
        ...

    def clear(self) -> None:
        """Remove all stored items."""
        ...
