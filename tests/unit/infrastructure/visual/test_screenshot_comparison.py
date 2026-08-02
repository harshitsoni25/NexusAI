"""Visual comparison verified deterministically with synthetic screenshots."""

from __future__ import annotations

from io import BytesIO

import pytest

pytest.importorskip("PIL")

from nexusai.domain.model.visual import VisualStatus
from nexusai.infrastructure.visual import (
    ScreenshotComparator,
    compare_screenshots,
)


def _png(color: tuple[int, int, int], size: tuple[int, int] = (100, 100)) -> bytes:
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _half_and_half(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> bytes:
    from PIL import Image

    image = Image.new("RGB", (100, 100), top)
    for y in range(50, 100):
        for x in range(100):
            image.putpixel((x, y), bottom)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class TestComparison:
    def test_identical_images_pass_with_zero_difference(self) -> None:
        white = _png((255, 255, 255))
        comparison, diff = compare_screenshots(white, white)
        assert comparison.difference_ratio == 0.0
        assert comparison.status is VisualStatus.PASS
        assert diff is None

    def test_completely_different_images_fail(self) -> None:
        comparison, diff = compare_screenshots(_png((0, 0, 0)), _png((255, 255, 255)))
        assert comparison.difference_ratio == pytest.approx(1.0)
        assert comparison.status is VisualStatus.FAIL
        assert diff is not None

    def test_half_changed_image_ratio_is_about_half(self) -> None:
        baseline = _png((255, 255, 255))
        current = _half_and_half((255, 255, 255), (0, 0, 0))
        comparison, _ = compare_screenshots(baseline, current)
        assert comparison.difference_ratio == pytest.approx(0.5, abs=0.01)
        assert comparison.status is VisualStatus.FAIL

    def test_small_change_warns_not_fails(self) -> None:
        from PIL import Image

        base = Image.new("RGB", (100, 100), (255, 255, 255))
        cur = base.copy()
        for x in range(100):
            for y in range(3):
                cur.putpixel((x, y), (0, 0, 0))  # 3% of rows changed
        b, c = BytesIO(), BytesIO()
        base.save(b, format="PNG")
        cur.save(c, format="PNG")
        comparison, _ = compare_screenshots(
            b.getvalue(), c.getvalue(), warning_threshold=0.01, fail_threshold=0.10
        )
        assert comparison.status is VisualStatus.WARNING

    def test_different_sizes_are_not_comparable(self) -> None:
        comparison, _diff = compare_screenshots(
            _png((0, 0, 0), (100, 100)), _png((0, 0, 0), (50, 50))
        )
        assert comparison.comparable is False
        assert comparison.status is VisualStatus.FAIL

    def test_comparator_thresholds_apply(self) -> None:
        comparator = ScreenshotComparator(warning_threshold=0.4, fail_threshold=0.9)
        comparison, _ = comparator.compare(
            _png((255, 255, 255)), _half_and_half((255, 255, 255), (0, 0, 0))
        )
        assert comparison.status is VisualStatus.WARNING  # 0.5 is between 0.4 and 0.9
