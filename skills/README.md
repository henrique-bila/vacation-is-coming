# Skills — thin adapters for any AI agent

These skills are short entry points. Full instructions live in [`AGENTS.md`](../AGENTS.md) and [`agents/`](../agents/).

| Skill | When to use | Playbook |
|-------|-------------|----------|
| [`fare-alerts`](fare-alerts/SKILL.md) | Routes, dates, schedule, WhatsApp / price alerts | [`agents/monitor-flights.md`](../agents/monitor-flights.md) |
| [`git`](git/SKILL.md) | Publish, commit, push to your remote | [`agents/git.md`](../agents/git.md) |

## How each tool discovers them

| Tool | How |
|------|-----|
| **Any AI agent** | Read [`AGENTS.md`](../AGENTS.md) + the relevant playbook under `agents/` |
| **Claude / Codex / GPT** | [`CLAUDE.md`](../CLAUDE.md) points at `AGENTS.md` |
| **Cursor** | Auto-discovers only `.cursor/skills/`. Create a **local** link (not committed): |

```powershell
# Windows (from repo root) — junction so Cursor finds skills/
New-Item -ItemType Directory -Force -Path .cursor | Out-Null
New-Item -ItemType Junction -Path .cursor\skills -Target (Resolve-Path skills)
```

```bash
# macOS / Linux (from repo root)
mkdir -p .cursor
ln -sfn "$(pwd)/skills" .cursor/skills
```

`.cursor/` is gitignored — keep it local only.
