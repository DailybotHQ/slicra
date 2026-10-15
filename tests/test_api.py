from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import slicra
from slicra import ConfigError, ImageSlicer, load_config


def test_documented_api_flow(grid_png: Path, tmp_path: Path) -> None:
    config = tmp_path / "slicra.yaml"
    config.write_text(
        "version: 1\ndetection: {mode: grid, rows: 5, cols: 5, gap_x: 12, gap_y: 12}\n"
        "output: {naming: 'avatar_{index:03d}'}\n"
    )
    slicer = ImageSlicer.from_config(config)
    result = slicer.extract(grid_png, output_dir=tmp_path / "avatars")
    assert result.region_count == 25
    assert result.manifest_path == (tmp_path / "avatars" / "manifest.json").resolve()
    assert result.outputs[0].name == "avatar_001.png"
    assert result.regions[0].bbox.as_tuple() == (0, 0, 120, 120)


def test_detect_and_render_without_files(grid_png: Path, tmp_path: Path) -> None:
    slicer = ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}, "extraction": {"shape": "star"}})
    detection = slicer.detect(grid_png)
    assert detection.region_count == 25 and detection.detector == "grid-auto"
    rendered = slicer.render(grid_png)
    assert all(isinstance(r.image, Image.Image) and r.shape == "star" for r in rendered)
    preview = slicer.preview(grid_png)
    assert preview.size == (648, 648)
    assert list(tmp_path.iterdir()) == [grid_png]


def test_accepts_in_memory_images(fixtures) -> None:
    image = fixtures.avatars_grid(rows=2, cols=2)
    assert ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}}).detect(image).region_count == 4


def test_overrides_take_precedence(tmp_path: Path) -> None:
    config = tmp_path / "c.yaml"
    config.write_text("detection: {mode: grid, rows: 2, cols: 2}\nextraction: {shape: ellipse}\n")
    cfg = load_config(config, {"detection": {"rows": 3}})
    assert cfg.detection.rows == 3 and cfg.detection.cols == 2 and cfg.extraction.shape == "ellipse"
    switched = load_config(config, {"detection": {"mode": "grid-auto"}})
    assert switched.detection.mode == "grid-auto"


def test_templates_resolve_and_reject_unknown() -> None:
    cfg = slicra.build_config({"detection": {"mode": "template", "template": "avatars-5x5", "overrides": {"gap_x": 4}}})
    assert cfg.detection.mode == "grid" and cfg.detection.gap_x == 4
    assert cfg.source_template == "builtin:avatars-5x5"
    with pytest.raises(ConfigError):
        slicra.build_config({"detection": {"mode": "template", "template": "nope"}})
    with pytest.raises(ConfigError):
        slicra.build_config({"detection": {"mode": "template", "template": "../../etc/passwd"}})


def test_auto_mode_records_selection(grid_png: Path) -> None:
    result = ImageSlicer().detect(grid_png)
    assert result.details["selected"] == "grid-auto"
    assert result.warnings[0].code == "auto-selected"


def test_auto_mode_falls_back_to_contours(shapes_png: Path) -> None:
    pytest.importorskip("cv2")
    result = ImageSlicer().detect(shapes_png)
    assert result.details["selected"] == "contours" and result.region_count == 3
    assert result.details["attempts"][0]["accepted"] is False


def test_register_detector_extension_point() -> None:
    with pytest.raises(ValueError):
        slicra.register_detector("grid", lambda image, cfg: None)
    assert "contours" in slicra.available_detectors()
