---
name: add-detector
description: Add a new detection mode to Slicra (config model, detector function, registry, tests, docs). Use when asked to support a new way of finding regions, e.g. a new layout type or an optional segmentation plugin.
---

# Add a detector

1. **Config model** in `src/slicra/config.py`: subclass `StrictModel`, `mode: Literal["<name>"] = "<name>"`, validated fields with `Field(..., ge=..., le=...)`; add it to the `Detection` union and `DETECTION_MODES`.
2. **Detector** in `src/slicra/detectors/<name>.py`: `detect_<name>(image, cfg) -> DetectionResult`. Boxes in source pixels, exclusive right/bottom; use `ordering.reading_order(regions, prefix=...)` for free-form regions; warnings with stable kebab-case codes; `DetectionError` + hint when evidence is insufficient. Heavy deps imported lazily with `MissingDependencyError` + install hint.
3. **Register** in `src/slicra/detectors/__init__.py` (`_REGISTRY`); decide whether `auto` should try it (and its acceptance rule).
4. **CLI**: expose only the key options through `collect_overrides` in `cli.py`; add a starter to `init_templates.py` if useful.
5. **Tests** `tests/test_<name>.py`: synthetic fixture with known geometry, exact boxes, warnings, failure modes, CLI exit code.
6. **Docs**: detectors README + `docs/README.md` algorithms, README EN/ES mode table, `skills/slicra/references/configuration.md`, CHANGELOG.
7. Gates: `ruff check src tests examples && ruff format --check src tests examples && mypy && python -m pytest`.
