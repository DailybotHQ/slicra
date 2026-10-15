"""Slicra: detect, slice and mask multiple regions of an image, locally.

Public API::

    from slicra import ImageSlicer

    slicer = ImageSlicer.from_config("slicra.yaml")
    result = slicer.extract("avatars.png", output_dir="avatars")
    print(result.region_count, result.manifest_path)
"""

from ._version import __version__
from .config import Config, build_config, load_config
from .detectors import available_detectors, register_detector
from .errors import (
    ConfigError,
    DetectionError,
    ExportError,
    ImageLoadError,
    MissingDependencyError,
    NoRegionsError,
    SlicraError,
)
from .models import (
    BatchResult,
    BBox,
    DetectionResult,
    DetectionWarning,
    ExtractedRegion,
    ExtractionResult,
    Region,
)
from .pipeline import ImageSlicer

__all__ = [
    "BBox",
    "BatchResult",
    "Config",
    "ConfigError",
    "DetectionError",
    "DetectionResult",
    "DetectionWarning",
    "ExportError",
    "ExtractedRegion",
    "ExtractionResult",
    "ImageLoadError",
    "ImageSlicer",
    "MissingDependencyError",
    "NoRegionsError",
    "Region",
    "SlicraError",
    "__version__",
    "available_detectors",
    "build_config",
    "load_config",
    "register_detector",
]
