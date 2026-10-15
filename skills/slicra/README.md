# `skills/slicra` — the Slicra Agent Skill

A portable [Agent Skill](https://agentskills.io/specification) shipped with Slicra for **end users**:
it teaches a coding agent to inspect, preview, extract and batch-process images with the locally
installed `slicra` CLI, without uploading anything.

| File | Purpose |
| --- | --- |
| `SKILL.md` | Entry point loaded by the agent (frontmatter `name: slicra` + short workflow) |
| `references/configuration.md` | Full YAML/CLI option reference and exit codes |
| `references/troubleshooting.md` | What to do when detection is ambiguous, merges or cuts objects |
| `assets/*.yaml` | Ready-to-use example configs (explicit 5x5 grid, real-sheet `grid-auto`) |

Install: see the "Agent Skill" section of the root [README](../../README.md). Validate after
editing with `agentskills validate skills/slicra` and `python -m pytest tests/test_skill.py`
(which also checks that every command the skill mentions exists). Keep it in sync with the CLI.
