"""Visual comparison infrastructure: pixel-level screenshot diffing.

Holds the concrete screenshot comparator, which reads PNG bytes and computes a
difference ratio and a difference image. It depends on Pillow, an optional extra;
the domain visual models carry no such dependency.
"""

from __future__ import annotations

from nexusai.infrastructure.visual.comparator import (
    ScreenshotComparator,
    compare_screenshots,
)

__all__ = ["ScreenshotComparator", "compare_screenshots"]
