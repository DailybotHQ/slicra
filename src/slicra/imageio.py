"""Image loading and normalization.

Every detector, the preview and the extractor receive the same normalized
image, so coordinates agree everywhere:

1. The file is opened read-only; the source is never modified.
2. EXIF orientation is applied (``ImageOps.exif_transpose``). All coordinates
   (manual regions, manifest boxes, preview) refer to this *upright* image.
3. The mode is normalized to ``RGB`` or ``RGBA`` (palette transparency,
   ``LA``, premultiplied ``RGBa`` and 16-bit grayscale are converted).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import ImageLoadError

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"})


@dataclass(frozen=True)
class LoadedImage:
    image: Image.Image
    path: Path | None
    original_size: tuple[int, int]
    exif_transposed: bool
    source_mode: str

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size


def normalize_mode(image: Image.Image) -> Image.Image:
    """Return an ``RGB`` or ``RGBA`` image, preserving any transparency."""
    if image.mode in ("RGB", "RGBA"):
        return image
    if image.mode == "RGBa":
        return image.convert("RGBA")
    has_alpha = image.mode in ("LA", "La", "PA") or "transparency" in image.info
    if image.mode in ("I;16", "I;16B", "I;16L", "I"):
        image = image.point(lambda v: v / 256).convert("L")
    if image.mode == "P" and has_alpha:
        return image.convert("RGBA")
    return image.convert("RGBA" if has_alpha else "RGB")


def load_image(source: str | Path | Image.Image, *, max_pixels: int = 150_000_000) -> LoadedImage:
    """Open and normalize an image from a path or an in-memory ``PIL.Image``."""
    if isinstance(source, Image.Image):
        if source.width == 0 or source.height == 0:
            raise ImageLoadError("image has zero width or height")
        orientation = source.getexif().get(0x0112, 1)
        oriented = ImageOps.exif_transpose(source)
        return LoadedImage(
            normalize_mode(oriented.copy()),
            None,
            source.size,
            orientation not in (None, 1),
            source.mode,
        )

    path = Path(source)
    if not path.exists():
        raise ImageLoadError(f"input not found: {path}")
    if not path.is_file():
        raise ImageLoadError(f"input is not a file: {path}")
    if path.stat().st_size == 0:
        raise ImageLoadError(f"input file is empty: {path}")

    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as opened:
                if opened.width * opened.height > max_pixels:
                    raise ImageLoadError(
                        f"{path} is {opened.width}x{opened.height}, above the {max_pixels:,} pixel limit",
                        hint="raise input.max_pixels if you trust this file",
                    )
                opened.load()
                original_size = opened.size
                source_mode = opened.mode
                orientation = opened.getexif().get(0x0112, 1)
                oriented = ImageOps.exif_transpose(opened)
                image = normalize_mode(oriented)
                if image is opened:
                    image = image.copy()
    except ImageLoadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageLoadError(
            f"{path} exceeds the configured pixel limit: {exc}",
            hint="raise input.max_pixels if you trust this file",
        ) from None
    except UnidentifiedImageError:
        raise ImageLoadError(f"not a recognized image (corrupt or unsupported format): {path}") from None
    except (OSError, SyntaxError) as exc:
        raise ImageLoadError(f"could not read image {path}: {exc}") from None
    finally:
        Image.MAX_IMAGE_PIXELS = previous

    if image.width == 0 or image.height == 0:
        raise ImageLoadError(f"image has zero width or height: {path}")
    return LoadedImage(image, path, original_size, orientation not in (None, 1), source_mode)


def iter_images(directory: Path, exclude: Path | None = None) -> list[Path]:
    """List supported images directly inside ``directory`` (sorted, non-recursive).

    Files under ``exclude`` (typically the output directory) are skipped so a
    batch never re-processes its own outputs.
    """
    excluded = exclude.resolve() if exclude is not None else None
    found: list[Path] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file() or entry.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if excluded is not None and excluded in entry.resolve().parents:
            continue
        found.append(entry)
    return found
