# AI agent collaboration

Rules for several agents (or agents and humans) working on Slicra at the same time.

## Ownership and boundaries

- One plan or task owns a surface at a time. Declare the files you will touch (the plan's
  *Touched Surface*) before editing, and stay inside it.
- High-conflict files: `src/slicra/config.py` (schema), `src/slicra/cli.py` (options),
  `src/slicra/__init__.py` (public API), `pyproject.toml`, `README.md`/`README.es.md`,
  `CHANGELOG.md`. Coordinate before two agents edit them in parallel; prefer sequential tasks.
- Detectors (`detectors/<name>.py`) and their tests are independent of each other and can be
  worked on in parallel.
- Vendored skills in `.agents/skills/deepworkplan/` and `.agents/skills/ai-diff-reviewer/` are
  not edited by hand; upgrade them through `/dwp-upgrade` or the pinned install commands.

## Handoffs

- Leave the tree green (fast suite + ruff + mypy) at every handoff, or state exactly what is red
  and why.
- Write handoff notes in the active plan (`.dwp/plans/<plan>/`), not in tracked files or the
  repository root.
- Summarize: what changed, what was validated (commands + results), what remains, and any open
  decision.

## Commits and branches

- Conventional Commits with the scopes listed in [`STANDARDS.md`](STANDARDS.md).
- Commit only when the user asks or a plan task's gate defines a commit. Never push, publish to
  PyPI, create releases or change repository settings without explicit approval.
- Work on a feature branch for anything non-trivial; `main` must stay releasable.

## Conflicts

- If another agent's change breaks your gate, do not revert their work; stop, record the
  conflict in the plan and ask the owner/user.
- Never resolve a merge conflict in `config.py` or `cli.py` by dropping options: both sides'
  behavior must survive, with tests.
