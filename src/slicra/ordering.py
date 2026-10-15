"""Stable reading order for free-form regions.

Regions are sorted by ``(top, left, bottom, right)``. Rows are then formed
greedily: a region joins the current row when its vertical center lies inside
the vertical span of the row's first region; otherwise it starts a new row.
Within a row, regions are ordered by ``(left, top, right, bottom)``. The
result is deterministic for identical input, and ``row``/``col`` (1-based) are
assigned from it.
"""

from __future__ import annotations

from dataclasses import replace

from .models import Region


def reading_order(regions: list[Region], prefix: str) -> list[Region]:
    pending = sorted(regions, key=lambda r: (r.bbox.top, r.bbox.left, r.bbox.bottom, r.bbox.right))
    rows: list[list[Region]] = []
    for region in pending:
        center = (region.bbox.top + region.bbox.bottom) / 2
        if rows:
            anchor = rows[-1][0].bbox
            if anchor.top <= center < anchor.bottom:
                rows[-1].append(region)
                continue
        rows.append([region])
    ordered: list[Region] = []
    for r, row in enumerate(rows, start=1):
        row.sort(key=lambda g: (g.bbox.left, g.bbox.top, g.bbox.right, g.bbox.bottom))
        for c, region in enumerate(row, start=1):
            index = len(ordered) + 1
            ordered.append(replace(region, id=region.id or f"{prefix}{index:03d}", index=index, row=r, col=c))
    return ordered
