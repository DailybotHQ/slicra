# Detector algorithms

Deeper notes for changing detection behavior. Entry: [../README.md](../README.md).

## `grid` — explicit geometry

Per axis: `usable = length - margin_start - margin_end`, `available = usable - sum(gaps)`.
Cell `i` spans `[floor(i*available/n), floor((i+1)*available/n))` offset by the margin and the
preceding gaps. Properties the tests pin down: cells differ by at most 1 px, never overlap,
never include a gap pixel, and there is no cumulative drift. With `cell_width`/`cell_height` the
cells have that exact size from the start margin; leftover space is reported
(`grid-unused-space`), overflow is a `DetectionError`.

## `grid-auto` — separator inference

1. **Background candidates.** First the median color of the 1-px image border, with its
   *uniformity* (share of border pixels within `tolerance`). If uniformity < 0.9 (no outer
   margin, the border is content), add the colors of full-length uniform rows/columns
   (`background.uniform_line_colors`), clustered by `tolerance`, most frequent first.
2. **Bands per candidate.** Foreground mask = any channel differs from the candidate by more
   than `tolerance` (or alpha above threshold). Column/row profiles are exact BOX averages of the
   mask. Lines with fill ≤ `max_separator_fill` are separators; separator runs shorter than
   `min_gap` merge into content; content bands shorter than `min_cell_size` are dropped with a
   warning.
3. **Choose.** Candidates producing more than one cell are scored by
   `cells * max(0.05, 1 - 2*variation) * uniformity` (`variation` = coefficient of variation of
   band sizes). The best wins; no candidate → `DetectionError`.
4. **Validate.** Expected `rows`/`cols` mismatch → error. Variation > 15% →
   `grid-auto-irregular`. Cells with < 1% foreground are empty (skipped with a warning by
   default). `silhouette: true` adds a per-tile rounded-rectangle mask for `shape: original`: the corner
   radius is measured on the diagonal of each tile corner (gap = `r * (1 - 1/sqrt(2))`) and the
   smallest of the four is used, so tile content that matches the background (a white shirt
   touching the edge) can never be cut out.

Calibrated on real 5 x 5 avatar sheets (1254 px, light background, gaps 11-17 px): all 25 tiles
per sheet found, ~20 ms per sheet.

## `contours` — connected components

Background `auto` uses the border estimate (transparent when most border alpha is low).
Distance = max channel difference to the background; `threshold: auto` is Otsu clamped to at
least `background_tolerance`. Optional morphology (open, then close, square kernel). Components
from `cv2.connectedComponentsWithStats` with the chosen connectivity; area filters with
counted warnings; each region carries its exact mask (holes kept or filled) and outer contour.
Score = border uniformity x bbox fill heuristic. Not suitable for overlapping objects or busy
photographic backgrounds (warned as `background-not-uniform` / `region-covers-image`).

## `auto`

Tries `strategies` in order (default `grid-auto`, `contours`). Accepts the first result with
regions, `score >= min_score`, no `*-irregular`/`background-not-uniform` warning and, for
`grid-auto`, mean cell fill ≥ `min_fill` (sparse objects in a "grid" of whitespace are better
served by contours). Every attempt and the selected strategy are recorded in `details`.

## Reading order (`ordering.py`)

Sort by `(top, left, bottom, right)`; a region joins the current row when its vertical center
lies inside the first region of that row; rows are then ordered left to right. Deterministic
and documented because users name files by index.
