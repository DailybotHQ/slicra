from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from slicra import ConfigError, ImageSlicer
from slicra.masks import ShapeSpec, build_mask
from slicra.models import BBox, Region

from .conftest import pixels

REGION = Region(id="r", bbox=BBox(0, 0, 100, 60))


def mask(shape: str, **kw) -> Image.Image:
    return build_mask(ShapeSpec(shape=shape, **kw), REGION, REGION.bbox)


def test_rectangle_keeps_every_pixel() -> None:
    assert mask("rectangle").getextrema() == (255, 255)


def test_ellipse_inside_and_antialiased_edges() -> None:
    m = mask("ellipse")
    assert m.getpixel((50, 30)) == 255 and m.getpixel((0, 0)) == 0
    assert any(0 < v < 255 for v in pixels(m)), "antialias produces partial alpha"
    hard = mask("ellipse", antialias=False)
    assert set(pixels(hard)) <= {0, 255}


def test_circle_contain_is_round_inside_rectangular_box() -> None:
    m = mask("circle")
    assert m.size == (100, 60)
    assert m.getpixel((50, 30)) == 255
    assert m.getpixel((15, 30)) == 0, "outside the 60px circle centered horizontally"


def test_star_points_rotation_and_validation() -> None:
    m = mask("star")
    assert m.getpixel((50, 30)) == 255
    assert m.getpixel((50, 1)) > 0, "first tip points up"
    assert m.getpixel((5, 55)) == 0
    from slicra.config import StarOptions

    with pytest.raises(ValueError):
        StarOptions(points=2)


def test_polygon_without_vertices_is_rejected() -> None:
    with pytest.raises(ConfigError, match="does not guess"):
        mask("polygon")
    with pytest.raises(ConfigError):
        ImageSlicer.from_dict({"detection": {"mode": "grid", "rows": 1, "cols": 1}, "extraction": {"shape": "polygon"}})


def test_relative_polygon_and_inset() -> None:
    m = mask("polygon", polygon_points=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)))
    assert m.getpixel((5, 5)) == 255 and m.getpixel((95, 55)) == 0
    inset = mask("rectangle", shape_inset=10)
    assert inset.getpixel((5, 5)) == 0 and inset.getpixel((50, 30)) == 255
    with pytest.raises(ConfigError):
        mask("rectangle", shape_inset=40)


def test_original_without_geometry_equals_bbox_rectangle() -> None:
    padded = BBox(0, 0, 100, 60)
    region = Region(id="r", bbox=BBox(10, 10, 90, 50))
    m = build_mask(ShapeSpec(shape="original"), region, padded)
    assert m.getpixel((5, 5)) == 0 and m.getpixel((50, 30)) == 255


@pytest.mark.parametrize("shape", ["circle", "star", "ellipse"])
def test_rectangular_detection_exported_with_other_shapes(grid_png: Path, tmp_path: Path, shape: str) -> None:
    """Acceptance 5: a rectangular grid cell can be exported as a circle or a star."""
    slicer = ImageSlicer.from_dict(
        {"detection": {"mode": "grid", "rows": 5, "cols": 5, "gap_x": 12, "gap_y": 12}, "extraction": {"shape": shape}}
    )
    result = slicer.extract(grid_png, tmp_path / shape)
    with Image.open(result.outputs[0]) as im:
        alpha = im.getchannel("A")
        assert alpha.getpixel((60, 60)) == 255
        assert alpha.getpixel((1, 1)) == 0
        assert alpha.getpixel((1, 118)) == 0


def test_center_square_circle_yields_square_output(tmp_path: Path) -> None:
    image = Image.new("RGB", (300, 100), (10, 120, 200))
    slicer = ImageSlicer.from_dict(
        {
            "detection": {"mode": "manual", "regions": [{"rect": [0, 0, 300, 100]}]},
            "extraction": {"shape": "circle", "circle_fit": "center-square"},
        }
    )
    [item] = slicer.render(image)
    assert item.image.size == (100, 100)
    assert item.crop_box.as_tuple() == (100, 0, 200, 100)
