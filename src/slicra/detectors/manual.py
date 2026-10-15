"""Manual regions: rectangles and polygons declared in source-pixel coordinates.

Regions keep the order in which they are declared (the user chose it). IDs
default to ``m001``, ``m002``... Out-of-bounds geometry is an error unless
``out_of_bounds: clip``. Overlapping regions are allowed — each one is
exported independently from the untouched source — and reported according to
``overlap`` (``allow`` / ``warn`` / ``error``).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ..config import ManualDetection, ManualRegion, format_validation_error
from ..errors import ConfigError, DetectionError
from ..models import BBox, DetectionResult, DetectionWarning, Polygon, Region


def load_regions_file(path: Path) -> list[ManualRegion]:
    if not path.is_file():
        raise ConfigError(f"regions_file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data: Any = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"{path}: cannot parse regions: {exc}") from None
    if isinstance(data, dict):
        data = data.get("regions")
    if not isinstance(data, list):
        raise ConfigError(f"{path}: expected a list of regions or a mapping with 'regions'")
    try:
        return [ManualRegion.model_validate(item) for item in data]
    except ValidationError as exc:
        raise ConfigError(f"{path}: " + format_validation_error(exc)) from None


def _shape_override(spec: ManualRegion) -> dict[str, Any] | None:
    override: dict[str, Any] = {}
    if spec.shape is not None:
        override["shape"] = spec.shape
    if spec.star is not None:
        override["star"] = spec.star.model_dump()
    if spec.circle_fit is not None:
        override["circle_fit"] = spec.circle_fit
    return override or None


def detect_manual(image_size: tuple[int, int], cfg: ManualDetection) -> DetectionResult:
    width, height = image_size
    specs = list(cfg.regions)
    if cfg.regions_file is not None:
        specs += load_regions_file(cfg.regions_file)
    ids = [s.id for s in specs if s.id]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ConfigError(f"duplicate manual region ids: {dupes}")

    warnings: list[DetectionWarning] = []
    regions: list[Region] = []
    for n, spec in enumerate(specs, start=1):
        rid = spec.id or f"m{n:03d}"
        polygon: Polygon | None = None
        if spec.rect is not None:
            left, top, right, bottom = spec.rect
        else:
            assert spec.polygon is not None
            polygon = tuple((float(x), float(y)) for x, y in spec.polygon)
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            left, top = math.floor(min(xs)), math.floor(min(ys))
            right, bottom = math.ceil(max(xs)), math.ceil(max(ys))
            right, bottom = max(right, left + 1), max(bottom, top + 1)
        inside = left >= 0 and top >= 0 and right <= width and bottom <= height
        if not inside:
            if cfg.out_of_bounds == "error":
                raise DetectionError(
                    f"region {rid!r} ({left}, {top}, {right}, {bottom}) is outside the {width}x{height} image",
                    hint="fix the coordinates or set detection.out_of_bounds: clip",
                )
            left, top = max(0, left), max(0, top)
            right, bottom = min(width, right), min(height, bottom)
            if right <= left or bottom <= top:
                raise DetectionError(f"region {rid!r} lies completely outside the {width}x{height} image")
            warnings.append(DetectionWarning("region-clipped", f"region {rid!r} was clipped to the image"))
        box = BBox(left, top, right, bottom)
        regions.append(
            Region(
                id=rid,
                bbox=box,
                index=n,
                polygon=polygon,
                area=box.area,
                shape=_shape_override(spec),
            )
        )

    overlaps = [(a.id, b.id) for i, a in enumerate(regions) for b in regions[i + 1 :] if a.bbox.intersects(b.bbox)]
    if overlaps and cfg.overlap != "allow":
        message = "overlapping regions (exported independently): " + ", ".join(f"{a}/{b}" for a, b in overlaps)
        if cfg.overlap == "error":
            raise DetectionError(message, hint="set detection.overlap: warn or allow to accept overlaps")
        warnings.append(DetectionWarning("regions-overlap", message))

    return DetectionResult(
        detector="manual",
        image_size=image_size,
        regions=regions,
        warnings=warnings,
        details={"declared": len(specs)},
    )
