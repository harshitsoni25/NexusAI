"""Structural conformance tests for the Phase 3 SDK contracts.

These lock the public contracts: a minimal conforming implementation must satisfy
each Protocol, and these tests fail loudly if a contract's shape drifts.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from nexusai.domain.model.assessment import ValidationResult
from nexusai.domain.model.metadata import Metadata
from nexusai.domain.ports import (
    Describable,
    Exporter,
    Factory,
    ReadableRepository,
    ReportGenerator,
    Repository,
    Service,
    StorageProvider,
    Strategy,
    UnitOfWork,
    Validator,
    WritableRepository,
)
from nexusai.domain.ports.strategy import ConditionalStrategy


class _Strategy:
    name = "s"

    def execute(self, request: int) -> str:
        return str(request)


class _ConditionalStrategy(_Strategy):
    def supports(self, request: int) -> bool:
        return request > 0


class _Validator:
    name = "v"

    def validate(self, value: object) -> ValidationResult:
        return ValidationResult.passing()


class _Exporter:
    name = "e"
    media_type = "text/csv"

    def export(self, items: Iterable[object], destination: str) -> Metadata:
        return Metadata.empty()


class _StorageProvider:
    name = "store"

    def store(self, items: Iterable[object]) -> int:
        return 0

    def read_all(self) -> Iterable[object]:
        return ()

    def clear(self) -> None:
        pass


class _ReportGenerator:
    name = "r"
    media_type = "text/html"

    def generate(self, model: object, destination: str) -> Metadata:
        return Metadata.empty()


class _Repository:
    def get(self, identity: str) -> object | None:
        return None

    def exists(self, identity: str) -> bool:
        return False

    def iterate(self) -> Iterator[object]:
        return iter(())

    def count(self) -> int:
        return 0

    def add(self, entity: object) -> None:
        pass

    def add_many(self, entities: object) -> None:
        pass

    def remove(self, identity: str) -> None:
        pass


class _UnitOfWork:
    def __enter__(self) -> _UnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None:
        return None

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class _Service:
    name = "svc"

    def initialize(self) -> None:
        pass

    def dispose(self) -> None:
        pass


class _Factory:
    def create(self, name: str) -> object:
        return object()

    def available(self) -> tuple[str, ...]:
        return ()


class _Describable:
    @property
    def metadata(self) -> Metadata:
        return Metadata.empty()


def test_strategy_conformance() -> None:
    assert isinstance(_Strategy(), Strategy)
    assert not isinstance(_Strategy(), ConditionalStrategy)
    assert isinstance(_ConditionalStrategy(), ConditionalStrategy)


def test_validator_conformance() -> None:
    assert isinstance(_Validator(), Validator)


def test_exporter_and_storage_are_distinct_contracts() -> None:
    assert isinstance(_Exporter(), Exporter)
    assert isinstance(_StorageProvider(), StorageProvider)


def test_report_generator_conformance() -> None:
    assert isinstance(_ReportGenerator(), ReportGenerator)


def test_repository_conformance() -> None:
    repo = _Repository()
    assert isinstance(repo, ReadableRepository)
    assert isinstance(repo, WritableRepository)
    assert isinstance(repo, Repository)


def test_unit_of_work_conformance() -> None:
    assert isinstance(_UnitOfWork(), UnitOfWork)


def test_service_and_factory_conformance() -> None:
    assert isinstance(_Service(), Service)
    assert isinstance(_Factory(), Factory)


def test_describable_conformance() -> None:
    assert isinstance(_Describable(), Describable)
    assert not isinstance(object(), Describable)
