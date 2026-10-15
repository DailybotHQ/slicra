"""Typed configuration: YAML file + CLI overrides + defaults.

Precedence is **CLI > YAML > defaults**. YAML is always read with
``yaml.safe_load``; no arbitrary objects are ever constructed. Unknown keys are
rejected so typos fail loudly instead of being silently ignored.

Relative paths inside a configuration (``input.path``, ``output.directory``,
``detection.regions_file``, ``detection.template``) are resolved against the
current working directory.
"""

from __future__ import annotations

import copy
import re
import string
from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .errors import ConfigError

RGBColor = tuple[int, int, int]
ShapeName = Literal["rectangle", "ellipse", "circle", "polygon", "star", "original"]
SHAPES: tuple[str, ...] = ("rectangle", "ellipse", "circle", "polygon", "star", "original")
NAMING_FIELDS = frozenset({"index", "row", "col", "id", "stem"})
_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def parse_color(value: Any) -> RGBColor:
    """Parse ``"#RRGGBB"``, ``"RRGGBB"``, ``"white"``/``"black"`` or ``[r, g, b]``."""
    if isinstance(value, str):
        named = {"white": "ffffff", "black": "000000"}
        text = named.get(value.strip().lower(), value.strip())
        match = _HEX_RE.match(text)
        if not match:
            raise ValueError(f"invalid color {value!r}; use '#RRGGBB' or [r, g, b]")
        raw = match.group(1)
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    valid = isinstance(value, (list, tuple)) and len(value) == 3
    if valid and all(isinstance(c, int) and 0 <= c <= 255 for c in value):
        return (int(value[0]), int(value[1]), int(value[2]))
    raise ValueError(f"invalid color {value!r}; use '#RRGGBB' or [r, g, b] with 0-255 values")


def _background(value: Any) -> Any:
    if isinstance(value, str) and value.strip().lower() in {"auto", "transparent"}:
        return value.strip().lower()
    return parse_color(value)


BackgroundSpec = Literal["auto", "transparent"] | RGBColor


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- detection


class Margins(StrictModel):
    left: int = Field(0, ge=0)
    top: int = Field(0, ge=0)
    right: int = Field(0, ge=0)
    bottom: int = Field(0, ge=0)


class GridDetection(StrictModel):
    """Explicit grid: the region boxes are computed from rows/cols/margins/gaps."""

    mode: Literal["grid"] = "grid"
    rows: int = Field(..., ge=1, le=10_000)
    cols: int = Field(..., ge=1, le=10_000)
    margins: Margins = Margins()
    gap_x: int | list[int] = 0
    gap_y: int | list[int] = 0
    cell_width: int | None = Field(None, ge=1)
    cell_height: int | None = Field(None, ge=1)
    exclude: list[tuple[int, int]] = Field(default_factory=list)

    @field_validator("gap_x", "gap_y")
    @classmethod
    def _non_negative(cls, value: int | list[int]) -> int | list[int]:
        values = value if isinstance(value, list) else [value]
        if any(v < 0 for v in values):
            raise ValueError("gaps must be >= 0")
        return value

    @model_validator(mode="after")
    def _check_shapes(self) -> GridDetection:
        if isinstance(self.gap_x, list) and len(self.gap_x) != self.cols - 1:
            raise ValueError(f"gap_x list must have cols-1 = {self.cols - 1} values")
        if isinstance(self.gap_y, list) and len(self.gap_y) != self.rows - 1:
            raise ValueError(f"gap_y list must have rows-1 = {self.rows - 1} values")
        for row, col in self.exclude:
            if not (1 <= row <= self.rows and 1 <= col <= self.cols):
                raise ValueError(f"exclude cell ({row}, {col}) is outside the {self.rows}x{self.cols} grid")
        if len(set(self.exclude)) >= self.rows * self.cols:
            raise ValueError("exclude removes every cell of the grid")
        return self


class GridAutoDetection(StrictModel):
    """Infer a grid from background-colored separator rows and columns."""

    mode: Literal["grid-auto"] = "grid-auto"
    background: BackgroundSpec = "auto"
    tolerance: int = Field(24, ge=0, le=255)
    max_separator_fill: float = Field(0.02, ge=0.0, lt=1.0)
    min_gap: int = Field(2, ge=1)
    min_cell_size: int = Field(8, ge=1)
    rows: int | None = Field(None, ge=1)
    cols: int | None = Field(None, ge=1)
    skip_empty: bool = True
    silhouette: bool = False

    @field_validator("background", mode="before")
    @classmethod
    def _bg(cls, value: Any) -> Any:
        return _background(value)


class Morphology(StrictModel):
    open: int = Field(0, ge=0, le=20)
    close: int = Field(0, ge=0, le=20)
    kernel: int = Field(3, ge=1, le=31)

    @field_validator("kernel")
    @classmethod
    def _odd(cls, value: int) -> int:
        if value % 2 == 0:
            raise ValueError("kernel must be odd")
        return value


class ContoursDetection(StrictModel):
    """Connected components over a foreground mask (requires ``slicra[opencv]``)."""

    mode: Literal["contours"] = "contours"
    background: BackgroundSpec = "auto"
    threshold: Literal["auto"] | int = "auto"
    background_tolerance: int = Field(16, ge=0, le=255)
    alpha_threshold: int = Field(8, ge=0, le=254)
    min_area: int = Field(64, ge=1)
    max_area: int | None = Field(None, ge=1)
    connectivity: Literal[4, 8] = 8
    holes: Literal["keep", "fill"] = "keep"
    morphology: Morphology = Morphology()
    max_regions: int = Field(10_000, ge=1)

    @field_validator("background", mode="before")
    @classmethod
    def _bg(cls, value: Any) -> Any:
        return _background(value)

    @field_validator("threshold")
    @classmethod
    def _threshold(cls, value: Literal["auto"] | int) -> Literal["auto"] | int:
        if isinstance(value, int) and not 0 <= value <= 255:
            raise ValueError("threshold must be 'auto' or 0-255")
        return value

    @model_validator(mode="after")
    def _areas(self) -> ContoursDetection:
        if self.max_area is not None and self.max_area < self.min_area:
            raise ValueError("max_area must be >= min_area")
        return self


class StarOptions(StrictModel):
    points: int = Field(5, ge=3, le=200)
    inner_ratio: float = Field(0.5, gt=0.0, lt=1.0)
    outer_ratio: float = Field(1.0, gt=0.0, le=1.0)
    rotation: float = 0.0


class PolygonOptions(StrictModel):
    """Vertices relative to the shape box: (0, 0) is top-left, (1, 1) bottom-right."""

    points: list[tuple[float, float]] = Field(..., min_length=3)

    @field_validator("points")
    @classmethod
    def _range(cls, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for x, y in points:
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("relative polygon points must be within [0, 1]")
        if abs(polygon_area(points)) < 1e-9:
            raise ValueError("polygon is degenerate (zero area)")
        return points


def polygon_area(points: list[tuple[float, float]] | tuple[tuple[float, float], ...]) -> float:
    """Signed shoelace area."""
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2.0


class ManualRegion(StrictModel):
    """A region declared in absolute source-image pixel coordinates."""

    id: str | None = None
    rect: tuple[int, int, int, int] | None = None
    polygon: list[tuple[float, float]] | None = None
    shape: ShapeName | None = None
    star: StarOptions | None = None
    circle_fit: Literal["contain", "center-square"] | None = None

    @field_validator("id")
    @classmethod
    def _id(cls, value: str | None) -> str | None:
        if value is not None and not _ID_RE.match(value):
            raise ValueError("id must be 1-64 chars of letters, digits, '_', '.', '-' and start alphanumeric")
        return value

    @model_validator(mode="after")
    def _geometry(self) -> ManualRegion:
        if (self.rect is None) == (self.polygon is None):
            raise ValueError("each manual region needs exactly one of 'rect' or 'polygon'")
        if self.rect is not None:
            left, top, right, bottom = self.rect
            if right <= left or bottom <= top:
                raise ValueError(f"rect {list(self.rect)} must satisfy right > left and bottom > top")
        if self.polygon is not None:
            if len(self.polygon) < 3:
                raise ValueError("polygon needs at least 3 vertices")
            if abs(polygon_area(self.polygon)) < 1.0:
                raise ValueError("polygon is degenerate (area < 1 px)")
        if self.shape == "polygon" and self.polygon is None:
            raise ValueError("shape 'polygon' on a rect region needs explicit polygon vertices")
        return self


class ManualDetection(StrictModel):
    mode: Literal["manual"] = "manual"
    regions: list[ManualRegion] = Field(default_factory=list)
    regions_file: Path | None = None
    out_of_bounds: Literal["error", "clip"] = "error"
    overlap: Literal["allow", "warn", "error"] = "warn"

    @model_validator(mode="after")
    def _check(self) -> ManualDetection:
        if not self.regions and self.regions_file is None:
            raise ValueError("manual mode needs 'regions' or 'regions_file'")
        ids = [r.id for r in self.regions if r.id is not None]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate region ids: {dupes}")
        return self


class AutoDetection(StrictModel):
    """Try explicit strategies in order and keep the first trustworthy result."""

    mode: Literal["auto"] = "auto"
    strategies: list[Literal["grid-auto", "contours"]] = Field(default=["grid-auto", "contours"], min_length=1)
    min_score: float = Field(0.6, ge=0.0, le=1.0)
    min_fill: float = Field(0.85, ge=0.0, le=1.0)
    grid_auto: dict[str, Any] = Field(default_factory=dict)
    contours: dict[str, Any] = Field(default_factory=dict)


class TemplateDetection(StrictModel):
    """Reference a reusable preset; resolved into a concrete detector at load time."""

    mode: Literal["template"] = "template"
    template: str
    overrides: dict[str, Any] = Field(default_factory=dict)


Detection = Annotated[
    GridDetection | GridAutoDetection | ContoursDetection | ManualDetection | AutoDetection,
    Field(discriminator="mode"),
]
DETECTION_MODES = ("grid", "grid-auto", "contours", "manual", "auto", "template")


# --------------------------------------------------------------------------- extraction/output


class Extraction(StrictModel):
    shape: ShapeName = "rectangle"
    crop_padding: int = Field(0, ge=0, le=10_000)
    shape_inset: int = Field(0, ge=0, le=10_000)
    antialias: bool = True
    supersample: int = Field(4, ge=1, le=8)
    circle_fit: Literal["contain", "center-square"] = "contain"
    star: StarOptions = StarOptions()
    polygon: PolygonOptions | None = None


class Resize(StrictModel):
    width: int | None = Field(None, ge=1, le=20_000)
    height: int | None = Field(None, ge=1, le=20_000)
    mode: Literal["contain", "cover", "stretch"] = "contain"
    upscale: bool = True

    @model_validator(mode="after")
    def _dims(self) -> Resize:
        if self.width is None and self.height is None:
            raise ValueError("resize needs width and/or height")
        if self.mode in ("cover", "stretch") and (self.width is None or self.height is None):
            raise ValueError(f"resize mode '{self.mode}' needs both width and height")
        return self


class Output(StrictModel):
    directory: Path | None = None
    format: Literal["png", "webp", "jpeg"] = "png"
    quality: int = Field(90, ge=1, le=100)
    naming: str = "region_{index:03d}"
    overwrite: bool = False
    background: RGBColor | None = None
    resize: Resize | None = None

    @field_validator("format", mode="before")
    @classmethod
    def _alias(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.lower().lstrip(".")
            return "jpeg" if value == "jpg" else value
        return value

    @field_validator("background", mode="before")
    @classmethod
    def _color(cls, value: Any) -> Any:
        if value is None or (isinstance(value, str) and value.lower() == "transparent"):
            return None
        return parse_color(value)

    @field_validator("naming")
    @classmethod
    def _naming(cls, value: str) -> str:
        validate_naming(value)
        return value


def validate_naming(pattern: str) -> set[str]:
    """Validate a naming pattern and return the field names it uses."""
    if not pattern.strip():
        raise ValueError("naming pattern is empty")
    used: set[str] = set()
    try:
        parsed = list(string.Formatter().parse(pattern))
    except ValueError as exc:
        raise ValueError(f"invalid naming pattern {pattern!r}: {exc}") from exc
    for literal, field_name, _spec, _conv in parsed:
        if any(sep in literal for sep in ("/", "\\")) or ".." in literal:
            raise ValueError("naming pattern must not contain path separators or '..'")
        if field_name is None:
            continue
        if field_name not in NAMING_FIELDS:
            raise ValueError(f"unknown naming field {{{field_name}}}; allowed: {sorted(NAMING_FIELDS)}")
        used.add(field_name)
    if not used & {"index", "id", "row", "col"}:
        raise ValueError("naming pattern must include {index}, {id} or {row}/{col} to keep names unique")
    return used


class Preview(StrictModel):
    enabled: bool = True
    filename: str = "preview.png"
    labels: bool = True
    line_width: int | None = Field(None, ge=1, le=50)


class ManifestCfg(StrictModel):
    enabled: bool = True
    filename: str = "manifest.json"


class InputCfg(StrictModel):
    path: Path | None = None
    max_pixels: int = Field(150_000_000, ge=1)


class Config(StrictModel):
    version: Literal[1] = 1
    input: InputCfg = InputCfg()
    detection: Detection = AutoDetection()
    extraction: Extraction = Extraction()
    output: Output = Output()
    preview: Preview = Preview()
    manifest: ManifestCfg = ManifestCfg()
    source_template: str | None = Field(
        None, description="Set automatically when detection was resolved from a template."
    )

    @model_validator(mode="before")
    @classmethod
    def _resolve_template(cls, data: Any) -> Any:
        if isinstance(data, dict):
            detection = data.get("detection")
            if isinstance(detection, dict) and detection.get("mode") == "template":
                data = dict(data)
                tmpl = TemplateDetection.model_validate(detection)
                data["detection"], data["source_template"] = resolve_template(tmpl)
        return data

    @model_validator(mode="after")
    def _cross_checks(self) -> Config:
        if self.extraction.shape == "polygon" and self.extraction.polygon is None:
            manual_polys = isinstance(self.detection, ManualDetection) and (
                self.detection.regions_file is not None or all(r.polygon is not None for r in self.detection.regions)
            )
            if not manual_polys:
                raise ValueError(
                    "shape 'polygon' needs extraction.polygon.points (relative vertices) "
                    "unless every region carries its own polygon"
                )
        for name, value in (("preview.filename", self.preview.filename), ("manifest.filename", self.manifest.filename)):
            if Path(value).name != value or value in ("", ".", ".."):
                raise ValueError(f"{name} must be a plain file name")
        return self

    def to_public_dict(self) -> dict[str, Any]:
        """JSON-friendly dump used in the manifest and by ``validate``."""
        return self.model_dump(mode="json", exclude_none=True)


# --------------------------------------------------------------------------- templates


def builtin_templates() -> dict[str, str]:
    """Return ``{name: description}`` for the presets shipped inside the package."""
    found: dict[str, str] = {}
    for entry in resources.files("slicra.presets").iterdir():
        if entry.name.endswith(".yaml"):
            data = yaml.safe_load(entry.read_text(encoding="utf-8")) or {}
            found[entry.name[: -len(".yaml")]] = str(data.get("description", ""))
    return dict(sorted(found.items()))


def _read_template(name: str) -> tuple[dict[str, Any], str]:
    candidate = Path(name)
    if candidate.suffix in (".yaml", ".yml") or "/" in name or "\\" in name:
        if not candidate.is_file():
            raise ValueError(f"template file not found: {name}")
        return _safe_yaml(candidate.read_text(encoding="utf-8"), str(candidate)), str(candidate)
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
        raise ValueError(f"invalid template name {name!r}")
    resource = resources.files("slicra.presets").joinpath(f"{name}.yaml")
    if not resource.is_file():
        raise ValueError(f"unknown template {name!r}; built-in templates: {sorted(builtin_templates())}")
    return _safe_yaml(resource.read_text(encoding="utf-8"), name), f"builtin:{name}"


def resolve_template(tmpl: TemplateDetection) -> tuple[dict[str, Any], str]:
    data, source = _read_template(tmpl.template)
    detection = data.get("detection")
    if not isinstance(detection, dict):
        raise ValueError(f"template {source} has no 'detection' mapping")
    if detection.get("mode") == "template":
        raise ValueError("templates cannot reference other templates")
    merged = deep_merge(detection, tmpl.overrides)
    return merged, source


# --------------------------------------------------------------------------- loading


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def merge_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Apply CLI/API overrides on top of YAML data.

    When the override switches ``detection.mode`` (or switches to another
    ``template``), the YAML detection block is dropped instead of merged: its
    keys belong to a different detector or preset.
    """
    base = copy.deepcopy(base)
    det_override = overrides.get("detection")
    if isinstance(det_override, dict) and "mode" in det_override:
        current = base.get("detection") or {}
        switched = not isinstance(current, dict) or current.get("mode") != det_override["mode"]
        if switched or current.get("template") != det_override.get("template", current.get("template")):
            base["detection"] = {}
    return deep_merge(base, overrides)


def _safe_yaml(text: str, origin: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{origin}: invalid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{origin}: top level must be a mapping")
    return data


def read_config_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}", hint="create one with 'slicra init'")
    return _safe_yaml(path.read_text(encoding="utf-8"), str(path))


def format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        msg = err["msg"].removeprefix("Value error, ")
        lines.append(f"  - {loc or '<root>'}: {msg}")
    return "invalid configuration:\n" + "\n".join(lines)


def build_config(data: dict[str, Any] | None = None, overrides: dict[str, Any] | None = None) -> Config:
    merged = merge_overrides(data or {}, overrides or {})
    try:
        return Config.model_validate(merged)
    except ValidationError as exc:
        raise ConfigError(format_validation_error(exc)) from None
    except ValueError as exc:  # template resolution errors raised before field validation
        raise ConfigError(f"invalid configuration: {exc}") from None


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Load a YAML config (optional) and apply overrides (CLI > YAML > defaults)."""
    data = read_config_file(path) if path is not None else {}
    return build_config(data, overrides)
