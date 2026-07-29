# Branching Strategy

This project uses **one branch per sprint**, with each branch containing the
**cumulative** state of the backend at the end of that sprint (not an isolated
feature diff). Sprint branches were created sequentially — each one branched
from the tip of the previous sprint's branch — so the full history from
`sprint-2-backend` through `sprint-8-backend` is strictly linear, with no
divergent/parallel work to reconcile.

## Branches

| Branch | Content |
|---|---|
| `sprint-1-setup` | Initial backend scaffolding, SRS, project setup |
| `sprint-2-backend` | DB architecture, authentication (signup/login/JWT, forgot/reset password) |
| `sprint-3-backend` | Workspace/project management, PDF upload + text extraction |
| `sprint-4-backend` | OCR, LLM summary generation, keyword extraction, visual element description |
| `sprint-5-backend` | Embeddings, FAISS similarity, citation graph, arXiv suggestions, paper type detection |
| `sprint-6-backend` | Reserved for Grounded Q&A — in practice this work landed directly on `sprint-7-backend` (see below), so this branch is identical to `sprint-5-backend` |
| `sprint-7-backend` | Q&A + chat history, draft CRUD/generation/PDF export, feedback review, credits system removal, project access restriction, multi-source paper suggestions (arXiv/CORE/PubMed) |
| `sprint-8-backend` | Search + filters, pagination, profile/download endpoints, error-handling audit, async LLM migration, background upload processing, AI call parallelization |
| `develop` | **Integration branch** — the full, current, functionally-complete backend. Created by merging `sprint-2-backend` → `sprint-3-backend` → ... → `sprint-8-backend` in order. |
| `main` | Reserved for stable/release milestones (e.g. once the frontend is integrated) — kept untouched at the initial commit until then |

## Merge strategy

Because every sprint branch is a direct ancestor of the next, integrating them
into `develop` is a **sequential fast-forward merge** — no merge commits, no
conflicts:

```
git checkout sprint-2-backend
git checkout -b develop
git merge --ff-only sprint-3-backend
git merge --ff-only sprint-4-backend
git merge --ff-only sprint-5-backend
git merge --ff-only sprint-6-backend   # no-op, identical to sprint-5-backend
git merge --ff-only sprint-7-backend
git merge --ff-only sprint-8-backend
```

After this, `develop` points at the exact same commit as `sprint-8-backend` —
verified with `git diff sprint-8-backend develop` (empty).

## Why keep every sprint branch around

The individual `sprint-X-backend` branches are **not deleted** after merging.
They're kept as a durable record of the project's incremental development —
each one is a checkpoint of exactly what existed at the end of that sprint,
useful for tracking progress over time (e.g. for the internship report) even
though `develop` now supersedes all of them functionally.
