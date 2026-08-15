# Agent playbook — publish to Git

Use when the user says **publish**, **push to git**, **commit**, **sync repo**, or invokes the **git** agent.

Goal: commit local vacation-is-coming changes and push to the user's configured remote — without leaking secrets.

## Before anything

1. Read [`config/repo.yaml`](../config/repo.yaml) (template: [`config/repo.example.yaml`](../config/repo.example.yaml)).
2. If `configured: false` or the file is missing → run **Git onboarding** (below). Do not push until `configured: true`.
3. Never stage or commit: `config/.env`, API keys, CallMeBot keys, tokens, or credential files.

## Git onboarding (ask when not configured)

Ask in the user's language, one step at a time if needed:

| Question | Why |
|----------|-----|
| Do you have **Git** installed? (`git --version`) | Required for commit/push |
| Do you already have a **GitHub repo** for this project? | Need a push target |
| **Repository URL** (HTTPS or SSH) | e.g. `https://github.com/user/vacation-is-coming.git` |
| **Default branch** | Usually `main` |
| Is the repo already **cloned** on this machine? | Clone vs `git remote add` |
| How do you **authenticate**? | `gh auth login`, SSH key, or PAT — never paste secrets in chat |

Then:

1. Create or update `config/repo.yaml` with `configured: true`, `remote_url`, `branch`, `remote_name: origin`.
2. Mirror a short note in [`config/preferences.md`](../config/preferences.md) under **Git remote**.
3. If no local repo: clone the URL or init + add remote.
4. If remote mismatch: `git remote set-url origin <remote_url>` (confirm with user first).

## Preflight checks

Run (read-only first):

```bash
git rev-parse --is-inside-work-tree
git remote -v
git status
git branch --show-current
```

Confirm:

- Current branch matches `repo.yaml` `branch` (or ask before pushing another branch).
- `origin` URL matches `repo.yaml` `remote_url` (or the configured `remote_name`).

## What to commit

Include when changed:

- `config/travel.yaml`, `config/preferences.md`, `config/repo.yaml`
- `config/travel.example.yaml`, `config/repo.example.yaml`
- `.github/workflows/` (especially after `--sync-schedule`)
- `src/`, `dev/tests/`, `agents/`, docs, README, skills

Exclude always:

- `config/.env`
- `.venv/`, `__pycache__/`

Snapshots (`config/snapshots/*.md`) — commit if the user asked to publish config/code changes; daily Action snapshots are usually committed by CI separately.

## Commit message

- 1–2 sentences, focus on **why**
- English, matching repo style
- Examples:
  - `Add price comparison and explore date mode for SerpAPI`
  - `Switch monitoring to Salvador explore mode for Feb 2027`

Use HEREDOC for commit messages on Windows PowerShell/bash as per user rules.

## Push

```bash
git add <files>
git commit -m "$(cat <<'EOF'
Message here.

EOF
)"
git push -u origin HEAD   # first time on branch
# or
git push origin main
```

After push:

- Confirm branch and remote URL
- Remind user that **GitHub Actions** runs on `main` with repository Secrets
- If workflow or schedule changed, mention Actions will pick it up on next cron

## Troubleshooting

| Problem | Action |
|---------|--------|
| Not a git repo | `git init` + remote, or clone user's URL |
| No remote | `git remote add origin <remote_url>` |
| Auth failed | Point user to `gh auth login` or SSH setup; do not ask for password in chat |
| Rejected push | `git pull --rebase origin main` then push (never force-push `main` unless user explicitly asks) |
| Dirty tree only snapshots | Ask if user wants only config commit or full sync |

## Response style

- Short confirmation: what was committed, branch, remote
- Explicit: "Pushed to `origin/main`" or what blocked the push
- Match user language in chat; keep commit messages and YAML in English
