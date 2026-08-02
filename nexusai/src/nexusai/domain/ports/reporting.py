"""The ReportGenerator contract.

A report generator renders a prepared report model into a concrete artefact --
an HTML dashboard, a JSON document, a CSV. It performs no computation and no
queries: the report model is assembled once, in the domain, and every generator
renders that same model, so the HTML and JSON versions of a report can never
disagree. A generator that queried the database would reintroduce exactly the
divergence reports exist to prevent.

The report model type is generic here because the concrete model is introduced
with the reporting engine in a later phase; this contract only fixes the shape of
"model in, artefact out".
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from nexusai.domain.model.metadata import Metadata

M_contra = TypeVar("M_contra", contravariant=True)


@runtime_checkable
class ReportGenerator(Protocol[M_contra]):
    """Renders a prepared report model into an artefact."""

    @property
    def name(self) -> str:
        """A stable identifier, also the output format name."""
        ...

    @property
    def media_type(self) -> str:
        """The media type of the artefact this generator produces."""
        ...

    def generate(self, model: M_contra, destination: str) -> Metadata:
        """Render ``model`` to ``destination`` and return artefact metadata."""
        ...
