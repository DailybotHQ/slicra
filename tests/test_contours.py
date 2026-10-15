from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from slicra import ImageSlicer, NoRegionsError
from slicra.config import ContoursDetection
from slicra.detectors.contours import detect_contours

pytest.importorskip("cv2")

EXACT = {"mode": "contours", "background": "auto", "min_area": 400, "morphology": {"open": 0, "close": 0}}


def _silhouette_matches(output: Path, source: Image.Image, crop_box: list[int], is_fg) -> float:
    """Fraction of crop pixels where (alpha > 0) agrees with the source foreground test."""
    with Image.open(output) as out:
        alpha = out.getchannel("A")
        left, top, right, bottom = crop_box
        agree = total = 0
        for y in range(top, bottom):
            for x in range(left, right):
                total += 1
                agree += (alpha.getpixel((x - left, y - top)) > 0) == is_fg(source.getpixel((x, y)))
        return agree / total


@pytest.mark.parametrize("variant", ["uniform", "transparent"])
def test_star_oval_triangle_become_three_masked_regions(tmp_path: Path, fixtures, variant: str) -> None:
    transparent = variant == "transparent"
    source = fixtures.shapes_sheet(transparent=transparent)
    path = tmp_path / "sheet.png"
    source.save(path)
    slicer = ImageSlicer.from_dict({"detection": EXACT, "extraction": {"shape": "original", "crop_padding": 3}})
    result = slicer.extract(path, tmp_path / "out")

    assert result.region_count == 3
    assert result.detection.details["background"] == ("transparent" if transparent else [255, 255, 255])
    # reading order: one row, left to right -> oval, star, triangle
    lefts = [r.bbox.left for r in result.regions]
    assert lefts == sorted(lefts)
    assert result.regions[0].bbox.as_tuple() == fixtures.OVAL_BOX

    is_fg = (lambda px: px[3] > 8) if transparent else (lambda px: px[:3] != (255, 255, 255))
    manifest_regions = __import__("json").loads(result.manifest_path.read_text())["regions"]
    for entry, output in zip(manifest_regions, result.outputs, strict=True):
        with Image.open(output) as im:
            assert im.mode == "RGBA"
            assert im.getchannel("A").getpixel((0, 0)) == 0, "outside the silhouette is transparent"
        assert _silhouette_matches(output, source.convert("RGBA"), entry["crop_box"], is_fg) == 1.0


def test_star_tips_survive_default_morphology(shapes_png: Path, tmp_path: Path) -> None:
    config = {**EXACT, "morphology": {"open": 1, "close": 1}}
    result = ImageSlicer.from_dict({"detection": config}).detect(shapes_png)
    star = result.regions[1]
    assert star.bbox.width > 185 and star.bbox.height > 175


def test_holes_keep_and_fill(tmp_path: Path) -> None:
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 20, 179, 179), fill=(200, 0, 0))
    draw.ellipse((70, 70, 129, 129), fill="white")
    keep = detect_contours(image, ContoursDetection(holes="keep", min_area=10))
    fill = detect_contours(image, ContoursDetection(holes="fill", min_area=10))
    assert keep.region_count == fill.region_count == 1
    local_center = (100 - 20, 100 - 20)
    assert keep.regions[0].mask.getpixel(local_center) == 0
    assert fill.regions[0].mask.getpixel(local_center) == 255


def test_min_area_too_large_gives_explicit_zero_regions(shapes_png: Path, tmp_path: Path) -> None:
    slicer = ImageSlicer.from_dict({"detection": {**EXACT, "min_area": 10**7}})
    detection = slicer.detect(shapes_png)
    assert detection.region_count == 0
    assert any(w.code == "below-min-area" for w in detection.warnings)
    with pytest.raises(NoRegionsError):
        slicer.extract(shapes_png, tmp_path / "out")
    assert not (tmp_path / "out").exists(), "nothing is written when nothing was detected"


def test_max_area_filters_large_components(shapes_png: Path) -> None:
    result = ImageSlicer.from_dict({"detection": {**EXACT, "max_area": 15000}}).detect(shapes_png)
    assert result.region_count < 3
    assert any(w.code == "above-max-area" for w in result.warnings)


def test_busy_background_is_reported(tmp_path: Path) -> None:
    image = Image.new("RGB", (120, 120))
    image.putdata([((x * 37) % 256, (y * 91) % 256, ((x + y) * 53) % 256) for y in range(120) for x in range(120)])
    result = detect_contours(image, ContoursDetection(min_area=10))
    assert any(w.code == "background-not-uniform" for w in result.warnings)
    assert result.score is not None and result.score < 0.6


def test_explicit_background_color_and_fixed_threshold(fixtures) -> None:
    sheet = fixtures.shapes_sheet()
    result = detect_contours(sheet, ContoursDetection(background=(255, 255, 255), threshold=40, min_area=400))
    assert result.region_count == 3
    assert result.details["threshold"] == 40
