"""Explicit grid detector.

Geometry along one axis (the other axis is identical)::

    | margin.left | cell | gap_x[0] | cell | gap_x[1] | ... | cell | margin.right |

* With ``cell_width`` set, every cell is exactly that wide and the grid is
  anchored at the left margin; it must fit inside the usable span.
* Otherwise the usable span minus the gaps is split across the cells with
  ``start_i = floor(i * available / n)``. Cells differ by at most one pixel,
  the remainder pixels are spread deterministically, and there is no
  accumulated rounding drift: cells never overlap and never touch a gap pixel.

Rows and columns are 1-based; regions are ordered row by row, left to right.
"""

from __future__ import annotations

from ..config import GridDetection
from ..errors import DetectionError
from ..models import BBox, DetectionResult, DetectionWarning, Region


def axis_spans(
    length: int,
    count: int,
    margin_start: int,
    margin_end: int,
    gaps: int | list[int],
    cell: int | None,
    axis: str,
) -> tuple[list[tuple[int, int]], list[DetectionWarning]]:
    """Return ``count`` half-open ``(start, end)`` spans along one axis."""
    gap_list = gaps if isinstance(gaps, list) else [gaps] * (count - 1)
    usable = length - margin_start - margin_end
    total_gaps = sum(gap_list)
    warnings: list[DetectionWarning] = []
    if usable <= 0:
        raise DetectionError(
            f"{axis}: margins ({margin_start}+{margin_end}) leave no usable space in {length}px",
        )
    if cell is not None:
        needed = cell * count + total_gaps
        if needed > usable:
            raise DetectionError(
                f"{axis}: {count} cells of {cell}px plus {total_gaps}px of gaps need {needed}px "
                f"but only {usable}px are usable",
            )
        if needed < usable:
            warnings.append(
                DetectionWarning(
                    "grid-unused-space",
                    f"{axis}: {usable - needed}px after the last cell are not covered by any cell",
                )
            )
        sizes_start = [i * cell for i in range(count)]
        sizes_end = [s + cell for s in sizes_start]
    else:
        available = usable - total_gaps
        if available < count:
            raise DetectionError(
                f"{axis}: {count} cells and {total_gaps}px of gaps do not fit in {usable}px",
                hint="check rows/cols, gap and margin values against the image size",
            )
        sizes_start = [(i * available) // count for i in range(count)]
        sizes_end = [((i + 1) * available) // count for i in range(count)]
        if available % count:
            warnings.append(
                DetectionWarning(
                    "grid-uneven-cells",
                    f"{axis}: {available}px do not divide evenly into {count} cells; cell sizes differ by at most 1px",
                )
            )
    spans = []
    for i in range(count):
        offset = margin_start + sum(gap_list[:i])
        spans.append((offset + sizes_start[i], offset + sizes_end[i]))
    return spans, warnings


def detect_grid(image_size: tuple[int, int], cfg: GridDetection) -> DetectionResult:
    width, height = image_size
    xs, wx = axis_spans(width, cfg.cols, cfg.margins.left, cfg.margins.right, cfg.gap_x, cfg.cell_width, "x")
    ys, wy = axis_spans(height, cfg.rows, cfg.margins.top, cfg.margins.bottom, cfg.gap_y, cfg.cell_height, "y")
    excluded = {(r, c) for r, c in cfg.exclude}
    regions: list[Region] = []
    for r, (top, bottom) in enumerate(ys, start=1):
        for c, (left, right) in enumerate(xs, start=1):
            if (r, c) in excluded:
                continue
            box = BBox(left, top, right, bottom)
            regions.append(
                Region(
                    id=f"r{r:02d}c{c:02d}",
                    bbox=box,
                    index=len(regions) + 1,
                    row=r,
                    col=c,
                    area=box.area,
                )
            )
    return DetectionResult(
        detector="grid",
        image_size=image_size,
        regions=regions,
        warnings=wx + wy,
        details={"rows": cfg.rows, "cols": cfg.cols, "excluded": len(excluded), "explicit": True},
    )
