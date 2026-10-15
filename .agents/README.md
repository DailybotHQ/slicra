# `.agents/` — agent kit for working on Slicra

Canonical, cross-agent home for the personas, procedures and commands that AI agents use while
developing this repository. `.claude` and `.cursor` are symlinks to this folder, so Claude Code
and Cursor read the same files; other agents can read them as plain Markdown.

| Path | Contents |
| --- | --- |
| `agents/` | Personas: architect, reviewer, executor, debugger, qa, perf-optimizer, security-auditor, cli-author, detector-author |
| `skills/` | Vendored `deepworkplan` and `ai-diff-reviewer` (pinned), the product skill `slicra` (symlink), and repo procedures (`add-detector`, `add-mask-shape`, `cli-option`, `release`) |
| `commands/` | `dwp-*` delegators, `skill-create`, `agent-create`, `lib-upgrade`, `code-review`, `commit`, `pr` |
| `docs/` | [skills_agents_catalog.md](docs/skills_agents_catalog.md), [COMMANDS_REFERENCE.md](docs/COMMANDS_REFERENCE.md) |
| `settings.json` | Claude Code permissions baseline (gates allowed, push/publish ask, `.env` denied) |

Not to be confused with `skills/slicra/` at the repository root: that is the skill **shipped
to Slicra's users**. Start at [AGENTS.md](../AGENTS.md).
