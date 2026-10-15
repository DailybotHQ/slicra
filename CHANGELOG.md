# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
