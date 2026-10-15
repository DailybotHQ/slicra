"""Public data models shared by detectors, the extractor, the exporter and the CLI.

Coordinates are always expressed in pixels of the *normalized* source image
(after EXIF orientation has been applied). Boxes use ``(left, top, right,
bottom)`` with **exclusive** right and bottom edges, the same convention as
Pillow's ``Image.crop``: a box ``(0, 0, 10, 10)`` covers exactly 100 pixels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

Point = tuple[float, float]
Polygon = tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class BBox:
    """Axis-aligned box with exclusive right/bottom edges."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError(f"degenerate box {self.as_tuple()}: right/bottom must exceed left/top")

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)

    def intersects(self, other: BBox) -> bool:
        return (
            self.left < other.right and other.left < self.right and self.top < other.bottom and other.top < self.bottom
        )

    def expand(self, amount: int, width: int, height: int) -> BBox:
        """Grow by ``amount`` pixels on every side, clamped to the image."""
        return BBox(
            max(0, self.left - amount),
            max(0, self.top - amount),
            min(width, self.right + amount),
            min(height, self.bottom + amount),
        )


@dataclass(frozen=True, slots=True)
class DetectionWarning:
    """A non-fatal diagnostic. ``code`` is stable and machine-readable."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class Region:
    """One detected (or declared) region of the source image.

    ``polygon`` is an optional outline in source coordinates. ``mask`` is an
    optional exact alpha mask (mode ``"L"``, same size as ``bbox``) produced by
    detectors that know the precise silhouette, such as ``contours``.
    ``shape`` optionally overrides the configured extraction shape for this
    region only (used by manual regions).
    """

    id: str
    bbox: BBox
    index: int = 0
    row: int | None = None
    col: int | None = None
    polygon: Polygon | None = None
    area: int | None = None
    score: float | None = None
    shape: dict[str, Any] | None = None
    mask: Image.Image | None = field(default=None, compare=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "index": self.index,
            "bbox": list(self.bbox.as_tuple()),
            "width": self.bbox.width,
            "height": self.bbox.height,
        }
        if self.row is not None:
            data["row"] = self.row
        if self.col is not None:
            data["col"] = self.col
        if self.area is not None:
            data["area"] = self.area
        if self.score is not None:
            data["score"] = round(self.score, 4)
        if self.polygon is not None:
            data["polygon_points"] = len(self.polygon)
        if self.mask is not None:
            data["has_mask"] = True
        if self.shape is not None:
            data["shape_override"] = self.shape
        return data


@dataclass
class DetectionResult:
    """Output of a detector: ordered regions plus diagnostics.

    ``score`` is a heuristic quality indicator in ``[0, 1]``; it is **not** a
    calibrated probability.
    """

    detector: str
    image_size: tuple[int, int]
    regions: list[Region]
    warnings: list[DetectionWarning] = field(default_factory=list)
    score: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def region_count(self) -> int:
        return len(self.regions)


@dataclass(frozen=True)
class ExtractedRegion:
    """A region rendered in memory (cropped, masked and resized)."""

    region: Region
    image: Image.Image
    crop_box: BBox
    shape: str


@dataclass
class ExtractionResult:
    """Everything produced by one ``extract`` call on a single image."""

    source: Path | None
    output_dir: Path
    detection: DetectionResult
    outputs: list[Path]
    manifest_path: Path | None
    preview_path: Path | None
    warnings: list[DetectionWarning]

    @property
    def region_count(self) -> int:
        return len(self.outputs)

    @property
    def regions(self) -> list[Region]:
        return self.detection.regions


@dataclass
class BatchResult:
    """Result of processing every image in a directory."""

    output_dir: Path
    results: list[ExtractionResult]
    failures: dict[Path, str]

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def region_count(self) -> int:
        return sum(r.region_count for r in self.results)
