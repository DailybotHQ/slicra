# `slicra.detectors`

Turns an image plus a detection config into a `DetectionResult` (ordered `Region`s, warnings,
heuristic score, details). Detectors never crop or mask.

| Module | Mode | Needs | Ordering / ids |
| --- | --- | --- | --- |
| `grid.py` | `grid` | core | row-major, `r01c01` |
| `grid_auto.py` | `grid-auto` | core (Pillow only) | row-major, `r01c01` |
| `contours.py` | `contours` | `[opencv]` extra | reading order (`ordering.py`), `shape001` |
| `manual.py` | `manual` | core | declaration order, user ids or `m001` |
| `__init__.py` | registry, `auto` | — | `run_detector`, `register_detector`, `detect_auto` |

`template` is not a detector: `config.Config` resolves it into one of the modes above at load
time.

## Contract for a detector

`(image: PIL.Image, cfg: <ConfigModel>) -> DetectionResult`

- Boxes inside the image, exclusive right/bottom; stable ids and `index` 1..n.
- Uncertainty is reported as `DetectionWarning(code, message)`; impossibility raises
  `DetectionError` with a `hint`. Never invent regions to satisfy expected counts.
- Heavy dependencies are imported lazily (`contours._require_cv`).

Algorithm details and the reasoning behind thresholds: [docs/](docs/README.md).

## Tests

`tests/test_grid.py`, `tests/test_grid_auto.py`, `tests/test_contours.py`,
`tests/test_manual.py`; `auto` and the registry in `tests/test_api.py`; real sheets in
`tests/test_real_samples.py` (optional).
