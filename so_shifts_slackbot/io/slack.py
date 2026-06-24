"""Slack adapter — look up user groups and update their members.

Uses the Slack Web API via slack_sdk. Required OAuth scopes for the bot token:
  - usergroups:read  (list groups, get members)
  - usergroups:write (update group membership)
  - users:read       (look up users by display name / real name)
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from so_shifts_slackbot.config import Settings
from so_shifts_slackbot.models import GroupUpdate, ShiftAssignment, SyncResult

logger = logging.getLogger(__name__)

_PARENTHETICAL = re.compile(r"\s*\(.*\)\s*$")


def _index_name(name: str) -> str:
    """Lowercase and strip trailing parentheticals for robust name matching."""
    return _PARENTHETICAL.sub("", name).strip().lower()


def make_client(settings: Settings) -> WebClient:
    return WebClient(token=settings.slack_bot_token)


def list_usergroups(client: WebClient) -> dict[str, str]:
    """Return {handle: group_id} for all enabled user groups in the workspace."""
    response = client.usergroups_list(include_disabled=False)
    return {g["handle"]: g["id"] for g in response["usergroups"]}


def list_users(client: WebClient) -> dict[str, str]:
    """Return {name_lower: user_id} for all non-bot, non-deleted users.

    Indexes display_name, real_name, and their normalized variants so the
    name matching is robust to minor profile differences.
    """
    mapping: dict[str, str] = {}
    cursor = None
    while True:
        kwargs: dict = {"limit": 200}
        if cursor:
            kwargs["cursor"] = cursor
        response = client.users_list(**kwargs)
        for member in response["members"]:
            if member.get("deleted") or member.get("is_bot"):
                continue
            uid = member["id"]
            profile = member.get("profile", {})
            for key in ("display_name", "real_name", "display_name_normalized", "real_name_normalized"):
                name = _index_name(profile.get(key, ""))
                if name:
                    mapping[name] = uid
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return mapping


def list_users_from_groups(
    client: WebClient,
    group_ids: list[str],
) -> dict[str, str]:
    """Return {name_lower: user_id} for members of the given group IDs.

    Fetches member lists via usergroups.users.list, then resolves each unique
    user ID via users.info. Much faster than paginating the whole workspace.
    """
    uid_set: set[str] = set()
    for group_id in group_ids:
        response = client.usergroups_users_list(usergroup=group_id)
        uid_set.update(response.get("users", []))

    mapping: dict[str, str] = {}
    for uid in uid_set:
        try:
            response = client.users_info(user=uid)
        except SlackApiError as exc:
            logger.warning("Could not fetch user %s: %s", uid, exc.response["error"])
            continue
        member = response["user"]
        if member.get("deleted") or member.get("is_bot"):
            continue
        profile = member.get("profile", {})
        for key in ("display_name", "real_name", "display_name_normalized", "real_name_normalized"):
            name = _index_name(profile.get(key, ""))
            if name:
                mapping[name] = uid
    return mapping


def resolve_names(
    names: tuple[str, ...],
    user_map: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Match full names to Slack user IDs. Returns (matched_ids, unmatched_names)."""
    matched, unmatched = [], []
    for name in names:
        uid = user_map.get(name.lower())
        if uid:
            matched.append(uid)
        else:
            unmatched.append(name)
    return matched, unmatched


def build_updates(
    assignments: list[ShiftAssignment],
    group_map: dict[str, str],
    user_map: dict[str, str],
) -> tuple[list[GroupUpdate], list[str]]:
    """Aggregate assignments by group handle and resolve names to Slack IDs.

    Multiple roles can feed the same group (e.g. OS Night Shift Manager and
    OS Late Shift both go to @os-night-shift). Returns (updates, warnings).
    """
    names_by_group: dict[str, list[str]] = defaultdict(list)
    for a in assignments:
        names_by_group[a.group_handle].extend(a.assignees)

    updates: list[GroupUpdate] = []
    warnings: list[str] = []

    for handle, names in names_by_group.items():
        group_id = group_map.get(handle)
        if not group_id:
            warnings.append(f"Slack group @{handle} not found in workspace")
            continue
        member_ids, unmatched = resolve_names(tuple(names), user_map)
        if unmatched:
            warnings.append(f"@{handle}: could not resolve Slack user(s): {', '.join(unmatched)}")
        if not member_ids:
            warnings.append(f"@{handle}: no members resolved — skipping update")
            continue
        updates.append(GroupUpdate(
            group_handle=handle,
            group_id=group_id,
            member_ids=tuple(member_ids),
            display_names=tuple(names),
        ))
    return updates, warnings


def apply_updates(
    client: WebClient,
    updates: list[GroupUpdate],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Push each GroupUpdate to Slack. Returns list of API error strings."""
    errors: list[str] = []
    for update in updates:
        names = ", ".join(update.display_names)
        if dry_run:
            logger.info("[dry-run] @%s → %s", update.group_handle, names)
            continue
        try:
            client.usergroups_users_update(
                usergroup=update.group_id,
                users=list(update.member_ids),
            )
            logger.info("Updated @%s → %s", update.group_handle, names)
        except SlackApiError as exc:
            msg = f"@{update.group_handle}: Slack API error — {exc.response['error']}"
            logger.error(msg)
            errors.append(msg)
    return errors


def post_result(
    client: WebClient,
    channel: str,
    result: SyncResult,
) -> None:
    """Post a one-line run summary to a Slack channel, with detail in a thread."""
    if result.errors:
        emoji = ":x:"
        summary = f"{emoji} Shift sync failed for {result.date} — see thread"
    elif result.skipped:
        emoji = ":warning:"
        summary = f"{emoji} Shifts synced for {result.date} — warnings, see thread"
    else:
        emoji = ":white_check_mark:"
        groups = ", ".join(f"@{u.group_handle}" for u in result.updates) or "nothing to update"
        summary = f"{emoji} Shifts synced for {result.date} — {groups}"

    try:
        resp = client.chat_postMessage(channel=channel, text=summary)
        ts = resp["ts"]
    except SlackApiError as exc:
        logger.error("Could not post run summary: %s", exc.response["error"])
        return

    thread_lines = [f"@{u.group_handle} → {', '.join(u.display_names)}" for u in result.updates]
    thread_lines += [f":warning: {w}" for w in result.skipped]
    thread_lines += [f":x: {e}" for e in result.errors]

    if thread_lines:
        try:
            client.chat_postMessage(
                channel=channel,
                thread_ts=ts,
                text="\n".join(thread_lines),
            )
        except SlackApiError as exc:
            logger.error("Could not post thread detail: %s", exc.response["error"])


def sync(
    settings: Settings,
    assignments: list[ShiftAssignment],
    *,
    client: WebClient | None = None,
    dry_run: bool = False,
) -> SyncResult:
    """Sync parsed sheet assignments to Slack user groups."""
    client = client or make_client(settings)
    result = SyncResult(date=date.today())

    group_map = list_usergroups(client)

    pool_ids = [group_map[h] for h in settings.user_pool_groups if h in group_map]
    missing_pools = [h for h in settings.user_pool_groups if h not in group_map]
    for h in missing_pools:
        logger.warning("pool group @%s not found in workspace — falling back to full user list", h)

    if pool_ids:
        user_map = list_users_from_groups(client, pool_ids)
    else:
        user_map = list_users(client)

    if settings.slack_group_overrides:
        assignments = [
            ShiftAssignment(
                date=a.date,
                role=a.role,
                group_handle=settings.slack_group_overrides.get(a.group_handle, a.group_handle),
                assignees=a.assignees,
            )
            for a in assignments
        ]

    updates, warnings = build_updates(assignments, group_map, user_map)
    result.skipped.extend(warnings)

    errors = apply_updates(client, updates, dry_run=dry_run)
    result.errors.extend(errors)
    result.updates.extend(updates)
    return result
