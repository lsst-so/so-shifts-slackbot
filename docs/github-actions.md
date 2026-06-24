# GitHub Actions — Daily Shift Sync

Runs `shifts-slackbot` every day on a cron schedule using GitHub Actions. No machine required.

---

## How it works

The workflow runs on GitHub's servers at a fixed UTC time each day. It:

1. Writes the Google OAuth token from a secret to the expected path on the runner.
2. Installs dependencies with `uv`.
3. Runs `shifts-slackbot`, which reads the sheet and updates the Slack groups.

Logs are available in the **Actions** tab of the repository.

---

## Prerequisites

Complete the [local setup](setup.md) first. You need:

- The OAuth token file already created locally (`~/.config/gspread/authorized_user.json`).
- `SHIFT_SHEET_ID` and `SLACK_BOT_TOKEN` known.
- Push access to the repository (to add secrets and the workflow file).

---

## Step 1 — Export the Google OAuth token

The token was created during local setup. Print its contents:

```bash
cat ~/.config/gspread/authorized_user.json
```

Copy the entire JSON output. You will paste it as a secret in the next step.

> The file contains a `refresh_token` which is long-lived. GitHub Actions uses it to
> get a fresh access token on each run without any browser interaction.

---

## Step 2 — Add GitHub secrets

In the repository: **Settings → Secrets and variables → Actions → New repository secret**.

Add these secrets:

| Secret name | Value |
|---|---|
| `SHIFT_SHEET_ID` | The Google Sheets spreadsheet id |
| `SLACK_BOT_TOKEN` | The Slack bot token (`xoxb-…`) |
| `GSPREAD_TOKEN_JSON` | The full contents of `authorized_user.json` (from step 1) |

Optional — add as a **variable** (not a secret, value is visible):

| Variable name | Value |
|---|---|
| `SLACK_STATUS_CHANNEL` | Channel ID or `#channel-name` to post run summaries to |

---

## Step 3 — The workflow file

The workflow lives at `.github/workflows/daily-sync.yml` in the repository. It runs at
**12:00 UTC** (≈ 08:00 Chile Standard Time / 09:00 Chile Summer Time).

```yaml
name: Daily Shift Sync

on:
  schedule:
    - cron: '0 12 * * *'   # 12:00 UTC — ~08:00 Chile time
  workflow_dispatch:         # manual trigger from the Actions tab
```

See the actual file for the full workflow definition.

---

## Step 4 — Enable and verify

After the workflow file is merged to `main`, trigger a manual run to confirm everything works:

1. Go to **Actions** → **Daily Shift Sync** → **Run workflow** → **Run workflow**.
2. Watch the log. A successful run ends with `Slack group updates:` and the assigned names.
3. Check that the Slack groups were updated (or use `--dry-run` for a non-destructive test —
   add it to the `Run` step temporarily).

Once the manual run passes, the scheduled runs will fire automatically at 12:00 UTC each day.

---

## Token refresh

GitHub Actions uses the `refresh_token` inside `GSPREAD_TOKEN_JSON` to get a new access token
on each run. The refresh token itself does not rotate, so the secret does not need to be
updated unless:

- You explicitly revoke the app's access in your Google account security settings.
- You delete and re-create the Google Cloud OAuth client.

If the bot starts failing with an authentication error, re-run the local setup auth step and
update the `GSPREAD_TOKEN_JSON` secret with the new token contents.

---

## Schedule reference

| UTC time | Chile Standard Time (UTC-4) | Chile Summer Time (UTC-3) |
|---|---|---|
| 12:00 | 08:00 | 09:00 |

Chile uses Standard Time roughly May–September and Summer Time October–April.
Adjust the cron expression in the workflow file if a different local time is preferred.

---

## Monitoring

- **Run logs:** Actions tab → Daily Shift Sync → click a run.
- **Run summary posted to Slack:** set `SLACK_STATUS_CHANNEL` (step 2) to get a message after each run.
- **Failed runs:** GitHub sends an email notification to the repository owner when a
  scheduled workflow fails. No additional alerting setup needed.
