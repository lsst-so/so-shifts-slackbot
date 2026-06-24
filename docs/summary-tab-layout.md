# Summary Tab Layout — Unified Shift Schedule Spreadsheet

Layout reference for the **`Summary`** tab of the *Unified Summit Shifts Schedule* spreadsheet.
This tab is the source of truth consumed by `so-shifts-slackbot` to update Slack user groups.
It is also the aggregation view used by humans to check daily coverage across all roles.

**Related documentation:**
- SupSci tab layout → `so-shifts-supsci` repo, `docs/sheet-integration.md`
- OS roster (names/initials) → `OS` tab in the same spreadsheet (described below)
- SupSci roster (names/initials) → `SupSci` tab in the same spreadsheet

---

## Column layout

| Column(s) | Content |
| --- | --- |
| A + B | Merged horizontally — human-readable row label (e.g. "OS Night Shift Manager") |
| C | One-letter role code (e.g. `S` = Summit Science Support Shift) |
| D → | One column per date, advancing right |

Columns A–C are **static** (no date data). All date-bearing data starts at column D.

The role code in column C is a compact identifier for each shift type. Known codes:

| Code | Role |
| --- | --- |
| `S` | Summit Science Support Shift (SupSci) |
| *(others TBD)* | OS roles — codes not yet confirmed |

---

## Row layout (header rows)

| Row | Content | Use programmatically? |
| --- | --- | --- |
| 1 | Month name — merged cells spanning the month's columns | **No** — merged headers only |
| 2 | Full date (stored as a Google Sheets date serial / full date value) | **Yes** — primary date key |
| 3 | Day-of-week label (e.g. "Mon", "Tue") | No — derived from row 2 |

Row 2 is the **date index**: fetch it with `UNFORMATTED_VALUE` to get the raw date serial,
then convert via the Google Sheets origin (`1899-12-30 + serial days`).

---

## Row layout (data rows)

Rows 4, 7, 12, and 15 are **visual dividers** — ignore them programmatically.
All data rows are **single rows** (no vertical merging in the Summary tab).
A cell holding **`-`** means no one is assigned to that role on that date.
A cell holding **`!`** means multiple people are assigned to a single-person role — this is
a data error in the sheet and should be flagged by any tool reading it, never silently processed.

### OS Night Shift (`@os-night-shift`)

Both rows 8 and 9 contribute members to the `@os-night-shift` Slack user group.

| Row | Role | Cell content |
| --- | --- | --- |
| 8 | OS Night Shift Manager | Initials of the assigned OS, or `-` |
| 9 | OS Late Shift | Initials of the assigned OS, or `-` |

The **combined** set of non-empty assignees from rows 8 and 9 on a given date is synced
to `@os-night-shift`.

### OS Day Shift (`@os-day-shift`)

Both rows 10 and 11 contribute members to the `@os-day-shift` Slack user group.

| Row | Role | Cell content |
| --- | --- | --- |
| 10 | OS Day Shift Manager | Initials of the assigned OS, or `-` |
| 11 | OS Day Shift | Initials of the assigned OS, or `-` |

The **combined** set of non-empty assignees from rows 10 and 11 is synced to `@os-day-shift`.

### Summit Support Scientist (`@summit-sup-sci`)

| Row | Role | Cell content |
| --- | --- | --- |
| 16 | Summit Support Scientist | Initials of the assigned SupSci, or `-` |

A single person per date is synced to `@summit-sup-sci`.

---

## Roster lookups (initials → full name → Slack user)

Cells in the data rows hold **initials**, not full names. The bot resolves initials
to full names using two roster tabs, then matches full names to Slack users.

### OS roster — `OS` tab

| Column | Content | Starting row |
| --- | --- | --- |
| A | Full name | Row 12 |
| B | Initials | Row 12 |

Each person occupies **two rows merged vertically** in column A (the merge pattern mirrors
the SupSci availability tab). The name appears only in the top cell of each merged pair;
the bottom cell is blank. Read pairs downward until the first blank name cell.

**Name format:** OS names are stored as `"Surname, Name"` (e.g. `"<name>"`).
Tools consuming this roster should normalize to `"Name Surname"` order by splitting on
the comma and reversing the parts.

Used for: rows 8, 9, 10, 11 in the Summary tab.

### SupSci roster — `SupSci` tab

| Column | Content | Starting row |
| --- | --- | --- |
| A | Full name | Row 6 |
| B | Initials | Row 6 |

Each person occupies **two rows merged vertically** in column A (availability row + shift
row, same as the rest of the SupSci tab). The name appears only in the top cell of each
merged pair. Read pairs downward (rows 6, 8, 10, …) until the first blank name cell.

**Name format:** SupSci names are stored as `"Name Surname"` (e.g. `"<name>"`) —
no reordering needed.

Used for: row 16 in the Summary tab.

### Cell value summary

| Value | Meaning |
| --- | --- |
| Initials (e.g. `BQ`) | Person assigned to this role on this date |
| `-` | No one assigned — intentionally empty |
| `!` | Data error — multiple people assigned to a single-person role; flag and skip |

Each role cell holds **exactly one person's initials** (or `-` or `!`). There is no
multi-value format; each role row represents a single assignment slot.
