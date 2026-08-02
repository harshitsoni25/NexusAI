"""Pixel-level screenshot comparison using Pillow.

Given two PNG screenshots, this computes the fraction of pixels that differ and
produces a difference image highlighting the changed regions. The comparison is
deterministic for identical inputs, which is what makes it testable without a
browser: synthetic images with known differences yield known ratios.

Determinism across *runs* of a real browser is a separate, harder problem —
viewport, fonts, device scale and animation all introduce noise — so the
comparator reports a ratio and lets a configurable threshold decide significance,
rather than treating any non-zero pixel difference as a failure.
"""

from __future__ import annotations

from io import BytesIO

from nexusai.domain.model.visual import (
    VisualComparison,
    VisualStatus,
    classify_difference,
)


def compare_screenshots(
    baseline_png: bytes,
    current_png: bytes,
    *,
    warning_threshold: float = 0.01,
    fail_threshold: float = 0.10,
) -> tuple[VisualComparison, bytes | None]:
    """Compare two PNG screenshots, returning the result and a diff image.

    The difference ratio is the fraction of pixels whose value changed. Images of
    different sizes are reported as not comparable (and treated as a failure),
    rather than silently resized. When Pillow is unavailable, this raises, since a
    real comparison cannot be performed.
    """
    from PIL import Image, ImageChops

    baseline = Image.open(BytesIO(baseline_png)).convert("RGB")
    current = Image.open(BytesIO(current_png)).convert("RGB")

    if baseline.size != current.size:
        comparison = VisualComparison(
            difference_ratio=1.0,
            warning_threshold=warning_threshold,
            fail_threshold=fail_threshold,
            status=VisualStatus.FAIL,
            comparable=False,
        )
        return comparison, None

    diff = ImageChops.difference(baseline, current)
    bbox = diff.getbbox()
    if bbox is None:
        ratio = 0.0
    else:
        # Count changed pixels via the grayscale histogram: bucket 0 is unchanged
        # (zero difference), so everything above it is changed. This avoids the
        # deprecated per-pixel getdata() iteration.
        histogram = diff.convert("L").histogram()
        changed = sum(histogram[1:])
        ratio = changed / (diff.width * diff.height)

    diff_png: bytes | None = None
    if ratio > 0:
        buffer = BytesIO()
        diff.save(buffer, format="PNG")
        diff_png = buffer.getvalue()

    status = classify_difference(
        ratio, warning_threshold=warning_threshold, fail_threshold=fail_threshold
    )
    comparison = VisualComparison(
        difference_ratio=ratio,
        warning_threshold=warning_threshold,
        fail_threshold=fail_threshold,
        status=status,
    )
    return comparison, diff_png


class ScreenshotComparator:
    """A configured screenshot comparator."""

    def __init__(self, *, warning_threshold: float = 0.01, fail_threshold: float = 0.10) -> None:
        self._warning = warning_threshold
        self._fail = fail_threshold

    def compare(
        self, baseline_png: bytes, current_png: bytes
    ) -> tuple[VisualComparison, bytes | None]:
        """Compare two screenshots with this comparator's thresholds."""
        return compare_screenshots(
            baseline_png,
            current_png,
            warning_threshold=self._warning,
            fail_threshold=self._fail,
        )
