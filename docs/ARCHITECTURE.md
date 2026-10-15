# Architecture

Slicra is a single installable Python package (`src/slicra/`, src-layout, Hatchling build) with
three front doors that share one engine: the Python API (`ImageSlicer`), the Typer CLI
(`slicra`), and the Agent Skill in `skills/slicra/` (Markdown instructions that call the CLI).
There is no server, database or network I/O.

## Pipeline

```text
input path / PIL.Image
   │  imageio.load_image        open read-only, pixel limit, EXIF transpose, RGB/RGBA
   ▼
LoadedImage ──► detectors.run_detector(config.detection) ──► DetectionResult(regions, warnings, score)
                    grid | grid-auto | contours | manual | auto      (template resolved in config)
   │
   ├─► preview.render_preview(image, regions)             same region list as export
   ▼
extraction.extract_regions
   │  crop_box_for (bbox + crop_padding, center-square)   masks.build_mask (shape)  resize_image
   ▼
export.plan_outputs ─► check_conflicts ─► save_image ─► build_manifest/write_manifest
   ▼
ExtractionResult(outputs, manifest_path, preview_path, warnings)
```

Every file path is planned and checked **before** the first write, so a conflict or a bad
naming pattern leaves the output directory untouched.

## Package layout

```text
src/slicra/
├── __init__.py        public API re-exports (ImageSlicer, Config, models, errors)
├── _version.py        single source of the version (read by Hatchling)
├── cli.py             Typer app: init, validate, inspect, preview, extract, templates
├── config.py          Pydantic models (StrictModel, extra=forbid), YAML loading, overrides, templates
├── pipeline.py        ImageSlicer: detect / render / preview / extract / extract_batch
├── imageio.py         safe loading + normalization, batch file discovery
├── background.py      Pillow-only background estimation, foreground masks, projections
├── ordering.py        deterministic reading order for free-form regions
├── extraction.py      crop + mask + resize in memory
├── preview.py         overlay rendering
├── export.py          naming, path safety, saving, manifest
├── models.py          BBox, Region, DetectionResult, ExtractionResult, BatchResult
├── errors.py          SlicraError hierarchy with CLI exit codes
├── init_templates.py  starter YAML written by `slicra init`
├── detectors/         one module per detector + registry (see detectors/README.md)
├── masks/             shape masks (see masks/README.md)
└── presets/           built-in detection templates (*.yaml, shipped as package data)
```

Per-module docs: [`src/slicra/README.md`](../src/slicra/README.md),
[`src/slicra/detectors/README.md`](../src/slicra/detectors/README.md),
[`src/slicra/masks/README.md`](../src/slicra/masks/README.md).

## Public API vs internals

Public (semver-protected): everything in `slicra.__all__`, the CLI commands/options/exit codes,
the YAML schema (`version: 1`) and the manifest schema (`schema_version: 1`). Internal: module
level helpers (`background`, `ordering`, `export` functions) and underscore methods.

## Key design decisions

| Decision | Why |
| --- | --- |
| Detection and masking are separate stages | A rectangular cell can become a circle; a detected star can export as a box. |
| Core depends only on Pillow, Pydantic, PyYAML, Typer | `grid`, `grid-auto`, `manual` work without NumPy/OpenCV; `contours` imports them lazily (`[opencv]` extra). |
| `grid-auto` evaluates background candidates | Sheets without outer margin have content at the border; separator-line colors are tried and the most regular grid wins. |
| Explicit `score`, never "probability" | Heuristics are surfaced as such, with warnings, so users and agents do not over-trust them. |
| Strict config models | Typos and incompatible options fail with exit code 2 instead of being ignored. |
| Plan-then-write export | No partial outputs on conflict; overwrite requires explicit consent. |
| Deterministic outputs, no timestamps in manifests | Reproducible runs and diffable manifests. |

## Runtime and distribution shape

A library/CLI distributed as wheel + sdist (`python -m build`), not yet published to PyPI. The
console script `slicra` maps to `slicra.cli:main`. CI (`.github/workflows/ci.yml`) runs lint/type
checks, the test matrix (Linux/macOS/Windows x Python 3.11-3.13), a core-only job without OpenCV,
and the packaging test.

## Extension points

- New detector: config model + function + `register_detector` (see CONTRIBUTING.md). Reserved
  for a future optional `ai/segmentation` plugin; nothing in the core calls an AI service.
- New mask shape: `masks/shapes.py::build_mask` + `ShapeName`.
- New preset: a YAML file in `src/slicra/presets/` with `description` and `detection`.
