"""The package tree matches the approved Phase 1 architecture.

Structure drifts silently. Asserting the tree means a package that is renamed,
moved or quietly deleted is caught by the build rather than discovered by the
next person who goes looking for it.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import nexusai

EXPECTED_PACKAGES = (
    "nexusai.shared",
    "nexusai.domain",
    "nexusai.domain.model",
    "nexusai.domain.provenance",
    "nexusai.domain.policy",
    "nexusai.domain.ports",
    "nexusai.domain.events",
    "nexusai.domain.errors",
    "nexusai.application",
    "nexusai.application.usecases",
    "nexusai.application.pipeline",
    "nexusai.application.dto",
    "nexusai.application.contracts",
    "nexusai.application.framework",
    "nexusai.application.services",
    "nexusai.application.retrieval",
    "nexusai.application.extraction",
    "nexusai.application.processing",
    "nexusai.application.downstream",
    "nexusai.application.runtime",
    "nexusai.application.jobs",
    "nexusai.application.workflow",
    "nexusai.application.checkpoint",
    "nexusai.application.analysis",
    "nexusai.application.scheduling",
    "nexusai.application.adapters",
    "nexusai.application.plugins",
    "nexusai.application.usecases",
    "nexusai.infrastructure.analysis",
    "nexusai.domain.observability",
    "nexusai.application.observability",
    "nexusai.application.benchmark",
    "nexusai.infrastructure.benchmark",
    "nexusai.infrastructure.visual",
    "nexusai.infrastructure.preflight",
    "nexusai.infrastructure",
    "nexusai.infrastructure.http",
    "nexusai.infrastructure.browser",
    "nexusai.infrastructure.parsing",
    "nexusai.infrastructure.extraction",
    "nexusai.infrastructure.retrieval",
    "nexusai.infrastructure.pagination",
    "nexusai.infrastructure.analysis",
    "nexusai.domain.observability",
    "nexusai.application.observability",
    "nexusai.application.benchmark",
    "nexusai.infrastructure.benchmark",
    "nexusai.infrastructure.visual",
    "nexusai.infrastructure.normalization",
    "nexusai.infrastructure.validation",
    "nexusai.infrastructure.rules",
    "nexusai.infrastructure.quality",
    "nexusai.infrastructure.change",
    "nexusai.infrastructure.persistence",
    "nexusai.infrastructure.artifacts",
    "nexusai.infrastructure.export",
    "nexusai.infrastructure.reporting",
    "nexusai.infrastructure.observability",
    "nexusai.infrastructure.config",
    "nexusai.infrastructure.plugins",
    "nexusai.infrastructure.scheduling",
    "nexusai.infrastructure.notification",
    "nexusai.infrastructure.events",
    "nexusai.presentation",
    "nexusai.presentation.cli",
    "nexusai.presentation.cli.commands",
    "nexusai.presentation.cli.rendering",
    "nexusai.composition",
    "nexusai.testing",
)


@pytest.mark.parametrize("name", EXPECTED_PACKAGES)
def test_every_approved_package_exists_and_imports(name: str) -> None:
    assert importlib.import_module(name) is not None


@pytest.mark.parametrize("name", EXPECTED_PACKAGES)
def test_every_package_explains_what_belongs_in_it(name: str) -> None:
    # An empty package is a mystery; a documented one is a plan.
    module = importlib.import_module(name)
    assert module.__doc__ and len(module.__doc__.strip()) > 40, f"{name} needs a docstring"


def test_the_distribution_declares_inline_type_information() -> None:
    assert (Path(nexusai.__file__).parent / "py.typed").exists()
