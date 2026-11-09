---
description: Finish and verify the current phase
---
1. Run backend tests (pytest) and fix failures.
2. Run ruff and mypy; for the frontend run eslint and tsc.
3. Run docker compose up --build and confirm /health returns OK.
4. Summarize what was built, what is untested, and known issues in an artifact.
5. Commit with a conventional commit message.
