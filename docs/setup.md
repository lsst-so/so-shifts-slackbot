# Setup Guide — so-shifts-slackbot

Start-to-finish instructions for getting the bot running on a new machine.

---

## Prerequisites

- Python 3.11 or later
- [`uv`](https://docs.astral.sh/uv/) (package manager)
- Access to the **Unified Summit Shifts Schedule** Google Sheet
- A Slack workspace with a configured bot (see [Slack bot setup](#slack-bot-setup) below)

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 1. Clone and install

```bash
git clone https://github.com/b1quint/so-shifts-slackbot.git
cd so-shifts-slackbot
uv sync
```

---

## 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:

| Variable | Where to find it |
|---|---|
| `SHIFT_SHEET_ID` | The spreadsheet URL: `/spreadsheets/d/<SHEET_ID>/edit` |
| `SLACK_BOT_TOKEN` | Slack app settings → **OAuth & Permissions** → Bot User OAuth Token (`xoxb-…`) |

Optional variables are documented in `.env.example`.

---

## 3. Google Sheets auth (one-time browser flow)

The bot uses OAuth user credentials. You authorize once and the token is cached.

```bash
uv run shifts-slackbot --sheet-only
```

A browser window opens asking you to sign in with your Google account and grant access to Google Sheets. After you approve, the token is saved to `~/.config/gspread/authorized_user.json`.

> **Already authorized `so-shifts-supsci` on this machine?** The token is shared — no second login needed.

---

## 4. Slack bot setup

If the Slack app doesn't exist yet, create one at [api.slack.com/apps](https://api.slack.com/apps):

1. **Create New App** → From scratch → give it a name and pick your workspace.
2. Go to **OAuth & Permissions** → **Scopes** → **Bot Token Scopes** and add:
   - `usergroups:read`
   - `usergroups:write` *(requires a paid Slack workspace)*
   - `users:read`
   - `chat:write` *(only needed if `SLACK_STATUS_CHANNEL` is set)*
3. Click **Install to Workspace** and copy the **Bot User OAuth Token** (`xoxb-…`) into `.env`.
4. If you set `SLACK_STATUS_CHANNEL`, invite the bot to that channel:
   ```
   /invite @your-bot-name
   ```

---

## 5. Test the setup

Read the sheet and print assignments without touching Slack:

```bash
uv run shifts-slackbot --sheet-only
```

Do a full dry-run (resolves Slack users, prints planned updates, no writes):

```bash
uv run shifts-slackbot --dry-run
```

If both pass, the bot is ready.

---

## 6. Scheduling

Run the bot daily via **GitHub Actions** (recommended — no machine required) or a local cron job.

See [github-actions.md](github-actions.md) for the cloud-based setup.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `SHIFT_SHEET_ID is required` | `.env` not loaded or variable not set |
| `SLACK_BOT_TOKEN is required` | Same — check `.env` |
| `Token has been expired or revoked` | Re-run step 3 to re-authorize |
| `unknown initials 'XY'` warning | Roster in the sheet has a gap; update the OS or SupSci tab |
| `usergroups:write` scope error | Slack workspace is free-tier — that scope requires a paid plan |
