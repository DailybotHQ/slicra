"""Build wheel/sdist, install the wheel in a fresh venv and run the installed CLI."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.slow


def test_build_install_and_run(tmp_path: Path) -> None:
    pytest.importorskip("build")
    dist = tmp_path / "dist"
    subprocess.run([sys.executable, "-m", "build", "--outdir", str(dist), str(ROOT)], check=True, capture_output=True)
    wheel = next(dist.glob("slicra-*.whl"))
    assert next(dist.glob("slicra-*.tar.gz"))
    names = zipfile.ZipFile(wheel).namelist()
    assert "slicra/presets/avatars-5x5.yaml" in names and "slicra/py.typed" in names

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    python = bindir / ("python.exe" if os.name == "nt" else "python")
    subprocess.run([str(python), "-m", "pip", "install", "-q", str(wheel)], check=True)
    cli = bindir / ("slicra.exe" if os.name == "nt" else "slicra")
    version = subprocess.run([str(cli), "--version"], check=True, capture_output=True, text=True)
    assert version.stdout.startswith("slicra ")
    templates = subprocess.run([str(cli), "templates"], check=True, capture_output=True, text=True)
    assert "avatars-5x5" in templates.stdout
    code = (
        "from PIL import Image; from slicra import ImageSlicer;"
        "im = Image.new('RGB', (50, 20), 'white');"
        "im.paste((0, 0, 0), (0, 0, 20, 20)); im.paste((0, 0, 0), (30, 0, 50, 20));"
        "print(ImageSlicer.from_dict({'detection': {'mode': 'grid-auto'}}).detect(im).region_count)"
    )
    out = subprocess.run([str(python), "-c", code], check=True, capture_output=True, text=True, cwd=tmp_path)
    assert out.stdout.strip() == "2"
