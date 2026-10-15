# Development commands

Run everything from the repository root. The package manager is **pip** (no lockfile; dependency
ranges live in `pyproject.toml`). `uv` works too but is not required.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"      # core + opencv extra + pytest, ruff, mypy, build
python examples/generate_fixtures.py   # synthetic inputs in examples/input/ (gitignored)
```

Core-only install (no NumPy/OpenCV): `python -m pip install -e .`

## Validation

| Purpose | Command | Kind |
| --- | --- | --- |
| All tests | `python -m pytest` | full |
| Fast tests | `python -m pytest -m "not slow"` | full (minus packaging) |
| One file | `python -m pytest tests/test_grid.py` | scoped |
| By name | `python -m pytest -k manual` | scoped |
| Packaging | `python -m pytest -m slow` | scoped (marker) |
| Lint | `ruff check src tests examples` | full |
| Lint a path | `ruff check src/slicra/detectors` | scoped |
| Format check | `ruff format --check src tests examples` | full |
| Apply format/fixes | `ruff format src tests examples && ruff check --fix src tests examples` | full |
| Types | `mypy` | full (project-wide is the real check) |
| Validate the Agent Skill | `agentskills validate skills/slicra` | needs `pip install skills-ref` (optional) |

All of the above except the skill validator run locally and in CI (`.github/workflows/ci.yml`).

## Build and run

```bash
python -m build                        # dist/slicra-<version>.tar.gz and .whl
slicra --version
slicra init --output slicra.yaml
slicra extract examples/input/avatars-grid.png --mode grid-auto --output output/avatars
slicra extract --config examples/configs/irregular-shapes.yaml
python examples/render_docs_assets.py  # regenerate docs/assets/demo-*.png
```

## Release (manual, not automated)

1. Bump `src/slicra/_version.py`, move CHANGELOG *Unreleased* entries under the new version.
2. `python -m pytest && python -m build`.
3. Publishing to PyPI (`twine upload dist/*`) and tagging happen only with the maintainer's
   explicit approval; there is no publishing workflow in CI.
