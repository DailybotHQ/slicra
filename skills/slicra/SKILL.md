---
name: slicra
description: Split one image into many with the local `slicra` CLI. Use when the user wants to cut a sheet of avatars, a photo mosaic, a sprite sheet, a sticker sheet, a contact sheet or any image with several separate elements into individual files; to export each element as a circle, star, ellipse, polygon or its exact silhouette with transparency; or to batch-process a folder of such sheets. Works offline and never modifies the source image.
license: MIT
compatibility: Requires Python 3.11+ and the slicra package (pip install "slicra[opencv]"); runs fully offline.
metadata:
  version: "0.1.0"
  homepage: https://github.com/DailybotHQ/slicra
---

# Slicra

Detect regions in an image, preview them, then export each one as its own file
with an optional mask. Detection (*where* the regions are) and masking (*which
silhouette* is kept) are independent.

## 0. Check the tool

```bash
slicra --version || python -m pip install "slicra[opencv]"
```

Never upload the user's images anywhere. Everything runs locally; the source
file is only read. Write outputs to a new directory.

## 1. Inspect before choosing a detector

```bash
slicra inspect sheet.png --mode grid-auto     # writes nothing
```

Choose the mode by what the image looks like:

| Image | Mode |
| --- | --- |
| Tiles separated by background-colored gaps (avatar sheets, mosaics) | `grid-auto` |
| Perfectly regular grid with known rows/cols/gaps/margins | `grid` |
| Disjoint objects on a plain or transparent background (sprites, stickers) | `contours` |
| Specific areas the user describes, or anything detection gets wrong | `manual` |
| Unsure | `auto` (tries grid-auto, then contours, and says which it picked) |

Pass `--rows/--cols` with `grid-auto` when the user states the expected count: it
then fails instead of guessing.

## 2. Preview, check, adjust

```bash
slicra preview sheet.png --mode grid-auto --output /tmp/preview.png
```

Open the preview: every region has a pink box and its index. Confirm the count
and that no box includes gap pixels or cuts an object before extracting. If it
is wrong, see [troubleshooting](references/troubleshooting.md).

## 3. Extract

```bash
slicra extract sheet.png --mode grid-auto --output out/            # rectangles
slicra extract sheet.png --mode grid-auto --shape circle --output out/
slicra extract sheet.png --config slicra.yaml --output out/
```

`out/` gets one PNG per region (transparent outside the mask), `preview.png` and
`manifest.json` (boxes, ids, files, warnings). Existing files are never replaced
unless the user asks for `--overwrite`.

## 4. Batch a folder

```bash
slicra extract sheets/ --mode grid-auto --output out/          # out/<sheet>/...
slicra extract sheets/ --mode grid-auto --output out/ --flat   # all PNGs in out/
```

With `--flat`, manifests are in `out/_manifests/` and previews in
`out/_previews/`. Report failures from the command output; the exit code is
non-zero when any image failed.

## 5. When detection is doubtful

Read the `warning [...]` lines and the exit code (3 = nothing trustworthy
detected). Do not claim success when regions are missing or merged: adjust
parameters, switch mode, or ask the user. Details:
[configuration](references/configuration.md) and
[troubleshooting](references/troubleshooting.md).
