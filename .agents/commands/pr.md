---
description: Open a pull request for the current Slicra branch following the PR review workflow.
---

# /pr

Follow `docs/PR_REVIEW_WORKFLOW.md`:
1. Branch is not `main`; gates are green; `/code-review` has no open verified critical finding.
2. Push the branch and open the PR with `gh pr create` **only after the user approves pushing**.
3. Description: what and why, user-visible changes (CLI/API/config/manifest), gates run with
   results, security note if a mitigation changed, CHANGELOG updated.
