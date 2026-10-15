"""Alpha masks for every supported shape.

All masks are ``L`` images with the size of the crop box (255 = keep).

* ``rectangle`` keeps the whole crop box (``crop_padding`` adds real pixels),
  shrunk by ``shape_inset`` on every side.
* **Parametric shapes** (``ellipse``, ``circle``, ``star`` and ``polygon``
  with relative points) are fitted to the *shape box*: the region bbox shrunk
  by ``shape_inset``. Any ``crop_padding`` therefore stays transparent around
  the shape (useful headroom for anti-aliased edges).
* **Geometric shapes** use the region's own geometry in source coordinates,
  projected into the crop: ``polygon`` with an explicit region polygon, and
  ``original`` (exact detector mask, else region polygon, else the region
  bbox rectangle).

With ``antialias`` the mask is drawn at ``supersample``x resolution and
reduced with a box filter, which yields smooth partial alpha on edges.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from ..config import SHAPES, StarOptions
from ..errors import ConfigError
from ..models import BBox, Region


@dataclass(frozen=True)
class ShapeSpec:
    """Fully resolved shape parameters for one region."""

    shape: str = "rectangle"
    shape_inset: int = 0
    antialias: bool = True
    supersample: int = 4
    circle_fit: str = "contain"
    star: StarOptions = field(default_factory=lambda: StarOptions())
    polygon_points: tuple[tuple[float, float], ...] | None = None

    def __post_init__(self) -> None:
        if self.shape not in SHAPES:
            raise ConfigError(f"unknown shape {self.shape!r}; choose one of {list(SHAPES)}")


def star_vertices(
    cx: float, cy: float, outer: float, inner: float, points: int, rotation_deg: float
) -> list[tuple[float, float]]:
    """Vertices of a star; ``rotation=0`` puts the first tip straight up."""
    base = math.radians(rotation_deg) - math.pi / 2
    vertices = []
    for k in range(points * 2):
        radius = outer if k % 2 == 0 else inner
        angle = base + k * math.pi / points
        vertices.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return vertices


def _inset(box: tuple[int, int, int, int], inset: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    out = (x0 + inset, y0 + inset, x1 - inset, y1 - inset)
    if out[2] <= out[0] or out[3] <= out[1]:
        raise ConfigError(f"shape_inset={inset} leaves no area inside a {x1 - x0}x{y1 - y0} box")
    return out


def build_mask(spec: ShapeSpec, region: Region, crop_box: BBox) -> Image.Image:
    size = (crop_box.width, crop_box.height)
    if spec.shape == "original" and region.mask is not None:
        mask = Image.new("L", size, 0)
        mask.paste(region.mask, (region.bbox.left - crop_box.left, region.bbox.top - crop_box.top))
        return mask

    s = spec.supersample if spec.antialias else 1
    canvas = Image.new("L", (size[0] * s, size[1] * s), 0)
    draw = ImageDraw.Draw(canvas)

    def scaled(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(x * s, y * s) for x, y in points]

    def fill_rect(box: tuple[float, float, float, float]) -> None:
        x0, y0, x1, y1 = box
        draw.rectangle((x0 * s, y0 * s, x1 * s - 1, y1 * s - 1), fill=255)

    b = region.bbox
    local = (
        max(0, b.left - crop_box.left),
        max(0, b.top - crop_box.top),
        min(size[0], b.right - crop_box.left),
        min(size[1], b.bottom - crop_box.top),
    )
    if local[2] <= local[0] or local[3] <= local[1]:  # center-square crop narrower than the region
        local = (0, 0, size[0], size[1])

    shape = spec.shape
    if shape == "original":
        shape = "polygon" if region.polygon is not None else "region-rect"

    if shape == "rectangle":
        fill_rect(_inset((0, 0, size[0], size[1]), spec.shape_inset))
    elif shape == "region-rect":
        fill_rect(local)
    elif shape in ("ellipse", "circle"):
        ex0, ey0, ex1, ey1 = (float(v) for v in _inset(local, spec.shape_inset))
        if shape == "circle":
            d = min(ex1 - ex0, ey1 - ey0)
            ex0 += ((ex1 - ex0) - d) / 2
            ey0 += ((ey1 - ey0) - d) / 2
            ex1, ey1 = ex0 + d, ey0 + d
        draw.ellipse((ex0 * s, ey0 * s, ex1 * s - 1, ey1 * s - 1), fill=255)
    elif shape == "star":
        x0, y0, x1, y1 = _inset(local, spec.shape_inset)
        outer = spec.star.outer_ratio * min(x1 - x0, y1 - y0) / 2
        vertices = star_vertices(
            (x0 + x1) / 2, (y0 + y1) / 2, outer, outer * spec.star.inner_ratio, spec.star.points, spec.star.rotation
        )
        draw.polygon(scaled(vertices), fill=255)
    elif shape == "polygon":
        if region.polygon is not None:
            points = [(x - crop_box.left, y - crop_box.top) for x, y in region.polygon]
        elif spec.polygon_points is not None:
            x0, y0, x1, y1 = _inset(local, spec.shape_inset)
            points = [(x0 + px * (x1 - x0), y0 + py * (y1 - y0)) for px, py in spec.polygon_points]
        else:
            raise ConfigError(
                f"region {region.id!r} has no polygon geometry and extraction.polygon.points is not set",
                hint="declare polygon vertices; Slicra does not guess polygons",
            )
        draw.polygon(scaled(points), fill=255)

    if s > 1:
        return canvas.resize(size, Image.Resampling.BOX)
    return canvas
