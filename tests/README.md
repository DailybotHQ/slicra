# Tests

pytest suite; how to run, scope and extend it is in
[docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md).

| File | Covers |
| --- | --- |
| `conftest.py` | synthetic fixtures (`grid_png` with magenta separators, `shapes_png`, transparent variant), pixel helpers |
| `test_grid.py` | explicit grid: 5x5 exactness, 3x7 asymmetric non-divisible, invariants across sizes, gap lists, exclude, invalid config |
| `test_grid_auto.py` | separator inference, irregular spacing, expected-count mismatch, refusal without separators, empty cells, silhouettes |
| `test_contours.py` | star/oval/triangle on uniform and transparent backgrounds (silhouette pixel match), holes, area filters, busy backgrounds |
| `test_manual.py` | polygon coordinates, mixed per-region shapes, bounds, overlap policy, regions files, invalid regions |
| `test_masks.py` | each shape's alpha, anti-aliasing, inset, polygon refusal, rectangular cells exported as circle/star/ellipse |
| `test_export.py` | PNG alpha, JPEG flattening, WebP, resize modes, overwrite protection, naming safety, manifest |
| `test_cli.py` | every command, overrides precedence, exit codes, batch and `--flat` |
| `test_api.py` | documented API flow, in-memory use, templates, auto selection, extension point |
| `test_end_to_end.py` | example configs, preview = export regions, source untouched, EXIF, bad inputs, limits, batch safety |
| `test_skill.py` | Agent Skill frontmatter, links, and that documented commands exist |
| `test_packaging.py` | `slow`: build wheel/sdist, install in a clean venv, run the CLI |
| `test_real_samples.py` | `real`: optional local avatar sheets via `SLICRA_SAMPLES` |

Fixtures are generated from geometry; never add real photographs.
