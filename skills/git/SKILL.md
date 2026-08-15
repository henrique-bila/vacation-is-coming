---
name: git
description: >-
  Publish vacation-is-coming changes to the user's Git remote. Use when the user asks
  to publish, push, commit, sync repo, or invoke the git agent. Read config/repo.yaml;
  if not configured, run Git onboarding from agents/git.md before pushing.
---

# git

Follow [`agents/git.md`](../../agents/git.md) and [`AGENTS.md`](../../AGENTS.md).

## Quick pointers

- Publish target: [`config/repo.yaml`](../../config/repo.yaml) (`configured: true` required)
- Template: [`config/repo.example.yaml`](../../config/repo.example.yaml)
- Never commit `config/.env` or API keys
- After schedule edits in the same session: ensure `python -m src --sync-schedule` ran before push
- Confirm push URL and branch match `repo.yaml`

## Trigger phrases

- "publish to git" / "publicar no git"
- "push" / "commit and push"
- "git agent" / "agent git"
- "sync my repo"
