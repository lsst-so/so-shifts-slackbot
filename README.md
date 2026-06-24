# so-shifts-slackbot

Reads the Unified Shift Schedule spreadsheet (`Summary` tab) and updates Slack user groups
with the current shift assignments:

- `@summit-sup-sci` — Support Scientist on shift
- `@os-day-shift` — Operations Specialist day shift
- `@os-night-shift` — Operations Specialist night shift

Optionally posts a one-line run summary to a Slack channel, with warnings and errors in a thread.

## Setup

1. Copy `.env.example` to `.env` and fill in the required values (see below).
2. Install: `uv sync`
3. Authorize Google Sheets (one-time browser flow): `uv run shifts-slackbot --sheet-only`

## Usage

```
shifts-slackbot [--date YYYY-MM-DD] [--dry-run] [--sheet-only] [-v]
```

| Flag | Effect |
|---|---|
| *(none)* | Live sync — reads sheet, updates Slack groups, posts summary if channel is set |
| `--dry-run` | Resolves names and plans updates but does not write to Slack |
| `--sheet-only` | Reads and prints assignments only — no Slack API calls |
| `--date YYYY-MM-DD` | Use a specific date instead of today |
| `-v` | Enable debug logging |

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SHIFT_SHEET_ID` | Yes | Google Sheets spreadsheet id (from the URL) |
| `SLACK_BOT_TOKEN` | Yes | Bot token (`xoxb-…`) |
| `SLACK_STATUS_CHANNEL` | No | Channel to post run summary to (e.g. `#shifts-bot`) |
| `SLACK_GROUP_SUPSCI` | No | Override the `summit-sup-sci` group handle (e.g. for testing) |
| `SLACK_GROUP_DAY` | No | Override the `os-day-shift` group handle |
| `SLACK_GROUP_NIGHT` | No | Override the `os-night-shift` group handle |

## Slack bot scopes

The bot token needs: `usergroups:read`, `usergroups:write`, `users:read`, `chat:write`.

- `usergroups:write` requires a paid Slack workspace.
- `chat:write` is only needed if `SLACK_STATUS_CHANNEL` is set. The bot must be invited to the channel.

## Google Sheets auth

OAuth token is cached at `~/.config/gspread/authorized_user.json`. If `so-shifts-supsci`
has already been authorized on the same machine, no re-auth is needed.

## Scheduling

Run daily (e.g. 07:00 Chile time) via GitHub Actions or a local cron job:

```bash
uv run shifts-slackbot
```
