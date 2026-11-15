# Engineering Workflow

## Git workflow

- Keep `main` limited to completed, conclusive work.
- Use one topic branch for each work segment. Branch names must start with
  `feat/`, `fix/`, `exp/`, `research/`, `infra/`, `docs/`, or `chore/`.
- Merge completed work with `git merge --no-ff`, then delete the topic branch.
- Write merge commits as `Merge <branch>: <one-line summary>`.
- Write commits as `type: description` or `type(scope): description`.
- Stage files explicitly; do not use `git commit -a`.
- Ask before rewriting history or pushing to a remote.

## Experiments

- Before implementation or execution, register the expectation and acceptance
  thresholds in a standalone commit on `main`.
- Keep exploratory work on an `exp/` or `research/` branch until it supports a
  conclusion.
- Do not revise registered thresholds after observing results.

## Data and secrets

- Never commit datasets, API keys, credentials, or secrets.
- Keep reusable scripts in the repository.
