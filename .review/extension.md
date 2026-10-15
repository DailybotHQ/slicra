# Review overrides for Slicra

Slicra is a local, deterministic Python library + CLI (`src/slicra/`) + portable Agent Skill
(`skills/slicra/`) that detects regions in an image and exports each one as its own file. It
reads untrusted images and YAML/JSON from users and writes files to disk, so the review focus is:
never modify or escape onto the user's files, never claim a detection that has no evidence, and
keep the CLI/API/Skill/docs surface in sync.

## Severity overrides for this codebase

- **Always `critical`:** any write path that can escape the output directory or overwrite
  without consent. Output names are built in `src/slicra/export.py` (`sanitize_name`,
  `render_name`, `plan_outputs`, `check_conflicts`) and the preview/manifest paths in
  `src/slicra/pipeline.py::ImageSlicer.extract`. Removing the `resolve()`/parent check, the
  duplicate-name check, the pre-write conflict check or the "refusing to overwrite the input
  image" guard is critical.
- **Always `critical`:** any code that opens, saves or truncates the *source* image for writing,
  or mutates `LoadedImage.image` in place before other consumers read it
  (`src/slicra/imageio.py`, `src/slicra/extraction.py`).
- **Always `critical`:** `yaml.load` / `yaml.unsafe_load` / `yaml.full_load`, `pickle`, `eval`,
  `exec`, `subprocess` with `shell=True`, or any network call (`urllib`, `requests`, `httpx`,
  sockets) inside `src/slicra/`. The product promise is offline processing with `yaml.safe_load`
  only (`config.py::_safe_yaml`, `detectors/manual.py::load_regions_file`).
- **Always `critical`:** reporting success with zero regions, or swallowing a `DetectionError`
  and continuing with fabricated regions (`pipeline.py::_require_regions`,
  `detectors/__init__.py::detect_auto`, `detectors/grid_auto.py`).
- **Escalate to `warning`:** a new config field on a `StrictModel` without validation of its
  range, or a model that drops `extra="forbid"` (typos must fail loudly).
- **Escalate to `warning`:** template resolution that accepts names outside
  `^[a-z0-9][a-z0-9-]*$` or lets a template reference another template
  (`config.py::_read_template`, `resolve_template`).
- **Escalate to `warning`:** removing `Image.MAX_IMAGE_PIXELS` / `input.max_pixels` handling or
  the `DecompressionBomb*` mapping in `imageio.py::load_image`.
- **Escalate to `warning`:** importing `cv2` or `numpy` at module level outside
  `detectors/contours.py::_require_cv`; the core must work without the `opencv` extra.
- **Escalate to `warning`:** a changed exit code or `SlicraError` subclass mapping in
  `errors.py` / `cli.py` without updating README, `skills/slicra/references/configuration.md`
  and tests (`tests/test_cli.py::test_error_exit_codes`).
- **De-escalate to `info`:** `slicra.cli` calling the underscore helper
  `ImageSlicer._detect_loaded`/`_require_regions`; the CLI is a deliberate thin layer over the
  same pipeline.

## Don't comment on

- Pixel constants and colors in `examples/generate_fixtures.py`; they are deliberate synthetic
  geometry that tests depend on.
- Generated files under `docs/assets/demo-*.png` (re-rendered by `examples/render_docs_assets.py`).
- Anything under `.agents/skills/deepworkplan/` or `.agents/skills/ai-diff-reviewer/` (vendored,
  pinned third-party skills).

## Repo-specific conventions

- **Coordinates:** boxes are `(left, top, right, bottom)` in pixels of the EXIF-normalized image,
  right/bottom **exclusive** (`models.py::BBox`). Off-by-one changes need a pixel test.
- **Grid rounding:** cell spans use `start_i = floor(i * available / n)` in
  `detectors/grid.py::axis_spans`; any change must keep "no overlap, no gap pixel, no drift".
- **Detection vs masking:** detectors return `Region`s only; masks live in `masks/shapes.py`.
  A detector that crops or masks, or a mask that changes region boxes, is a `warning`.
- **Honest diagnostics:** heuristic numbers are named `score` and documented as not calibrated
  probabilities; new uncertainty must surface as a `DetectionWarning` with a stable `code`.
- **One engine:** CLI (`cli.py`) and API (`pipeline.py`) must not duplicate pipeline logic.
- **Docs sync:** a new CLI command/option needs `--help` text, README (EN + ES) and the skill
  references updated; `tests/test_skill.py` checks that skill commands exist.

## Test-strategy expectations

- Detector or mask changes need pixel-level assertions with synthetic fixtures (see
  `tests/conftest.py`, `examples/generate_fixtures.py`) — never only "the file exists".
- New CLI behavior needs a `typer.testing.CliRunner` test in `tests/test_cli.py`, including the
  exit code of its failure mode.
- No photographs or personal data in tests; `tests/test_real_samples.py` reads local sheets only
  via `SLICRA_SAMPLES` and must stay skippable.
- Packaging changes (`pyproject.toml`, presets, package data) must keep `tests/test_packaging.py`
  green.
