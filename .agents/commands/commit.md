---
description: Create a Conventional Commit for the current Slicra changes after the gates pass.
---

# /commit

1. Run the gates for the touched surface (`docs/TESTING_GUIDE.md`); stop if anything is red.
2. Stage only files that belong to the change (never `.venv/`, `output/`, `tmp/`, `.dwp/` except
   `.dwp/config.json`, or real images).
3. Message: `type(scope): description` with scopes from `docs/STANDARDS.md`; body explains why.
   End with the attribution trailer the session requires.
4. Commit only when the user asked for it or a plan task's gate defines it. Never push here.
