"""Google Sheets adapter — read the Summary tab and roster tabs.

This is the only module that imports gspread. All parsing functions are pure
(take plain grids, return plain objects) so they are unit-testable without auth.

Auth: OAuth user credentials via gspread.oauth() — authorize once in a browser,
token cached at ~/.config/gspread/. Spreadsheet id from Settings.sheet_id.

Cells are fetched with UNFORMATTED_VALUE so date cells come back as integer
serials, converted by _to_date() via the Google Sheets origin (1899-12-30).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import gspread
from gspread.utils import ValueRenderOption

from so_shifts_slackbot.config import RosterLayout, Settings, SummaryLayout
from so_shifts_slackbot.models import ShiftAssignment

logger = logging.getLogger(__name__)

_SHEETS_ORIGIN = date(1899, 12, 30)
_EMPTY = {"-", ""}
_ERROR = {"!"}


def _normalize_name(name: str) -> str:
    """Flip 'Surname, Given' to 'Given Surname' for consistent name format."""
    if "," in name:
        surname, given = name.split(",", 1)
        return f"{given.strip()} {surname.strip()}"
    return name


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _stringify(value: Any) -> str:
    return "" if value is None else str(value)


def _to_date(value: str) -> date | None:
    """Convert a stringified Sheets cell to a date.

    Handles integer serials (stored as "46196" or "46196.0"), ISO strings,
    and a few common formatted strings.
    """
    value = value.strip()
    if not value:
        return None
    try:
        return _SHEETS_ORIGIN + timedelta(days=int(float(value)))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def fetch_grid(worksheet: gspread.Worksheet) -> list[list[str]]:
    """Fetch a worksheet as a stringified grid with UNFORMATTED_VALUE."""
    raw = worksheet.get_all_values(value_render_option=ValueRenderOption.unformatted)
    return [[_stringify(cell) for cell in row] for row in raw]


# ---------------------------------------------------------------------------
# Pure parsing — no gspread, testable with fixture grids
# ---------------------------------------------------------------------------

def parse_roster(grid: list[list[str]], layout: RosterLayout) -> dict[str, str]:
    """Build {initials: full_name} from a two-rows-per-person roster grid.

    Reads every ``layout.row_stride`` rows starting at ``layout.start_row``,
    taking the name from ``layout.name_col`` and initials from
    ``layout.initials_col``. Stops at the first blank name cell.
    """
    result: dict[str, str] = {}
    row = layout.start_row
    while row < len(grid):
        name = grid[row][layout.name_col].strip() if layout.name_col < len(grid[row]) else ""
        if not name:
            break
        initials = grid[row][layout.initials_col].strip() if layout.initials_col < len(grid[row]) else ""
        if initials:
            result[initials] = _normalize_name(name)
        row += layout.row_stride
    return result


def parse_date_row(
    grid: list[list[str]],
    date_row: int,
    col_start: int,
) -> dict[int, date]:
    """Return {col_index: date} for every parseable date in the date header row."""
    if date_row >= len(grid):
        return {}
    result: dict[int, date] = {}
    for col, cell in enumerate(grid[date_row]):
        if col < col_start:
            continue
        d = _to_date(cell)
        if d is not None:
            result[col] = d
    return result


def parse_summary_grid(
    summary: list[list[str]],
    os_roster: dict[str, str],
    supsci_roster: dict[str, str],
    target_date: date,
    layout: SummaryLayout,
) -> tuple[list[ShiftAssignment], list[str]]:
    """Extract shift assignments for ``target_date`` from the raw Summary grid.

    Returns ``(assignments, warnings)``. Warnings are non-fatal issues such as
    unknown initials or data errors (``!``) in the sheet. The caller decides
    whether to log or surface them.
    """
    col_by_date = {d: col for col, d in parse_date_row(summary, layout.date_row, layout.date_col_start).items()}

    if target_date not in col_by_date:
        return [], []

    col = col_by_date[target_date]
    assignments: list[ShiftAssignment] = []
    warnings: list[str] = []

    for row_idx, (role_label, group_handle) in layout.role_rows.items():
        if row_idx >= len(summary):
            continue
        row = summary[row_idx]
        if col >= len(row):
            continue

        cell = row[col].strip()

        if cell in _EMPTY:
            continue

        if cell in _ERROR:
            warnings.append(
                f"sheet error on {target_date}, row {row_idx + 1} ({role_label}): "
                f"'!' indicates multiple assignees in a single-person role"
            )
            continue

        roster = supsci_roster if group_handle == "summit-sup-sci" else os_roster
        full_name = roster.get(cell)
        if full_name is None:
            warnings.append(
                f"unknown initials '{cell}' on {target_date}, row {row_idx + 1} ({role_label}): "
                f"not found in roster"
            )
            continue

        assignments.append(ShiftAssignment(
            date=target_date,
            role=role_label,
            group_handle=group_handle,
            assignees=(full_name,),
        ))

    return assignments, warnings


# ---------------------------------------------------------------------------
# Network entry point
# ---------------------------------------------------------------------------

def authorize(settings: Settings) -> gspread.Client:
    return gspread.oauth()


def fetch_summary(
    settings: Settings,
    *,
    client: gspread.Client | None = None,
    target_date: date | None = None,
) -> list[ShiftAssignment]:
    """Read the Summary, OS, and SupSci tabs and return assignments for ``target_date``.

    Logs any roster or data warnings. Raises ``ValueError`` if the spreadsheet
    id is missing.
    """
    if not settings.sheet_id:
        raise ValueError("SHIFT_SHEET_ID is required.")
    target_date = target_date or date.today()
    client = client or authorize(settings)
    spreadsheet = client.open_by_key(settings.sheet_id)

    summary_grid = fetch_grid(spreadsheet.worksheet(settings.summary_tab_name))
    os_grid = fetch_grid(spreadsheet.worksheet(settings.os_tab_name))
    supsci_grid = fetch_grid(spreadsheet.worksheet(settings.supsci_tab_name))

    os_roster = parse_roster(os_grid, settings.os_roster_layout)
    supsci_roster = parse_roster(supsci_grid, settings.supsci_roster_layout)

    assignments, warnings = parse_summary_grid(
        summary_grid, os_roster, supsci_roster, target_date, settings.summary_layout
    )
    for w in warnings:
        logger.warning(w)

    return assignments
