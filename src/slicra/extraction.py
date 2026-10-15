"""Crop, mask and resize regions in memory. The source image is never modified.

Resize modes (``output.resize``):

* ``contain`` (default): scale to fit inside width x height keeping the aspect
  ratio, then center on a canvas of exactly that size. The added area is
  transparent, or ``output.background`` when set. With only one dimension the
  other follows the aspect ratio and no canvas is added.
* ``cover``: scale to fill width x height keeping the aspect ratio, then
  center-crop the overflow.
* ``stretch``: resize to exactly width x height (aspect ratio may change).

Resizing RGBA uses premultiplied alpha internally (Pillow), so transparent
edges do not get dark fringes.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops

from .config import Config, Extraction, Resize, StarOptions
from .masks import ShapeSpec, build_mask
from .models import BBox, ExtractedRegion, Region


def shape_spec(extraction: Extraction, override: dict[str, Any] | None = None) -> ShapeSpec:
    override = override or {}
    star = extraction.star
    if "star" in override:
        star = StarOptions.model_validate(override["star"])
    return ShapeSpec(
        shape=override.get("shape", extraction.shape),
        shape_inset=extraction.shape_inset,
        antialias=extraction.antialias,
        supersample=extraction.supersample,
        circle_fit=override.get("circle_fit", extraction.circle_fit),
        star=star,
        polygon_points=tuple(extraction.polygon.points) if extraction.polygon else None,
    )


def crop_box_for(region: Region, spec: ShapeSpec, padding: int, image_size: tuple[int, int]) -> BBox:
    box = region.bbox.expand(padding, *image_size)
    if spec.shape == "circle" and spec.circle_fit == "center-square":
        side = min(box.width, box.height)
        left = box.left + (box.width - side) // 2
        top = box.top + (box.height - side) // 2
        box = BBox(left, top, left + side, top + side)
    return box


def resize_image(image: Image.Image, resize: Resize, background: tuple[int, int, int] | None) -> Image.Image:
    w, h = image.size
    resample = Image.Resampling.LANCZOS
    if resize.mode == "stretch":
        assert resize.width and resize.height
        return image.resize((resize.width, resize.height), resample)
    if resize.mode == "cover":
        assert resize.width and resize.height
        scale = max(resize.width / w, resize.height / h)
        if not resize.upscale:
            scale = min(scale, 1.0)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        scaled = image.resize((nw, nh), resample)
        left = max(0, (nw - resize.width) // 2)
        top = max(0, (nh - resize.height) // 2)
        return scaled.crop((left, top, left + min(nw, resize.width), top + min(nh, resize.height)))
    # contain
    scales = []
    if resize.width:
        scales.append(resize.width / w)
    if resize.height:
        scales.append(resize.height / h)
    scale = min(scales)
    if not resize.upscale:
        scale = min(scale, 1.0)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    scaled = image.resize((nw, nh), resample) if (nw, nh) != (w, h) else image
    if resize.width is None or resize.height is None:
        return scaled
    fill = (*background, 255) if background is not None else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (resize.width, resize.height), fill)
    canvas.alpha_composite(scaled, ((resize.width - nw) // 2, (resize.height - nh) // 2))
    return canvas


def extract_region(image: Image.Image, region: Region, config: Config) -> ExtractedRegion:
    spec = shape_spec(config.extraction, region.shape)
    crop_box = crop_box_for(region, spec, config.extraction.crop_padding, image.size)
    crop = image.crop(crop_box.as_tuple()).convert("RGBA")
    mask = build_mask(spec, region, crop_box)
    alpha = ImageChops.multiply(crop.getchannel("A"), mask)
    crop.putalpha(alpha)
    if config.output.resize is not None:
        crop = resize_image(crop, config.output.resize, config.output.background)
    return ExtractedRegion(region=region, image=crop, crop_box=crop_box, shape=spec.shape)


def extract_regions(image: Image.Image, regions: list[Region], config: Config) -> list[ExtractedRegion]:
    return [extract_region(image, region, config) for region in regions]
