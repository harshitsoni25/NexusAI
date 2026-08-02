"""Tests for the retrieval engine: selection, recovery, pagination."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nexusai.application.retrieval import RetrievalEngine
from nexusai.domain.errors.exceptions import (
    AcquisitionError,
    ConfigurationError,
    NetworkError,
)
from nexusai.domain.model.recovery import RecoveryDecision
from nexusai.domain.model.retrieval import (
    Document,
    RetrievalMethod,
    RetrievalRequest,
)


def _doc(url: str = "https://x") -> Document:
    return Document(
        url=url,
        content=b"ok",
        status_code=200,
        provider="fake",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        media_type="text/html",
    )


class RecordingProvider:
    """A provider returning a fixed document and recording calls."""

    name = "recording"

    def __init__(self, *, supports: bool = True) -> None:
        self._supports = supports
        self.calls = 0

    def supports(self, request: RetrievalRequest) -> bool:
        return self._supports

    def initialize(self) -> None:
        pass

    def dispose(self) -> None:
        pass

    def retrieve(self, request: RetrievalRequest) -> Document:
        self.calls += 1
        return _doc(request.url)


class FlakyProvider:
    """A provider that fails a set number of times before succeeding."""

    name = "flaky"

    def __init__(self, failures: int) -> None:
        self._remaining = failures
        self.calls = 0

    def supports(self, request: RetrievalRequest) -> bool:
        return True

    def initialize(self) -> None:
        pass

    def dispose(self) -> None:
        pass

    def retrieve(self, request: RetrievalRequest) -> Document:
        self.calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise NetworkError("transient", url=request.url)
        return _doc(request.url)


class StubPolicy:
    """A recovery policy returning scripted decisions per attempt."""

    name = "stub"

    def __init__(self, *decisions: RecoveryDecision) -> None:
        self._decisions = list(decisions)

    def decide(self, error: Exception, attempt: int) -> RecoveryDecision:
        index = min(attempt - 1, len(self._decisions) - 1)
        return self._decisions[index]


def test_engine_requires_at_least_one_provider() -> None:
    with pytest.raises(ConfigurationError):
        RetrievalEngine([], StubPolicy(RecoveryDecision.skip()))


def test_engine_selects_first_supporting_provider() -> None:
    skipping = RecordingProvider(supports=False)
    chosen = RecordingProvider()
    engine = RetrievalEngine([skipping, chosen], StubPolicy(RecoveryDecision.skip()))
    document = engine.retrieve(RetrievalRequest(url="https://x"))
    assert document.url == "https://x"
    assert chosen.calls == 1
    assert skipping.calls == 0


def test_engine_raises_when_no_provider_supports() -> None:
    engine = RetrievalEngine(
        [RecordingProvider(supports=False)], StubPolicy(RecoveryDecision.skip())
    )
    with pytest.raises(ConfigurationError, match="No provider supports"):
        engine.retrieve(RetrievalRequest(url="https://x", method=RetrievalMethod.API))


def test_engine_retries_until_success() -> None:
    provider = FlakyProvider(failures=2)
    policy = StubPolicy(RecoveryDecision.retry(0.0), RecoveryDecision.retry(0.0))
    engine = RetrievalEngine([provider], policy)
    document = engine.retrieve(RetrievalRequest(url="https://x"))
    assert document.status_code == 200
    assert provider.calls == 3


def test_engine_sleeps_between_retries() -> None:
    slept: list[float] = []
    provider = FlakyProvider(failures=1)
    policy = StubPolicy(RecoveryDecision.retry(1.5))
    engine = RetrievalEngine([provider], policy, sleeper=slept.append)
    engine.retrieve(RetrievalRequest(url="https://x"))
    assert slept == [1.5]


def test_engine_raises_when_skip_leaves_no_document() -> None:
    provider = FlakyProvider(failures=1)
    engine = RetrievalEngine([provider], StubPolicy(RecoveryDecision.skip("give up")))
    with pytest.raises(AcquisitionError, match="not recoverable"):
        engine.retrieve(RetrievalRequest(url="https://x"))


class SucceedThenFailProvider:
    """Succeeds on the first page, then fails, to drive pagination recovery."""

    name = "seq"

    def __init__(self) -> None:
        self.calls = 0

    def supports(self, request: RetrievalRequest) -> bool:
        return True

    def initialize(self) -> None:
        pass

    def dispose(self) -> None:
        pass

    def retrieve(self, request: RetrievalRequest) -> Document:
        self.calls += 1
        if self.calls == 1:
            return _doc(request.url)
        raise NetworkError("later failure", url=request.url)


class AlwaysNext:
    """A pagination strategy that always asks for one more page."""

    name = "always"

    def next_request(
        self, request: RetrievalRequest, document: Document
    ) -> RetrievalRequest | None:
        return request.with_params(page="next")


def test_paginated_collects_until_skip() -> None:
    provider = SucceedThenFailProvider()
    engine = RetrievalEngine([provider], StubPolicy(RecoveryDecision.skip("stop")))
    outcome = engine.retrieve_paginated(RetrievalRequest(url="https://x"), AlwaysNext())
    assert len(outcome.documents) == 1
    assert outcome.skipped == (("https://x", "stop"),)
    assert outcome.aborted is False
    assert outcome.is_complete is False


def test_paginated_aborts_on_abort_decision() -> None:
    provider = SucceedThenFailProvider()
    engine = RetrievalEngine([provider], StubPolicy(RecoveryDecision.abort("halt")))
    outcome = engine.retrieve_paginated(RetrievalRequest(url="https://x"), AlwaysNext())
    assert outcome.aborted is True
    assert len(outcome.documents) == 1


def test_paginated_complete_when_strategy_exhausts() -> None:
    class OnePage:
        name = "one"

        def next_request(
            self, request: RetrievalRequest, document: Document
        ) -> RetrievalRequest | None:
            return None

    engine = RetrievalEngine([RecordingProvider()], StubPolicy(RecoveryDecision.skip()))
    outcome = engine.retrieve_paginated(RetrievalRequest(url="https://x"), OnePage())
    assert len(outcome.documents) == 1
    assert outcome.is_complete is True


def test_paginated_partial_decision_continues_without_document() -> None:
    class PartialThenStop:
        """Fails first page (partial), the strategy is not reached for it."""

        name = "p"

        def __init__(self) -> None:
            self.calls = 0

        def supports(self, request: RetrievalRequest) -> bool:
            return True

        def initialize(self) -> None:
            pass

        def dispose(self) -> None:
            pass

        def retrieve(self, request: RetrievalRequest) -> Document:
            self.calls += 1
            raise NetworkError("fail", url=request.url)

    engine = RetrievalEngine(
        [PartialThenStop()], StubPolicy(RecoveryDecision.partial("keep going"))
    )
    outcome = engine.retrieve_paginated(RetrievalRequest(url="https://x"), AlwaysNext())
    assert outcome.documents == ()
    assert outcome.aborted is False
