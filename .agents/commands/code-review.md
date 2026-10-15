---
description: Review the current Slicra change set with the local AI Diff Reviewer and the repo reviewer persona.
---

# /code-review

1. Determine the range: staged + unstaged changes, or `main...HEAD` on a branch.
2. Run the vendored AI Diff Reviewer (Flow A): read `.agents/skills/ai-diff-reviewer/SKILL.md`
   and review that range; it layers `.review/extension.md` on its base rubric.
3. Apply the `reviewer` persona checklist (`.agents/agents/reviewer.md`).
4. Report findings ranked by severity. A verified `critical` must be fixed before commit/merge;
   an incomplete review is reported as incomplete, never as clean.
