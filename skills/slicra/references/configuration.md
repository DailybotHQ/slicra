# Slicra configuration reference

Start from `slicra init --mode grid|grid-auto|contours|manual --output slicra.yaml`,
then check it with `slicra validate --config slicra.yaml`.

Precedence is **CLI flags > YAML > defaults**. Unknown keys are errors. Relative paths
resolve against the current working directory. Coordinates are pixels of the image
after EXIF rotation; boxes are `[left, top, right, bottom]` with exclusive right/bottom.

## detection

| mode | key options |
| --- | --- |
| `grid` | `rows`, `cols`, `margins: {left, top, right, bottom}`, `gap_x`, `gap_y` (int or a list of cols-1 / rows-1 values), `cell_width`, `cell_height`, `exclude: [[row, col], ...]` (1-based) |
| `grid-auto` | `background: auto\|transparent\|"#RRGGBB"`, `tolerance` (0-255, default 24), `max_separator_fill` (0.02), `min_gap` (2), `min_cell_size` (8), `rows`/`cols` (expected counts, fail on mismatch), `skip_empty` (true), `silhouette` (false; true fits a rounded-rectangle mask to each tile so `shape: original` keeps rounded corners transparent) |
| `contours` | `background`, `threshold: auto\|0-255`, `background_tolerance` (16), `alpha_threshold` (8), `min_area` (64), `max_area`, `connectivity: 4\|8`, `holes: keep\|fill`, `morphology: {open, close, kernel}` |
| `manual` | `regions: [{id, rect: [l, t, r, b]} \| {id, polygon: [[x, y], ...]}]`, optional per-region `shape`, `star`, `circle_fit`; `regions_file` (YAML/JSON); `out_of_bounds: error\|clip`; `overlap: allow\|warn\|error` |
| `auto` | `strategies: [grid-auto, contours]`, `min_score` (0.6), `min_fill` (0.85), `grid_auto: {...}`, `contours: {...}` |
| `template` | `template: <built-in name or YAML path>`, `overrides: {...}`; list built-ins with `slicra templates` |

`gap` is the space **between** cells and is never part of a crop. `margins` is the space
around the whole grid.

## extraction

| key | meaning |
| --- | --- |
| `shape` | `rectangle`, `ellipse`, `circle`, `polygon`, `star`, `original` |
| `crop_padding` | grow every crop box by N px (clamped to the image). With `rectangle` it adds real pixels; with other shapes it adds transparent headroom |
| `shape_inset` | shrink the mask by N px inside its box |
| `antialias`, `supersample` | smooth mask edges (default on, 4x) |
| `circle_fit` | `contain` (circle inside the original box, transparent sides) or `center-square` (crop to the centered square first, square output) |
| `star` | `points` (>=3), `inner_ratio`, `outer_ratio`, `rotation` (degrees, 0 = tip up) |
| `polygon.points` | vertices relative to the region box, 0..1 (required for `shape: polygon` unless every region has its own polygon) |

`original` keeps the detector's exact silhouette (contours, grid-auto with
`silhouette: true`) or the manual polygon; for plain boxes it equals the box.

## output

`directory`, `format: png|webp|jpeg`, `quality`, `naming` (fields `{index}`, `{row}`,
`{col}`, `{id}`, `{stem}`), `overwrite`, `background` (fill for jpeg and contain
padding), `resize: {width, height, mode: contain|cover|stretch, upscale}`.

PNG/WebP keep transparency. JPEG has no alpha: it is flattened against `background`
(white by default) and a `jpeg-flattened` warning is recorded.

## preview / manifest

`preview: {enabled, filename, labels, line_width}` and `manifest: {enabled, filename}`.
The manifest lists the resolved config, detector, warnings, each region's bbox,
crop box, shape and output file, and every file written.

## Exit codes

0 ok · 2 invalid config/usage · 3 detection failed or zero regions · 4 image not
loadable · 5 output conflict · 6 missing optional dependency.
