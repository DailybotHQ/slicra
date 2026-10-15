---
name: release
description: "Prepare a Slicra release (version bump, changelog, full validation and build artifacts). Publishing itself needs explicit maintainer approval. Use when asked to cut or prepare a release."
---

# Prepare a release

1. Pick the version (SemVer): breaking CLI/API/config/manifest changes → major (minor while 0.x).
2. Update `src/slicra/_version.py` and `skills/slicra/SKILL.md` `metadata.version`; move CHANGELOG *Unreleased* entries under `## [x.y.z] - YYYY-MM-DD`.
3. Validate: `ruff check src tests examples && ruff format --check src tests examples && mypy && python -m pytest` (includes the packaging test).
4. Build: `python -m build` → `dist/`; inspect the wheel contents (presets, py.typed).
5. Stop and ask the maintainer before: tagging, pushing, creating a GitHub release, or `twine upload`. These are never done implicitly.
