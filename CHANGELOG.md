# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Output safety: the input image is compared with `samefile` (case-insensitive filesystems),
  preview/manifest targets are containment-checked and never written through symlinks,
  `slicra preview` refuses to overwrite its input, and the manifest uses an unpredictable temp file.
- Batch: case-insensitive unique per-image keys and an in-run collision guard; the exit code now
  reflects the failure kind (e.g. 5 for output conflicts).
- RGB/L images with a PNG transparency key keep their alpha; 32-bit integer and float images
  are scaled to 8 bits.
- CLI flags override a YAML template's `overrides`, and switching templates drops the previous
  ones; detector flags without `--mode` select a matching detector instead of failing.
- `auto` no longer accepts a region covering the whole image or results with dropped content bands.
- `circle_fit: center-square` stays centered on the region near image edges.
- Manual default ids can no longer collide with explicit ids; duplicate `exclude` cells are counted once.
- A local file can no longer shadow a built-in template name.
- `grid-auto` silhouettes are fitted rounded rectangles, so background-colored content touching a
  tile edge is never cut out.

## [0.1.0] - 2026-10-14

### Added

- Detectors: explicit `grid` (margins, per-axis and per-gap spacing, explicit cell sizes, excluded
  cells, drift-free rounding), `grid-auto` (separator inference with background candidates and
  optional per-tile silhouettes), `contours` (OpenCV extra), `manual` (rectangles and polygons from
  YAML/JSON), `auto` (explicit strategy order with recorded selection) and `template` presets.
- Masks: `rectangle`, `ellipse`, `circle` (`contain` / `center-square`), `polygon`, `star`,
  `original`, with anti-aliasing, `crop_padding` and `shape_inset`.
- Export to PNG/WebP (alpha) and JPEG (flattened), `contain`/`cover`/`stretch` resize, safe naming,
  overwrite protection, preview with indices and a JSON manifest.
- CLI: `init`, `validate`, `inspect`, `preview`, `extract` (single file and batch, `--flat`),
  `templates`; Python API `ImageSlicer`.
- Portable Agent Skill in `skills/slicra`, synthetic fixtures, CI on Linux/macOS/Windows.
