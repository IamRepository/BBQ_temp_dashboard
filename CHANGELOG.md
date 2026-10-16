# Changelog

All releases of the Cook Profile Dashboard, newest first. Dates are when each release reached GitHub. The running version is shown under the page title and stored in `version.py`.

## [1.7.0] - 2026-10-16

Roles for multi-device cooks (Typhur + Weber), as agreed on 16 October 2026. Commit [`COMMIT`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/COMMIT).

### Added
- **Check the import.** After "Import uploaded files", a card lists every temperature column found. Nothing is added until "Add" is clicked; "Cancel" adds nothing. Each column has:
  - an Import tick, to leave a column out;
  - a Probe label: which probe or device it comes from, for example "Typhur probe 2", or "Smoque_XL Probe 1" when a file has numbered probes;
  - a Role.
  A line under the list shows the names the profiles will get.
- **Roles:** Meat, Point, Flat, Grate, Pit, Hold, Setpoint and Other. The suggestion comes from the column name:
  - Typhur "Ambient temperature" becomes Grate, and "Meat temperature" becomes Meat (choose Point or Flat for a brisket).
  - The Weber "cavity temperature" becomes Pit.
  - "Setpoint", "Target" and "Set temperature" become Setpoint.
- **Names "<probe> - <role>",** for example "Typhur probe 2 - Grate", made unique when needed.
- **Colour by probe, line style by role.** All lines of one probe share a colour: four Typhur probes plus a Weber with two probes are 7 colours for 11 lines, within the 8 validated colours.
  - Meat, Point and Flat are solid, Grate dash-dot, Pit long dash, Hold long dash-dot, and a Setpoint dashed as before.
  - With more than four lines the legend moves to the right of the chart, so it no longer runs into the title.
- **Role in Profile details,** in place of the "Setpoint (dashed line)" tick box.
  - Choosing Setpoint makes the profile a setpoint: drawn dashed and available under Setpoint vs measured.
  - A name still in the "<probe> - <role>" form follows a role change.
- **Excel export names the Brisket Tenderness Analyzer reads correctly.** The Analyzer picks a role from words in each column name, in a fixed order, so some names misled it. The export now adjusts a name only when needed:
  - A meat probe on the Smoque XL lost the role to the controller rule ("smoque"); it is now exported as "XL Probe 1 - Meat".
  - A Pit name without a controller word gets "(PID)".
  - A setpoint is written as "Set temperature", because "Setpoint" contains "point" and was taken for the brisket point.
  - On screen the names are unchanged. A test checks every probe and role against a copy of the Analyzer's rules (v2.8.3).
- **Typed start times from BBQ Chart to Data.** A text column "Start time source" is read, not imported as a temperature.
  - When it says "typed", Import notes says so and the profile's status line adds "start time typed in Chart to Data, check it".
  - This follows the format proposed for Chart to Data's next update: a "Start time source" column with "read and confirmed" or "typed".
- 14 more regression tests (73 in all): role and probe suggestions, every export name against the Analyzer's rules, colours by probe, line styles, the Chart to Data files with a typed start (two new example files), re-importing the merged export with the same roles, and the import review (defaults, changed choices, Cancel, role change).

### Changed
- Profiles loaded before 1.7.0 get a role and probe from their column and file names. Their line style can change, for example the Weber cavity line becomes long-dashed (role Pit).

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): several files changed and `roles.py` is new.

## [1.6.10] - 2026-10-16

Target line and new defaults. Commit [`aaecc53`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/aaecc53).

### Added
- **Target line.** A new "Target line" switch under Chart options draws a straight, dotted line across the chart at the temperature the cook aimed for. It is labelled at the left, for example "Target 200 °C".
  - The temperature is set in "Target temperature (°C)", which appears when the switch is on; it starts at 200 °C.
  - The line appears on the comparison chart and the selected profile's chart, and in images saved from them.
  - It is drawn in the page's text colour (light in dark mode, dark in light mode), so it never looks like one of the profiles.
  - The temperature axis stretches to include the target when it is above or below all readings.
  - It is not part of the Excel export or the setpoint comparison; for a target that changes during the cook, use a setpoint profile.
- 3 more regression tests (59 in all): the new defaults, and the target line on both charts.

### Changed
- The app opens in **dark mode**; Light is one click away under Theme.
- Chart images are saved as **JPEG** by default; PNG is still available under Image download.
- The default **line width is 3.5** (was 2.5).

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py` changed.

## [1.6.9] - 2026-10-13

Compact Profile details on the same screen as the chart. Commit [`6f20a3d`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/6f20a3d).

### Changed
- **Profile details and the comparison chart share one card.** On a 1440 × 900 or 1920 × 1080 screen, the controls, the whole chart and the export row fit on one screen, so a change to a profile is seen at once.
- **Profile details is about 60% shorter** (258 instead of about 620 pixels), in two rows:
  - Row 1: Profile, Display name, Channel label, Time offset (min), Color and Setpoint (dashed line).
  - Row 2: Trim all profiles together, the trim slider, Reset and Remove profile.
- **One status line under the trim slider.** It shows the profile's full name, its file, the samples shown, the trim window (or the points hidden left and right), and the time offset as h:mm:ss when it is not zero. It replaces the separate sample, offset and window lines. Because the full name is in this line, a long name cut off in the Profile box can still be read; this replaces the separate full-name line from 1.6.7 and 1.6.8.
- **Chart heading.** The card heading "Temperature profile comparison" and its note are gone. The chart title "Temperature profiles" now has the summary as a subtitle, for example "4 profiles | 2 devices | 1.3 - 1.5 h duration range". The subtitle is also in saved chart images.
- **Excel export under the chart.** Export interval and Download Excel file moved from Profile details to below the chart. The section label "Export visible profiles" is gone; the Export interval help says that the visible profiles are exported.
- Shorter labels to fit the rows:
  - "Line color" is now "Color".
  - "Reset data window" is now "Reset", and "Reset all data windows" is now "Reset all".
  - Each reset button has a help tip saying what it resets.

### Added
- 3 more regression tests (56 in all): the chart subtitle, the order of controls, chart and export in the card, and the status line with file, samples and offset.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py` changed.

## [1.6.8] - 2026-10-13

Layout: Profile details above the chart, and 16:9 charts. Commit [`d6654f9`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/d6654f9).

### Changed
- **Profile details moved above the chart.** It was a narrow column to the right of the comparison chart. It is now a full-width panel between the overview cards and the chart, so a change to a profile shows in the chart directly below it.
  - Top row: Profile, Display name, Channel label, Time offset and Line color, side by side.
  - Second row, three groups: Visible data window (Trim all profiles together, the trim slider and its reset button); Selected profile (Setpoint tick box and Remove profile); Export visible profiles (Export interval and Download Excel file).
  - The comparison chart now uses the full page width.
  - On a phone the groups stack, as before.
- **16:9 charts.** The comparison chart and the selected profile's chart keep a 16:9 shape at any window width, instead of a fixed 650-pixel height. Images saved with the camera icon are 16:9 too, 3200 × 1800 pixels (1600 × 900 at scale 2), whatever the window size. The Setpoint vs measured chart keeps its short, wide shape.
- Shorter labels so nothing is cut off in the new layout:
  - "Time offset (minutes)" is now "Time offset (min)".
  - "This is a setpoint (dashed line)" is now "Setpoint (dashed line)".
  - "Remove selected profile" is now "Remove profile".
  - The help texts are unchanged in meaning.
- The full-name line under the Profile box (added in 1.6.7) is shown only on windows 640 to 1399 pixels wide. The box is now wide enough for full names on wider windows; on a phone it is full width.

### Added
- 3 more regression tests (53 in all): no fixed chart height, 16:9 saved images, and the panel order.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py` changed.

## [1.6.7] - 2026-10-13

Speed and upkeep: fixes M6, M7, L6 and L7, the last open issues from the 12 October audit, and adds trimming of all profiles at once. Commit [`4798881`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/4798881).

### Added
- **Trim all profiles together**, a tick box under Visible data window. When ticked, one slider sets the same time window for every loaded profile instead of trimming them one by one. It uses clock time, with each profile's time offset, when every profile has clock times. Otherwise it uses hours from each profile's start, as on the Start timeline. The slider starts at the window that covers all current trims, so ticking the box changes nothing until you move it.
  - A line under the slider spells out the window (for example "16:04 to 16:36 on 03/10/2026") and how many points of the selected profile are shown.
  - A profile with no readings inside the window is left as it was and named under the slider.
  - "Reset all data windows" shows every profile in full again.
  - Untick the box to fine-tune a single profile; its own slider picks up the shared trim.
- 13 more regression tests (50 in all), for chart thinning on a made-up 18-hour cook, trimming all profiles in clock time and in hours, the time offset, the pinned versions, the full-name line and the download button.

### Fixed
- Long cooks made the page slow: an 18-hour cook logged every second (64,800 readings per probe) took 3 to 4 s per click, 9.6 s with "As logged" export selected, and sent 13 MB of chart data. Each click now takes about 0.1 s on the server (0.6 to 0.9 s in the browser, including drawing) and sends 0.35 MB, then about 0.02 MB per click. (M6) Three changes:
  - Charts draw at most 4,000 points per line, keeping the lowest and highest reading in each stretch, so short spikes such as a lid opening still show. Lines with fewer points are drawn in full. Statistics, the setpoint comparison and the Excel file always use every reading.
  - The profile name and channel in the chart's hover box are sent once per line instead of once per reading.
  - The Excel file is built only when "Download Excel file" is clicked, not on every click elsewhere on the page. With "As logged" on a very long cook the download itself takes several seconds.
- The closed Profile box cut long names off in the narrow Profile details column. The full name now shows under the box, with a bar in the line colour. (L6)
- The Export interval help still said "One Excel sheet"; since 1.6.6, profiles without clock times go on a second sheet. The help now says so.
- Two time calculations in the clock-change handling used a form that new numpy versions warn about and will later reject. Both now give the unit explicitly; no change in results.

### Changed
- `requirements.txt` pins the exact versions tested: Streamlit 1.65.0, Plotly 6.9.0, pandas 2.3.3, openpyxl 3.1.5 and xlrd 2.0.2. Before, any Streamlit 1.x from 1.60 was allowed, so a reboot could install a newer Streamlit that breaks the dark-mode styling. numpy stays a range, because which numpy builds exist depends on the server's Python version. New versions are adopted in a release of their own, after testing. (M7)

### Removed
- The unused file `example_data.py`; the app never loaded it. (L7)

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py`, `models.py` and `profile_loader.py` changed, and the reboot also installs the pinned package versions.

## [1.6.6] - 2026-10-13

Everyday use: fixes M2 to M5, L1 to L5, L8 and L9 from the 12 October audit. Commit [`5bd1ab2`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/5bd1ab2).

### Fixed
- Pressing "Import uploaded files" a second time added the same files again (4 profiles became 8 with identical names). A file already loaded, or listed twice in one import, is now skipped with a note in Import notes. Files are recognised by their contents, so a renamed copy is skipped too. (M2)
- A second import with "Keep existing profiles" reused colours already on the chart. New profiles now take the first colour not in use. (M3)
- Chart titles were dark grey on the dark card in dark mode (contrast 1.4:1). Streamlit's chart theme overrode the title colour; charts are now drawn with the app's own colours, and the titles measure 14.3:1. All other chart text is at least 7:1. (M4)
- The rename warning "Profile names must be unique" stayed on screen after switching to another profile. It now clears. (L1)
- Importing the dashboard's own Excel file gave names like "Cook profiles 2026-10-03 - Cook profiles - Connet - Probe 1 (°C)". " (°C)" is dropped from column names, and the sheet name is left out when a workbook has only one sheet. (L2)
- The Preview imported data table added the time offset to elapsed hours but not to the timestamps. Both now move. (L4)
- In Clock alignment, profiles without clock times were drawn on hours beside clock-time profiles. They are now left out of that chart with a note naming them; Start, Peak and End alignment still show them. The single-profile chart shows them on their own timeline. (L9)

### Changed
- Line colours come from a new 8-colour palette, checked with a colour-vision validator on the light and dark chart backgrounds: every neighbouring pair stays distinct for red-green and blue-yellow colour blindness. The old palette had a violet and sky blue that look alike to colour-blind readers, and a yellow too pale on white. The plan said 12 colours; only 8 pass these checks, so a ninth profile reuses the least-used colour. (M3)
- The time offset is now a number box in minutes (to 0.01 min, up to ±24 h), with arrows that step one minute, and a readout in h:mm:ss below it. It replaces the slider with 15-minute steps, so a device clock a few minutes off can be corrected. Existing offsets carry over. (M5)
- The Excel export keeps clock time for profiles that have it, on the "Cook profiles" sheet. Elapsed-only profiles go on a second sheet, "Elapsed time", counted in hours from their own start. Before, one elapsed-only profile switched the whole file to elapsed hours, so devices no longer lined up. Exports with only clock-time profiles are unchanged. (L3)
- The CHANNELS card is now DEVICES and counts source files. It counted distinct channel labels, so two devices' "Probe 1" counted once. (L5)

### Corrected
- The 1.6.3 entry said no text was below 3:1 contrast. That audit covered the page text only, not text inside charts, which is how the dark-mode chart titles (M4) were missed. The entry now says so, and release checks include chart text. (L8)

### Added
- 15 more regression tests (37 in all), one or more per fixed issue, and the example file `tests/data/l2_dashboard_export.xlsx`.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `profile_loader.py`, `export_utils.py`, `chart_builder.py` and `models.py` changed.

## [1.6.5] - 2026-10-13

Reliable file import: fixes the five high-severity issues from the 12 October audit, plus M1 and M8. Commit [`c0b6a55`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/c0b6a55).

### Fixed
- Year-first dates (2026-10-04) on days 1 to 12 of a month were read with day and month swapped, so a cook crossing midnight seemed to last 720 hours. Year-first text is now always read as year-month-day, and day-first text (03/10/2026, 03.10.2026) as day-month-year. (H1)
- Files with only an elapsed-time column (minutes, hours or seconds) were read as clock times in nanoseconds, so every cook lasted zero hours. Number columns are no longer treated as dates; Excel date serial numbers under a date header are still read as dates. (H2)
- Timestamps with a UTC offset (+02:00, Z, GMT+2) crashed the whole page. They are now converted to one clock time per file. (H3)
- A cook across the autumn clock change was scrambled: the repeated hour was sorted into the wrong order and the cook looked an hour short. Zone names (CEST, CET and others) and offsets are now used to keep one continuous clock, the one in force when the cook started, with a note in Import notes. A log without zone names that steps back by about an hour once is corrected the same way. (H4)
- A setpoint column with one fixed value (for example 120 °C all cook) was discarded. Constant columns whose header names a temperature or setpoint are kept. (H5)
- Columns without a temperature word in the header (for example "Target") were dropped whenever another column had one. Every column in the temperature range is now imported. Columns that are clearly not temperatures (%, fan, battery, humidity, rpm, signal and similar) are skipped, and Import notes lists them with the reason. (M1)
- A probe plugged in partway through a cook was dropped when it had readings in less than 60% of the rows. Any column whose filled cells are readings is now kept. (Found while testing M1.)
- Columns in Fahrenheit were shown as °C. Headers with °F, (F) or Fahrenheit are converted to °C, and Import notes says so. (M8)

### Added
- Regression tests in `tests/`: 22 tests, covering each fixed issue with its own small example file, formats that already worked, and the main page interactions. Run with `python -m unittest discover -s tests -v`.

### Unchanged
- Your thermometer files (Weber Connect, Smoque XL) import exactly as before: same profiles, times, readings and notes.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `profile_loader.py` changed.

## [1.6.4] - 2026-10-12

Colour-coded profile dropdowns with full names. Commit [`1665b1a`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/1665b1a).

### Changed
- The Profile, Setpoint and Measured probe dropdowns show a colour swatch beside each entry, in that profile's line colour, so each stream can be matched to its line at a glance. The swatch follows the line colour when it is changed.
- These dropdowns open wide enough to show each profile's full name instead of cutting it off. The list stays attached to its box and on screen, also in the narrow right-hand column.

### Fixed
- Open dropdown lists were white in dark mode, because this Streamlit version draws them in a different container from the one the v1.6.3 styling targeted. They now follow the dark theme.

## [1.6.3] - 2026-10-10

Dark mode fixes and Excel export. Commit [`7c02c22`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/7c02c22).

### Fixed
- Unreadable text in dark mode: "Reset data window", "Remove selected profile" and the download button had near-white text on white, and help tooltips had the same problem.
- "Import uploaded files" now has white text on blue in light mode too; it was dark text on blue.
- Dropdown lists, uploaded-file chips, the uploader's add icon, dropdown arrows and the small heading above the title now follow the dark theme.
- Checked with an automated contrast audit of every visible text element on the page, in light and dark mode, on Streamlit 1.60 and 1.65: none is below 3:1. Correction (1.6.6): the audit did not cover text inside charts; the chart titles were 1.4:1 in dark mode until 1.6.6.

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

[1.7.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/aaecc53...COMMIT
[1.6.10]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/6f20a3d...aaecc53
[1.6.9]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/d6654f9...6f20a3d
[1.6.8]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/4798881...d6654f9
[1.6.7]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/5bd1ab2...4798881
[1.6.6]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/c0b6a55...5bd1ab2
[1.6.5]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/49fbe62...c0b6a55
[1.6.4]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/b9ade35...1665b1a
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
