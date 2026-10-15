"""Writing outputs: region images, preview and manifest.

Safety rules:

* File names come from ``output.naming``; the rendered name is sanitized
  (no separators, no ``..``, no control or reserved characters) and must stay
  inside the output directory.
* All target paths are computed and checked **before** anything is written:
  duplicate names are an error, and existing files are an error unless
  ``overwrite`` is enabled.
* JPEG has no alpha channel: images are flattened against
  ``output.background`` (white when unset) and a warning is recorded.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from ._version import __version__
from .config import Config
from .errors import ConfigError, ExportError
from .imageio import LoadedImage
from .models import DetectionResult, DetectionWarning, ExtractedRegion, Region

MANIFEST_SCHEMA_VERSION = 1
EXTENSIONS = {"png": ".png", "webp": ".webp", "jpeg": ".jpg"}
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def sanitize_name(name: str) -> str:
    cleaned = _UNSAFE.sub("_", name).strip().strip(".")
    cleaned = cleaned.replace("..", "_")
    if not cleaned:
        raise ExportError(f"naming produced an empty file name from {name!r}")
    if cleaned.split(".")[0].lower() in _RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:200]


def render_name(pattern: str, region: Region, stem: str) -> str:
    values: dict[str, Any] = {"index": region.index, "id": region.id, "stem": stem}
    if region.row is not None:
        values["row"] = region.row
    if region.col is not None:
        values["col"] = region.col
    try:
        return sanitize_name(pattern.format(**values))
    except KeyError as exc:
        raise ConfigError(
            f"naming field {exc} is not available for region {region.id!r} "
            "(row/col exist only for grid-like detections)",
            hint="use {index} or {id} in output.naming",
        ) from None
    except (ValueError, IndexError) as exc:
        raise ConfigError(f"cannot apply naming pattern {pattern!r}: {exc}") from None


def plan_outputs(regions: list[Region], config: Config, output_dir: Path, stem: str) -> list[Path]:
    ext = EXTENSIONS[config.output.format]
    root = output_dir.resolve()
    paths: list[Path] = []
    seen: dict[str, str] = {}
    reserved = set()
    if config.preview.enabled:
        reserved.add(config.preview.filename.lower())
    if config.manifest.enabled:
        reserved.add(config.manifest.filename.lower())
    for region in regions:
        filename = render_name(config.output.naming, region, stem) + ext
        key = filename.lower()  # case-insensitive filesystems (macOS, Windows)
        if key in seen:
            raise ExportError(
                f"naming pattern produces duplicate file name {filename!r} for regions {seen[key]!r} and {region.id!r}",
                hint="include {index} or {id} in output.naming",
            )
        if key in reserved:
            raise ExportError(f"region file name {filename!r} collides with the preview/manifest name")
        seen[key] = region.id
        target = safe_target(root / filename, root)
        if target.parent != root:
            raise ExportError(f"refusing to write outside the output directory: {filename!r}")
        paths.append(target)
    return paths


def same_file(a: Path, b: Path) -> bool:
    """True when two paths name the same file (follows symlinks, case-insensitive filesystems)."""
    try:
        if a.exists() and b.exists():
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.normcase(str(a.resolve())).casefold() == os.path.normcase(str(b.resolve())).casefold()


def safe_target(path: Path, root: Path) -> Path:
    """Resolve ``path`` and require it to stay inside ``root`` and not to be a symlink."""
    if path.is_symlink():
        raise ExportError(f"refusing to write through a symbolic link: {path}")
    resolved = path.resolve()
    root = root.resolve()
    if resolved != root and root not in resolved.parents:
        raise ExportError(f"refusing to write outside the output directory: {path}")
    return resolved


def check_conflicts(paths: list[Path], overwrite: bool) -> None:
    if overwrite:
        return
    existing = [p for p in paths if p.exists()]
    if existing:
        shown = ", ".join(p.name for p in existing[:5])
        more = f" (+{len(existing) - 5} more)" if len(existing) > 5 else ""
        raise ExportError(
            f"{len(existing)} output file(s) already exist: {shown}{more}",
            hint="choose another --output directory or pass --overwrite",
        )


def save_image(image: Image.Image, path: Path, config: Config) -> list[DetectionWarning]:
    fmt = config.output.format
    warnings: list[DetectionWarning] = []
    if fmt == "jpeg":
        color = config.output.background or (255, 255, 255)
        flat = Image.new("RGB", image.size, color)
        if image.mode == "RGBA":
            low, _high = image.getchannel("A").getextrema()
            if isinstance(low, (int, float)) and low < 255:
                warnings.append(
                    DetectionWarning(
                        "jpeg-flattened",
                        f"{path.name}: JPEG has no alpha; transparency flattened against {list(color)}",
                    )
                )
            flat.paste(image, (0, 0), image)
        else:
            flat.paste(image)
        flat.save(path, "JPEG", quality=config.output.quality, optimize=True)
    elif fmt == "webp":
        image.save(path, "WEBP", quality=config.output.quality, method=4)
    else:
        image.save(path, "PNG", optimize=False)
    return warnings


def write_atomic_text(path: Path, text: str) -> None:
    """Write via a fresh, uniquely named temp file in the same directory, then rename."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def build_manifest(
    *,
    loaded: LoadedImage,
    config: Config,
    detection: DetectionResult,
    extracted: list[ExtractedRegion],
    outputs: list[Path],
    output_dir: Path,
    preview_path: Path | None,
    manifest_path: Path,
    warnings: list[DetectionWarning],
) -> dict[str, Any]:
    root = output_dir.resolve()

    def rel(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)

    regions = []
    for item, path in zip(extracted, outputs, strict=True):
        entry = item.region.to_dict()
        entry["crop_box"] = list(item.crop_box.as_tuple())
        entry["shape"] = item.shape
        entry["output"] = rel(path)
        entry["output_size"] = list(item.image.size)
        regions.append(entry)
    files = [rel(p) for p in outputs]
    if preview_path is not None:
        files.append(rel(preview_path))
    files.append(rel(manifest_path))
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "tool": {"name": "slicra", "version": __version__},
        "source": {
            "path": str(loaded.path) if loaded.path else None,
            "width": loaded.size[0],
            "height": loaded.size[1],
            "mode": loaded.image.mode,
            "source_mode": loaded.source_mode,
            "original_size": list(loaded.original_size),
            "exif_transposed": loaded.exif_transposed,
            "coordinates": "EXIF-normalized pixels; bbox = [left, top, right, bottom], right/bottom exclusive",
        },
        "detector": {
            "mode": detection.detector,
            "score": detection.score,
            "score_note": "heuristic quality indicator, not a calibrated probability",
            "details": detection.details,
        },
        "config": config.to_public_dict(),
        "region_count": len(regions),
        "warnings": [w.to_dict() for w in warnings],
        "regions": regions,
        "files": files,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    write_atomic_text(path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
