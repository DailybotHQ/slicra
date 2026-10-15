"""Detector registry.

A detector is any callable ``(image, detection_config) -> DetectionResult``.
Built-in detectors are registered by mode name. ``register_detector`` is the
extension point for future detectors (for example an optional
``ai/segmentation`` plugin): a new detector also needs a configuration model
in :mod:`slicra.config`. See CONTRIBUTING.md.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PIL import Image

from ..config import (
    AutoDetection,
    ContoursDetection,
    GridAutoDetection,
    GridDetection,
    ManualDetection,
)
from ..errors import ConfigError, DetectionError, MissingDependencyError
from ..models import DetectionResult, DetectionWarning
from .contours import detect_contours
from .grid import detect_grid
from .grid_auto import detect_grid_auto
from .manual import detect_manual

Detector = Callable[[Image.Image, Any], DetectionResult]

_REGISTRY: dict[str, Detector] = {
    "grid": lambda image, cfg: detect_grid(image.size, cfg),
    "grid-auto": detect_grid_auto,
    "contours": detect_contours,
    "manual": lambda image, cfg: detect_manual(image.size, cfg),
}


def register_detector(mode: str, detector: Detector, *, replace: bool = False) -> None:
    if mode in _REGISTRY and not replace:
        raise ValueError(f"detector {mode!r} is already registered")
    _REGISTRY[mode] = detector


def available_detectors() -> list[str]:
    return sorted([*_REGISTRY, "auto"])


DOUBTFUL = frozenset({"background-not-uniform", "region-covers-image", "grid-auto-small-band"})


def detect_auto(image: Image.Image, cfg: AutoDetection) -> DetectionResult:
    """Try ``cfg.strategies`` in order; keep the first result that is trustworthy.

    A strategy is accepted when it returns at least one region, a score of at
    least ``min_score`` and no ``*-irregular`` warning nor any warning in
    ``DOUBTFUL`` (non-uniform background, a region covering the image, dropped
    content bands). ``grid-auto`` is additionally required to find densely filled
    cells (mean fill >= ``min_fill``): sparse objects separated by background
    are better served by ``contours``. Every attempt is recorded in ``details["attempts"]``.
    """
    attempts: list[dict[str, Any]] = []
    for strategy in cfg.strategies:
        try:
            if strategy == "grid-auto":
                result = detect_grid_auto(image, GridAutoDetection.model_validate(cfg.grid_auto))
            else:
                result = detect_contours(image, ContoursDetection.model_validate(cfg.contours))
        except (DetectionError, MissingDependencyError) as exc:
            attempts.append({"strategy": strategy, "accepted": False, "reason": exc.message})
            continue
        except ValueError as exc:
            raise ConfigError(f"detection.{strategy.replace('-', '_')}: {exc}") from None
        doubtful = [w.code for w in result.warnings if w.code.endswith("-irregular") or w.code in DOUBTFUL]
        score = result.score or 0.0
        sparse = strategy == "grid-auto" and result.details.get("mean_fill", 1.0) < cfg.min_fill
        if sparse:
            doubtful.append("grid-auto-sparse-cells")
        ok = result.region_count > 0 and score >= cfg.min_score and not doubtful
        reason = "accepted" if ok else f"score={score:.2f}, regions={result.region_count}, warnings={doubtful}"
        attempts.append({"strategy": strategy, "accepted": ok, "reason": reason, "score": score})
        if ok:
            result.details["attempts"] = attempts
            result.details["selected"] = strategy
            result.warnings.insert(0, DetectionWarning("auto-selected", f"auto mode selected strategy '{strategy}'"))
            return result
    summary = "; ".join(f"{a['strategy']}: {a['reason']}" for a in attempts)
    raise DetectionError(
        f"auto detection found no trustworthy strategy ({summary})",
        hint="run 'slicra inspect' with --mode grid/grid-auto/contours/manual and explicit parameters",
    )


def run_detector(image: Image.Image, cfg: Any) -> DetectionResult:
    if isinstance(cfg, AutoDetection):
        return detect_auto(image, cfg)
    detector = _REGISTRY.get(cfg.mode)
    if detector is None:
        raise ConfigError(f"no detector registered for mode {cfg.mode!r}")
    return detector(image, cfg)


__all__ = [
    "ContoursDetection",
    "Detector",
    "GridAutoDetection",
    "GridDetection",
    "ManualDetection",
    "available_detectors",
    "register_detector",
    "run_detector",
]
