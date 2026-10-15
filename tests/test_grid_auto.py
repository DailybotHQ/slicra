from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from slicra import DetectionError, ImageSlicer
from slicra.config import GridAutoDetection
from slicra.detectors.grid_auto import detect_grid_auto


def test_infers_exact_tile_boxes(fixtures) -> None:
    image = fixtures.avatars_grid(margins=(20, 10, 30, 15))
    result = detect_grid_auto(image, GridAutoDetection())
    assert result.region_count == 25
    assert result.details["rows"] == 5 and result.details["cols"] == 5
    first = result.regions[0].bbox.as_tuple()
    assert first == (20, 10, 140, 130)
    assert result.regions[6].bbox.as_tuple() == (20 + 132, 10 + 132, 140 + 132, 130 + 132)
    assert result.score is not None and result.score > 0.9


def test_irregular_spacing_is_handled_where_fixed_gaps_would_fail() -> None:
    image = Image.new("RGB", (400, 120), (250, 250, 250))
    draw = ImageDraw.Draw(image)
    spans = [(5, 95), (110, 205), (222, 310), (321, 395)]  # gaps 15, 17, 11
    for left, right in spans:
        draw.rectangle((left, 10, right - 1, 109), fill=(30, 60, 90))
    result = detect_grid_auto(image, GridAutoDetection())
    assert [(r.bbox.left, r.bbox.right) for r in result.regions] == spans


def test_expected_counts_mismatch_fails(fixtures) -> None:
    with pytest.raises(DetectionError, match="expected 4"):
        detect_grid_auto(fixtures.avatars_grid(), GridAutoDetection(rows=4, cols=5))


def test_no_separators_refuses_to_guess() -> None:
    image = Image.new("RGB", (200, 200), (10, 10, 10))
    ImageDraw.Draw(image).rectangle((0, 0, 199, 199), fill=(200, 30, 30))
    with pytest.raises(DetectionError):
        detect_grid_auto(image, GridAutoDetection(background=(255, 255, 255)))


def test_empty_cell_is_skipped_with_warning(fixtures) -> None:
    image = fixtures.avatars_grid(rows=2, cols=2)
    ImageDraw.Draw(image).rectangle((132, 132, 251, 251), fill=fixtures.SEPARATOR)
    result = detect_grid_auto(image, GridAutoDetection())
    assert result.region_count == 3
    assert any(w.code == "grid-auto-empty-cells" for w in result.warnings)


def test_silhouette_never_cuts_background_colored_content_at_the_edge(tmp_path) -> None:
    """Regression: a light sweater touching a tile corner must stay opaque."""
    bg = (248, 250, 253)
    image = Image.new("RGB", (220, 100), bg)
    draw = ImageDraw.Draw(image)
    for left in (10, 120):
        draw.rounded_rectangle((left, 10, left + 89, 89), radius=12, fill=(90, 120, 160))
    # first tile: background-colored "sweater" filling its bottom-left corner area
    draw.rectangle((10, 60, 50, 89), fill=(246, 249, 252))
    slicer = ImageSlicer.from_dict(
        {"detection": {"mode": "grid-auto", "silhouette": True}, "extraction": {"shape": "original"}}
    )
    [first, second] = slicer.render(image)
    alpha = first.image.getchannel("A")
    assert alpha.getpixel((20, 75)) == 255 and alpha.getpixel((2, 60)) == 255, "content kept opaque"
    assert alpha.getpixel((0, 0)) == 0, "rounded corner (measured on clean corners) is transparent"
    assert second.image.getchannel("A").getpixel((45, 45)) == 255


def test_silhouette_keeps_rounded_corners_transparent(tmp_path) -> None:
    image = Image.new("RGB", (220, 100), (248, 250, 253))
    draw = ImageDraw.Draw(image)
    for left in (10, 120):
        draw.rounded_rectangle((left, 10, left + 89, 89), radius=20, fill=(90, 120, 160))
        draw.rectangle((left + 30, 40, left + 59, 59), fill=(248, 250, 253))  # bg-colored interior
    slicer = ImageSlicer.from_dict(
        {"detection": {"mode": "grid-auto", "silhouette": True}, "extraction": {"shape": "original"}}
    )
    result = slicer.extract(image, tmp_path / "out")
    with Image.open(result.outputs[0]) as im:
        alpha = im.getchannel("A")
        assert alpha.getpixel((0, 0)) == 0, "rounded corner must be transparent"
        assert alpha.getpixel((45, 45)) == 255, "interior holes are filled, not cut out"
        assert alpha.getpixel((45, 5)) == 255
