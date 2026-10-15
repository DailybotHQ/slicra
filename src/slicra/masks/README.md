# `slicra.masks`

Builds the alpha mask (`L` image, 255 = keep) for one region inside its crop box. Independent
of detection: any shape can be applied to any region.

`build_mask(spec: ShapeSpec, region: Region, crop_box: BBox) -> Image`

| Shape | Geometry source |
| --- | --- |
| `rectangle` | whole crop box (so `crop_padding` adds real pixels), minus `shape_inset` |
| `ellipse`, `circle` | region box minus inset; `circle` is the largest centered circle |
| `star` | region box minus inset; `points`, `inner_ratio`, `outer_ratio`, `rotation` (0 = tip up) |
| `polygon` | region polygon in source coordinates, else `extraction.polygon.points` relative to the region box; neither → `ConfigError` (never guessed) |
| `original` | detector mask (`contours`, `grid-auto` + `silhouette`), else region polygon, else region box |

Anti-aliasing: draw at `supersample`x and reduce with a BOX filter. Exact detector masks are
pasted as-is (no smoothing). `circle_fit: center-square` is applied earlier, in
`extraction.crop_box_for`, by squaring the crop box.

Per-region overrides (`Region.shape`, from manual regions) are merged into the spec by
`extraction.shape_spec`.

Tests: `tests/test_masks.py` (alpha at known pixels, decoupling from detection),
`tests/test_contours.py` and `tests/test_manual.py` (silhouettes and polygons end to end).
