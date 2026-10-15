"""Structural checks for the portable Agent Skill (agentskills.io specification)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "slicra"


def frontmatter() -> tuple[dict, str]:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    assert match, "SKILL.md must start with YAML frontmatter"
    return yaml.safe_load(match.group(1)), match.group(2)


def test_frontmatter_follows_spec() -> None:
    meta, body = frontmatter()
    assert meta["name"] == SKILL_DIR.name == "slicra"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", meta["name"]) and len(meta["name"]) <= 64
    assert 0 < len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]
    assert len(meta.get("compatibility", "")) <= 500
    assert len(body.splitlines()) < 500


def test_linked_references_exist() -> None:
    _meta, body = frontmatter()
    for link in re.findall(r"\]\(([^)#]+)\)", body):
        assert (SKILL_DIR / link).is_file(), link


def test_skill_commands_exist_in_cli() -> None:
    import typer
    from typer.testing import CliRunner

    from slicra.cli import app

    _meta, body = frontmatter()
    for command in sorted(set(re.findall(r"slicra (\w+)", body)) - {"inspect"} | {"inspect"}):
        assert CliRunner().invoke(app, [command, "--help"]).exit_code == 0, command
    # Inspect the registered options, not the rendered help: Rich adds ANSI codes in CI terminals.
    extract = typer.main.get_command(app).commands["extract"]  # type: ignore[attr-defined]
    options = {opt for param in extract.params for opt in param.opts}
    assert "--flat" in options
