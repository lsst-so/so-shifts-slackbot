# Slack Workflow Builder — /refresh-shift-tags

Sets up a Slack slash command that triggers an on-demand sync without a persistent server.
The workflow catches `/refresh-shift-tags` in Slack, posts a "please wait" message, then
fires the GitHub Actions `daily-sync.yml` workflow via the GitHub API.

The GitHub Actions job runs the sync and posts the result to `SLACK_STATUS_CHANNEL` when
it finishes (~1 minute later).

---

## Prerequisites

- Admin or workflow-editor access to the Slack workspace.
- The daily sync GitHub Actions workflow already set up (see [github-actions.md](github-actions.md)).

---

## Step 1 — Create a GitHub Personal Access Token

The workflow needs a token to call the GitHub API and dispatch the Actions workflow.

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Click **Generate new token**.
3. Set:
   - **Token name:** `so-shifts-slackbot workflow dispatch`
   - **Expiration:** 1 year (rotate annually)
   - **Repository access:** Only select repositories → `lsst-so/so-shifts-slackbot`
   - **Permissions → Repository permissions → Actions:** Read and write
4. Click **Generate token** and copy it immediately — you won't see it again.

---

## Step 2 — Create the Slack workflow

1. In Slack, go to **Tools → Workflow Builder** (or **More → Automations**).
2. Click **New Workflow**.
3. **Name:** `Refresh Shift Tags`

### Trigger: link

1. Choose **From a link in Slack** as the trigger.
2. **Workflow name:** `Refresh Shift Tags` (this becomes the link label).
3. Save the trigger — Slack generates a `https://slack.com/shortcuts/…` link.
4. Post that link in `#rso-shift-bot` (pin it so it's easy to find). Anyone who clicks it runs the workflow.

### Step 1 — Confirmation message

1. Add step: **Send a message**.
2. **Send to:** The channel where the command was used (`{{channel}}`).
3. **Message:**
   > Refreshing shift tags… this takes about a minute. I'll post an update when it's done.

### Step 2 — Trigger GitHub Actions

1. Add step: **Send a web request**.
2. Fill in:

| Field | Value |
|---|---|
| **URL** | `https://api.github.com/repos/lsst-so/so-shifts-slackbot/actions/workflows/daily-sync.yml/dispatches` |
| **Method** | `POST` |
| **Request body** | `{"ref": "main"}` |

3. Add request headers:

| Key | Value |
|---|---|
| `Authorization` | `Bearer <your PAT from step 1>` |
| `Accept` | `application/vnd.github+json` |
| `X-GitHub-Api-Version` | `2022-11-28` |
| `Content-Type` | `application/json` |

4. Save the step.

### Publish

Click **Publish** to make the workflow active.

---

## Step 3 — Test

In `#rso-shift-bot`, type `/refresh-shift-tags`:

- The "Refreshing…" message should appear immediately.
- After ~1 minute, the bot posts a run summary to `SLACK_STATUS_CHANNEL`.
- Confirm the run triggered in the [Actions tab](https://github.com/lsst-so/so-shifts-slackbot/actions).

---

## Notes

- The GitHub API returns HTTP 204 (No Content) on success — the dispatch is asynchronous,
  so there is no immediate result payload. The Workflow Builder step succeeds as long as it
  gets a 2xx response.
- The PAT is visible to workspace admins in the Workflow Builder config. Rotate it annually
  or immediately if it is ever exposed.
- If the sync fails, GitHub sends an email to the repo owner (standard Actions failure alert)
  and the Slack run summary will include error details.
