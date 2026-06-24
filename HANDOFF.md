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

**Goal:** Allow users to type `/refresh-shift-tags` in `#rso-shift-bot` to trigger an
on-demand sync, without needing a persistent server.

**Chosen approach:** Slack Workflow Builder (no server required).

The workflow will:
1. Be triggered by the `/refresh-shift-tags` slash command (configured inside Workflow Builder — not the Slack app)
2. Post a "Refreshing..." message to the channel
3. Send an HTTP POST to the GitHub API to trigger `workflow_dispatch` on `daily-sync.yml`
4. The GitHub Actions job runs the sync and posts the result to `SLACK_STATUS_CHANNEL`

**GitHub API call needed:**
```
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/daily-sync.yml/dispatches
Authorization: Bearer {github_personal_access_token}
Content-Type: application/json
Body: {"ref": "main"}
```

The GitHub PAT needs the `actions:write` scope (or `repo` scope).
Store it as a variable in the Slack workflow — do not hardcode it.

**Steps to complete:**
1. Create a GitHub Personal Access Token with `actions:write` scope.
2. In Slack → Tools → Workflow Builder → Create Workflow:
   - Trigger: Slash command → `/refresh-shift-tags`
   - Step 1: Send a message → "Refreshing shift tags, please wait…"
   - Step 2: Send a web request → POST to the GitHub API (details above)
3. Publish the workflow.
4. Test in `#rso-shift-bot`.

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
└── summary-tab-layout.md   # authoritative layout reference for the Summary tab
```
