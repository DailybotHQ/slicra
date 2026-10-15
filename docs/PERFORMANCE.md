# Performance

Slicra processes one image at a time in memory. Typical inputs are a few megapixels; the default
safety limit is `input.max_pixels = 150_000_000`.

## Measured reference points (Apple Silicon dev machine, 2026-10-14)

| Workload | Time |
| --- | --- |
| `grid-auto` detection on a 1254 x 1254 RGB avatar sheet | ~20 ms |
| Full batch of 7 such sheets (175 crops, previews, manifests) | ~2-3 s |
| Fast test suite (`pytest -m "not slow"`) | ~9 s |

These numbers are indicative, not guarantees.

## Hot paths and how they stay fast

- **Projections** (`background.py`): foreground masks and row/column profiles use Pillow C
  operations (`ImageChops`, `point`, `resize(..., BOX)`) instead of Python loops over pixels.
- **`uniform_line_colors`** performs two full-image difference passes; it only runs when the
  image border is not uniform.
- **`contours`** uses OpenCV `connectedComponentsWithStats` once; per-component work is limited
  to its bounding box. `max_regions` (default 10 000) stops runaway noise.
- **Mask supersampling** draws at `supersample`x (default 4) of the crop size; cost grows with
  the square of the factor. Use `antialias: false` for very large crops.

## Known costs

- `grid-auto` with `silhouette: true` flood-fills each tile in Python (`ImageDraw.floodfill`):
  roughly linear in tile pixels, noticeable above ~1 MP per tile.
- Large outputs with `resize` use LANCZOS; `contain` adds a canvas composite.
- PNG encoding dominates export time for big crops; WebP/JPEG are faster to write.

## Budgets for changes

- Detection on a 2 MP sheet should stay well under one second.
- Do not introduce per-pixel Python loops in `src/slicra/`; use Pillow or NumPy (inside the
  `opencv` extra) operations. Tests may use simple loops on small synthetic images.
