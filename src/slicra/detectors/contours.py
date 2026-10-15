"""Connected-component detector (requires the ``opencv`` extra).

Suitable for sheets of **disjoint** objects on a uniform or transparent
background (sprite sheets, sticker sheets, shapes). It does not separate
overlapping objects and is not a semantic segmenter for photographic scenes.

Pipeline: background estimate -> per-pixel distance to background (or alpha)
-> threshold (fixed or Otsu) -> optional morphology (open, then close) ->
connected components -> per-component exact mask (holes kept or filled) and
outer contour.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from ..background import estimate_background
from ..config import ContoursDetection
from ..errors import DetectionError, MissingDependencyError
from ..models import BBox, DetectionResult, DetectionWarning, Region
from ..ordering import reading_order


def _require_cv() -> tuple[Any, Any]:
    try:
        import cv2
        import numpy as np
    except ImportError:  # pragma: no cover - exercised only without the extra
        raise MissingDependencyError(
            "mode 'contours' needs OpenCV and NumPy",
            hint="pip install 'slicra[opencv]'",
        ) from None
    return cv2, np


def detect_contours(image: Image.Image, cfg: ContoursDetection) -> DetectionResult:
    cv2, np = _require_cv()
    warnings: list[DetectionWarning] = []

    uniformity = 1.0
    background: str | tuple[int, int, int]
    if cfg.background == "auto":
        background, uniformity = estimate_background(image, cfg.background_tolerance, cfg.alpha_threshold)
        if uniformity < 0.9:
            warnings.append(
                DetectionWarning(
                    "background-not-uniform",
                    f"only {uniformity:.0%} of border pixels match the estimated background "
                    f"{background}; contours on busy backgrounds are unreliable",
                )
            )
    else:
        background = cfg.background

    arr = np.asarray(image)
    threshold_used: int | str
    if background == "transparent":
        if image.mode != "RGBA":
            alpha = np.full(arr.shape[:2], 255, dtype=np.uint8)
            warnings.append(DetectionWarning("no-alpha", "background 'transparent' but the image has no alpha channel"))
        else:
            alpha = arr[:, :, 3]
        cut = cfg.alpha_threshold if cfg.threshold == "auto" else cfg.threshold
        binary = (alpha > cut).astype(np.uint8)
        threshold_used = int(cut)
    else:
        assert not isinstance(background, str)
        rgb = arr[:, :, :3].astype(np.int16)
        distance = np.abs(rgb - np.array(background, dtype=np.int16)).max(axis=2).astype(np.uint8)
        if cfg.threshold == "auto":
            otsu, _ = cv2.threshold(distance, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            cut = int(max(otsu, cfg.background_tolerance))
            threshold_used = f"auto:{cut}"
        else:
            cut = cfg.threshold
            threshold_used = cut
        binary = (distance > cut).astype(np.uint8)
        if image.mode == "RGBA":
            binary &= (arr[:, :, 3] > cfg.alpha_threshold).astype(np.uint8)

    kernel = np.ones((cfg.morphology.kernel, cfg.morphology.kernel), np.uint8)
    if cfg.morphology.open:
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=cfg.morphology.open)
    if cfg.morphology.close:
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=cfg.morphology.close)

    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, connectivity=cfg.connectivity)
    small = large = 0
    candidates: list[Region] = []
    for label in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[label])
        if area < cfg.min_area:
            small += 1
            continue
        if cfg.max_area is not None and area > cfg.max_area:
            large += 1
            continue
        local = (labels[y : y + h, x : x + w] == label).astype(np.uint8) * 255
        contours, _ = cv2.findContours(local, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        outer = max(contours, key=cv2.contourArea)
        if cfg.holes == "fill":
            local = np.zeros_like(local)
            cv2.drawContours(local, contours, -1, 255, thickness=cv2.FILLED)
        polygon = tuple((float(px + x), float(py + y)) for px, py in outer.reshape(-1, 2))
        bbox_fill = area / float(w * h)
        candidates.append(
            Region(
                id="",
                bbox=BBox(x, y, x + w, y + h),
                polygon=polygon if len(polygon) >= 3 else None,
                area=int((local > 0).sum()),
                score=round(min(1.0, uniformity) * (0.5 + 0.5 * min(1.0, bbox_fill * 1.5)), 4),
                mask=Image.fromarray(local, mode="L"),
            )
        )
        if len(candidates) > cfg.max_regions:
            raise DetectionError(
                f"more than {cfg.max_regions} regions detected; likely noise",
                hint="raise min_area, add morphology.open or set a fixed threshold",
            )

    if small:
        warnings.append(
            DetectionWarning("below-min-area", f"ignored {small} component(s) smaller than min_area={cfg.min_area}")
        )
    if large:
        warnings.append(
            DetectionWarning("above-max-area", f"ignored {large} component(s) larger than max_area={cfg.max_area}")
        )
    image_area = image.width * image.height
    if any(r.bbox.area >= 0.9 * image_area for r in candidates):
        warnings.append(
            DetectionWarning(
                "region-covers-image",
                "a region covers almost the whole image; the background was probably not separated",
            )
        )

    regions = reading_order(candidates, prefix="shape")
    score = round(min((r.score or 0.0) for r in regions), 4) if regions else 0.0
    return DetectionResult(
        detector="contours",
        image_size=image.size,
        regions=regions,
        warnings=warnings,
        score=score,
        details={
            "background": background if isinstance(background, str) else list(background),
            "threshold": threshold_used,
            "components": count - 1,
            "ignored_small": small,
            "ignored_large": large,
        },
    )
