"""Background estimation and foreground masks using Pillow only (no NumPy)."""

from __future__ import annotations

from PIL import Image, ImageChops, ImageStat

from .config import RGBColor


def border_strip(image: Image.Image) -> Image.Image:
    """Concatenate the 1-pixel border of ``image`` into a single-row image."""
    w, h = image.size
    parts = [
        image.crop((0, 0, w, 1)),
        image.crop((0, h - 1, w, h)),
        image.crop((0, 0, 1, h)).transpose(Image.Transpose.ROTATE_90),
        image.crop((w - 1, 0, w, h)).transpose(Image.Transpose.ROTATE_90),
    ]
    total = sum(p.width for p in parts)
    strip = Image.new(image.mode, (total, 1))
    x = 0
    for part in parts:
        strip.paste(part, (x, 0))
        x += part.width
    return strip


def _max_channel(image: Image.Image) -> Image.Image:
    bands = image.split()
    out = bands[0]
    for band in bands[1:]:
        out = ImageChops.lighter(out, band)
    return out


def threshold(image: Image.Image, cutoff: int) -> Image.Image:
    """Binary ``L`` mask: 255 where the pixel value is strictly above ``cutoff``."""
    return image.point(lambda v: 255 if v > cutoff else 0)


def fraction_on(mask: Image.Image) -> float:
    """Fraction of non-zero pixels of a binary ``L`` mask."""
    hist = mask.histogram()
    total = sum(hist)
    return (total - hist[0]) / total if total else 0.0


def estimate_background(image: Image.Image, tolerance: int, alpha_threshold: int = 8) -> tuple[str | RGBColor, float]:
    """Guess the background from the image border.

    Returns ``("transparent", uniformity)`` when most border pixels are
    transparent, otherwise ``((r, g, b), uniformity)`` using the per-channel
    median. ``uniformity`` is the fraction of border pixels within
    ``tolerance`` of that background, a heuristic for how trustworthy a
    background-based detection will be.
    """
    strip = border_strip(image)
    if image.mode == "RGBA":
        alpha = strip.getchannel("A")
        transparent = 1.0 - fraction_on(threshold(alpha, alpha_threshold))
        if transparent >= 0.5:
            return "transparent", transparent
    rgb = strip.convert("RGB")
    median = ImageStat.Stat(rgb).median
    color: RGBColor = (int(median[0]), int(median[1]), int(median[2]))
    diff = _max_channel(ImageChops.difference(rgb, Image.new("RGB", rgb.size, color)))
    uniformity = 1.0 - fraction_on(threshold(diff, tolerance))
    return color, uniformity


def foreground_mask(
    image: Image.Image,
    background: str | RGBColor,
    tolerance: int,
    alpha_threshold: int = 8,
) -> Image.Image:
    """Binary ``L`` mask (255 = foreground) relative to a background spec."""
    if background == "transparent":
        if image.mode != "RGBA":
            return Image.new("L", image.size, 255)
        return threshold(image.getchannel("A"), alpha_threshold)
    assert not isinstance(background, str)
    rgb = image.convert("RGB")
    diff = _max_channel(ImageChops.difference(rgb, Image.new("RGB", rgb.size, background)))
    mask = threshold(diff, tolerance)
    if image.mode == "RGBA":
        mask = ImageChops.multiply(mask, threshold(image.getchannel("A"), alpha_threshold))
    return mask


def column_profile(mask: Image.Image) -> list[float]:
    """Mean foreground fraction of every column (exact BOX average)."""
    reduced = mask.resize((mask.width, 1), Image.Resampling.BOX)
    return [v / 255.0 for v in _flat(reduced)]


def row_profile(mask: Image.Image) -> list[float]:
    reduced = mask.resize((1, mask.height), Image.Resampling.BOX)
    return [v / 255.0 for v in _flat(reduced)]


def _flat(image: Image.Image) -> list[int]:
    getter = getattr(image, "get_flattened_data", None)
    data = getter() if getter is not None else image.getdata()
    return [int(v) for v in data]  # type: ignore[union-attr]


def uniform_line_colors(image: Image.Image, tolerance: int) -> list[RGBColor]:
    """Colors of full-length rows/columns that are (nearly) a single color.

    Separator lines of a grid are exactly that, so these are the background
    candidates for sheets without an outer margin (where the image border is
    content). Similar colors are clustered; the most frequent comes first.
    """
    rgb = image.convert("RGB")
    found: list[RGBColor] = []
    for size in ((rgb.width, 1), (1, rgb.height)):
        means = rgb.resize(size, Image.Resampling.BOX)
        spread = means.resize(rgb.size, Image.Resampling.NEAREST)
        deviation = threshold(_max_channel(ImageChops.difference(rgb, spread)), tolerance)
        profile = _flat(deviation.resize(size, Image.Resampling.BOX))
        for i, value in enumerate(profile):
            if value == 0:
                px = means.getpixel((i, 0) if size[1] == 1 else (0, i))
                assert isinstance(px, tuple)
                found.append((int(px[0]), int(px[1]), int(px[2])))
    clusters: list[tuple[RGBColor, int]] = []
    for color in found:
        for n, (center, count) in enumerate(clusters):
            if max(abs(a - b) for a, b in zip(color, center, strict=True)) <= tolerance:
                clusters[n] = (center, count + 1)
                break
        else:
            clusters.append((color, 1))
    clusters.sort(key=lambda item: -item[1])
    return [center for center, _count in clusters]
