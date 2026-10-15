# Commands reference

Commands live in `.agents/commands/`. Invoke them as `/name` in Claude Code, as `#name` in
agents that intercept slash syntax, or in plain text ("run `dwp-create` ...") on hosts without
slash commands. Every flow is local: no network service is consulted to find or run them.

## Deep Work Plan (thin delegators to `.agents/skills/deepworkplan/`)

| Command | Routes to | Writes? |
| --- | --- | --- |
| `/dwp-create <goal>` | `create` | yes — a Lite or Full plan in `.dwp/plans/` |
| `/dwp-execute [plan]` | `execute` | yes — task by task with gates |
| `/dwp-resume [plan]` | `resume` | yes — continues from the first open task |
| `/dwp-refine [plan]` | `refine` | yes — edit tasks, `promote` Lite → Full |
| `/dwp-status [plan]` | `status` | no (read-only) |
| `/dwp-verify [plan]` | `verify` | no (read-only conformance report) |
| `/dwp-upgrade` | `upgrade` | only with explicit consent |
| `/skill-create <name>` | `author` (create a skill) | yes — `.agents/skills/` + catalog |
| `/agent-create <name>` | `author` (create an agent) | yes — `.agents/agents/` + catalog |

## Repository commands

| Command | Purpose |
| --- | --- |
| `/lib-upgrade` | Batched, gated dependency upgrades (dependency-upgrade addon delegator) |
| `/code-review` | Local AI Diff Reviewer + reviewer checklist over the current changes |
| `/commit` | Conventional Commit after the gates pass (only when asked) |
| `/pr` | Open a PR per `docs/PR_REVIEW_WORKFLOW.md` (push needs approval) |

Product commands (`slicra init|validate|inspect|preview|extract|templates`) are documented in
the root README and `skills/slicra/`.
