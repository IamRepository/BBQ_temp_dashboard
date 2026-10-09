# Changelog

All releases of the Cook Profile Dashboard, newest first. Dates are when each release reached GitHub. The running version is shown under the page title and stored in `version.py`.

## [1.6.3] - 2026-10-10

Dark mode fixes and Excel export. Commit [`7c02c22`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/7c02c22).

### Fixed
- Unreadable text in dark mode: "Reset data window", "Remove selected profile" and the download button had near-white text on white, and help tooltips had the same problem.
- "Import uploaded files" now has white text on blue in light mode too; it was dark text on blue.
- Dropdown lists, uploaded-file chips, the uploader's add icon, dropdown arrows and the small heading above the title now follow the dark theme.
- Checked with an automated contrast audit of every visible text element in light and dark mode, on Streamlit 1.60 and 1.65: none is below 3:1.

### Changed
- The data download is now one Excel sheet instead of a ZIP of CSV files: Timestamp (dd/mm/yyyy hh:mm), then one "<profile name> (°C)" column per visible profile. The button is called "Download Excel file".
- New Export interval setting (As logged, 10 s, 30 s, 1 min, 5 min; default 1 min). Readings are averaged within each interval and rounded to 0.1 °C.
- Trimming and time offsets are applied to the export; smoothing is not. The file is named after the cook date, for example "Cook profiles 2026-10-03.xlsx".

### Removed
- The unused file `profile_processing.py`.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app). Otherwise the server can keep the previous `export_utils.py` in memory and fail to start.

## [1.6.2] - 2026-10-05

Cosmetic adjustments. Commit [`7fd6ede`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/7fd6ede).

### Changed
- The explanation of the Smoothing control moved into an info icon next to its heading, shown on hover, like Timeline alignment.
- Chart options no longer sit in a dropdown: Grid lines and Legend are toggles, with Line width below them.
- In Profile details, the profile picker, display name and channel label take the colour of the selected line and follow it when the colour or the selected profile changes. The text switches between dark and white for readability.
- Toggles use the same blue as the other selected controls.

### Added
- Image download setting (PNG or JPEG): the camera icon in the top right of each chart saves the picture in the chosen format at twice the screen size. The chart toolbar is always visible.

## [1.6.1] - 2026-10-05

Sidebar tidy-up. Commit [`98c1887`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/98c1887).

### Changed
- "Cook Profile" and the Data section moved up; the sidebar collapse arrow no longer takes a row of its own.
- Import notes now sit below Chart options.
- Chart options: Grid lines and Legend checkboxes, and Line width as an input box with minus and plus buttons (0.5 steps, 1.0 to 5.0; the arrow keys also work).
- The explanation of the timeline alignment modes moved into an info icon next to the heading, shown on hover and covering all four modes.

### Fixed
- Collapse arrow, info icon and the plus and minus buttons are readable in dark mode.

## [1.6.0] - 2026-10-05

Setpoint comparison and smoothing. Commit [`3e73d04`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/3e73d04).

### Added
- "Setpoint vs measured" card: tick "This is a setpoint" for a profile (for example the cooker's own temperature setting), then compare it with any measured probe.
- The card shows the average difference, lowest to highest difference, time within an accepted band (default ±10 °C) and time analysed, plus a chart of probe minus setpoint with the band shaded.
- "Ignore first (minutes)" leaves out the warm-up phase; trimmed data windows are respected.
- Profiles from different devices are matched by clock time and time offsets, whatever timeline alignment is selected.
- Setpoint profiles are drawn as dashed lines and labelled "(setpoint)".
- Smoothing control (Off, 1, 5 or 10 min): a rolling average on measured lines only. Setpoints and exported data are never smoothed; the single-profile chart keeps the raw readings faintly behind the smoothed line.
- The running version number is shown under the page title (stored in `version.py`).
- New file `analysis.py` with the smoothing and comparison logic.

### Changed
- Timeline alignment is a row of buttons (Start, Peak, End, Clock) like the Theme control.
- The time offset also shifts profiles in Clock time mode.

### Fixed
- For current Streamlit versions: profile chips are neutral again, the top line of the page is no longer hidden under the header, and buttons, dropdowns, inputs and the Import notes panel are readable in dark mode.

## [1.5.0] - 2026-10-05

Stability and import fixes. Commit [`3fe53b5`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/3fe53b5).

### Fixed
- Crash when clicking "Reset data window".
- Crash when clicking "Remove selected profile".
- Newly imported profiles are shown automatically; before, they stayed hidden after importing more files or re-importing after "Clear all".
- Renaming a profile updates everywhere immediately.
- Column names are trimmed, so "Probe 1" no longer imports as " Probe 1".
- Timestamps with zone names (for example "CEST") parse reliably instead of relying on a deprecated pandas behaviour.
- One unreadable file no longer cancels the whole import; it is skipped with a note.
- The Theme selector can no longer end up empty; multiselect tags follow the dark theme.
- The ZIP export no longer overwrites profiles that share a name.

### Added
- Loggers that drop a reading when a probe disconnects (rows with fewer values than the header) are detected. Values are placed in the matching probe column, and an "Import notes" panel reports what happened. Import notes stay visible after the page refreshes.

### Changed
- Uses Streamlit's current `width='stretch'` option; requires Streamlit 1.60 or newer.

### Note
- These release notes also listed the removal of `profile_processing.py`, but the file stayed in the repository until 1.6.3.

## [1.4.0] - 2026-10-03

Profile trimming. Commit [`822bd30`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/822bd30).

### Added
- A dual-handle slider for each selected profile: the left handle hides leading data points, the right handle hides trailing ones.
- Trimming updates the comparison charts, individual charts, statistics and exported data.
- Visible, total and hidden-point counts.
- A one-click reset of the selected profile's data window.
- The original uploaded data stays unchanged in memory.

## [1.3.0] - 2026-10-03

Visual cleanup. Commit [`45abf0d`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/45abf0d).

### Changed
- One page background and white cards for the light theme.
- Neutral slate profile chips instead of warning-red ones.
- Lighter shadows, border contrast and sidebar weight.
- Taller main chart and wider chart column.
- Fainter chart grid and simpler metric labels.
- Rounded line-colour control; unnecessary metric arrows removed.
- Light and dark themes both kept.

## [1.2.0] - 2026-10-03

Visual redesign. Commit [`52f9ac1`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/52f9ac1).

### Added
- In-app Light and Dark theme selector; light is the default.

### Changed
- Reworked spacing, typography, cards, sidebar, controls and chart surfaces.
- Softer borders, restrained shadows and higher-contrast text.
- Profile details and the comparison chart as distinct cards.
- Improved Plotly legend, grid, hover labels and tooltip content.
- Blue accent and a neutral palette.

## [1.1.1] - 2026-10-03

Selection fixes. Commit [`a5ccee5`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/a5ccee5).

### Fixed
- Profile-selection crashes, by using stable profile IDs.
- Explicit unique keys on stateful Streamlit widgets.
- The selection is kept across profile changes and renaming.
- The selection resets safely after deleting the active profile.

## [1.1.0] - 2026-10-03

Celsius only and new statistics. Commit [`1df5ebc`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/1df5ebc).

### Added
- Summary cards: visible profiles, unique channels, duration range and temperature range.
- Selected-profile statistics: name, duration, maximum temperature and sample count.
- Original, peak, end and clock-time alignment modes.

### Removed
- Fahrenheit and all temperature conversion.
- Example-data loading from the interface.

### Kept
- CSV, XLSX and XLS multi-file import, Plotly charts, profile customisation and CSV ZIP export.

## [1.0.0] - 2026-10-03

First Streamlit version. Commits [`8711111`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/8711111) and [`f86988e`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/f86988e) (re-upload).

### Added
- Upload of one or more CSV, XLSX or XLS files, reading every Excel worksheet.
- Detection of date/time, elapsed-time and temperature columns; one profile per temperature channel.
- Interactive Plotly chart overlaying several profiles.
- Show or hide, rename, recolour and time-offset each profile.
- Celsius and Fahrenheit display; elapsed time or clock time.
- Export of visible profile data as a ZIP of CSV files.
- Built-in example profiles.

## Prototype - 2026-10-03

A first React and Vite version ([`480c979`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/480c979)) that ran in the browser: CSV and Excel upload, automatic column detection, an elapsed-time chart, and Celsius or Fahrenheit display. It was replaced by the Streamlit version the same day.

[1.6.3]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/7fd6ede...7c02c22
[1.6.2]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/98c1887...7fd6ede
[1.6.1]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/3e73d04...98c1887
[1.6.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/3fe53b5...3e73d04
[1.5.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/822bd30...3fe53b5
[1.4.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/45abf0d...822bd30
[1.3.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/52f9ac1...45abf0d
[1.2.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/a5ccee5...52f9ac1
[1.1.1]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/1df5ebc...a5ccee5
[1.1.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/f86988e...1df5ebc
[1.0.0]: https://github.com/IamRepository/BBQ_temp_dashboard/commit/f86988e
