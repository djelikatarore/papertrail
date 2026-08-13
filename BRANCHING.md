# Branching Strategy

This project now uses three long-lived branches. The earlier per-sprint branch
history (`sprint-1-setup` through `sprint-8-backend`, plus the `develop`
integration branch) has been retired — `develop` was renamed to `backend`,
`sprint-9-frontend` was renamed to `frontend`, and every intermediate sprint
branch was deleted once its content was folded into `backend`.

## Branches

| Branch | Content |
|---|---|
| `main` | Reserved for stable/release milestones. Kept blank (initial commit only) — nothing has been merged into it yet. |
| `backend` | Backend-only mirror: just the `backend/` directory, kept in sync with its current state on `frontend`. Not developed on directly — every change originates on `frontend` and is copied over (see "Keeping `backend` in sync" below). |
| `frontend` | The full, current project — backend and frontend together. This is the active development branch; almost all work happens here. |

## Keeping `backend` in sync

`backend` exists as a standalone snapshot of just the Python backend, useful
for anyone who only needs that half of the project. Since all real
development happens on `frontend`, `backend` is brought up to date by
replacing its `backend/` directory wholesale with `frontend`'s current
`backend/` directory — not by cherry-picking or merging individual commits:

```
git checkout backend
git rm -r --quiet backend/
git checkout frontend -- backend/
git diff --quiet frontend -- backend/   # verify: no output means identical
git commit -m "sync: replace backend/ with its current state from the frontend branch"
git checkout frontend
```

This is a manual, on-demand sync (typically done after a batch of backend
changes lands on `frontend`), not an automated or scheduled one.
