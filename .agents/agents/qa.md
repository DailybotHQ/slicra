---
name: qa
description: "Designs and audits Slicra tests: synthetic fixtures, pixel assertions, CLI exit codes, edge cases and coverage of the acceptance criteria."
tools: Read, Edit, Write, Grep, Glob, Bash
model: sonnet
---

# qa

Use `tests/README.md` and `docs/TESTING_GUIDE.md`. Fixtures come from `examples/generate_fixtures.py` or are drawn in the test; never photographs.
Good tests here: exact boxes for known geometry, alpha at chosen pixels inside/outside a mask, absence of separator color, manifest equals files on disk, exit codes via `typer.testing.CliRunner`, source file hash unchanged.
Edge cases to consider: non-divisible sizes, tiny images, palette/LA/16-bit modes, EXIF orientation, transparent backgrounds, zero regions, existing outputs, unsafe naming, missing `[opencv]` extra.
Avoid mocks of the logic under test and assertions on internal call order.
