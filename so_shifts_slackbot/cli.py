"""CLI entrypoint for the Shifts Slack bot.

Usage:
    shifts-slackbot [--date YYYY-MM-DD] [--dry-run] [--sheet-only]

Reads the Summary tab of the Unified Shift Schedule for the given date
(default: today) and updates the configured Slack user groups.

Required environment variables:
    SHIFT_SHEET_ID    — Google Sheets spreadsheet id
    SLACK_BOT_TOKEN   — Slack bot token (xoxb-...)
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from dotenv import load_dotenv

from so_shifts_slackbot.config import Settings
from so_shifts_slackbot.io.sheets import fetch_summary
from so_shifts_slackbot.io.slack import make_client, post_result, sync


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="shifts-slackbot",
        description="Sync today's shift assignments from the spreadsheet to Slack user groups.",
    )
    p.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Date to sync (default: today).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve Slack users and print what would change, but do not update any groups.",
    )
    p.add_argument(
        "--sheet-only",
        action="store_true",
        help="Read and print sheet assignments only — skip all Slack API calls.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    settings = Settings.from_env()
    try:
        settings.validate()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    target_date: date | None = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"error: invalid date {args.date!r} — use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

    effective_date = target_date or date.today()
    print(f"Reading Summary tab for {effective_date} …")
    assignments = fetch_summary(settings, target_date=target_date)

    if not assignments:
        print("No assignments found for that date.")
        sys.exit(0)

    print("\nAssignments read from sheet:")
    for a in assignments:
        names = ", ".join(a.assignees) or "(none)"
        print(f"  [{a.group_handle}] {a.role}: {names}")

    if args.sheet_only:
        return

    result = sync(settings, assignments, dry_run=args.dry_run)

    print("\nSlack group updates:")
    if result.updates:
        for u in result.updates:
            names = ", ".join(u.display_names)
            tag = "[dry-run] " if args.dry_run else ""
            print(f"  {tag}@{u.group_handle} → {names}")
    else:
        print("  (none)")

    for w in result.skipped:
        print(f"warning: {w}")
    for e in result.errors:
        print(f"error: {e}", file=sys.stderr)

    if settings.slack_status_channel and not args.dry_run:
        post_result(make_client(settings), settings.slack_status_channel, result)

    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
