# Pull request review workflow

1. **Branch** from `main`; keep the PR focused on one concern.
2. **Local gates** (must pass before opening):
   `ruff check src tests examples && ruff format --check src tests examples && mypy && python -m pytest`
3. **Local AI review** (Flow A, installed): run the vendored AI Diff Reviewer against the branch
   diff — ask your agent to "review this diff with ai-diff-reviewer". It applies the base rubric
   plus [`.review/extension.md`](../.review/extension.md). Resolve verified `critical` findings
   before opening; an incomplete review is not a clean review.
4. **PR description**: what and why, user-visible changes (CLI/API/config/manifest), the gates you
   ran with results, and a security note when any mitigation in [`SECURITY.md`](SECURITY.md) is
   touched. End with the attribution lines the repository uses.
5. **CI** must be green on the full matrix (lint, tests on Linux/macOS/Windows x 3.11-3.13,
   core-without-opencv, packaging).
6. **Review focus**: path safety and overwrite rules, honest diagnostics (no fabricated regions),
   pixel-level tests, docs/skill sync for CLI changes.
7. **Merge** with a Conventional Commit title; update `CHANGELOG.md` under *Unreleased*.

The CI review Action (Flow B, `pr-review.yml`) is **not installed**; it can be added later through
the AI Diff Reviewer `setup` sub-skill with a provider secret configured by a maintainer.
