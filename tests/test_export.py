from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from slicra import ConfigError, ExportError, ImageSlicer

GRID = {"mode": "grid", "rows": 5, "cols": 5, "gap_x": 12, "gap_y": 12}


def slicer(**sections) -> ImageSlicer:
    return ImageSlicer.from_dict({"detection": GRID, **sections})


def test_png_keeps_alpha_and_jpeg_flattens_against_configured_color(grid_png: Path, tmp_path: Path) -> None:
    png = slicer(extraction={"shape": "circle"}).extract(grid_png, tmp_path / "png")
    with Image.open(png.outputs[0]) as im:
        assert im.mode == "RGBA" and im.getpixel((0, 0))[3] == 0

    jpg = slicer(extraction={"shape": "circle"}, output={"format": "jpeg", "background": "#102030"}).extract(
        grid_png, tmp_path / "jpg"
    )
    assert jpg.outputs[0].suffix == ".jpg"
    with Image.open(jpg.outputs[0]) as im:
        assert im.mode == "RGB"
        r, g, b = im.getpixel((0, 0))
        assert abs(r - 0x10) < 6 and abs(g - 0x20) < 6 and abs(b - 0x30) < 6
    assert any(w.code == "jpeg-flattened" for w in jpg.warnings)


def test_webp_output(grid_png: Path, tmp_path: Path) -> None:
    result = slicer(output={"format": "webp", "quality": 80}).extract(grid_png, tmp_path / "webp")
    with Image.open(result.outputs[0]) as im:
        assert im.format == "WEBP"


@pytest.mark.parametrize(
    "resize,expected_size",
    [
        ({"width": 64, "height": 32, "mode": "contain"}, (64, 32)),
        ({"width": 64, "height": 32, "mode": "cover"}, (64, 32)),
        ({"width": 64, "height": 32, "mode": "stretch"}, (64, 32)),
        ({"width": 60}, (60, 60)),
    ],
)
def test_resize_modes_sizes(grid_png: Path, resize, expected_size) -> None:
    [first, *_] = slicer(output={"resize": resize}).render(grid_png)
    assert first.image.size == expected_size


def test_contain_does_not_distort(tmp_path: Path) -> None:
    """A 200x100 red bar contained into 50x50 occupies 50x25 centered, the rest transparent."""
    image = Image.new("RGB", (200, 100), (255, 0, 0))
    cfg = {
        "detection": {"mode": "manual", "regions": [{"rect": [0, 0, 200, 100]}]},
        "output": {"resize": {"width": 50, "height": 50, "mode": "contain"}},
    }
    [item] = ImageSlicer.from_dict(cfg).render(image)
    alpha = item.image.getchannel("A")
    bbox = alpha.point(lambda v: 255 if v > 127 else 0).getbbox()
    assert bbox is not None and (bbox[2] - bbox[0], bbox[3] - bbox[1]) == (50, 25)
    assert alpha.getpixel((25, 2)) == 0
    stretched = ImageSlicer.from_dict(
        {**cfg, "output": {"resize": {"width": 50, "height": 50, "mode": "stretch"}}}
    ).render(image)[0]
    assert stretched.image.getchannel("A").getextrema() == (255, 255)
    cover = ImageSlicer.from_dict({**cfg, "output": {"resize": {"width": 50, "height": 50, "mode": "cover"}}}).render(
        image
    )[0]
    assert cover.image.getchannel("A").getextrema() == (255, 255)


def test_existing_outputs_require_overwrite(grid_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    slicer().extract(grid_png, out)
    before = (out / "region_001.png").stat().st_mtime_ns
    with pytest.raises(ExportError, match="already exist"):
        slicer().extract(grid_png, out)
    assert (out / "region_001.png").stat().st_mtime_ns == before
    slicer().extract(grid_png, out, overwrite=True)


@pytest.mark.parametrize("pattern", ["../x_{index}", "a/{index}", "{index}{bogus}", "constant", "{index:q}"])
def test_unsafe_or_invalid_naming_rejected(grid_png: Path, tmp_path: Path, pattern: str) -> None:
    with pytest.raises((ConfigError, ExportError)):
        slicer(output={"naming": pattern}).extract(grid_png, tmp_path / "out")
    assert not any((tmp_path / "out").glob("*.png")) if (tmp_path / "out").exists() else True


def test_duplicate_names_fail_before_writing(grid_png: Path, tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="duplicate"):
        slicer(output={"naming": "row{row}"}).extract(grid_png, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_row_naming_unavailable_for_free_regions(shapes_png: Path, tmp_path: Path) -> None:
    cfg = {"detection": {"mode": "manual", "regions": [{"rect": [0, 0, 10, 10]}]}, "output": {"naming": "{row}"}}
    with pytest.raises(ConfigError, match="row"):
        ImageSlicer.from_dict(cfg).extract(shapes_png, tmp_path / "out")


def test_manifest_reflects_outputs_and_config(grid_png: Path, tmp_path: Path) -> None:
    result = slicer(output={"naming": "a_{row}_{col}"}).extract(grid_png, tmp_path / "out")
    manifest = json.loads(result.manifest_path.read_text())
    on_disk = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert sorted(manifest["files"]) == on_disk
    assert manifest["region_count"] == 25 == len(manifest["regions"])
    assert manifest["config"]["output"]["naming"] == "a_{row}_{col}"
    assert manifest["config"]["detection"]["gap_x"] == 12
    assert manifest["source"]["width"] == 648 and manifest["schema_version"] == 1
    first = manifest["regions"][0]
    assert first["output"] == "a_1_1.png" and first["bbox"] == [0, 0, 120, 120] and first["shape"] == "rectangle"
    assert manifest["detector"]["mode"] == "grid"


def test_input_image_is_never_overwritten(grid_png: Path) -> None:
    original = grid_png.read_bytes()
    with pytest.raises(ExportError):
        slicer(output={"naming": "grid{index}"}, manifest={"filename": "grid.png"}).extract(
            grid_png, grid_png.parent, overwrite=True
        )
    assert grid_png.read_bytes() == original


def test_preview_and_manifest_can_be_disabled(grid_png: Path, tmp_path: Path) -> None:
    result = slicer(preview={"enabled": False}, manifest={"enabled": False}).extract(grid_png, tmp_path / "o")
    assert result.manifest_path is None and result.preview_path is None
    assert len(list((tmp_path / "o").iterdir())) == 25
