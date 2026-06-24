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

## Next step — scheduling

Run daily (e.g. 07:00 Chile time) via a GitHub Actions cron workflow or a local cron job:

```bash
uv run shifts-slackbot
```

A GitHub Actions workflow is the recommended path — no machine to babysit, logs in the
Actions tab, and secrets stored in the repo settings.

## Known issues / open items

| # | Issue | Where to fix |
|---|---|---|
| 1 | Column C role codes (for OS rows) not yet documented | `docs/summary-tab-layout.md` |

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
├── config.py       # Settings, SummaryLayout, RosterLayout (all row/col indices here)
├── models.py       # ShiftAssignment, GroupUpdate, SyncResult
└── io/
    ├── sheets.py   # gspread adapter + pure parsers; _normalize_name flips Surname/Given
    └── slack.py    # slack_sdk adapter: list_users_from_groups (pool-scoped), sync,
                    #   post_result (summary + thread)
docs/
└── summary-tab-layout.md   # authoritative layout reference for the Summary tab
```
