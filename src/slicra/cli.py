"""Command-line interface. Thin layer over :class:`slicra.ImageSlicer`.

Exit codes: 0 ok, 1 unexpected error, 2 invalid configuration/usage,
3 detection failed or found zero regions, 4 image could not be loaded,
5 output conflict or write error, 6 missing optional dependency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from ._version import __version__
from .config import DETECTION_MODES, SHAPES, builtin_templates, format_validation_error, read_config_file
from .errors import ConfigError, SlicraError
from .init_templates import TEMPLATES
from .models import DetectionResult
from .pipeline import ImageSlicer

app = typer.Typer(
    name="slicra",
    help="Detect, slice and mask multiple regions of an image — locally and deterministically.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"slicra {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version and exit.")
    ] = False,
) -> None:
    """Slicra command-line interface."""


# --------------------------------------------------------------------------- shared options

ConfigOpt = Annotated[Path | None, typer.Option("--config", "-c", help="YAML configuration file.")]
ModeOpt = Annotated[str | None, typer.Option("--mode", "-m", help=f"Detection mode: {', '.join(DETECTION_MODES)}.")]
TemplateOpt = Annotated[str | None, typer.Option("--template", help="Built-in template name or template YAML path.")]
RowsOpt = Annotated[int | None, typer.Option("--rows", help="Grid rows.")]
ColsOpt = Annotated[int | None, typer.Option("--cols", help="Grid columns.")]
GapXOpt = Annotated[int | None, typer.Option("--gap-x", help="Horizontal gap between columns (px).")]
GapYOpt = Annotated[int | None, typer.Option("--gap-y", help="Vertical gap between rows (px).")]
GapOpt = Annotated[int | None, typer.Option("--gap", help="Set both --gap-x and --gap-y (px).")]
MarginOpt = Annotated[int | None, typer.Option("--margin", help="Outer margin on all four sides (px).")]
CellWOpt = Annotated[int | None, typer.Option("--cell-width", help="Explicit grid cell width (px).")]
CellHOpt = Annotated[int | None, typer.Option("--cell-height", help="Explicit grid cell height (px).")]
BgOpt = Annotated[str | None, typer.Option("--background", help="auto, transparent or #RRGGBB.")]
ThreshOpt = Annotated[str | None, typer.Option("--threshold", help="contours: 'auto' or 0-255.")]
TolOpt = Annotated[int | None, typer.Option("--tolerance", help="grid-auto: background tolerance 0-255.")]
MinAreaOpt = Annotated[int | None, typer.Option("--min-area", help="contours: minimum component area (px).")]
ShapeOpt = Annotated[str | None, typer.Option("--shape", "-s", help=f"Mask shape: {', '.join(SHAPES)}.")]
PadOpt = Annotated[int | None, typer.Option("--padding", help="crop_padding: grow each crop box (px).")]
InsetOpt = Annotated[int | None, typer.Option("--inset", help="shape_inset: shrink the mask inside the crop (px).")]
FormatOpt = Annotated[str | None, typer.Option("--format", "-f", help="png, webp or jpeg.")]
QualityOpt = Annotated[int | None, typer.Option("--quality", help="Quality for webp/jpeg (1-100).")]
NamingOpt = Annotated[str | None, typer.Option("--naming", help="Pattern with {index}, {row}, {col}, {id}, {stem}.")]
WidthOpt = Annotated[int | None, typer.Option("--width", help="Resize width (px).")]
HeightOpt = Annotated[int | None, typer.Option("--height", help="Resize height (px).")]
ResizeOpt = Annotated[str | None, typer.Option("--resize-mode", help="contain, cover or stretch.")]
BgColorOpt = Annotated[str | None, typer.Option("--fill", help="Background color for jpeg/contain padding (#RRGGBB).")]
OverwriteOpt = Annotated[bool, typer.Option("--overwrite", help="Allow replacing existing output files.")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")]


def _set(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def collect_overrides(config_data: dict[str, Any], **opts: Any) -> dict[str, Any]:
    """Translate CLI flags into a nested override dict (CLI > YAML > defaults)."""
    det: dict[str, Any] = {}
    if opts.get("template"):
        det["mode"] = "template"
        det["template"] = opts["template"]
    _set(det, "mode", opts.get("mode"))
    for key in ("rows", "cols", "cell_width", "cell_height", "tolerance", "min_area", "background"):
        _set(det, key, opts.get(key))
    gap = opts.get("gap")
    _set(det, "gap_x", opts.get("gap_x") if opts.get("gap_x") is not None else gap)
    _set(det, "gap_y", opts.get("gap_y") if opts.get("gap_y") is not None else gap)
    if opts.get("margin") is not None:
        m = opts["margin"]
        det["margins"] = {"left": m, "top": m, "right": m, "bottom": m}
    threshold = opts.get("threshold")
    if threshold is not None:
        det["threshold"] = threshold if threshold == "auto" else _int(threshold, "--threshold")

    yaml_mode = (config_data.get("detection") or {}).get("mode")
    if det and "mode" not in det and yaml_mode is None:
        det["mode"] = "grid" if ({"rows", "cols"} & det.keys()) else "auto"
    if det.get("mode") == "template" and len(det) > 2:
        extra = {k: v for k, v in det.items() if k not in ("mode", "template")}
        det = {"mode": "template", "template": det["template"], "overrides": extra}

    ext: dict[str, Any] = {}
    _set(ext, "shape", opts.get("shape"))
    _set(ext, "crop_padding", opts.get("padding"))
    _set(ext, "shape_inset", opts.get("inset"))

    out: dict[str, Any] = {}
    for key in ("format", "quality", "naming"):
        _set(out, key, opts.get(key))
    _set(out, "background", opts.get("fill"))
    if opts.get("overwrite"):
        out["overwrite"] = True
    resize: dict[str, Any] = {}
    _set(resize, "width", opts.get("width"))
    _set(resize, "height", opts.get("height"))
    _set(resize, "mode", opts.get("resize_mode"))
    if resize:
        out["resize"] = resize

    overrides: dict[str, Any] = {}
    for key, value in (("detection", det), ("extraction", ext), ("output", out)):
        if value:
            overrides[key] = value
    return overrides


def _int(value: str, flag: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{flag} must be 'auto' or an integer, got {value!r}") from None


def _slicer(config: Path | None, **opts: Any) -> ImageSlicer:
    data = read_config_file(config) if config is not None else {}
    return ImageSlicer.from_dict(data, collect_overrides(data, **opts))


def _fail(exc: SlicraError) -> typer.Exit:
    typer.secho(f"error: {exc.message}", fg=typer.colors.RED, err=True)
    if exc.hint:
        typer.echo(f"hint: {exc.hint}", err=True)
    return typer.Exit(exc.exit_code)


def _print_warnings(warnings: list[Any]) -> None:
    for w in warnings:
        typer.secho(f"warning [{w.code}]: {w.message}", fg=typer.colors.YELLOW, err=True)


def _resolve_input(input_path: Path | None, slicer: ImageSlicer) -> Path:
    path = input_path or slicer.config.input.path
    if path is None:
        raise ConfigError("no input image", hint="pass INPUT or set input.path in the config")
    return path


# --------------------------------------------------------------------------- commands


@app.command()
def init(
    output: Annotated[Path, typer.Option("--output", "-o", help="Where to write the YAML.")] = Path("slicra.yaml"),
    mode: Annotated[str, typer.Option("--mode", "-m", help=f"Starter: {', '.join(TEMPLATES)}.")] = "grid",
    overwrite: OverwriteOpt = False,
) -> None:
    """Write a commented starter configuration."""
    if mode not in TEMPLATES:
        raise _fail(ConfigError(f"unknown starter {mode!r}; choose one of {list(TEMPLATES)}"))
    if output.exists() and not overwrite:
        raise _fail(ConfigError(f"{output} already exists", hint="pass --overwrite to replace it"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(TEMPLATES[mode], encoding="utf-8")
    typer.echo(f"wrote {output} ({mode})")


@app.command()
def validate(
    config: Annotated[Path, typer.Option("--config", "-c", help="YAML configuration file.")],
    json_out: JsonOpt = False,
) -> None:
    """Validate a configuration file and print the resolved settings."""
    try:
        data = read_config_file(config)
        slicer = ImageSlicer.from_dict(data)
    except SlicraError as exc:
        raise _fail(exc) from None
    resolved = slicer.config.to_public_dict()
    if json_out:
        typer.echo(json.dumps(resolved, indent=2))
        return
    det = slicer.config.detection
    typer.echo(f"{config}: valid")
    typer.echo(
        f"  detection: {det.mode}"
        + (f" (template {slicer.config.source_template})" if slicer.config.source_template else "")
    )
    typer.echo(f"  shape: {slicer.config.extraction.shape}  format: {slicer.config.output.format}")


def _detection_dict(result: DetectionResult, source: Path) -> dict[str, Any]:
    return {
        "source": str(source),
        "width": result.image_size[0],
        "height": result.image_size[1],
        "detector": result.detector,
        "score": result.score,
        "region_count": result.region_count,
        "warnings": [w.to_dict() for w in result.warnings],
        "details": result.details,
        "regions": [r.to_dict() for r in result.regions],
    }


@app.command()
def inspect(
    input_path: Annotated[Path | None, typer.Argument(metavar="INPUT", help="Image to analyze.")] = None,
    config: ConfigOpt = None,
    mode: ModeOpt = None,
    template: TemplateOpt = None,
    rows: RowsOpt = None,
    cols: ColsOpt = None,
    gap: GapOpt = None,
    gap_x: GapXOpt = None,
    gap_y: GapYOpt = None,
    margin: MarginOpt = None,
    cell_width: CellWOpt = None,
    cell_height: CellHOpt = None,
    background: BgOpt = None,
    threshold: ThreshOpt = None,
    tolerance: TolOpt = None,
    min_area: MinAreaOpt = None,
    json_out: JsonOpt = False,
) -> None:
    """Detect regions and print them. Writes no files."""
    try:
        slicer = _slicer(**locals_without(locals(), "input_path", "json_out"))
        source = _resolve_input(input_path, slicer)
        loaded = slicer.load(source)
        result = slicer._detect_loaded(loaded)
    except SlicraError as exc:
        raise _fail(exc) from None
    if json_out:
        typer.echo(json.dumps(_detection_dict(result, source), indent=2))
    else:
        w, h = result.image_size
        typer.echo(
            f"image: {source} ({w}x{h}, {loaded.source_mode}{', EXIF-rotated' if loaded.exif_transposed else ''})"
        )
        score = "n/a (explicit geometry)" if result.score is None else f"{result.score:.2f} (heuristic)"
        typer.echo(f"detector: {result.detector}  score: {score}")
        typer.echo(f"regions: {result.region_count}")
        for r in result.regions:
            pos = f" r{r.row}c{r.col}" if r.row is not None else ""
            b = r.bbox
            typer.echo(
                f"  {r.index:>4}  {r.id:<12} bbox=({b.left}, {b.top}, {b.right}, {b.bottom})  {b.width}x{b.height}{pos}"
            )
        _print_warnings(result.warnings)
    if result.region_count == 0:
        typer.secho("error: detected 0 regions", fg=typer.colors.RED, err=True)
        raise typer.Exit(3)


def locals_without(values: dict[str, Any], *names: str) -> dict[str, Any]:
    return {k: v for k, v in values.items() if k not in names}


@app.command()
def preview(
    input_path: Annotated[Path | None, typer.Argument(metavar="INPUT", help="Image to preview.")] = None,
    output: Annotated[Path, typer.Option("--output", "-o", help="Preview PNG path.")] = Path("preview.png"),
    config: ConfigOpt = None,
    mode: ModeOpt = None,
    template: TemplateOpt = None,
    rows: RowsOpt = None,
    cols: ColsOpt = None,
    gap: GapOpt = None,
    gap_x: GapXOpt = None,
    gap_y: GapYOpt = None,
    margin: MarginOpt = None,
    cell_width: CellWOpt = None,
    cell_height: CellHOpt = None,
    background: BgOpt = None,
    threshold: ThreshOpt = None,
    tolerance: TolOpt = None,
    min_area: MinAreaOpt = None,
    overwrite: OverwriteOpt = False,
) -> None:
    """Render only the preview (boxes, outlines and indices)."""
    try:
        slicer = _slicer(**locals_without(locals(), "input_path", "output"))
        source = _resolve_input(input_path, slicer)
        detection = slicer.detect(source)
        slicer._require_regions(detection)
        slicer.preview(source, output)
    except SlicraError as exc:
        raise _fail(exc) from None
    _print_warnings(detection.warnings)
    typer.echo(f"wrote {output} ({detection.region_count} regions, detector {detection.detector})")


@app.command()
def extract(
    input_path: Annotated[
        Path | None, typer.Argument(metavar="INPUT", help="Image file, or a directory for batch mode.")
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory.")] = None,
    config: ConfigOpt = None,
    mode: ModeOpt = None,
    template: TemplateOpt = None,
    rows: RowsOpt = None,
    cols: ColsOpt = None,
    gap: GapOpt = None,
    gap_x: GapXOpt = None,
    gap_y: GapYOpt = None,
    margin: MarginOpt = None,
    cell_width: CellWOpt = None,
    cell_height: CellHOpt = None,
    background: BgOpt = None,
    threshold: ThreshOpt = None,
    tolerance: TolOpt = None,
    min_area: MinAreaOpt = None,
    shape: ShapeOpt = None,
    padding: PadOpt = None,
    inset: InsetOpt = None,
    format: FormatOpt = None,
    quality: QualityOpt = None,
    naming: NamingOpt = None,
    width: WidthOpt = None,
    height: HeightOpt = None,
    resize_mode: ResizeOpt = None,
    fill: BgColorOpt = None,
    overwrite: OverwriteOpt = False,
    preview_flag: Annotated[
        bool | None, typer.Option("--preview/--no-preview", help="Also write preview.png (default: config).")
    ] = None,
    flat: Annotated[
        bool,
        typer.Option("--flat", help="Batch: put every region PNG directly in --output (names prefixed with the stem)."),
    ] = False,
    json_out: JsonOpt = False,
) -> None:
    """Export every region, plus the manifest (and preview when enabled).

    INPUT may be a directory: every image in it is processed (batch mode).
    """
    try:
        slicer = _slicer(**locals_without(locals(), "input_path", "output", "preview_flag", "json_out", "flat"))
        source = _resolve_input(input_path, slicer)
        if source.is_dir():
            batch = slicer.extract_batch(source, output, preview=preview_flag, flat=flat)
            for result in batch.results:
                _print_warnings(result.warnings)
            if json_out:
                typer.echo(
                    json.dumps(
                        {
                            "output_dir": str(batch.output_dir),
                            "images": len(batch.results),
                            "region_count": batch.region_count,
                            "manifests": [str(r.manifest_path) for r in batch.results],
                            "failures": {str(k): v for k, v in batch.failures.items()},
                        },
                        indent=2,
                    )
                )
            else:
                for result in batch.results:
                    typer.echo(f"{result.source}: {result.region_count} regions -> {result.output_dir}")
                for path, message in batch.failures.items():
                    typer.secho(f"failed {path}: {message}", fg=typer.colors.RED, err=True)
                typer.echo(
                    f"batch: {len(batch.results)} image(s), {batch.region_count} regions, "
                    f"{len(batch.failures)} failure(s) -> {batch.output_dir}"
                )
            if batch.failures:
                raise typer.Exit(3 if batch.results else 4)
            return
        result = slicer.extract(source, output, preview=preview_flag)
    except SlicraError as exc:
        raise _fail(exc) from None
    _print_warnings(result.warnings)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "region_count": result.region_count,
                    "manifest": str(result.manifest_path) if result.manifest_path else None,
                    "preview": str(result.preview_path) if result.preview_path else None,
                    "outputs": [str(p) for p in result.outputs],
                },
                indent=2,
            )
        )
        return
    typer.echo(f"extracted {result.region_count} regions ({result.detection.detector}) -> {result.output_dir}")
    if result.preview_path:
        typer.echo(f"preview: {result.preview_path}")
    if result.manifest_path:
        typer.echo(f"manifest: {result.manifest_path}")


@app.command()
def templates() -> None:
    """List the built-in detection templates (use with --template NAME)."""
    for name, description in builtin_templates().items():
        typer.echo(f"{name:<20} {description}")


def main() -> None:
    try:
        app()
    except ValidationError as exc:  # pragma: no cover - defensive
        typer.echo(f"error: {format_validation_error(exc)}", err=True)
        sys.exit(2)


if __name__ == "__main__":  # pragma: no cover
    main()
