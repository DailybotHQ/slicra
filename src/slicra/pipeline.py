"""The single engine shared by the Python API and the CLI.

``load -> detect -> (preview) -> crop -> mask -> resize -> export -> manifest``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .config import Config, build_config, load_config
from .detectors import run_detector
from .errors import ConfigError, ExportError, NoRegionsError, SlicraError
from .export import (
    build_manifest,
    check_conflicts,
    plan_outputs,
    safe_target,
    same_file,
    save_image,
    write_manifest,
)
from .extraction import extract_regions
from .imageio import LoadedImage, iter_images, load_image
from .models import BatchResult, DetectionResult, DetectionWarning, ExtractedRegion, ExtractionResult
from .preview import render_preview

ImageSource = str | Path | Image.Image


class ImageSlicer:
    """Detect regions in an image and export them as individual images.

    >>> slicer = ImageSlicer.from_config("slicra.yaml")    # doctest: +SKIP
    >>> result = slicer.extract("avatars.png", output_dir="out")  # doctest: +SKIP
    >>> result.region_count, result.manifest_path               # doctest: +SKIP
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config if config is not None else Config()

    # ------------------------------------------------------------------ constructors

    @classmethod
    def from_config(cls, path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> ImageSlicer:
        """Load a YAML file; ``overrides`` (nested dict) win over the file."""
        return cls(load_config(path, overrides))

    @classmethod
    def from_dict(cls, data: dict[str, Any], overrides: dict[str, Any] | None = None) -> ImageSlicer:
        return cls(build_config(data, overrides))

    # ------------------------------------------------------------------ in-memory API

    def load(self, source: ImageSource | None = None) -> LoadedImage:
        if source is None:
            source = self.config.input.path
        if source is None:
            raise ConfigError("no input image given", hint="pass an image path or set input.path in the config")
        return load_image(source, max_pixels=self.config.input.max_pixels)

    def _detect_loaded(self, loaded: LoadedImage) -> DetectionResult:
        return run_detector(loaded.image, self.config.detection)

    def detect(self, source: ImageSource | None = None) -> DetectionResult:
        """Detect regions without writing anything. Zero regions is a valid result here."""
        return self._detect_loaded(self.load(source))

    def render(self, source: ImageSource | None = None) -> list[ExtractedRegion]:
        """Return cropped/masked/resized regions as ``PIL.Image`` objects (no files)."""
        loaded = self.load(source)
        detection = self._require_regions(self._detect_loaded(loaded))
        return extract_regions(loaded.image, detection.regions, self.config)

    def preview(self, source: ImageSource | None = None, output: str | Path | None = None) -> Image.Image:
        """Render the preview; also save it when ``output`` is given (no other files)."""
        loaded = self.load(source)
        detection = self._detect_loaded(loaded)
        image = render_preview(
            loaded.image,
            detection.regions,
            labels=self.config.preview.labels,
            line_width=self.config.preview.line_width,
        )
        if output is not None:
            target = Path(output)
            if target.is_symlink():
                raise ExportError(f"refusing to write through a symbolic link: {target}")
            if loaded.path is not None and same_file(target, loaded.path):
                raise ExportError(f"refusing to overwrite the input image {loaded.path}")
            if target.exists() and not self.config.output.overwrite:
                raise ExportError(f"{target} already exists", hint="pass --overwrite or choose another path")
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, "PNG")
        return image

    # ------------------------------------------------------------------ file output

    @staticmethod
    def _require_regions(detection: DetectionResult) -> DetectionResult:
        if detection.region_count == 0:
            notes = "; ".join(w.message for w in detection.warnings) or "no diagnostics"
            raise NoRegionsError(
                f"{detection.detector}: detected 0 regions ({notes})",
                hint="run 'slicra inspect' and adjust thresholds, min_area or the detection mode",
            )
        return detection

    def extract(
        self,
        source: ImageSource | None = None,
        output_dir: str | Path | None = None,
        *,
        overwrite: bool | None = None,
        preview: bool | None = None,
        stem: str | None = None,
        preview_path: str | Path | None = None,
        manifest_path: str | Path | None = None,
        reserved: set[str] | None = None,
    ) -> ExtractionResult:
        """Detect, export every region, the optional preview and the manifest.

        ``preview_path``/``manifest_path`` override the default locations
        (``<output_dir>/preview.png`` and ``<output_dir>/manifest.json``).
        ``reserved`` (used by batch runs) holds paths already written in the same
        run; colliding with one is an error even with ``overwrite``.
        """
        config = self.config
        out = Path(output_dir) if output_dir is not None else config.output.directory
        if out is None:
            raise ConfigError("no output directory", hint="pass --output or set output.directory")
        overwrite = config.output.overwrite if overwrite is None else overwrite
        want_preview = config.preview.enabled if preview is None else preview

        loaded = self.load(source)
        detection = self._require_regions(self._detect_loaded(loaded))
        extracted = extract_regions(loaded.image, detection.regions, config)

        name_stem = stem or (loaded.path.stem if loaded.path else "image")
        outputs = plan_outputs(detection.regions, config, out, name_stem)
        root = out.resolve()
        preview_target = safe_target(Path(preview_path) if preview_path else root / config.preview.filename, root)
        manifest_target = safe_target(Path(manifest_path) if manifest_path else root / config.manifest.filename, root)
        preview_out = preview_target if want_preview else None
        planned = outputs + [p for p in (preview_out,) if p is not None]
        if config.manifest.enabled:
            planned.append(manifest_target)
        if len({p.as_posix().casefold() for p in planned}) != len(planned):
            raise ExportError("output, preview and manifest paths collide")
        if loaded.path is not None and any(same_file(p, loaded.path) for p in planned):
            raise ExportError(f"refusing to overwrite the input image {loaded.path}")
        if reserved is not None:
            clashes = [p for p in planned if p.as_posix().casefold() in reserved]
            if clashes:
                raise ExportError(
                    f"{clashes[0].name} was already written by another image in this batch",
                    hint="include {stem} in output.naming or rename the colliding inputs",
                )
        check_conflicts(planned, overwrite)
        if reserved is not None:
            reserved.update(p.as_posix().casefold() for p in planned)

        root.mkdir(parents=True, exist_ok=True)
        for extra in (preview_out, manifest_target if config.manifest.enabled else None):
            if extra is not None:
                extra.parent.mkdir(parents=True, exist_ok=True)
        warnings: list[DetectionWarning] = list(detection.warnings)
        for item, path in zip(extracted, outputs, strict=True):
            warnings += save_image(item.image, path, config)
        if preview_out is not None:
            render_preview(
                loaded.image, detection.regions, labels=config.preview.labels, line_width=config.preview.line_width
            ).save(preview_out, "PNG")
        written_manifest: Path | None = None
        if config.manifest.enabled:
            manifest = build_manifest(
                loaded=loaded,
                config=config,
                detection=detection,
                extracted=extracted,
                outputs=outputs,
                output_dir=root,
                preview_path=preview_out,
                manifest_path=manifest_target,
                warnings=warnings,
            )
            write_manifest(manifest_target, manifest)
            written_manifest = manifest_target
        return ExtractionResult(
            source=loaded.path,
            output_dir=root,
            detection=detection,
            outputs=outputs,
            manifest_path=written_manifest,
            preview_path=preview_out,
            warnings=warnings,
        )

    def extract_batch(
        self,
        input_dir: str | Path,
        output_dir: str | Path | None = None,
        *,
        overwrite: bool | None = None,
        preview: bool | None = None,
        flat: bool = False,
    ) -> BatchResult:
        """Process every supported image directly inside ``input_dir``.

        By default each image gets its own sub-directory ``<output_dir>/<stem>/``.
        With ``flat=True`` every region image lands directly in ``output_dir``
        (the naming pattern gets a ``{stem}_`` prefix unless it already uses
        ``{stem}``), while previews and manifests go to
        ``<output_dir>/_previews/<stem>.png`` and ``<output_dir>/_manifests/<stem>.json``.
        Files inside the output directory are never treated as inputs. One
        failing image does not stop the batch; failures are reported in the result.
        """
        directory = Path(input_dir)
        if not directory.is_dir():
            raise ConfigError(f"input directory not found: {directory}")
        out = Path(output_dir) if output_dir is not None else self.config.output.directory
        if out is None:
            raise ConfigError("no output directory", hint="pass --output or set output.directory")
        if out.resolve() == directory.resolve():
            raise ConfigError("the output directory must differ from the input directory")
        images = iter_images(directory, exclude=out)
        if not images:
            raise ConfigError(f"no supported images found in {directory}")
        keys = batch_keys(images)
        runner = self
        if flat and "{stem" not in self.config.output.naming:
            naming = "{stem}_" + self.config.output.naming
            runner = ImageSlicer(
                self.config.model_copy(update={"output": self.config.output.model_copy(update={"naming": naming})})
            )
        results: list[ExtractionResult] = []
        failures: dict[Path, str] = {}
        codes: dict[Path, int] = {}
        written: set[str] = set()
        for path, key in zip(images, keys, strict=True):
            try:
                if flat:
                    result = runner.extract(
                        path,
                        out,
                        overwrite=overwrite,
                        preview=preview,
                        stem=key,
                        preview_path=out / "_previews" / f"{key}.png",
                        manifest_path=out / "_manifests" / f"{key}.json",
                        reserved=written,
                    )
                else:
                    result = runner.extract(
                        path, out / key, overwrite=overwrite, preview=preview, stem=path.stem, reserved=written
                    )
                results.append(result)
            except SlicraError as exc:
                failures[path] = str(exc)
                codes[path] = exc.exit_code
        return BatchResult(output_dir=out.resolve(), results=results, failures=failures, failure_codes=codes)


def batch_keys(images: list[Path]) -> list[str]:
    """Unique, case-insensitive per-image keys for batch output folders/prefixes.

    The key is the file stem; stems shared by several files (``a.png``/``a.jpg``)
    get the extension appended, and any remaining clash gets ``_2``, ``_3``...
    """
    stems = [p.stem.casefold() for p in images]
    keys: list[str] = []
    taken: set[str] = set()
    for path, folded in zip(images, stems, strict=True):
        key = path.stem if stems.count(folded) == 1 else f"{path.stem}_{path.suffix.lstrip('.').lower()}"
        candidate, n = key, 2
        while candidate.casefold() in taken:
            candidate = f"{key}_{n}"
            n += 1
        taken.add(candidate.casefold())
        keys.append(candidate)
    return keys
