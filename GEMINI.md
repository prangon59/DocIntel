# Project Rules: AI Document Intelligence System

## Source of truth
- Requirements live in docs/SPEC.md. Re-read it at the start of every phase.
- Do not change the tech stack without asking me.

## Workflow
- Work in phases. Produce a plan artifact first and wait for approval.
- After each phase: run tests, lint (ruff, mypy, eslint), and summarize results in an artifact. Do not start the next phase on your own.
- Commit at the end of each phase (conventional commits).

## Backend standards
- Python 3.12, type hints everywhere, Pydantic v2, async SQLAlchemy.
- Money is always Decimal, never float.
- Small single-purpose modules. Business logic lives in services/, never in route handlers.
- All config via pydantic-settings. No secrets in code. Keep .env.example updated.
- LLM calls go only through the LLMClient interface.
- Validation (math, duplicates, missing fields) is deterministic code, never the LLM.
- Never invent extracted values: missing means null with a confidence score.
- One failed file or page must never crash a batch.

## Frontend standards
- Next.js App Router, TypeScript strict, Tailwind, shadcn/ui, TanStack Query.
- Every page needs loading, error, and empty states. Dark mode supported.

## Testing and honesty
- Every service gets tests, including failure cases.
- NEVER fabricate metrics. Report only numbers produced by running /eval.
- State clearly that the evaluation dataset is synthetic.

## Terminal safety
- Ask before deleting files or running destructive commands.
- Never commit .env or API keys.
