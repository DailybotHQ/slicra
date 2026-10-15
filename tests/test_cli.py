from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from slicra import __version__
from slicra.cli import app

runner = CliRunner()
HAS_CV = importlib.util.find_spec("cv2") is not None
NO_REGIONS = 3 if HAS_CV else 6  # without the opencv extra, contours exits with "missing dependency"


def run(*args: str):
    return runner.invoke(app, [str(a) for a in args])


def test_version_and_help() -> None:
    result = run("--version")
    assert result.exit_code == 0 and __version__ in result.output
    for command in ("", "init", "validate", "inspect", "preview", "extract", "templates"):
        args = [command, "--help"] if command else ["--help"]
        assert run(*args).exit_code == 0


def test_init_then_validate(tmp_path: Path) -> None:
    config = tmp_path / "slicra.yaml"
    assert run("init", "--output", config).exit_code == 0
    assert run("init", "--output", config).exit_code == 2, "refuses to overwrite"
    for mode in ("grid", "grid-auto", "contours", "manual"):
        path = tmp_path / f"{mode}.yaml"
        assert run("init", "--output", path, "--mode", mode).exit_code == 0
        result = run("validate", "--config", path)
        assert result.exit_code == 0, result.output
    result = run("validate", "--config", config, "--json")
    assert json.loads(result.output)["detection"]["rows"] == 5


def test_validate_reports_invalid_config(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\ndetection: {mode: grid, rows: -1, cols: 2}\n")
    result = run("validate", "--config", bad)
    assert result.exit_code == 2
    assert "rows" in result.output
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text("!!python/object/apply:os.system ['echo hacked']\n")
    assert run("validate", "--config", unsafe).exit_code == 2
    assert run("validate", "--config", tmp_path / "missing.yaml").exit_code == 2


def test_inspect_writes_nothing(grid_png: Path, tmp_path: Path) -> None:
    before = set(grid_png.parent.iterdir())
    result = run("inspect", grid_png, "--mode", "grid", "--rows", 5, "--cols", 5, "--gap", 12)
    assert result.exit_code == 0, result.output
    assert "regions: 25" in result.output and "648x648" in result.output
    assert set(grid_png.parent.iterdir()) == before
    data = json.loads(run("inspect", grid_png, "--mode", "grid-auto", "--json").output)
    assert data["region_count"] == 25 and data["detector"] == "grid-auto"


def test_preview_command(grid_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "p.png"
    result = run("preview", grid_png, "--rows", 5, "--cols", 5, "--gap-x", 12, "--gap-y", 12, "--output", out)
    assert result.exit_code == 0, result.output
    assert out.is_file() and len(list(tmp_path.iterdir())) == 2  # input dir + preview only


def test_extract_with_flags(grid_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "avatars"
    result = run(
        "extract",
        grid_png,
        "--mode",
        "grid",
        "--rows",
        5,
        "--cols",
        5,
        "--gap-x",
        12,
        "--gap-y",
        12,
        "--output",
        out,
        "--shape",
        "circle",
        "--width",
        64,
        "--height",
        64,
    )
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("region_*.png"))) == 25
    assert (out / "manifest.json").is_file() and (out / "preview.png").is_file()
    again = run("extract", grid_png, "--rows", 5, "--cols", 5, "--gap", 12, "--output", out)
    assert again.exit_code == 5 and "--overwrite" in again.output
    assert (
        run("extract", grid_png, "--rows", 5, "--cols", 5, "--gap", 12, "--output", out, "--overwrite").exit_code == 0
    )


def test_cli_overrides_beat_yaml(grid_png: Path, tmp_path: Path) -> None:
    config = tmp_path / "c.yaml"
    config.write_text("version: 1\ndetection: {mode: grid, rows: 1, cols: 1}\noutput: {naming: 'x_{index}'}\n")
    result = run(
        "extract",
        grid_png,
        "-c",
        config,
        "--rows",
        5,
        "--cols",
        5,
        "--gap",
        12,
        "-o",
        tmp_path / "o",
        "--naming",
        "y_{index}",
        "--json",
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["region_count"] == 25
    assert (tmp_path / "o" / "y_1.png").is_file()


@pytest.mark.parametrize(
    "args,code",
    [
        (["extract", "missing.png", "--rows", "2", "--cols", "2", "-o", "out"], 4),
        (["inspect", "missing.png"], 4),
        (["extract", "{grid}", "--rows", "2", "--cols", "2"], 2),  # no output dir
        (["extract", "{grid}", "--mode", "nope", "-o", "o"], 2),
        (["extract", "{grid}", "--mode", "contours", "--rows", "3", "-o", "o"], 2),  # incompatible option
        (["extract", "{grid}", "--rows", "2", "--cols", "2", "--format", "gif", "-o", "o"], 2),
        (["extract", "{grid}", "--mode", "contours", "--min-area", "99999999", "-o", "o"], NO_REGIONS),
        (["inspect", "{grid}", "--mode", "contours", "--min-area", "99999999"], NO_REGIONS),
    ],
)
def test_error_exit_codes(grid_png: Path, tmp_path: Path, monkeypatch, args, code) -> None:
    monkeypatch.chdir(tmp_path)
    result = run(*[a.replace("{grid}", str(grid_png)) for a in args])
    assert result.exit_code == code, result.output


def test_batch_directory(tmp_path: Path, fixtures) -> None:
    inputs = tmp_path / "in"
    inputs.mkdir()
    for name in ("a.png", "b.png"):
        fixtures.avatars_grid(rows=2, cols=3).save(inputs / name)
    (inputs / "notes.txt").write_text("not an image")
    result = run("extract", inputs, "--mode", "grid-auto", "-o", tmp_path / "out")
    assert result.exit_code == 0, result.output
    assert len(list((tmp_path / "out" / "a").glob("region_*.png"))) == 6
    assert (tmp_path / "out" / "b" / "manifest.json").is_file()
    flat = run("extract", inputs, "--mode", "grid-auto", "-o", tmp_path / "flat", "--flat")
    assert flat.exit_code == 0, flat.output
    assert sorted(p.name for p in (tmp_path / "flat").glob("*.png"))[:2] == ["a_region_001.png", "a_region_002.png"]
    assert len(list((tmp_path / "flat").glob("*.png"))) == 12
    assert (tmp_path / "flat" / "_manifests" / "a.json").is_file()
    assert (tmp_path / "flat" / "_previews" / "b.png").is_file()


def test_templates_command() -> None:
    result = run("templates")
    assert result.exit_code == 0 and "avatars-5x5" in result.output
