"""Settings for the Slack bot — loaded from environment variables.

All policy and layout constants live here; nothing is hard-coded elsewhere.
Load with ``Settings.from_env()`` at startup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class SummaryLayout:
    """Physical layout of the Summary tab (all indices 0-based)."""

    date_row: int = 1        # sheet row 2 — holds full date serials
    date_col_start: int = 3  # column D — first date column

    # {0-based row index: (human role label, slack group handle)}
    role_rows: dict[int, tuple[str, str]] = field(default_factory=lambda: {
        7:  ("OS Night Shift Manager",   "os-night-shift"),
        8:  ("OS Late Shift",            "os-night-shift"),
        9:  ("OS Day Shift Manager",     "os-day-shift"),
        10: ("OS Day Shift",             "os-day-shift"),
        15: ("Summit Support Scientist", "summit-sup-sci"),
    })


@dataclass
class RosterLayout:
    """Layout of a name↔initials roster within a tab (all indices 0-based)."""

    start_row: int           # first data row
    name_col: int = 0        # column A
    initials_col: int = 1    # column B
    row_stride: int = 2      # rows per person (vertically merged pairs)


@dataclass
class Settings:
    sheet_id: str = ""
    slack_bot_token: str = ""

    summary_tab_name: str = "Summary"
    os_tab_name: str = "OS"
    supsci_tab_name: str = "SupSci"

    summary_layout: SummaryLayout = field(default_factory=SummaryLayout)

    # Slack user groups whose members are eligible to be on shift.
    # Used to scope user lookup to a small pool instead of the whole workspace.
    user_pool_groups: tuple[str, ...] = ("summit-sci", "os-team")

    # Optional handle remapping: {canonical_handle: actual_handle}.
    # Set via SLACK_GROUP_SUPSCI / SLACK_GROUP_DAY / SLACK_GROUP_NIGHT in .env.
    # Useful for pointing at test groups without touching defaults.
    slack_group_overrides: dict[str, str] = field(default_factory=dict)

    # Channel to post a run summary to (e.g. "C12345678" or "#shifts-bot").
    # Leave empty to skip posting.
    slack_status_channel: str = ""

    # OS roster: names A12:A, initials B12:B → start_row=11 (0-based)
    os_roster_layout: RosterLayout = field(default_factory=lambda: RosterLayout(start_row=11))

    # SupSci roster: names A6:A, initials B6:B → start_row=5 (0-based)
    supsci_roster_layout: RosterLayout = field(default_factory=lambda: RosterLayout(start_row=5))

    @classmethod
    def from_env(cls) -> Settings:
        s = cls()
        s.sheet_id = os.environ.get("SHIFT_SHEET_ID", "")
        s.slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        overrides = {
            "summit-sup-sci": os.environ.get("SLACK_GROUP_SUPSCI", ""),
            "os-day-shift":   os.environ.get("SLACK_GROUP_DAY", ""),
            "os-night-shift": os.environ.get("SLACK_GROUP_NIGHT", ""),
        }
        s.slack_group_overrides = {k: v for k, v in overrides.items() if v}
        s.slack_status_channel = os.environ.get("SLACK_STATUS_CHANNEL", "")
        return s

    def validate(self) -> None:
        if not self.sheet_id:
            raise ValueError("SHIFT_SHEET_ID is required.")
        if not self.slack_bot_token:
            raise ValueError("SLACK_BOT_TOKEN is required.")
