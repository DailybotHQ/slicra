"""Starter configurations written by ``slicra init``."""

from __future__ import annotations

_COMMON = """\
extraction:
  shape: {shape}            # rectangle | ellipse | circle | polygon | star | original
  crop_padding: 0           # grow each crop box by N px (clamped to the image)
  shape_inset: 0            # shrink the mask inside the crop by N px
  antialias: true
output:
  directory: output/{name}
  format: png               # png | webp | jpeg (jpeg has no alpha)
  naming: "{naming}"
  overwrite: false
  # resize: {{width: 256, height: 256, mode: contain}}   # contain | cover | stretch
preview:
  enabled: true
manifest:
  enabled: true
"""

TEMPLATES: dict[str, str] = {
    "grid": """\
# Slicra configuration — explicit grid.
# All values are pixels of the source image. Measure your image first:
#   slicra inspect your-image.png --mode grid-auto
version: 1
detection:
  mode: grid
  rows: 5
  cols: 5
  margins: {left: 0, top: 0, right: 0, bottom: 0}
  gap_x: 12                 # space between columns (never part of a crop)
  gap_y: 12                 # space between rows
"""
    + _COMMON.format(shape="rectangle", name="grid", naming="cell_{index:03d}"),
    "grid-auto": """\
# Slicra configuration — grid inferred from background separators.
version: 1
detection:
  mode: grid-auto
  background: auto          # auto | transparent | "#RRGGBB"
  tolerance: 24             # channel difference that counts as content
  # rows: 5                 # optional: fail if a different count is found
  # cols: 5
"""
    + _COMMON.format(shape="rectangle", name="grid-auto", naming="cell_{index:03d}"),
    "contours": """\
# Slicra configuration — disjoint objects on a uniform/transparent background.
# Requires: pip install 'slicra[opencv]'
version: 1
detection:
  mode: contours
  background: auto          # auto | transparent | "#RRGGBB"
  threshold: auto           # auto (Otsu) | 0-255
  min_area: 400
  morphology: {open: 1, close: 1}
"""
    + _COMMON.format(shape="original", name="shapes", naming="shape_{index:03d}"),
    "manual": """\
# Slicra configuration — regions declared by hand (source pixel coordinates).
version: 1
detection:
  mode: manual
  regions:
    - id: first
      rect: [0, 0, 100, 100]          # [left, top, right, bottom], right/bottom exclusive
    - id: second
      polygon: [[150, 0], [250, 100], [150, 100]]
"""
    + _COMMON.format(shape="original", name="manual", naming="{id}"),
}
