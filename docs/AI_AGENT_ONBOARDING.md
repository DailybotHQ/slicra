# AI agent onboarding — first session checklist

1. **Read** [`AGENTS.md`](../AGENTS.md) (rules + quick commands), then
   [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md).
2. **Install** (Python 3.11+):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   python -m pip install -e ".[dev]"
   python examples/generate_fixtures.py
   ```
3. **Validate the baseline** before changing anything:
   ```bash
   ruff check src tests examples && ruff format --check src tests examples && mypy
   python -m pytest -m "not slow"
   ```
   Expect all green. If not, stop and report: do not build on a broken baseline.
4. **Try the product** once so you understand its behavior:
   ```bash
   slicra inspect examples/input/avatars-grid.png --mode grid-auto
   slicra extract examples/input/shapes-sheet.png --mode contours --shape original --output tmp/try
   ```
   Open `tmp/try/preview.png` and `tmp/try/manifest.json`.
5. **Find your way:**
   - Detection logic → `src/slicra/detectors/` ([README](../src/slicra/detectors/README.md))
   - Shapes/masks → `src/slicra/masks/` ([README](../src/slicra/masks/README.md))
   - Config schema → `src/slicra/config.py`; CLI → `src/slicra/cli.py`
   - Tests → `tests/` (mapping in [`TESTING_GUIDE.md`](TESTING_GUIDE.md))
   - Agent Skill shipped to users → `skills/slicra/` (do not confuse with `.agents/skills/`,
     the skills for agents working on this repository)
6. **Plan non-trivial work** with `/dwp-create "<goal>"`; small direct edits are done directly.
7. **Before finishing:** run the gates for your touched surface (see the testing guide), update
   docs/CHANGELOG for user-visible changes, and report what you validated.

Scratch output goes to `tmp/` (gitignored). Plan artifacts go to `.dwp/plans/<plan>/`.
Never put user images or real photographs in the repository.
