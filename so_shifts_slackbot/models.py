"""Pure domain types for the Slack bot.

No gspread, no Slack SDK imports here — just data.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ShiftAssignment:
    """One person assigned to one role on one date, with their group resolved."""

    date: date
    role: str           # e.g. "OS Night Shift Manager"
    group_handle: str   # e.g. "os-night-shift"
    assignees: tuple[str, ...]  # resolved full names from the roster


@dataclass(frozen=True)
class GroupUpdate:
    """A pending update: set a Slack user group to a list of member user IDs."""

    group_handle: str            # e.g. "summit-sup-sci"
    group_id: str                # Slack usergroup ID (S...)
    member_ids: tuple[str, ...]  # Slack user IDs (U...)
    display_names: tuple[str, ...]  # for human-readable logging


@dataclass
class SyncResult:
    """Outcome of one sync run."""

    date: date
    updates: list[GroupUpdate] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # warnings (group not found, etc.)
    errors: list[str] = field(default_factory=list)    # API errors
