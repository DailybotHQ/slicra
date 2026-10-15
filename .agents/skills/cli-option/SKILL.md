---
name: cli-option
description: Add or change a Slicra CLI option or command consistently across config, CLI, tests and docs. Use when a user-facing flag is requested.
---

# Add a CLI option

1. Make sure the behavior exists as a config key first (`config.py`); the CLI only maps flags to overrides.
2. Define an `Annotated[...]` alias near the other options in `src/slicra/cli.py` with clear help text; add the parameter to every command where it applies (`inspect`, `preview`, `extract`).
3. Map it in `collect_overrides` to the nested config key. CLI > YAML > defaults.
4. Tests in `tests/test_cli.py`: the option changes the outcome, the YAML value is overridden, invalid values exit 2.
5. Docs: README EN/ES CLI section, `skills/slicra/SKILL.md` or references when agents should use it, CHANGELOG.
6. `tests/test_skill.py` checks that commands referenced by the skill exist; keep it green.
