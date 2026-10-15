# AGENTS.md — Slicra

Entry point for AI coding agents (Claude Code, Codex, Cursor, Gemini, Copilot, Cline, ...)
working **on** this repository. `CLAUDE.md` is a symlink to this file.

Slicra is a Python 3.11+ library + `slicra` CLI + portable Agent Skill that detects regions in an
image (grids, sprite sheets, irregular shapes) and exports each one as its own file with an
independent mask. Local, deterministic, no network. Product context:
[docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).

DWP standard: 7.0.0 (onboarded 2026-10-14; skill 7.8.1)

## Documentation index

| Document | Use it for |
| --- | --- |
| [docs/README.md](docs/README.md) | Index of all technical docs |
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | What and why: users, capabilities, non-goals |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline, package layout, public API, design decisions |
| [docs/STANDARDS.md](docs/STANDARDS.md) | Code conventions, errors/exit codes, forbidden patterns |
| [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | Full/scoped commands, source-to-test map, escalation |
| [docs/DEVELOPMENT_COMMANDS.md](docs/DEVELOPMENT_COMMANDS.md) | Setup, validation, build, release commands |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat surface and mitigations, supply chain |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Hot paths and budgets |
| [docs/AI_AGENT_ONBOARDING.md](docs/AI_AGENT_ONBOARDING.md) | First-session checklist |
| [docs/AI_AGENT_COLLAB.md](docs/AI_AGENT_COLLAB.md) | Ownership, handoffs, conflicts |
| [docs/PR_REVIEW_WORKFLOW.md](docs/PR_REVIEW_WORKFLOW.md) | Branch → local AI review → CI → merge |
| [src/slicra/README.md](src/slicra/README.md) | Package surface and invariants |
| [src/slicra/detectors/README.md](src/slicra/detectors/README.md) | Detector contract; [algorithms](src/slicra/detectors/docs/README.md) |
| [src/slicra/masks/README.md](src/slicra/masks/README.md) | Mask shapes and geometry rules |
| [tests/README.md](tests/README.md) | What each test file covers |
| [examples/README.md](examples/README.md) | Example configs and fixtures |
| [skills/slicra/SKILL.md](skills/slicra/SKILL.md) | The Agent Skill shipped to **users** of Slicra |
| [.agents/README.md](.agents/README.md) | Agent kit for working on this repo (agents, skills, commands) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor workflow, adding detectors/masks |

## Repository structure

```text
slicra/
├── AGENTS.md, CLAUDE.md → AGENTS.md   agent entry point
├── README.md, README.es.md            user docs (EN/ES), logo in docs/assets/
├── pyproject.toml                     Hatchling build, deps, extras [opencv] [dev], ruff/mypy/pytest config
├── src/slicra/                        the package
│   ├── cli.py, pipeline.py            CLI (Typer) and the single engine (ImageSlicer)
│   ├── config.py, models.py, errors.py   schema, data models, exit-coded errors
│   ├── imageio.py, background.py, ordering.py, extraction.py, preview.py, export.py
│   ├── detectors/                     grid, grid_auto, contours (OpenCV), manual, registry/auto
│   ├── masks/                         shape masks
│   └── presets/                       built-in detection templates (package data)
├── tests/                             pytest suite (synthetic fixtures only)
├── examples/                          fixture generator, example configs, docs renderer
├── skills/slicra/                     portable Agent Skill for end users (SKILL.md + references/)
├── docs/                              technical docs + assets/
├── .agents/                           agent kit for this repo (.claude → .agents, .cursor → .agents)
├── .review/extension.md               repo rules for the AI Diff Reviewer
├── .github/workflows/ci.yml           lint, test matrix, core-without-opencv, packaging
├── .dwp/                              Deep Work Plans (gitignored except config.json)
└── tmp/                               scratch space (gitignored)
```

## Mandatory rules

1. **English only** in code, comments, docs, commits and CLI output (user-facing Spanish lives
   only in `README.es.md`).
2. **Conventional Commits:** `type(scope): description`. Scopes: `grid`, `grid-auto`,
   `contours`, `manual`, `masks`, `export`, `cli`, `config`, `api`, `skill`, `docs`, `ci`,
   `deps`, `harness`.
3. **Tests with every behavior change.** pytest files `tests/test_<area>.py`; assert pixels,
   boxes, alpha, exit codes — never only "a file exists". Synthetic fixtures only; no real
   photographs or personal data. Bug fixes add a failing-first regression test.
4. **Validation rule.** Select gates from your touched surface with the mapping in
   [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md); changes to shared/core files (`config.py`,
   `models.py`, `pipeline.py`, `errors.py`, `cli.py`, `pyproject.toml`, `conftest.py`) run the
   full suite. When unsure, run the fallback:
   `ruff check src tests examples && ruff format --check src tests examples && mypy && python -m pytest`.
5. **Errors and diagnostics.** Expected failures raise a `SlicraError` subclass with a stable
   exit code and a `hint`; uncertainty becomes a `DetectionWarning` with a stable code. Never
   fabricate regions, never report success with zero regions, never call a heuristic a
   probability. No `print` in library code.
6. **Safety invariants.** Never write to the source image, never escape the output directory,
   never overwrite without `overwrite`/`--overwrite`; `yaml.safe_load` only; no network calls,
   telemetry, `pickle`, `eval`/`exec`, `shell=True` in `src/slicra/`. See
   [docs/SECURITY.md](docs/SECURITY.md).
7. **One engine, synced surfaces.** CLI and API share `pipeline.py`. A change to a command,
   option, default, config key, manifest field or exit code updates README (EN + ES),
   `skills/slicra/` references, CHANGELOG and tests together.
8. **Optional dependencies stay optional.** NumPy/OpenCV only inside `detectors/contours.py`
   helpers; the core must pass its tests without the `[opencv]` extra.
9. **Repository boundaries.** Commit only when asked or when a plan task's gate defines it.
   Never push, tag, publish to PyPI, change repository settings or install system-wide tools
   without explicit approval. Do not edit vendored skills in `.agents/skills/deepworkplan/` or
   `.agents/skills/ai-diff-reviewer/` by hand.
10. **Where outputs go.** Plan artifacts (analysis, gate logs, reviews) live in that plan's
    `.dwp/plans/<plan>/analysis_results/`; throwaway output goes to `tmp/`. Never write scratch
    files to the repository root.
11. **Progress reporting** (status notes, optional team reports) is best-effort and never blocks
    the work.

## Working principles

Work with autonomy, ownership and sound judgment. Pursue correctness, clarity, simplicity and
verified completion.

- **Own the outcome.** Carry authorized work through investigation, implementation and
  validation until the requested outcome is complete or a concrete blocker stops it.
- **Be resourceful before asking.** Read the code, docs, tests and prior decisions first; answer
  what reasonable investigation can answer instead of handing that work to the user.
- **Make routine decisions independently.** Choose sensible approaches within the authorized
  scope, take the recommended option, and record consequential decisions (options, choice, why,
  how to reverse) in the plan or PR. Do not ask to confirm routine or already-authorized steps.
- **Ask when judgment or authorization is missing.** Escalate only what is critical and name its
  class: an action needing approval not already granted (push, publish, release), a consent or
  login screen, irreducible ambiguity, a gate that cannot pass without weakening it, risk of
  damage, terms, or exhausted capacity. Bring the evidence, options and your recommendation.
- **Make approvals concrete.** Finish the authorized preparation first, then present a
  reviewable result and name the exact action that needs approval and why.
- **Work through obstacles.** Investigate failures and attempt reasonable recovery within scope;
  continue independent authorized work while a decision is pending; respect stop conditions.
- **Respect intent and scope.** Analysis requests stay analysis. Propose broader improvements
  separately. Preserve the user's existing work, decisions and approval rules.
- **Apply proportionate rigor.** Fix root causes, prefer maintainable solutions, match
  validation and polish to the impact, and avoid unrelated changes.
- **Communicate directly and precisely.** Lead with the result or decision; separate verified
  facts, assumptions and open uncertainty.
- **Verify before declaring completion.** Check the result against the request, run the
  appropriate gates, fix what is in scope, and report what was validated and what was not.
  Never claim actions, checks or outcomes that did not happen.

These defaults never override host permissions, a narrower request, plan gates, read-only flows
or the boundaries in rule 9.

## Quick Commands

Run from the repository root with the venv active (`source .venv/bin/activate`) or prefix with
`.venv/bin/`. Package manager: pip (no lockfile).

| Task | Command | Kind |
| --- | --- | --- |
| Install (dev) | `python3 -m venv .venv && python -m pip install -e ".[dev]"` | — |
| Install (core only) | `python -m pip install -e .` | — |
| Generate fixtures | `python examples/generate_fixtures.py` | — |
| Tests | `python -m pytest` | full (~40 s, includes packaging) |
| Tests (fast) | `python -m pytest -m "not slow"` | full minus packaging (~9 s) |
| Tests (file) | `python -m pytest tests/test_grid.py` | scoped (verified: 29 tests) |
| Tests (name) | `python -m pytest -k manual` | scoped (verified: 11 tests) |
| Packaging | `python -m pytest -m slow` | scoped marker (verified: 1 test) |
| Lint | `ruff check src tests examples` | full |
| Lint (path) | `ruff check src/slicra/detectors` | scoped |
| Format check | `ruff format --check src tests examples` | full |
| Types | `mypy` | full (project-wide is the real check) |
| Build | `python -m build` | — |
| Run | `slicra extract examples/input/avatars-grid.png --mode grid-auto --output tmp/avatars` | — |
| Skill validation | `agentskills validate skills/slicra` | optional (`pip install skills-ref`) |

CI (`.github/workflows/ci.yml`) runs the same commands on Linux/macOS/Windows x Python
3.11-3.13, plus a job without the `[opencv]` extra.

## Deep Work Plans — invocation

Structured work runs through the local DWP flows (`.agents/commands/dwp-*` delegators; the
flows live in `.agents/skills/deepworkplan/` — discovery is local, no network service is
consulted):

| Intent | Route |
|---|---|
| "plan this work", "create a plan" | `/dwp-create` |
| "execute / run the plan" | `/dwp-execute` |
| "continue / resume the interrupted plan" | `/dwp-resume` |
| "plan status", "what's left" | `/dwp-status` (read-only) |
| "verify the repo / the plan" | `/dwp-verify` (read-only) |
| "change the plan", "promote to full" | `/dwp-refine` |
| "check for a newer DWP skill" | `/dwp-upgrade` (installs only with consent) |
| ordinary direct edit ("fix this", "rename that") | done directly — never silently becomes a plan |

Hosts without slash commands invoke the same flows by name (`#deepworkplan-create` or plain
text). `trust`/`auto` authorizes unattended continuation within the requested flow; it is not a
flow selector, and read-only routes stay read-only. Every plan ends with the Final Review: a
security pass over the plan's changes including the local AI Diff Reviewer run, final-state
validation, and skills reconciliation. All commands: [.agents/docs/COMMANDS_REFERENCE.md](.agents/docs/COMMANDS_REFERENCE.md).

### Local review

The AI Diff Reviewer local review (v3.3.14, `.agents/skills/ai-diff-reviewer/`) is installed
with the repo rules in [.review/extension.md](.review/extension.md). Active flow: **Flow A
(local only)**. The CI Action (Flow B) is not installed.

### Host capabilities and authority (for unattended plans)

- **Host capabilities** (recorded in `.dwp/config.json` → `host`): `subagents: true`. Not
  available: `stop_agent`, `meter_spend`, `meter_tokens`, `meter_wall_clock`,
  `cancel_children`, `model_routing`; `telemetry: false` (no consent). Resource limits in plans
  are therefore **advisory, not enforced**.
- **Authority.** The maintainer (repository owner) authors or approves plans; a plan approved
  in advance may run unattended inside its contract. Always stop for approval before: pushing,
  tagging, publishing to PyPI, creating releases, changing GitHub settings, adding runtime
  dependencies, editing vendored skills, or any action outside the repository. Approval for a
  plan covers its listed tasks only; it is not re-requested for those, and it never extends to
  the actions above.
- **Outcome checks** for plan acceptance criteria come from the commands above and the mapping
  in [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md); behavior with real user images is not
  covered by CI (optional `tests/test_real_samples.py`).

## Scratch and plan output

- `tmp/` — gitignored freeform scratch (exploratory runs, exports, prompt handoffs).
- `.dwp/plans/PLAN_<id>_<slug>/` — Deep Work Plans and everything they produce
  (`analysis_results/`); `.dwp/config.json` (addon registry, host capabilities) is tracked.
