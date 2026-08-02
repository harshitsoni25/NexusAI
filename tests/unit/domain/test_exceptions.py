"""The exception hierarchy."""

from __future__ import annotations

import pytest

from nexusai.domain.errors import (
    AcquisitionError,
    ConfigurationError,
    ErrorCategory,
    HttpStatusError,
    InternalError,
    NetworkError,
    NexusAIError,
    PluginContractError,
    PluginError,
    TransactionError,
)


def test_context_is_rendered_in_the_message() -> None:
    error = ConfigurationError("Bad key", key="logging.level", source="env")
    assert "Bad key" in str(error)
    assert "key='logging.level'" in str(error)


def test_a_message_without_context_stands_alone() -> None:
    assert str(ConfigurationError("Bad key")) == "Bad key"


def test_an_already_formatted_message_is_not_repeated_back() -> None:
    # Configuration errors compose a multi-line report; appending the context
    # would print the same keys twice.
    error = ConfigurationError("Invalid:\n  - logging.level: bad", invalid_keys=("logging.level",))
    assert str(error) == "Invalid:\n  - logging.level: bad"
    assert error.context["invalid_keys"] == ("logging.level",)


def test_every_error_reports_a_category() -> None:
    assert ConfigurationError("x").category is ErrorCategory.CONFIGURATION
    assert AcquisitionError("x").category is ErrorCategory.ACQUISITION
    assert InternalError("x").category is ErrorCategory.INTERNAL


def test_transient_failures_are_marked_retryable_by_type() -> None:
    # Retryability is a property of the type so that one retry policy can be
    # applied consistently, and tested once.
    assert NetworkError("x").retryable is True
    assert ConfigurationError("x").retryable is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [(429, True), (500, True), (503, True), (400, False), (404, False), (200, False)],
)
def test_http_retryability_depends_on_the_status_class(status: int, expected: bool) -> None:
    assert HttpStatusError("failed", status_code=status).retryable is expected


def test_subclasses_inherit_their_parent_category() -> None:
    assert TransactionError("x").category is ErrorCategory.STORAGE
    assert PluginContractError("x").category is ErrorCategory.PLUGIN


def test_everything_derives_from_the_framework_base() -> None:
    # Callers need one except clause that reliably catches framework failures
    # and reliably does not catch anything else.
    for error_type in (ConfigurationError, NetworkError, PluginError, InternalError):
        assert issubclass(error_type, NexusAIError)


def test_serialisation_carries_what_a_report_needs() -> None:
    payload = HttpStatusError("failed", status_code=503, url="https://example.test").to_dict()
    assert payload == {
        "type": "HttpStatusError",
        "category": "acquisition",
        "message": "failed",
        "retryable": True,
        "context": {"status_code": 503, "url": "https://example.test"},
    }


def test_chaining_preserves_the_original_traceback() -> None:
    with pytest.raises(ConfigurationError) as caught:
        try:
            raise OSError("disk gone")
        except OSError as exc:
            raise ConfigurationError("Could not read config") from exc
    assert isinstance(caught.value.__cause__, OSError)


def test_repr_round_trips_the_context() -> None:
    assert repr(ConfigurationError("x", key="a")) == "ConfigurationError('x', **{'key': 'a'})"
