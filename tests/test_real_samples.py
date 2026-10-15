"""Optional regression test against real avatar sheets kept outside the repository.

Set SLICRA_SAMPLES to a directory of 5x5 avatar sheets (for example the
maintainer's local ``avatars-grids`` folder). Skipped when not available, so CI
only ever uses the synthetic fixtures.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from slicra import ImageSlicer

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = Path(os.environ.get("SLICRA_SAMPLES", ROOT.parent / "avatars-grids"))
SHEETS = sorted(SAMPLES.glob("*.png")) if SAMPLES.is_dir() else []

pytestmark = [pytest.mark.real, pytest.mark.skipif(not SHEETS, reason=f"no sample sheets in {SAMPLES}")]


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda p: p.stem[:8])
def test_real_sheet_yields_25_avatars_without_separators(sheet: Path, tmp_path: Path) -> None:
    slicer = ImageSlicer.from_config(ROOT / "examples" / "configs" / "avatar-sheet-auto.yaml")
    result = slicer.extract(sheet, tmp_path)
    assert result.region_count == 25
    background = tuple(result.detection.details["background"])
    for path in result.outputs:
        with Image.open(path) as im:
            assert 180 <= im.width <= 260 and 180 <= im.height <= 260
            rgba = im.convert("RGBA")
            # the crop's middle row starts and ends on tile content, never on separator background
            for x in (0, im.width - 1):
                r, g, b, _ = rgba.getpixel((x, im.height // 2))
                assert max(abs(r - background[0]), abs(g - background[1]), abs(b - background[2])) > 0
