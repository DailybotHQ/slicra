---
name: cli-author
description: Adds or changes Slicra CLI commands and options with clear help text, consistent exit codes and synced docs.
tools: Read, Edit, Write, Grep, Glob, Bash
model: sonnet
---

# cli-author

CLI lives in `src/slicra/cli.py` (Typer). Options map to config keys via `collect_overrides`; precedence is CLI > YAML > defaults.
For every change: `--help` text, an Annotated option alias reused across commands where it applies, the right exit code (`errors.py`), a `CliRunner` test in `tests/test_cli.py` (success and failure), README EN + ES, `skills/slicra/SKILL.md`/references if agents should use it, CHANGELOG.
Backward compatibility: never rename or remove an option without a deprecation path; never change an exit code silently.
