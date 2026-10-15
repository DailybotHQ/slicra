"""Regression tests for bugs found in the pre-release review (one test per bug)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from typer.testing import CliRunner

from slicra import ConfigError, ExportError, ImageSlicer, build_config
from slicra.cli import app
from slicra.models import BBox, Region

GRID_1X2 = {"detection": {"mode": "grid", "rows": 1, "cols": 2}}
runner = CliRunner()


def two_tiles(path: Path, color: tuple[int, int, int] = (200, 30, 30)) -> Path:
    image = Image.new("RGB", (40, 20), "white")
    ImageDraw.Draw(image).rectangle((0, 0, 17, 19), fill=color)
    ImageDraw.Draw(image).rectangle((22, 0, 39, 19), fill=color)
    image.save(path)
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_insensitive_fs(directory: Path) -> bool:
    probe = directory / "CaseProbe"
    probe.write_text("x")
    try:
        return (directory / "caseprobe").exists()
    finally:
        probe.unlink()


def test_input_guard_is_case_insensitive(tmp_path: Path) -> None:
    if not case_insensitive_fs(tmp_path):
        pytest.skip("filesystem is case-sensitive")
    source = two_tiles(tmp_path / "Region_001.PNG")
    before = digest(source)
    slicer = ImageSlicer.from_dict({**GRID_1X2, "manifest": {"enabled": False}, "preview": {"enabled": False}})
    with pytest.raises(ExportError, match="input image"):
        slicer.extract(source, tmp_path, overwrite=True)
    assert digest(source) == before


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_symlinked_preview_or_manifest_never_escapes(tmp_path: Path) -> None:
    source = two_tiles(tmp_path / "in.png")
    outside = tmp_path / "outside"
    outside.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "preview.png").symlink_to(outside / "stolen.png")
    with pytest.raises(ExportError, match="symbolic link"):
        ImageSlicer.from_dict(GRID_1X2).extract(source, out)
    (out / "preview.png").unlink()
    (out / "preview.png").symlink_to(source)
    with pytest.raises(ExportError):
        ImageSlicer.from_dict(GRID_1X2).extract(source, out, overwrite=True)
    assert not any(outside.iterdir())


def test_manifest_temp_file_is_not_predictable(tmp_path: Path) -> None:
    source = two_tiles(tmp_path / "in.png")
    out = tmp_path / "out"
    out.mkdir()
    (out / "manifest.json.tmp").write_text("keep")
    ImageSlicer.from_dict(GRID_1X2).extract(source, out)
    assert (out / "manifest.json.tmp").read_text() == "keep"
    assert json.loads((out / "manifest.json").read_text())["region_count"] == 2


def test_preview_command_refuses_to_overwrite_input(tmp_path: Path) -> None:
    source = two_tiles(tmp_path / "in.png")
    before = digest(source)
    result = runner.invoke(
        app, ["preview", str(source), "--rows", "1", "--cols", "2", "-o", str(source), "--overwrite"]
    )
    assert result.exit_code == 5
    assert digest(source) == before


def test_batch_keys_are_unique_case_insensitively() -> None:
    from slicra.pipeline import batch_keys

    names = [Path("a.png"), Path("a.jpg"), Path("a_png.png"), Path("B.png"), Path("b.webp")]
    keys = batch_keys(names)
    assert len({k.casefold() for k in keys}) == len(keys)
    assert keys[:3] == ["a_png", "a_jpg", "a_png_2"]


@pytest.mark.parametrize("flat", [False, True])
def test_batch_never_mixes_images_with_colliding_stems(tmp_path: Path, flat: bool) -> None:
    inputs = tmp_path / "in"
    inputs.mkdir()
    two_tiles(inputs / "a.png", (200, 0, 0))
    two_tiles(inputs / "a.jpg", (0, 0, 200))
    two_tiles(inputs / "a_png.png", (0, 200, 0))
    batch = ImageSlicer.from_dict(GRID_1X2).extract_batch(inputs, tmp_path / "out", overwrite=True, flat=flat)
    assert batch.ok and batch.region_count == 6
    written = [p for r in batch.results for p in r.outputs]
    assert len({p.as_posix().casefold() for p in written}) == 6
    assert all(p.exists() for p in written)


def test_batch_exit_code_reflects_the_failure_kind(tmp_path: Path) -> None:
    inputs = tmp_path / "in"
    inputs.mkdir()
    two_tiles(inputs / "a.png")
    args = ["extract", str(inputs), "--rows", "1", "--cols", "2", "-o", str(tmp_path / "out"), "--flat"]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code == 5, "existing outputs are an export conflict"


def test_rgb_png_with_transparency_key_keeps_alpha(tmp_path: Path) -> None:
    path = tmp_path / "keyed.png"
    image = Image.new("RGB", (4, 4), (1, 2, 3))
    image.putpixel((0, 0), (200, 0, 0))
    image.save(path, transparency=(1, 2, 3))
    loaded = ImageSlicer().load(path)
    assert loaded.image.mode == "RGBA"
    assert loaded.image.getpixel((1, 1))[3] == 0 and loaded.image.getpixel((0, 0))[3] == 255


def test_float_and_int32_images_are_scaled(tmp_path: Path) -> None:
    from slicra.imageio import normalize_mode

    gradient = Image.new("F", (2, 1))
    gradient.putpixel((0, 0), 0.0)
    gradient.putpixel((1, 0), 1.0)
    assert normalize_mode(gradient).getpixel((1, 0)) == (255, 255, 255)
    wide = Image.new("I", (2, 1))
    wide.putpixel((1, 0), 65535)
    assert normalize_mode(wide).getpixel((1, 0)) == (255, 255, 255)


def test_switching_template_drops_the_previous_overrides(tmp_path: Path) -> None:
    config = tmp_path / "c.yaml"
    config.write_text("detection: {mode: template, template: avatars-5x5, overrides: {rows: 2, cols: 3}}\n")
    switched = runner.invoke(app, ["validate", "--config", str(config), "--json"])
    assert switched.exit_code == 0
    from slicra.cli import collect_overrides
    from slicra.config import load_config

    data = {"detection": {"mode": "template", "template": "avatars-5x5", "overrides": {"rows": 2, "cols": 3}}}
    cfg = load_config(config, collect_overrides(data, template="avatar-sheet"))
    assert cfg.detection.mode == "grid-auto" and cfg.detection.rows is None
    flagged = load_config(config, collect_overrides(data, rows=4))
    assert flagged.detection.mode == "grid" and flagged.detection.rows == 4 and flagged.detection.cols == 3


def test_auto_rejects_a_region_covering_the_whole_image() -> None:
    pytest.importorskip("cv2")
    image = Image.new("RGB", (200, 200), "white")
    image.paste(Image.frombytes("RGB", (192, 192), bytes((i * 97 + 13) % 256 for i in range(192 * 192 * 3))), (4, 4))
    from slicra import DetectionError

    with pytest.raises(DetectionError):
        ImageSlicer().detect(image)


def test_center_square_circle_stays_centered_near_the_edge() -> None:
    from slicra.config import Extraction
    from slicra.extraction import crop_box_for, shape_spec

    spec = shape_spec(Extraction(shape="circle", circle_fit="center-square"))
    region = Region(id="r", bbox=BBox(0, 0, 100, 50))
    box = crop_box_for(region, spec, padding=30, image_size=(300, 300))
    assert box.width == box.height == 110
    assert (box.left + box.right) / 2 == 50 or box.left == 0
    centered = crop_box_for(Region(id="c", bbox=BBox(100, 100, 200, 150)), spec, 30, (300, 300))
    assert (centered.left + centered.right) / 2 == 150 and (centered.top + centered.bottom) / 2 == 125


def test_manual_default_ids_cannot_collide_with_explicit_ids() -> None:
    regions = [{"rect": [0, 0, 5, 5]}, {"id": "m001", "rect": [5, 5, 9, 9]}]
    with pytest.raises(ConfigError, match="duplicate"):
        ImageSlicer.from_dict({"detection": {"mode": "manual", "regions": regions}}).detect(Image.new("RGB", (10, 10)))


def test_duplicate_exclude_entries_are_not_counted_twice() -> None:
    cfg = build_config({"detection": {"mode": "grid", "rows": 1, "cols": 2, "exclude": [[1, 1], [1, 1]]}})
    assert cfg.detection.exclude == [(1, 1), (1, 1)]


def test_local_file_cannot_shadow_a_builtin_template(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "avatars-5x5").write_text("detection: {mode: grid, rows: 1, cols: 1}\n")
    cfg = build_config({"detection": {"mode": "template", "template": "avatars-5x5"}})
    assert cfg.detection.rows == 5 and cfg.source_template == "builtin:avatars-5x5"


def test_detector_flags_without_mode_pick_a_matching_detector(tmp_path: Path) -> None:
    from slicra.cli import collect_overrides

    assert collect_overrides({}, min_area=50)["detection"] == {"mode": "contours", "min_area": 50}
    assert collect_overrides({}, tolerance=10)["detection"] == {"mode": "grid-auto", "tolerance": 10}
    routed = collect_overrides({}, background="#ffffff")["detection"]
    assert routed["mode"] == "auto" and routed["grid_auto"] == routed["contours"] == {"background": "#ffffff"}
    build_config({}, collect_overrides({}, background="#ffffff"))
