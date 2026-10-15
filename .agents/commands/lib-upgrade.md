---
description: Safely upgrade this repo's dependencies (batched, validated, revertible) via the DeepWorkPlan dependency-upgrade addon.
---

# /lib-upgrade

Bring Slicra's dependencies up to date **without breaking the build**. This command is a
**thin delegator** to the DeepWorkPlan `deepworkplan-addon-dependency-upgrade` addon — it does not
contain the upgrade logic itself.

## Steps

1. Invoke the addon: read `.agents/skills/deepworkplan/addons/dependency-upgrade/SKILL.md` and
   follow its flow.
2. Package manager: **pip** with ranges in `pyproject.toml` (no lockfile). Runtime deps: pillow,
   pydantic, pyyaml, typer; extra `opencv`: numpy, opencv-python-headless; dev: pytest, ruff,
   mypy, types-PyYAML, build.
3. After each batch run the real gate:
   `ruff check src tests examples && ruff format --check src tests examples && mypy && python -m pytest`.
   Revert any batch whose gate fails, and summarize.
4. Surface the upgrade report and the diff; do **not** auto-commit.

## Notes

- Majors (e.g. a new Pillow or NumPy major) require explicit approval before they are included.
- Also check the CI matrix Python versions still install the new ranges.
