"""Render the README illustrations from the synthetic fixtures (no real photos).

python examples/generate_fixtures.py && python examples/render_docs_assets.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from slicra import ImageSlicer

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "examples" / "input"
ASSETS = ROOT / "docs" / "assets"


def checker(size: tuple[int, int], cell: int = 12) -> Image.Image:
    board = Image.new("RGB", size, (236, 238, 242))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], cell):
        for x in range((y // cell) % 2 * cell, size[0], cell * 2):
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(214, 218, 225))
    return board


def strip(images: list[Image.Image], height: int = 150, gap: int = 14) -> Image.Image:
    tiles = []
    for image in images:
        image = image.copy()
        image.thumbnail((height * 2, height))
        tile = checker(image.size)
        tile.paste(image, (0, 0), image)
        tiles.append(tile)
    width = sum(t.width for t in tiles) + gap * (len(tiles) + 1)
    canvas = Image.new("RGB", (width, height + 2 * gap), "white")
    x = gap
    for tile in tiles:
        canvas.paste(tile, (x, gap + (height - tile.height) // 2))
        x += tile.width + gap
    return canvas


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    grid = ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}})
    grid.preview(INPUT / "avatars-grid.png").resize((432, 432)).save(ASSETS / "demo-grid-preview.png")

    with tempfile.TemporaryDirectory() as tmp:
        shapes = ImageSlicer.from_dict(
            {"detection": {"mode": "contours", "min_area": 400}, "extraction": {"shape": "original", "crop_padding": 4}}
        )
        shapes.preview(INPUT / "shapes-sheet.png").save(ASSETS / "demo-shapes-preview.png")
        cut = shapes.extract(INPUT / "shapes-sheet.png", Path(tmp) / "shapes")
        masks = [
            ImageSlicer.from_dict({"detection": {"mode": "grid-auto"}, "extraction": {"shape": s}})
            .render(INPUT / "avatars-grid.png")[i]
            .image
            for i, s in enumerate(["rectangle", "circle", "star", "ellipse"])
        ]
        images = [Image.open(p).convert("RGBA") for p in cut.outputs] + masks
        strip(images).save(ASSETS / "demo-cutouts.png")
    for path in sorted(ASSETS.glob("demo-*.png")):
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
