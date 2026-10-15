# Troubleshooting Slicra detections

Always re-run `slicra preview` after a change and compare the region count with
what the user expects.

## Crops include gap pixels / bands look shifted (grid)

Real sheets are rarely perfectly regular. Use `--mode grid-auto`: it measures every
separator instead of assuming a constant gap. Keep `grid` for sheets whose geometry
is known exactly (generated sheets, sprite atlases with fixed cells).

## grid-auto finds the wrong number of rows or columns

- `grid-auto: no separators detected`: the gaps are not close enough to the
  background. Set `--background "#RRGGBB"` to the gap color, or raise `--tolerance`.
- Too many bands: light content (white clothing, sky) looks like background. Lower
  `--tolerance` or raise `min_gap`/`min_cell_size` in YAML.
- Pass `--rows N --cols M` to make the run fail rather than guess.
- `grid-auto-irregular` warning: band sizes differ a lot; inspect the preview before
  trusting the result.

## contours: objects merged, split or missing

- Merged: objects touch, or `morphology.close` bridges them. Lower `close`, use
  `connectivity: 4`. Overlapping objects cannot be separated; use `manual`.
- Split or ragged: raise `morphology.close`, or set a fixed `threshold`.
- Missing small objects: lower `min_area` (warnings report how many were ignored).
- `background-not-uniform` or `region-covers-image`: the background is not plain.
  Contours is not a semantic segmenter; use `manual` regions.

## Edges cut off

Add `crop_padding` (e.g. 4) to grow every crop, or `shape_inset` to shrink the mask.

## Zero regions

Exit code 3 and nothing written. Read the warnings, then change the mode or parameters.
Never report success in this case.

## Output already exists

Exit code 5. Choose a new `--output` directory, or pass `--overwrite` only if the
user agrees to replace files.

## Privacy

Images stay local: no network calls, no telemetry. Do not copy user images into
public places, and keep outputs out of the source folder.
