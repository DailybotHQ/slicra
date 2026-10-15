from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import generate_fixtures as fx  # noqa: E402

MAGENTA = (255, 0, 255)


@pytest.fixture
def fixtures():
    return fx


@pytest.fixture
def grid_png(tmp_path: Path) -> Path:
    """5x5 grid, 120px cells, 12px gaps, magenta separators (a color no tile uses)."""
    path = tmp_path / "grid.png"
    fx.avatars_grid(separator=MAGENTA).save(path)
    return path


@pytest.fixture
def shapes_png(tmp_path: Path) -> Path:
    path = tmp_path / "shapes.png"
    fx.shapes_sheet().save(path)
    return path


@pytest.fixture
def shapes_transparent_png(tmp_path: Path) -> Path:
    path = tmp_path / "shapes-transparent.png"
    fx.shapes_sheet(transparent=True).save(path)
    return path


def pixels(image: Image.Image) -> list:
    getter = getattr(image, "get_flattened_data", None)
    return list(getter() if getter is not None else image.getdata())


def count_color(image: Image.Image, color: tuple[int, int, int]) -> int:
    return sum(1 for px in pixels(image.convert("RGB")) if px == color)
