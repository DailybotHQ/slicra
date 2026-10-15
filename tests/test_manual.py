from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from slicra import ConfigError, DetectionError, ImageSlicer

TRIANGLE = [[470, 270], [560, 80], [610, 270]]


def _inside_triangle(x: float, y: float) -> bool:
    (x1, y1), (x2, y2), (x3, y3) = TRIANGLE

    def sign(ax, ay, bx, by, cx, cy):
        return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy)

    d1, d2, d3 = sign(x, y, x1, y1, x2, y2), sign(x, y, x2, y2, x3, y3), sign(x, y, x3, y3, x1, y1)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def test_manual_polygon_exports_with_correct_coordinates(shapes_png: Path, tmp_path: Path) -> None:
    slicer = ImageSlicer.from_dict(
        {
            "detection": {"mode": "manual", "regions": [{"id": "tri", "polygon": TRIANGLE}]},
            "extraction": {"shape": "original", "antialias": False},
            "output": {"naming": "{id}"},
        }
    )
    result = slicer.extract(shapes_png, tmp_path / "out")
    assert result.regions[0].bbox.as_tuple() == (470, 80, 610, 270)
    out = result.outputs[0]
    assert out.name == "tri.png"
    with Image.open(out) as im:
        alpha = im.getchannel("A")
        mismatches = 0
        for y in range(im.height):
            for x in range(im.width):
                sx, sy = x + 470 + 0.5, y + 80 + 0.5
                if abs(sx - 560) < 2 and sy < 85:  # skip the apex pixel ambiguity
                    continue
                inside = _inside_triangle(sx, sy)
                if (alpha.getpixel((x, y)) > 0) != inside:
                    mismatches += 1
        # only boundary pixels may disagree (rasterization rule), never the interior
        assert mismatches < 2 * (im.width + im.height)
        assert alpha.getpixel((90, 150)) == 255  # inside
        assert alpha.getpixel((5, 5)) == 0  # outside, top-left corner of bbox


def test_mixed_shapes_on_one_sheet(shapes_png: Path, tmp_path: Path) -> None:
    config = Path(__file__).resolve().parents[1] / "examples" / "configs" / "manual-shapes.yaml"
    slicer = ImageSlicer.from_config(config, {"input": {"path": str(shapes_png)}})
    result = slicer.extract(output_dir=tmp_path / "out")
    assert [p.name for p in result.outputs] == ["oval.png", "star.png", "triangle.png"]
    with Image.open(result.outputs[1]) as star:
        assert star.getchannel("A").getpixel((star.width // 2, star.height // 2)) == 255
        assert star.getchannel("A").getpixel((5, star.height - 5)) == 0


def test_out_of_bounds_error_and_clip(shapes_png: Path) -> None:
    region = {"id": "big", "rect": [600, 300, 700, 400]}
    with pytest.raises(DetectionError, match="outside"):
        ImageSlicer.from_dict({"detection": {"mode": "manual", "regions": [region]}}).detect(shapes_png)
    clipped = ImageSlicer.from_dict(
        {"detection": {"mode": "manual", "regions": [region], "out_of_bounds": "clip"}}
    ).detect(shapes_png)
    assert clipped.regions[0].bbox.as_tuple() == (600, 300, 640, 360)
    assert clipped.warnings[0].code == "region-clipped"


def test_overlap_policy(shapes_png: Path) -> None:
    regions = [{"rect": [0, 0, 100, 100]}, {"rect": [50, 50, 150, 150]}]
    warned = ImageSlicer.from_dict({"detection": {"mode": "manual", "regions": regions}}).detect(shapes_png)
    assert any(w.code == "regions-overlap" for w in warned.warnings)
    assert [r.id for r in warned.regions] == ["m001", "m002"]
    with pytest.raises(DetectionError):
        ImageSlicer.from_dict({"detection": {"mode": "manual", "regions": regions, "overlap": "error"}}).detect(
            shapes_png
        )


def test_regions_file_json(shapes_png: Path, tmp_path: Path) -> None:
    file = tmp_path / "regions.json"
    file.write_text(json.dumps({"regions": [{"id": "a", "rect": [0, 0, 10, 10]}]}))
    result = ImageSlicer.from_dict({"detection": {"mode": "manual", "regions_file": str(file)}}).detect(shapes_png)
    assert result.regions[0].id == "a"


@pytest.mark.parametrize(
    "regions",
    [
        [{"rect": [10, 10, 5, 20]}],
        [{"polygon": [[0, 0], [10, 10], [20, 20]]}],
        [{"polygon": [[0, 0], [10, 0]]}],
        [{"rect": [0, 0, 5, 5], "polygon": [[0, 0], [5, 0], [0, 5]]}],
        [{"id": "x", "rect": [0, 0, 5, 5]}, {"id": "x", "rect": [5, 5, 9, 9]}],
        [{"id": "../evil", "rect": [0, 0, 5, 5]}],
    ],
)
def test_invalid_manual_regions(regions) -> None:
    with pytest.raises(ConfigError):
        ImageSlicer.from_dict({"detection": {"mode": "manual", "regions": regions}})
