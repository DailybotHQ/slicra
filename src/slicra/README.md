# `slicra` package

The installable library behind the API, the CLI and the Agent Skill. Architecture overview:
[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).

## Responsibility

Load an image safely, find regions with a detector, render a preview, crop/mask/resize each
region, and write outputs plus a manifest without ever touching the source or overwriting
without consent.

## Public surface

| Module | Exposes |
| --- | --- |
| `__init__.py` | `ImageSlicer`, `Config`, `build_config`, `load_config`, models, errors, `register_detector`, `available_detectors`, `__version__` |
| `pipeline.py` | `ImageSlicer.from_config/from_dict`, `detect`, `render`, `preview`, `extract`, `extract_batch` |
| `config.py` | Pydantic schema (`version: 1`), `load_config`, `build_config`, `merge_overrides`, `builtin_templates` |
| `models.py` | `BBox`, `Region`, `DetectionWarning`, `DetectionResult`, `ExtractedRegion`, `ExtractionResult`, `BatchResult` |
| `errors.py` | `SlicraError` and subclasses with `exit_code` |
| `cli.py` | Typer `app` and `main` (console script `slicra`) |

Internal helpers: `imageio.py` (loading, EXIF, batch discovery), `background.py` (Pillow-only
background/foreground/projections), `ordering.py` (reading order), `extraction.py`,
`preview.py`, `export.py` (naming, safety, manifest), `init_templates.py`, `presets/`.

Subpackages: [`detectors/`](detectors/README.md) and [`masks/`](masks/README.md).

## Invariants

- Boxes are `(left, top, right, bottom)`, right/bottom exclusive, on the EXIF-normalized image.
- Preview and export consume the same `DetectionResult.regions` list.
- Output paths are planned and checked before the first write.
- Zero regions raises `NoRegionsError` (exit 3) in `extract`/`render`; `detect` returns it so
  `inspect` can show diagnostics.

## Tests

See the mapping in [docs/TESTING_GUIDE.md](../../docs/TESTING_GUIDE.md#3-source-to-test-mapping);
the API is covered by `tests/test_api.py` and `tests/test_end_to_end.py`, the CLI by
`tests/test_cli.py`.
