# Coding standards

These are the conventions the existing code follows. `ruff` and `mypy` enforce the mechanical
part; the rest is reviewed (see `.review/extension.md`).

## Language and tooling

- Python **3.11+**, `from __future__ import annotations` at the top of every module.
- Formatting and linting: `ruff format` + `ruff check` with the rule set in `pyproject.toml`
  (`E, F, W, I, B, UP, SIM, RUF`, line length 120). Import order is ruff's isort (`I`).
- Typing: `mypy` in **strict** mode with the Pydantic plugin; `cv2` is the only untyped import
  allowed (`ignore_missing_imports`). Public functions are fully annotated.
- English only in code, comments, docs, commits and CLI output.

## Structure

- Keep the stages separate: loading (`imageio`), detection (`detectors/`), masking (`masks/`),
  extraction (`extraction`), export (`export`), orchestration (`pipeline`). The CLI only parses
  options and formats output; it never re-implements pipeline logic.
- Prefer plain functions and frozen dataclasses over class hierarchies. Detectors are callables
  `(image, cfg) -> DetectionResult`.
- Configuration models subclass `StrictModel` (`extra="forbid"`, frozen) and validate ranges
  with `Field(..., ge=..., le=...)`; cross-field rules go in `model_validator(mode="after")`.
- Optional heavy dependencies (NumPy, OpenCV) are imported inside the function that needs them
  and raise `MissingDependencyError` with an install hint.

## Errors and user-facing messages

- Raise a `SlicraError` subclass (`errors.py`) for every expected failure; each carries a stable
  `exit_code` used verbatim by the CLI: 2 config, 3 detection/zero regions, 4 image load,
  5 export conflict, 6 missing dependency. Add a `hint=` with the next practical step.
- Never print from library code; return `DetectionWarning(code, message)` with a stable,
  kebab-case `code` (e.g. `grid-auto-irregular`). The CLI prints warnings to stderr.
- Do not guess: when evidence is insufficient, warn or raise instead of fabricating regions.
- Heuristic numbers are called `score` and documented as "not a calibrated probability".

## Images and coordinates

- Boxes are `(left, top, right, bottom)` with exclusive right/bottom, in pixels of the
  EXIF-normalized image. Use `BBox`, not raw tuples, across module boundaries.
- Never mutate the loaded image in place; crop/copy first. Never write to the source path.
- Keep alpha: work in `RGBA` for outputs; flatten only in `export.save_image` for JPEG.

## CLI surface

- Every command and option has `--help` text. Options mirror config keys (`--gap-x` ↔
  `detection.gap_x`). Precedence is CLI > YAML > defaults (`config.merge_overrides`).
- Changing a command, option, default or exit code is a public-API change: update README
  (EN + ES), `skills/slicra/` references, CHANGELOG and tests together.

## Commits and changes

- Conventional Commits: `type(scope): description`. Scopes used here: `grid`, `grid-auto`,
  `contours`, `manual`, `masks`, `export`, `cli`, `config`, `api`, `skill`, `docs`, `ci`,
  `deps`, `harness`.
- Keep changes focused; no unrelated reformatting.
- Update `CHANGELOG.md` under *Unreleased* for user-visible changes.

## Forbidden

- `yaml.load`/`full_load`/`unsafe_load`, `pickle`, `eval`/`exec`, `shell=True`, network calls.
- Tests that only mock the interesting function or only check that a file exists.
- Real photographs or personal data in the repository.
- Module-level `import cv2`/`import numpy` outside `detectors/contours.py` helpers.
