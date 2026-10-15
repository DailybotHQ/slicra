# Skills and agents catalog

Everything in `.agents/` for agents working **on** Slicra. Reachable as `.claude/` and `.cursor/`
through symlinks. Keep this file in sync with disk (`/skill-create` and `/agent-create` do it).

## Skills (`.agents/skills/`)

| Skill | Kind | Purpose |
| --- | --- | --- |
| `deepworkplan/` | vendored, pinned v7.8.1 | Deep Work Plan flows: create, execute, refine, resume, status, verify, onboard, author, upgrade |
| `ai-diff-reviewer/` | vendored, pinned v3.3.14 | Local AI diff review (Flow A) with `.review/extension.md`; sub-skills generate-extension, setup, open-pr, apply-review, address-review |
| `slicra/` | symlink → `skills/slicra/` | The product's own Agent Skill: lets agents in this repo run the `slicra` CLI on images |
| `add-detector/` | repo | Add a new detection mode end to end |
| `add-mask-shape/` | repo | Add a new output mask shape |
| `cli-option/` | repo | Add or change a CLI option consistently |
| `release/` | repo | Prepare a release (publishing needs maintainer approval) |

Vendored skills are installed with `npx skills add ...tree/<tag>`; hashes in `skills-lock.json`.
Do not edit them by hand.

## Agents (`.agents/agents/`)

| Agent | Model tier | Role |
| --- | --- | --- |
| `architect` | opus | Cross-stage design, public API and schema coherence |
| `security-auditor` | opus | File-system safety, untrusted input, supply chain, Final Review security pass |
| `reviewer` | sonnet | Diff review against standards, security and docs sync |
| `executor` | sonnet | Implement a scoped task with tests, docs and gates |
| `debugger` | sonnet | Root-cause wrong detections, crops and failing tests |
| `qa` | sonnet | Test design: synthetic fixtures, pixel assertions, edge cases |
| `perf-optimizer` | sonnet | Hot-path profiling without changing outputs |
| `cli-author` | sonnet | CLI commands/options, help text, exit codes |
| `detector-author` | sonnet | Implement or tune detectors per the detector contract |

Opus is reserved for roles where a missed issue is expensive (design, security); the rest are
implementation roles where sonnet is sufficient.
