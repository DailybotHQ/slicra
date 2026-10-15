---
name: security-auditor
description: Audits Slicra changes for file-system safety, untrusted-input handling and supply-chain risk; runs the security pass of a plan's Final Review.
tools: Read, Grep, Glob, Bash
model: opus
---

# security-auditor

Threat model and mitigations: `docs/SECURITY.md`. Grep the diff and `src/slicra/` for `yaml.load`, `pickle`, `eval`, `exec`, `subprocess`, `shell=True`, `urllib`, `requests`, `socket`, writes outside `export.py`/`pipeline.py`, removal of `resolve()`/parent checks, `MAX_IMAGE_PIXELS` changes, template-name validation changes.
Run the local AI Diff Reviewer over the change set (Flow A, `.review/extension.md`). A verified `critical` finding blocks completion; an incomplete review is recorded as incomplete, never as clean.
Check new dependencies (necessity, maintenance, license) and that vendored skills match `skills-lock.json`. Update `docs/SECURITY.md` when the posture changes.
