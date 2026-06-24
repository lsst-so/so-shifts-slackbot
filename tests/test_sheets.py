"""Tests for the Summary tab and roster parsers (pure — no network)."""

from datetime import date

from so_shifts_slackbot.config import RosterLayout, SummaryLayout
from so_shifts_slackbot.io.sheets import (
    _normalize_name,
    _to_date,
    parse_date_row,
    parse_roster,
    parse_summary_grid,
)

# 2026-06-23 as a Google Sheets serial
_SERIAL_20260623 = str((date(2026, 6, 23) - date(1899, 12, 30)).days)  # "46196"


# ---------------------------------------------------------------------------
# _to_date
# ---------------------------------------------------------------------------

def test_to_date_integer_serial():
    assert _to_date(_SERIAL_20260623) == date(2026, 6, 23)


def test_to_date_float_serial():
    assert _to_date(_SERIAL_20260623 + ".0") == date(2026, 6, 23)


def test_to_date_iso_string():
    assert _to_date("2026-06-23") == date(2026, 6, 23)


def test_to_date_blank():
    assert _to_date("") is None
    assert _to_date("   ") is None


# ---------------------------------------------------------------------------
# parse_date_row
# ---------------------------------------------------------------------------

def _make_date_row(dates: list[date], col_start: int = 3) -> list[list[str]]:
    """Build a minimal two-row grid with a date header at row index 1."""
    def serial(d: date) -> str:
        return str((d - date(1899, 12, 30)).days)
    header = [""] * col_start + [serial(d) for d in dates]
    return [[""] * len(header), header]


def test_parse_date_row_returns_col_to_date():
    dates = [date(2026, 6, 23), date(2026, 6, 24), date(2026, 6, 25)]
    grid = _make_date_row(dates, col_start=3)
    result = parse_date_row(grid, date_row=1, col_start=3)
    assert result == {3: dates[0], 4: dates[1], 5: dates[2]}


def test_parse_date_row_skips_static_columns():
    dates = [date(2026, 6, 23)]
    grid = _make_date_row(dates, col_start=3)
    result = parse_date_row(grid, date_row=1, col_start=3)
    assert 0 not in result and 1 not in result and 2 not in result


def test_parse_date_row_missing_row_returns_empty():
    assert parse_date_row([], date_row=1, col_start=3) == {}


# ---------------------------------------------------------------------------
# _normalize_name
# ---------------------------------------------------------------------------

def test_normalize_name_flips_surname_given():
    assert _normalize_name("Jones, Alice") == "Alice Jones"


def test_normalize_name_passthrough_when_no_comma():
    assert _normalize_name("Alice Jones") == "Alice Jones"


def test_normalize_name_trims_whitespace():
    assert _normalize_name("Smith ,  Alice ") == "Alice Smith"


# ---------------------------------------------------------------------------
# parse_roster
# ---------------------------------------------------------------------------

def _os_grid() -> list[list[str]]:
    """Minimal OS tab: names in col A, initials in col B, starting at row 11 (0-based)."""
    grid = [[""] * 3 for _ in range(11)]  # rows 0-10: headers/filler
    grid += [
        ["Alice Smith", "AS", ""],
        ["", "", ""],           # merged pair — bottom row blank
        ["Bob Jones", "BJ", ""],
        ["", "", ""],
        ["Carol Ray", "CR", ""],
        ["", "", ""],
        ["", "", ""],           # blank name → stop
    ]
    return grid


def test_parse_roster_reads_every_other_row():
    layout = RosterLayout(start_row=11)
    roster = parse_roster(_os_grid(), layout)
    assert roster == {"AS": "Alice Smith", "BJ": "Bob Jones", "CR": "Carol Ray"}


def test_parse_roster_stops_at_blank_name():
    layout = RosterLayout(start_row=11)
    roster = parse_roster(_os_grid(), layout)
    assert len(roster) == 3  # blank row at end stops iteration


def test_parse_roster_empty_grid():
    assert parse_roster([], RosterLayout(start_row=0)) == {}


def test_parse_roster_normalizes_comma_format():
    grid = [[""] * 3 for _ in range(11)]
    grid += [
        ["Jones, Alice", "AJ", ""],
        ["", "", ""],
        ["", "", ""],
    ]
    roster = parse_roster(grid, RosterLayout(start_row=11))
    assert roster == {"AJ": "Alice Jones"}


# ---------------------------------------------------------------------------
# parse_summary_grid
# ---------------------------------------------------------------------------

def _layout() -> SummaryLayout:
    return SummaryLayout(
        date_row=1,
        date_col_start=3,
        role_rows={
            7:  ("OS Night Shift Manager",   "os-night-shift"),
            8:  ("OS Late Shift",            "os-night-shift"),
            9:  ("OS Day Shift Manager",     "os-day-shift"),
            10: ("OS Day Shift",             "os-day-shift"),
            15: ("Summit Support Scientist", "summit-sup-sci"),
        },
    )


def _build_summary(
    target_date: date,
    values: dict[int, str],  # {row_index: cell_value for target_date column}
    col_start: int = 3,
) -> list[list[str]]:
    """Build a minimal Summary grid with one date column at col_start."""
    serial = str((target_date - date(1899, 12, 30)).days)
    n_rows = max(values.keys()) + 1 if values else 16
    n_cols = col_start + 1
    grid = [[""] * n_cols for _ in range(max(n_rows, 2))]
    grid[1][col_start] = serial  # date header row
    for row_idx, val in values.items():
        while len(grid) <= row_idx:
            grid.append([""] * n_cols)
        while len(grid[row_idx]) <= col_start:
            grid[row_idx].append("")
        grid[row_idx][col_start] = val
    return grid


_OS_ROSTER = {"AS": "Alice Smith", "BJ": "Bob Jones", "CR": "Carol Ray", "DR": "Dana Rios"}
_SS_ROSTER = {"MK": "Maria Kim"}


def test_parse_summary_happy_path():
    target = date(2026, 6, 23)
    summary = _build_summary(target, {7: "AS", 8: "BJ", 9: "CR", 10: "DR", 15: "MK"})
    assignments, warnings = parse_summary_grid(summary, _OS_ROSTER, _SS_ROSTER, target, _layout())

    assert not warnings
    assert len(assignments) == 5

    by_role = {a.role: a for a in assignments}
    assert by_role["OS Night Shift Manager"].assignees == ("Alice Smith",)
    assert by_role["OS Night Shift Manager"].group_handle == "os-night-shift"
    assert by_role["OS Late Shift"].assignees == ("Bob Jones",)
    assert by_role["Summit Support Scientist"].assignees == ("Maria Kim",)
    assert by_role["Summit Support Scientist"].group_handle == "summit-sup-sci"


def test_parse_summary_dash_is_skipped():
    target = date(2026, 6, 23)
    summary = _build_summary(target, {7: "-", 15: "MK"})
    assignments, warnings = parse_summary_grid(summary, _OS_ROSTER, _SS_ROSTER, target, _layout())
    assert not any(a.role == "OS Night Shift Manager" for a in assignments)
    assert not warnings


def test_parse_summary_exclamation_is_warned_and_skipped():
    target = date(2026, 6, 23)
    summary = _build_summary(target, {7: "!", 15: "MK"})
    assignments, warnings = parse_summary_grid(summary, _OS_ROSTER, _SS_ROSTER, target, _layout())
    assert not any(a.role == "OS Night Shift Manager" for a in assignments)
    assert len(warnings) == 1
    assert "!" in warnings[0]


def test_parse_summary_unknown_initials_warns_and_skips():
    target = date(2026, 6, 23)
    summary = _build_summary(target, {7: "ZZ", 15: "MK"})
    assignments, warnings = parse_summary_grid(summary, _OS_ROSTER, _SS_ROSTER, target, _layout())
    assert not any(a.role == "OS Night Shift Manager" for a in assignments)
    assert any("ZZ" in w for w in warnings)


def test_parse_summary_wrong_date_returns_empty():
    target = date(2026, 6, 23)
    summary = _build_summary(target, {7: "AS", 15: "MK"})
    assignments, warnings = parse_summary_grid(
        summary, _OS_ROSTER, _SS_ROSTER, date(2026, 6, 24), _layout()
    )
    assert assignments == []
    assert warnings == []


def test_parse_summary_supsci_uses_supsci_roster():
    target = date(2026, 6, 23)
    # "AS" is in the OS roster but not in the SupSci roster
    summary = _build_summary(target, {15: "AS"})
    _, warnings = parse_summary_grid(summary, _OS_ROSTER, _SS_ROSTER, target, _layout())
    assert any("AS" in w for w in warnings)
