"""Layer merging and origin tracking."""

from __future__ import annotations

from nexusai.infrastructure.config.merger import merge_sources
from nexusai.infrastructure.config.sources import DefaultsSource


def test_later_sources_win() -> None:
    merged = merge_sources([DefaultsSource({"level": "INFO"}), DefaultsSource({"level": "DEBUG"})])
    assert merged.values["level"] == "DEBUG"


def test_mappings_merge_recursively_rather_than_replacing() -> None:
    merged = merge_sources(
        [
            DefaultsSource({"logging": {"level": "INFO", "colorize": True}}),
            DefaultsSource({"logging": {"level": "DEBUG"}}),
        ]
    )
    # The higher layer changed one key; the sibling must survive.
    assert merged.values["logging"] == {"level": "DEBUG", "colorize": True}


def test_sequences_are_replaced_wholesale() -> None:
    # A partial override of a list has no unambiguous meaning, so it is not
    # attempted.
    merged = merge_sources(
        [DefaultsSource({"allowlist": ["a", "b"]}), DefaultsSource({"allowlist": ["c"]})]
    )
    assert merged.values["allowlist"] == ["c"]


def test_origin_names_the_layer_that_last_set_a_key() -> None:
    merged = merge_sources(
        [
            DefaultsSource({"logging": {"level": "INFO"}}),
            DefaultsSource({"logging": {"colorize": False}}),
        ]
    )
    assert merged.origin_of("logging.level") is not None
    assert merged.origin_of("logging.colorize") is not None


def test_origin_falls_back_to_the_nearest_configured_ancestor() -> None:
    merged = merge_sources([DefaultsSource({"logging": {"level": "INFO"}})])
    assert merged.origin_of("logging.console.colorize") == merged.origin_of("logging")


def test_an_unknown_key_has_no_origin() -> None:
    merged = merge_sources([DefaultsSource({"logging": {"level": "INFO"}})])
    assert merged.origin_of("storage.backend") is None


def test_a_mapping_replacing_a_scalar_still_tracks_its_origin() -> None:
    merged = merge_sources(
        [DefaultsSource({"logging": "INFO"}), DefaultsSource({"logging": {"level": "DEBUG"}})]
    )
    assert merged.values["logging"] == {"level": "DEBUG"}
    assert merged.origin_of("logging.level") is not None
