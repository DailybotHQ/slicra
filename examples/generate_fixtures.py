"""Generate the synthetic, reproducible example images used by docs and tests.

    python examples/generate_fixtures.py            # writes examples/input/
    python examples/generate_fixtures.py --out DIR

Everything is drawn from geometry and fixed colors: no photographs, no
randomness, no network. Re-running produces identical pixels.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

SEPARATOR = (240, 242, 245)
AVATAR_PALETTE = [
    (231, 76, 60),
    (230, 126, 34),
    (241, 196, 15),
    (46, 204, 113),
    (26, 188, 156),
    (52, 152, 219),
    (155, 89, 182),
    (52, 73, 94),
    (22, 160, 133),
    (39, 174, 96),
    (41, 128, 185),
    (142, 68, 173),
    (44, 62, 80),
    (243, 156, 18),
    (211, 84, 0),
    (192, 57, 43),
    (127, 140, 141),
    (100, 30, 22),
    (20, 90, 50),
    (21, 67, 96),
    (74, 35, 90),
    (120, 66, 18),
    (11, 83, 69),
    (81, 46, 95),
    (110, 44, 0),
]
SKIN = [(255, 224, 189), (241, 194, 125), (224, 172, 105), (198, 134, 66), (141, 85, 36)]


def avatar(size: int, index: int) -> Image.Image:
    """A flat geometric 'avatar': colored tile, head and shoulders. Never a real person."""
    bg = AVATAR_PALETTE[index % len(AVATAR_PALETTE)]
    tile = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(tile)
    skin = SKIN[index % len(SKIN)]
    shirt = tuple(255 - c for c in bg)
    draw.ellipse((size * 0.18, size * 0.68, size * 0.82, size * 1.25), fill=shirt)
    draw.ellipse((size * 0.30, size * 0.18, size * 0.70, size * 0.62), fill=skin)
    eye = max(2, size // 30)
    for ex in (0.42, 0.58):
        cx, cy = size * ex, size * 0.38
        draw.ellipse((cx - eye, cy - eye, cx + eye, cy + eye), fill=(30, 30, 30))
    draw.arc(
        (size * 0.40, size * 0.40, size * 0.60, size * 0.52), 20, 160, fill=(120, 40, 40), width=max(1, size // 60)
    )
    return tile


def avatars_grid(
    rows: int = 5,
    cols: int = 5,
    cell: int = 120,
    gap_x: int = 12,
    gap_y: int = 12,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    separator: tuple[int, int, int] = SEPARATOR,
) -> Image.Image:
    """``margins`` is (left, top, right, bottom)."""
    left, top, right, bottom = margins
    width = left + right + cols * cell + (cols - 1) * gap_x
    height = top + bottom + rows * cell + (rows - 1) * gap_y
    sheet = Image.new("RGB", (width, height), separator)
    for r in range(rows):
        for c in range(cols):
            sheet.paste(avatar(cell, r * cols + c), (left + c * (cell + gap_x), top + r * (cell + gap_y)))
    return sheet


def star_points(cx: float, cy: float, outer: float, inner: float, n: int = 5) -> list[tuple[float, float]]:
    import math

    pts = []
    for k in range(2 * n):
        rad = outer if k % 2 == 0 else inner
        ang = -math.pi / 2 + k * math.pi / n
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


# Geometry of the shapes sheet (source pixel coordinates), reused by examples/configs.
SHEET_SIZE = (640, 360)
OVAL_BOX = (40, 90, 220, 270)  # left, top, right, bottom (exclusive)
STAR_CENTER, STAR_OUTER, STAR_INNER = (330, 180), 100, 42
TRIANGLE = [(470, 270), (560, 80), (610, 270)]


def shapes_sheet(transparent: bool = False) -> Image.Image:
    """Star, oval and triangle, disjoint, on white or on a transparent background."""
    mode, bg = ("RGBA", (0, 0, 0, 0)) if transparent else ("RGB", (255, 255, 255))
    sheet = Image.new(mode, SHEET_SIZE, bg)
    draw = ImageDraw.Draw(sheet)
    draw.ellipse((OVAL_BOX[0], OVAL_BOX[1], OVAL_BOX[2] - 1, OVAL_BOX[3] - 1), fill=(46, 134, 222))
    draw.polygon(star_points(*STAR_CENTER, STAR_OUTER, STAR_INNER), fill=(235, 77, 75))
    draw.polygon(TRIANGLE, fill=(32, 191, 107))
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "input")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "avatars-grid.png": avatars_grid(),
        "shapes-sheet.png": shapes_sheet(),
        "shapes-transparent.png": shapes_sheet(transparent=True),
    }
    for name, image in outputs.items():
        image.save(args.out / name)
        print(f"wrote {args.out / name} {image.size[0]}x{image.size[1]}")


if __name__ == "__main__":
    main()
