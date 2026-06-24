# Slack Workflow Builder — on-demand shift sync

Sets up a Slack link that triggers an on-demand sync without a persistent server or HTTP
connector. Clicking the link creates a sentinel GitHub issue; the Actions workflow detects
it, runs the sync, then closes the issue automatically.

No GitHub PAT required — the workflow uses its built-in `GITHUB_TOKEN`.

---

## How it works

```
User clicks Slack link
  → Workflow Builder posts "Refreshing…" message
  → Workflow Builder creates GitHub issue titled "refresh-shift-tags"
    → daily-sync.yml fires (issues: opened trigger)
      → sync runs
      → issue closed automatically
        → bot posts run summary to SLACK_STATUS_CHANNEL
```

---

## Prerequisites

- Workflow Builder access in the Slack workspace.
- The GitHub connector connected to the `lsst-so` org in your Slack workspace
  (Workflow Builder → Add a step → GitHub → Connect).
- The daily sync GitHub Actions workflow already set up (see [github-actions.md](github-actions.md)).
  The `daily-sync.yml` file already contains the `issues` trigger — nothing extra to configure
  on the GitHub side.

---

## Step 1 — Create the Slack workflow

1. In Slack, go to **Tools → Workflow Builder** (or **More → Automations**).
2. Click **New Workflow**.
3. **Name:** `Refresh Shift Tags`

### Trigger: link

1. Choose **From a link in Slack** as the trigger.
2. Save — Slack generates a `https://slack.com/shortcuts/…` link.

### Step 1 — Confirmation message

1. Add step: **Send a message**.
2. **Send to:** The channel where the link was clicked (`{{channel}}`).
3. **Message:**
   > Refreshing shift tags… this takes about a minute. I'll post an update when it's done.

### Step 2 — Create the trigger issue

1. Add step: **GitHub → Create an issue**.
2. Configure:

| Field | Value |
|---|---|
| **Repository** | `lsst-so/so-shifts-slackbot` |
| **Title** | `refresh-shift-tags` |
| **Body** | *(optional)* `On-demand sync triggered from Slack.` |

3. Save the step.

### Publish

Click **Publish** to make the workflow active.

### Post the link

Copy the generated `https://slack.com/shortcuts/…` link and post it (pinned) in `#rso-shift-bot`.

---

## Step 2 — Test

Click the pinned link in `#rso-shift-bot`:

- The "Refreshing…" message appears immediately.
- A `refresh-shift-tags` issue opens in the repository, then closes automatically once the sync finishes.
- After ~1 minute, the bot posts a run summary to `SLACK_STATUS_CHANNEL`.
- Check the [Actions tab](https://github.com/lsst-so/so-shifts-slackbot/actions) to confirm the run.

---

## Notes

- Any issue opened in the repo with a title that does **not** contain `refresh-shift-tags` is
  ignored by the workflow — normal issue tracker use is unaffected.
- The issue list will stay clean: every trigger issue is closed automatically with a
  "Sync complete." comment.
- The `GITHUB_TOKEN` used to close the issue is scoped to the repository and expires when the
  workflow run ends — no long-lived secrets required.
