from __future__ import annotations

import itertools
from pathlib import Path

import pytest
from PIL import Image

from slicra import ConfigError, DetectionError, ImageSlicer
from slicra.config import GridDetection
from slicra.detectors.grid import detect_grid

from .conftest import MAGENTA, count_color


def grid_cfg(**kw):
    base = {"mode": "grid", "rows": 5, "cols": 5, "gap_x": 12, "gap_y": 12}
    base.update(kw)
    return GridDetection.model_validate(base)


def test_5x5_exports_exactly_25_without_separator_pixels(grid_png: Path, tmp_path: Path, fixtures) -> None:
    slicer = ImageSlicer.from_dict(
        {
            "detection": {"mode": "grid", "rows": 5, "cols": 5, "gap_x": 12, "gap_y": 12},
            "output": {"naming": "avatar_{index:03d}"},
        }
    )
    result = slicer.extract(grid_png, tmp_path / "out")
    assert result.region_count == 25
    names = sorted(p.name for p in result.outputs)
    assert names == [f"avatar_{i:03d}.png" for i in range(1, 26)]
    for i, path in enumerate(result.outputs):
        with Image.open(path) as im:
            assert im.size == (120, 120)
            assert count_color(im, MAGENTA) == 0, f"{path.name} contains separator pixels"
            # stable row-major order: the tile background color identifies the cell
            assert im.convert("RGB").getpixel((2, 2)) == fixtures.AVATAR_PALETTE[i]


def test_ids_rows_cols_are_row_major() -> None:
    result = detect_grid((648, 648), grid_cfg())
    assert [(r.row, r.col) for r in result.regions[:6]] == [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (2, 1)]
    assert result.regions[0].id == "r01c01" and result.regions[-1].id == "r05c05"
    assert [r.index for r in result.regions] == list(range(1, 26))


def _gap_spans(spans):
    return [(a[1], b[0]) for a, b in itertools.pairwise(spans)]


def test_3x7_asymmetric_margins_non_divisible_never_overlap_or_escape() -> None:
    width, height = 1003, 701
    cfg = grid_cfg(rows=3, cols=7, gap_x=9, gap_y=4, margins={"left": 5, "top": 7, "right": 11, "bottom": 3})
    result = detect_grid((width, height), cfg)
    assert result.region_count == 21
    boxes = [r.bbox for r in result.regions]
    for box in boxes:
        assert 5 <= box.left < box.right <= width - 11
        assert 7 <= box.top < box.bottom <= height - 3
    for a, b in itertools.combinations(boxes, 2):
        assert not a.intersects(b)
    xs = sorted({(b.left, b.right) for b in boxes})
    ys = sorted({(b.top, b.bottom) for b in boxes})
    assert all(g[1] - g[0] == 9 for g in _gap_spans(xs)), "every column gap is exactly gap_x"
    assert all(g[1] - g[0] == 4 for g in _gap_spans(ys))
    # cells cover the whole usable span except the gaps: no drift, no lost pixels
    assert sum(hi - lo for lo, hi in xs) == (width - 16) - 6 * 9
    assert max(hi - lo for lo, hi in xs) - min(hi - lo for lo, hi in xs) <= 1
    assert any(w.code == "grid-uneven-cells" for w in result.warnings)


@pytest.mark.parametrize("size", [(97, 61), (500, 333), (1254, 1254), (31, 1999)])
@pytest.mark.parametrize("rows,cols,gap", [(1, 1, 0), (2, 3, 1), (5, 5, 3), (7, 2, 0)])
def test_grid_invariants_across_sizes(size, rows, cols, gap) -> None:
    result = detect_grid(size, grid_cfg(rows=rows, cols=cols, gap_x=gap, gap_y=gap))
    boxes = [r.bbox for r in result.regions]
    assert len(boxes) == rows * cols
    for a, b in itertools.combinations(boxes, 2):
        assert not a.intersects(b)
    assert all(b.left >= 0 and b.right <= size[0] and b.top >= 0 and b.bottom <= size[1] for b in boxes)


def test_per_gap_lists_and_explicit_cells() -> None:
    cfg = grid_cfg(rows=1, cols=3, gap_x=[2, 10], gap_y=0, cell_width=20, cell_height=30)
    result = detect_grid((100, 30), cfg)
    assert [r.bbox.as_tuple() for r in result.regions] == [(0, 0, 20, 30), (22, 0, 42, 30), (52, 0, 72, 30)]
    assert any(w.code == "grid-unused-space" for w in result.warnings)


def test_exclude_cells() -> None:
    result = detect_grid((648, 648), grid_cfg(exclude=[(1, 1), (5, 5)]))
    assert result.region_count == 23
    assert result.regions[0].id == "r01c02" and result.regions[0].index == 1


@pytest.mark.parametrize(
    "kw,size",
    [
        ({"margins": {"left": 400, "right": 400}}, (648, 648)),
        ({"cell_width": 200}, (648, 648)),
        ({"gap_x": 200}, (648, 648)),
    ],
)
def test_impossible_geometry_fails_explicitly(kw, size) -> None:
    with pytest.raises(DetectionError):
        detect_grid(size, grid_cfg(**kw))


@pytest.mark.parametrize(
    "detection",
    [
        {"mode": "grid", "rows": 0, "cols": 5},
        {"mode": "grid", "rows": 2, "cols": 2, "gap_x": -1},
        {"mode": "grid", "rows": 2, "cols": 3, "gap_x": [1]},
        {"mode": "grid", "rows": 2, "cols": 2, "exclude": [[3, 1]]},
        {"mode": "grid", "rows": 2, "cols": 2, "bogus": 1},
    ],
)
def test_invalid_grid_config(detection) -> None:
    with pytest.raises(ConfigError):
        ImageSlicer.from_dict({"detection": detection})
