# Product spec — Slicra

## What it is, in one sentence

Slicra takes one image that contains many pictures or shapes (a sheet of 25 avatars, a sprite
sheet, stickers on a page) and gives you back each one as its own image file, cut cleanly, with
the shape of your choice.

## The problem

People regularly receive or generate "contact sheets": a grid of profile pictures, an AI image
with several variations, a page of icons. Cutting them by hand in an image editor is slow and
error-prone: the gaps between pictures sneak into the crops, sizes come out inconsistent, and
doing it for dozens of sheets is tedious. Generic tools either assume a perfect grid (and fail
on real images whose spacing varies by a few pixels) or require cloud AI services that upload
private pictures.

The original case: a 5 x 5 grid of square avatars with white space between them must become
exactly 25 images, with none of the white space included. Real sheets of this kind have spacing
that varies from 11 to 17 pixels, so "every gap is 12 px" is not good enough.

## Who it is for

- **Designers, marketers and community managers** who need individual avatars, icons or
  stickers from a sheet.
- **Developers and game makers** splitting sprite sheets or generated assets in a build step.
- **AI coding agents** acting for a user: the bundled Agent Skill teaches them to run the same
  local tool safely.
- **Python programs** that need region detection and masking as a library.

## Key capabilities

1. **Find the pieces.** Explicit grids, grids inferred from the background-colored gaps,
   free-standing objects on plain/transparent backgrounds, or regions you declare by hand.
2. **Choose the output shape independently.** Keep the rectangle, or export a circle, ellipse,
   star, polygon, or the exact detected silhouette with transparency.
3. **See before you cut.** A preview image numbers every region that will be exported.
4. **Process folders.** One command turns a folder of sheets into a folder of individual PNGs.
5. **Audit the result.** A manifest lists every region, its coordinates and its output file.
6. **Use it the way you work.** Command line, Python library, or through an AI agent.

## Principles (what users can rely on)

- Runs entirely on the user's machine: no uploads, no telemetry, no AI services.
- Never modifies the original image and never overwrites files without permission.
- Never pretends: if it cannot find the pieces with confidence, it says so and stops.
- Same input + same settings = same output, byte for byte.

## Success criteria

- A 5 x 5 avatar sheet becomes exactly 25 correct images, with no separator pixels, in one
  command — including real sheets with irregular spacing.
- Irregular shapes on a plain background come out as transparent cut-outs that keep their
  outline.
- Mode, spacing, margins, output size, shape, format and file names can be changed through
  settings, never by editing code.
- Installation is one `pip install`; the test suite and package build pass on Linux, macOS and
  Windows.

## Non-goals

- Semantic segmentation of photographs (separating a person from a busy background).
- Separating objects that overlap each other.
- Image editing beyond crop, mask and resize (no color correction, no upscaling models).
- A graphical user interface or a hosted web service.
- SVG input or masks (possible future extension, not available today).
