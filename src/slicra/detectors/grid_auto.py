"""Infer a grid from separator rows/columns of near-uniform background.

Algorithm (Pillow only, deterministic):

1. Estimate the background from the image border (or use the configured one).
   When the border is not uniform (no outer margin), every color of a
   full-length uniform row/column is a candidate; the candidate that yields
   the most regular grid with the most cells wins.
2. Build a binary foreground mask: pixels differing from the background by more
   than ``tolerance`` on any channel (or with alpha above the threshold).
3. Project the mask onto each axis; a column/row whose foreground fraction is
   at most ``max_separator_fill`` is a separator candidate.
4. Content bands are runs of non-separator lines. Separator runs narrower than
   ``min_gap`` are absorbed into content; content bands narrower than
   ``min_cell_size`` are dropped with a warning.
5. Every row band x column band is a cell; empty cells are skipped (with a
   warning) when ``skip_empty`` is set. With ``silhouette`` each tile gets a
   rounded-rectangle mask whose radius is measured on its corners.

The detector refuses to guess: no separators means an error, and irregular
band sizes or a mismatch with expected ``rows``/``cols`` are reported instead
of being silently "fixed".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev

from PIL import Image, ImageDraw

from ..background import (
    column_profile,
    estimate_background,
    foreground_mask,
    fraction_on,
    row_profile,
    uniform_line_colors,
)
from ..config import GridAutoDetection, RGBColor
from ..errors import DetectionError
from ..models import BBox, DetectionResult, DetectionWarning, Region

EMPTY_CELL_FILL = 0.01


def content_bands(
    profile: list[float], max_fill: float, min_gap: int, min_size: int, axis: str
) -> tuple[list[tuple[int, int]], list[DetectionWarning]]:
    is_content = [v > max_fill for v in profile]
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate([*is_content, False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i))
            start = None
    merged: list[tuple[int, int]] = []
    for run in runs:
        if merged and run[0] - merged[-1][1] < min_gap:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(run)
    warnings: list[DetectionWarning] = []
    kept = [r for r in merged if r[1] - r[0] >= min_size]
    if len(kept) != len(merged):
        warnings.append(
            DetectionWarning(
                "grid-auto-small-band",
                f"{axis}: ignored {len(merged) - len(kept)} content band(s) narrower than {min_size}px",
            )
        )
    return kept, warnings


def _variation(sizes: list[int]) -> float:
    return pstdev(sizes) / mean(sizes) if len(sizes) > 1 else 0.0


@dataclass
class _Bands:
    background: str | RGBColor
    uniformity: float
    source: str
    mask: Image.Image
    rows: list[tuple[int, int]]
    cols: list[tuple[int, int]]
    warnings: list[DetectionWarning]

    @property
    def variation(self) -> float:
        return max(
            _variation([b - a for a, b in self.cols]) if self.cols else 0.0,
            _variation([b - a for a, b in self.rows]) if self.rows else 0.0,
        )


def _bands(
    image: Image.Image, background: str | RGBColor, uniformity: float, source: str, cfg: GridAutoDetection
) -> _Bands:
    mask = foreground_mask(image, background, cfg.tolerance)
    cols, wx = content_bands(column_profile(mask), cfg.max_separator_fill, cfg.min_gap, cfg.min_cell_size, "x")
    rows, wy = content_bands(row_profile(mask), cfg.max_separator_fill, cfg.min_gap, cfg.min_cell_size, "y")
    return _Bands(background, uniformity, source, mask, rows, cols, wx + wy)


def corner_radius(mask: Image.Image) -> int:
    """Estimate the corner radius of a (rounded) rectangular tile from its binary mask.

    Along each corner's diagonal, the background gap before the first foreground pixel is
    ``r * (1 - 1/sqrt(2))`` for a circular corner of radius ``r``. The smallest of the four
    corners is used: content that happens to match the background (a white shirt touching
    a corner) can only make a corner look *more* rounded, never less.
    """
    w, h = mask.size
    limit = min(w, h) // 2
    corners = ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1))
    radii = []
    for x0, y0, dx, dy in corners:
        gap = next((i for i in range(limit) if mask.getpixel((x0 + dx * i, y0 + dy * i))), limit)
        radii.append(round(gap / (1 - 1 / math.sqrt(2))))
    return min(min(radii), limit)


def tile_silhouette(size: tuple[int, int], radius: int, supersample: int = 4) -> Image.Image:
    """Anti-aliased rounded-rectangle mask covering the whole tile."""
    w, h = size
    if radius <= 0:
        return Image.new("L", size, 255)
    big = Image.new("L", (w * supersample, h * supersample), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * supersample - 1, h * supersample - 1), radius=radius * supersample, fill=255
    )
    return big.resize(size, Image.Resampling.BOX)


def detect_grid_auto(image: Image.Image, cfg: GridAutoDetection) -> DetectionResult:
    warnings: list[DetectionWarning] = []
    candidates: list[tuple[str | RGBColor, float, str]] = []
    if cfg.background == "auto":
        border, uniformity = estimate_background(image, cfg.tolerance)
        candidates.append((border, uniformity, "border"))
        if uniformity < 0.9:
            candidates += [(c, 0.95, "separator-lines") for c in uniform_line_colors(image, cfg.tolerance)[:6]]
    else:
        candidates.append((cfg.background, 1.0, "config"))

    best: tuple[float, _Bands] | None = None
    for background, uniformity, source in candidates:
        bands = _bands(image, background, uniformity, source, cfg)
        if len(bands.rows) * len(bands.cols) <= 1:
            continue
        quality = len(bands.rows) * len(bands.cols) * max(0.05, 1.0 - 2.0 * bands.variation) * uniformity
        if best is None or quality > best[0]:
            best = (quality, bands)
    if best is None:
        bands = _bands(image, *candidates[0], cfg)
        found = f"found {len(bands.rows)} row band(s) x {len(bands.cols)} column band(s)"
        if not bands.rows or not bands.cols:
            raise DetectionError(
                f"grid-auto: no content found against background {bands.background} ({found})",
                hint="set detection.background explicitly or lower detection.tolerance",
            )
        raise DetectionError(
            f"grid-auto: no separators detected ({found})",
            hint="use mode 'grid' with explicit rows/cols/gaps, or set detection.background",
        )
    bands = best[1]
    background, uniformity, mask, rows, cols = bands.background, bands.uniformity, bands.mask, bands.rows, bands.cols
    warnings += bands.warnings
    if uniformity < 0.9:
        warnings.append(
            DetectionWarning(
                "background-not-uniform",
                f"only {uniformity:.0%} of border pixels match the estimated background {background}",
            )
        )
    found = f"found {len(rows)} row band(s) x {len(cols)} column band(s)"
    if (cfg.rows is not None and cfg.rows != len(rows)) or (cfg.cols is not None and cfg.cols != len(cols)):
        raise DetectionError(
            f"grid-auto: expected {cfg.rows or '?'} rows x {cfg.cols or '?'} cols but {found}",
            hint="inspect the preview; adjust tolerance/max_separator_fill or switch to mode 'grid'",
        )

    widths = [b - a for a, b in cols]
    heights = [b - a for a, b in rows]
    variation = bands.variation
    if variation > 0.15:
        warnings.append(
            DetectionWarning(
                "grid-auto-irregular",
                f"band sizes vary by {variation:.0%} (widths {widths}, heights {heights}); "
                "the layout may not be a regular grid",
            )
        )

    regions: list[Region] = []
    empty = 0
    for r, (top, bottom) in enumerate(rows, start=1):
        for c, (left, right) in enumerate(cols, start=1):
            box = BBox(left, top, right, bottom)
            cell_mask = mask.crop(box.as_tuple())
            fill = fraction_on(cell_mask)
            if fill < EMPTY_CELL_FILL:
                empty += 1
                if cfg.skip_empty:
                    continue
            silhouette = tile_silhouette((box.width, box.height), corner_radius(cell_mask)) if cfg.silhouette else None
            regions.append(
                Region(
                    id=f"r{r:02d}c{c:02d}",
                    bbox=box,
                    index=len(regions) + 1,
                    row=r,
                    col=c,
                    area=box.area,
                    score=round(fill, 4),
                    mask=silhouette,
                )
            )
    if empty:
        verb = "skipped" if cfg.skip_empty else "kept"
        warnings.append(DetectionWarning("grid-auto-empty-cells", f"{verb} {empty} empty cell(s)"))

    score = max(0.0, 1.0 - 2.0 * variation) * uniformity
    return DetectionResult(
        detector="grid-auto",
        image_size=image.size,
        regions=regions,
        warnings=warnings,
        score=round(score, 4),
        details={
            "rows": len(rows),
            "cols": len(cols),
            "background": background if isinstance(background, str) else list(background),
            "background_source": bands.source,
            "mean_fill": round(sum(r.score or 0.0 for r in regions) / len(regions), 4) if regions else 0.0,
            "row_bands": [list(b) for b in rows],
            "col_bands": [list(b) for b in cols],
            "empty_cells": empty,
        },
    )
