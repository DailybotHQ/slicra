"""Preview rendering: the source image with every region's box, outline and index.

The preview consumes exactly the region list that extraction uses, so what you
see is what will be exported.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .models import Region

BOX_COLOR = (255, 0, 153)
OUTLINE_COLOR = (0, 200, 255)
LABEL_TEXT = (255, 255, 255)


def _checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    board = Image.new("RGB", size, (235, 235, 235))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], cell):
        for x in range((y // cell) % 2 * cell, size[0], cell * 2):
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(200, 200, 200))
    return board


def render_preview(
    image: Image.Image,
    regions: list[Region],
    *,
    labels: bool = True,
    line_width: int | None = None,
) -> Image.Image:
    if image.mode == "RGBA":
        base = _checkerboard(image.size)
        base.paste(image, (0, 0), image)
    else:
        base = image.convert("RGB").copy()
    short = min(base.size)
    width = line_width or max(1, round(short / 400))
    font = ImageFont.load_default(size=max(10, min(48, round(short / 45))))
    draw = ImageDraw.Draw(base)

    for region in regions:
        if region.polygon is not None and len(region.polygon) >= 3:
            points = [*region.polygon, region.polygon[0]]
            draw.line(points, fill=OUTLINE_COLOR, width=width, joint="curve")
        b = region.bbox
        draw.rectangle((b.left, b.top, b.right - 1, b.bottom - 1), outline=BOX_COLOR, width=width)
    if labels:
        for region in regions:
            b = region.bbox
            text = f"{region.index}"
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            pad = max(2, width)
            tw, th = right - left + 2 * pad, bottom - top + 2 * pad
            x, y = b.left + width, b.top + width
            draw.rectangle((x, y, x + tw, y + th), fill=BOX_COLOR)
            draw.text((x + pad - left, y + pad - top), text, fill=LABEL_TEXT, font=font)
    return base
