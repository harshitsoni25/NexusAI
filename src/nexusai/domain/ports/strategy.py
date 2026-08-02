"""The Strategy contract.

A strategy is an interchangeable algorithm selected at runtime. Scraping,
extraction, validation, storage, export and reporting are all specified to
support multiple strategies chosen by configuration; this is the one contract
they share.

It is generic in its input and output so that the same abstraction serves a
scraping strategy (a target becomes acquired pages) and an export strategy (a
record stream becomes a file), without the core naming either concretely.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

In_contra = TypeVar("In_contra", contravariant=True)
Out_co = TypeVar("Out_co", covariant=True)


@runtime_checkable
class Strategy(Protocol[In_contra, Out_co]):
    """An interchangeable algorithm from an input to an output.

    Implementations are pure with respect to the framework: given an input and
    whatever collaborators they were constructed with, they produce an output.
    Selection among strategies is a separate concern, handled by a selector, so
    a strategy never has to know why it was chosen.
    """

    @property
    def name(self) -> str:
        """A stable identifier used to register and select the strategy."""
        ...

    def execute(self, request: In_contra) -> Out_co:
        """Apply the strategy to ``request`` and return the result."""
        ...


@runtime_checkable
class ConditionalStrategy(Strategy[In_contra, Out_co], Protocol[In_contra, Out_co]):
    """A strategy that can declare whether it applies to a given input.

    Where a selector chooses by inspecting candidates rather than by name, each
    candidate answers :meth:`supports` for the input, and the first that applies
    is used. This keeps the decision with the strategy that knows its own
    applicability, rather than in a central table that must be edited whenever a
    strategy is added.
    """

    def supports(self, request: In_contra) -> bool:
        """Whether this strategy can handle ``request``."""
        ...
