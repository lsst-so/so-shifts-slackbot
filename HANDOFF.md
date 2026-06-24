# Handoff — so-shifts-slackbot

Current branch: `minimum-valuable-product` → merged to `main`.

## What works (verified end-to-end)

```
❯ uv run shifts-slackbot --date YYYY-MM-DD

Reading Summary tab for YYYY-MM-DD …

Assignments read from sheet:
  [os-night-shift] OS Night Shift Manager: <name>
  [os-night-shift] OS Late Shift: <name>
  [os-day-shift] OS Day Shift Manager: <name>
  [os-day-shift] OS Day Shift: <name>
  [summit-sup-sci] Summit Support Scientist: <name>

Slack group updates:
  @os-night-shift → <name>, <name>
  @os-day-shift → <name>, <name>
  @summit-sup-sci → <name>
```

- Sheet parsing resolves initials → full names (OS names normalized from `Surname, Name` to `Given Surname`).
- Slack user lookup is scoped to `@summit-sci` and `@os-team` pool groups instead of paginating the whole workspace.
- Slack profile names with trailing parentheticals (e.g. pronouns) are stripped before matching.
- Group handle overrides allow redirecting writes to test groups via env vars.
- A one-line run summary is posted to `SLACK_STATUS_CHANNEL` on live runs, with warnings/errors in a thread.
- **Row 12 fallback:** if the on-site OS Day Shift (sheet row 11) is empty, the bot picks up the remote OS from row 12 automatically.

## Environment setup

```bash
cp .env.example .env
# Required:
#   SHIFT_SHEET_ID=<spreadsheet id from the URL>
#   SLACK_BOT_TOKEN=xoxb-...
# Optional:
#   SLACK_STATUS_CHANNEL=#shifts-bot
```

Google Sheets OAuth token is cached at `~/.config/gspread/authorized_user.json` (shared with
`so-shifts-supsci` — no re-auth needed if that project has already been authorized).

Slack bot scopes required: `usergroups:read`, `usergroups:write`, `users:read`, `chat:write`.

## Next step — /refresh-shift-tags slash command via Slack Workflow Builder

Full setup instructions in **[docs/workflow-builder-setup.md](docs/workflow-builder-setup.md)**.

Short version (no PAT required — uses `GITHUB_TOKEN`):
1. In Slack → Tools → Workflow Builder, create a workflow triggered by a link:
   post a confirmation message, then **GitHub → Create an issue** titled `refresh-shift-tags`
   in this repo. The Actions workflow detects the issue, syncs, and closes it automatically.
2. Pin the generated Slack shortcut link in `#rso-shift-bot`.
3. Publish and test in `#rso-shift-bot`.

## Known issues / open items

| # | Issue | Where to fix |
|---|---|---|
| 1 | Column C role codes (for OS rows) not yet documented | `docs/summary-tab-layout.md` |
| 2 | `/refresh-shift-tags` via Workflow Builder not yet set up | See "Next step" above |

## Architecture

`cli.py` loads `.env`, reads `Settings`, calls `io/sheets.fetch_summary` (opens 3 tabs,
resolves initials → full names), then calls `io/slack.sync` (resolves full names → Slack
user IDs via pool groups, updates user groups, posts run summary if channel is configured).
All parsing logic is pure Python with no network calls — fully unit-tested. The only
network calls are in `io/sheets.py` (gspread) and `io/slack.py` (slack_sdk).

## File map

```
so_shifts_slackbot/
├── cli.py          # entrypoint — flags: --date, --dry-run, --sheet-only, -v
├── config.py       # Settings, SummaryLayout (role_rows incl. row 11 remote fallback), RosterLayout
├── models.py       # ShiftAssignment, GroupUpdate, SyncResult
└── io/
    ├── sheets.py   # gspread adapter + pure parsers; _normalize_name flips Surname/Given
    └── slack.py    # slack_sdk adapter: list_users_from_groups (pool-scoped), sync,
                    #   post_result (summary + thread)
docs/
├── setup.md                # start-to-finish local + Slack bot setup
├── github-actions.md       # daily cron workflow setup
├── workflow-builder-setup.md # /refresh-shift-tags slash command via Slack Workflow Builder
└── summary-tab-layout.md   # authoritative layout reference for the Summary tab
```
