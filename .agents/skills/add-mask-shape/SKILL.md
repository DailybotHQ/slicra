---
name: add-mask-shape
description: Add a new extraction mask shape to Slicra (e.g. rounded rectangle, heart, hexagon). Use when asked for a new output silhouette.
---

# Add a mask shape

1. Add the name to `ShapeName` and `SHAPES` in `src/slicra/config.py`; add an options model (StrictModel) to `Extraction` if the shape is parametric.
2. Draw it in `src/slicra/masks/shapes.py::build_mask`. Parametric shapes fit the region box minus `shape_inset` (`local`), use the supersampling canvas `s`, and never change region boxes. Pass options through `ShapeSpec` and `extraction.shape_spec` (including per-region overrides if manual regions should set it).
3. Tests in `tests/test_masks.py`: alpha 255 at an inside pixel, 0 at an outside pixel, partial alpha on edges with antialias, behavior with inset; one end-to-end export via `ImageSlicer.from_dict(...).render(...)`.
4. Docs: `src/slicra/masks/README.md`, README EN/ES shape table, `skills/slicra/references/configuration.md`, CHANGELOG.
5. Gates: ruff, mypy, `python -m pytest tests/test_masks.py tests/test_export.py`, then the fast suite.
