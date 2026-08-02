"""The single place where framework errors become exit codes."""

from __future__ import annotations

import pytest

from nexusai.domain.errors import ConfigurationError, StorageError
from nexusai.presentation.cli.exit_codes import ExitCode
from nexusai.presentation.cli.rendering.console import error_boundary


def test_a_framework_error_becomes_an_exit_code() -> None:
    with pytest.raises(SystemExit) as caught, error_boundary():
        raise ConfigurationError("bad key", key="logging.level")
    assert caught.value.code == int(ExitCode.CONFIGURATION_ERROR)


def test_a_storage_error_exits_with_the_generic_failure_code() -> None:
    with pytest.raises(SystemExit) as caught, error_boundary():
        raise StorageError("disk full")
    assert caught.value.code == int(ExitCode.FAILURE)


def test_an_unexpected_exception_keeps_its_traceback() -> None:
    # A stack trace is exactly what is wanted when the framework itself has a
    # defect, and section 41 forbids swallowing it.
    with pytest.raises(ZeroDivisionError), error_boundary():
        _ = 1 / 0


def test_success_passes_through_untouched() -> None:
    with error_boundary():
        pass
