# Examples

```bash
python examples/generate_fixtures.py     # writes examples/input/ (gitignored, reproducible)
```

| Config | Input | What it shows |
| --- | --- | --- |
| [`configs/avatars-grid.yaml`](configs/avatars-grid.yaml) | `avatars-grid.png` | explicit 5x5 grid, 12 px gaps, resized 256x256 PNGs |
| [`configs/irregular-shapes.yaml`](configs/irregular-shapes.yaml) | `shapes-sheet.png` | `contours` + `shape: original`: transparent star, oval and triangle |
| [`configs/manual-shapes.yaml`](configs/manual-shapes.yaml) | `shapes-sheet.png` | the same sheet with hand-declared regions: an ellipse, a star mask on a rectangle, a polygon |
| [`configs/avatars-circles.yaml`](configs/avatars-circles.yaml) | `avatars-grid.png` | a built-in template + circular WebP avatars |
| [`configs/avatar-sheet-auto.yaml`](configs/avatar-sheet-auto.yaml) | your own sheets | `grid-auto` for real sheets with irregular spacing, rounded-corner silhouettes |

Run one from the repository root (paths are relative to the working directory):

```bash
slicra extract --config examples/configs/avatars-grid.yaml
slicra extract path/to/sheets --config examples/configs/avatar-sheet-auto.yaml --output output/sheets --flat
```

`render_docs_assets.py` regenerates the README illustrations in `docs/assets/` from these
synthetic inputs.
