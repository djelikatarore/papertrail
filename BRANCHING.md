# Branching Strategy

This project uses three long-lived branches. `main` is the full project and
the active development branch — almost all work happens here. `backend` and
`frontend` are read-only mirrors of just their respective directory, kept in
sync with `main` on demand; neither is developed on directly.

(Earlier history: the project used per-sprint branches plus a `develop`
integration branch, later consolidated into `develop`→`backend` and
`sprint-9-frontend`→`frontend`, with `frontend` as the active branch and
`main` left blank. `main` has since absorbed `frontend`'s full history and
become the active branch instead; `frontend` was recreated as a
frontend-only mirror, mirroring how `backend` already worked.)

## Branches

| Branch | Content |
|---|---|
| `main` | The full, current project — backend and frontend together. This is the active development branch; almost all work happens here. |
| `backend` | Backend-only mirror: just the `backend/` directory, kept in sync with its current state on `main`. Not developed on directly — every change originates on `main` and is copied over (see below). |
| `frontend` | Frontend-only mirror: just the `frontend/` directory, kept in sync with its current state on `main`. Not developed on directly — every change originates on `main` and is copied over (see below). |

## Keeping `backend`/`frontend` in sync

Both mirror branches exist as standalone snapshots of just one half of the
project, useful for anyone who only needs that half. Since all real
development happens on `main`, each is brought up to date by replacing its
directory wholesale with `main`'s current version of that directory — not by
cherry-picking or merging individual commits:

```
# backend
git checkout backend
git rm -r --quiet backend/
git checkout main -- backend/
git diff --quiet main -- backend/   # verify: no output means identical
git commit -m "sync: replace backend/ with its current state from the main branch"
git checkout main

# frontend
git checkout frontend
git rm -r --quiet frontend/
git checkout main -- frontend/
git diff --quiet main -- frontend/   # verify: no output means identical
git commit -m "sync: replace frontend/ with its current state from the main branch"
git checkout main
```

This is a manual, on-demand sync (typically done after a batch of changes
lands on `main`), not an automated or scheduled one.
