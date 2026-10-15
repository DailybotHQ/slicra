from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from slicra import ExportError, ImageLoadError, ImageSlicer
from slicra.preview import BOX_COLOR

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "examples" / "configs"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch, fixtures) -> Path:
    """A temp copy of examples/ with generated inputs; cwd is set to it."""
    (tmp_path / "examples").mkdir()
    shutil.copytree(CONFIGS, tmp_path / "examples" / "configs")
    inputs = tmp_path / "examples" / "input"
    inputs.mkdir()
    fixtures.avatars_grid().save(inputs / "avatars-grid.png")
    fixtures.shapes_sheet().save(inputs / "shapes-sheet.png")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_example_1_avatars(workspace: Path) -> None:
    result = ImageSlicer.from_config("examples/configs/avatars-grid.yaml").extract()
    assert result.region_count == 25
    out = workspace / "output" / "avatars"
    assert sorted(p.name for p in out.glob("avatar_*.png")) == [f"avatar_{i:03d}.png" for i in range(1, 26)]
    with Image.open(out / "avatar_001.png") as im:
        assert im.size == (256, 256)
    assert (out / "preview.png").is_file() and (out / "manifest.json").is_file()


def test_example_2_and_3_shapes(workspace: Path) -> None:
    pytest.importorskip("cv2")
    shapes = ImageSlicer.from_config("examples/configs/irregular-shapes.yaml").extract()
    assert shapes.region_count == 3
    manual = ImageSlicer.from_config("examples/configs/manual-shapes.yaml").extract()
    assert [p.name for p in manual.outputs] == ["oval.png", "star.png", "triangle.png"]


def test_template_example(workspace: Path) -> None:
    result = ImageSlicer.from_config("examples/configs/avatars-circles.yaml").extract()
    assert result.region_count == 25 and result.outputs[0].suffix == ".webp"


def test_preview_and_extract_consume_the_same_regions(grid_png: Path, tmp_path: Path) -> None:
    slicer = ImageSlicer.from_dict({"detection": {"mode": "grid", "rows": 5, "cols": 5, "gap_x": 12, "gap_y": 12}})
    result = slicer.extract(grid_png, tmp_path / "out")
    detection = slicer.detect(grid_png)
    assert [r.bbox for r in detection.regions] == [r.bbox for r in result.regions]
    with Image.open(result.preview_path) as preview:
        rgb = preview.convert("RGB")
        for region in result.regions:
            b = region.bbox
            assert rgb.getpixel((b.left, b.top + 60)) == BOX_COLOR, f"box {region.index} outlined"
            assert rgb.getpixel((b.right - 1, b.bottom - 30)) == BOX_COLOR
    manifest = json.loads(result.manifest_path.read_text())
    assert [r["bbox"] for r in manifest["regions"]] == [list(r.bbox.as_tuple()) for r in detection.regions]
    assert [r["index"] for r in manifest["regions"]] == list(range(1, 26))


def test_source_file_is_never_modified(grid_png: Path, tmp_path: Path) -> None:
    digest = hashlib.sha256(grid_png.read_bytes()).hexdigest()
    ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}, "extraction": {"shape": "star"}}).extract(
        grid_png, tmp_path / "o"
    )
    assert hashlib.sha256(grid_png.read_bytes()).hexdigest() == digest


def test_exif_orientation_is_applied_before_detection(tmp_path: Path) -> None:
    upright = Image.new("RGB", (100, 200), "white")
    upright.paste((200, 0, 0), (10, 10, 40, 60))  # red block near the top-left
    stored = upright.transpose(Image.Transpose.ROTATE_90)  # stored sideways: 200x100
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 CW to display upright
    path = tmp_path / "rotated.jpg"
    stored.save(path, exif=exif, quality=100)
    slicer = ImageSlicer.from_dict({"detection": {"mode": "manual", "regions": [{"rect": [10, 10, 40, 60]}]}})
    loaded = slicer.load(path)
    assert loaded.size == (100, 200) and loaded.exif_transposed
    [item] = slicer.render(path)
    r, g, b, _ = item.image.getpixel((15, 25))
    assert r > 150 and g < 80 and b < 80
    result = slicer.extract(path, tmp_path / "out")
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["source"]["exif_transposed"] is True and manifest["source"]["width"] == 100


def test_bad_inputs_fail_clearly(tmp_path: Path) -> None:
    slicer = ImageSlicer.from_dict({"detection": {"mode": "grid", "rows": 1, "cols": 1}})
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"\x89PNG\r\n\x1a\nnot really")
    for path, match in ((tmp_path / "missing.png", "not found"), (empty, "empty"), (corrupt, "corrupt|could not read")):
        with pytest.raises(ImageLoadError, match=match):
            slicer.detect(path)
    with pytest.raises(ImageLoadError):
        slicer.detect(tmp_path)


def test_pixel_limit(tmp_path: Path) -> None:
    path = tmp_path / "big.png"
    Image.new("RGB", (400, 400)).save(path)
    slicer = ImageSlicer.from_dict({"detection": {"mode": "grid", "rows": 1, "cols": 1}, "input": {"max_pixels": 1000}})
    with pytest.raises(ImageLoadError, match="limit"):
        slicer.detect(path)


def test_tiny_image_and_palette_transparency(tmp_path: Path) -> None:
    tiny = Image.new("P", (3, 2))
    tiny.info["transparency"] = 0
    path = tmp_path / "tiny.png"
    tiny.save(path, transparency=0)
    slicer = ImageSlicer.from_dict({"detection": {"mode": "grid", "rows": 1, "cols": 3}})
    result = slicer.extract(path, tmp_path / "o")
    assert result.region_count == 3
    with Image.open(result.outputs[0]) as im:
        assert im.size == (1, 2) and im.getpixel((0, 0))[3] == 0
    with pytest.raises(Exception, match="fit"):
        ImageSlicer.from_dict({"detection": {"mode": "grid", "rows": 1, "cols": 4}}).detect(path)


def test_batch_never_reprocesses_outputs_or_overwrites(tmp_path: Path, fixtures) -> None:
    inputs = tmp_path / "sheets"
    inputs.mkdir()
    fixtures.avatars_grid(rows=1, cols=2).save(inputs / "one.png")
    fixtures.avatars_grid(rows=2, cols=1).save(inputs / "two.png")
    snapshot = {p.name: p.read_bytes() for p in inputs.iterdir()}
    slicer = ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}})
    batch = slicer.extract_batch(inputs, inputs / "out")  # output nested inside the input dir
    assert batch.ok and batch.region_count == 4
    batch2 = slicer.extract_batch(inputs, inputs / "out")
    assert not batch2.ok and len(batch2.failures) == 2, "existing outputs are not overwritten silently"
    assert {p.name: p.read_bytes() for p in inputs.iterdir() if p.is_file()} == snapshot
    with pytest.raises(Exception, match="differ"):
        slicer.extract_batch(inputs, inputs)


def test_overwrite_guard_for_preview(grid_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "p.png"
    target.write_bytes(b"keep")
    with pytest.raises(ExportError):
        ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}}).preview(grid_png, target)
    assert target.read_bytes() == b"keep"
