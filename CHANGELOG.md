# Changelog

All releases of Probe-2-Plot (called Cook Profile Dashboard up to v1.7.6), newest first. Dates are when each release reached GitHub. The running version is shown under the page title and stored in `version.py`.

## [1.8.2] - 2026-11-05

The rest of the 28 Oct diff audit (D4, D7, D8, D11 in part) and the legend item from the 5 Nov audit. Commit [`47ce58e`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/47ce58e).

### Added
- **Probe field in Profile details (D8).** The probe a profile comes from could only be set in Check the import. It can now be changed at any time, between Display name and Channel. Colour follows the probe: type the name of a probe already on the dashboard to take its colour, or a new name to give the profile its own unused colour. A display name still in the "<probe> - <role>" form follows the new probe ("Typhur 1 - Ambient"). A blank entry is ignored.

### Changed
- **The overview card counts probes, not files (D7).** "DEVICES / Source files" is now "PROBES / From N files", and the chart summary says "4 probes" instead of "2 devices". Chart-2-Data writes one file per Typhur probe, so files over-counted Typhurs; one Weber file holds the controller and its own probes, so files under-counted it.
- **Excel export names keep a probe name (D4).** Removing the words the Brisket Tenderness Analyzer reads as other roles could leave only the role: "Hold oven - Meat" became "Meat", and two such columns came out as "Meat" and "Meat 2". Now the file name, without those words, is put in front, or "Device" when nothing is left: "Device - Meat", "Kitchen - Meat". The Analyzer still reads the intended role from every name.
- **The selected profile's legend sits under its chart.** Above the plot, the room for it was estimated for the old sidebar layout and left an empty band about 40 px high on wide screens. Under the chart Plotly makes exactly the room needed, one row or two, at any width. (The comparison chart's legend, grouped by role, stays at the right.)
- **"Channel label" is now "Channel"**, with a help text, so row 1 of Profile details fits eight fields. Below about 1,180 px that row wraps onto two lines instead of squeezing every field.
- README: the tested Python version (3.13) and the Probe field. A LICENSE file is not added yet: the licence is the owner's choice.

### Removed
- The legend-row estimate (`_legend_extra`), no longer needed.

### Tests
- 7 more regression tests (111 in all): export names that keep a probe name and two such columns staying apart; the Probe field (new probe gets its own colour and name, joining a probe takes its colour, blank ignored); the legend under the selected profile's chart and beside the grouped comparison chart. Two tests updated for PROBES. All pass on Streamlit 1.66.1 and 1.60.0. Browser: row 1 checked at 1,000, 1,180, 1,280 and 1,440 px; contrast scan in dark and light mode with every panel open, nothing new below 4.5:1.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (`roles.py`, `export_utils.py` and `chart_builder.py` changed).

## [1.8.1] - 2026-11-05

Import, export and security fixes from the 28 Oct diff audit (D1, D2, D3, D5, D6, D9, D10) and the 5 Nov audit backlog; Clear all asks first. Commit [`ee3b467`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/ee3b467).

### Fixed
- **Wide files with probe dropouts no longer stall the import (D1).** When a row had fewer values than the header, every possible placement of its values was tried: a 26-column file took about 6 s per short row, 30 columns about 3 minutes. The best placement is now found column by column, with the same result (checked against the old method in 1,500 random cases), in well under a millisecond per row.
- **US time zones (D2).** CST (US Central) was missing, so a US log running from CDT into CST went backwards by an hour. Added CST, Alaska, Hawaii, Australian, New Zealand and Japanese zone names. A zone name the app does not know is now reported in Import notes ("time zone IST not recognised"), instead of being dropped silently.
- **Excel headers stay text.** A profile or file name starting with "=" (for example a file called "=SUM(1,2).csv") became a formula cell in the export header; it is now saved as text, so Excel and the Brisket Tenderness Analyzer read the name.
- **Names are shown exactly as written.** File and profile names were read as formatting: HTML such as `<br>` in the chart legend, hover and title, and Markdown, `$...$` maths or `:colour[...]` in captions, notes and warnings. They are now escaped everywhere they are shown.
- **Clear all starts the next cook clean.** Roles switched off under the chart, the Roles shown choice, Import notes and the trim note of the removed cook no longer carry over to the next import.
- **A CSV that cannot be read says why (D5),** for example "could not be parsed as CSV (unexpected end of data)".
- **All roles switched off (D6):** the chart summary now says "All roles hidden (...)  |  choose the roles to show under the chart" instead of "0 of 5 profiles | 0 devices | 0.0 - 0.0 h".

### Changed
- **Clear all asks first.** It opens a small panel: "Remove all 5 profiles?", what is lost, and a "Remove all 5 profiles" button. Nothing is removed until that button is pressed.
- **Upload limit 25 MB per file** (was Streamlit's 200 MB), set in the new `.streamlit/config.toml`. An 18-hour cook logged every second is about 4 MB.
- **Streamlit 1.66.1 and Pillow 13.0.0 (D3).** Streamlit 1.65.0 kept the Pillow image library at 12.3.0, which has known security problems. Pillow is now pinned too. Page styling, panels, sliders and contrast re-checked in the browser on 1.66.1 and 1.60.
- **"Grill" is a pit word (D9):** a column such as "Grill temp" now starts with the role Pit (was Other). "Grill grate" stays Grate and "Grilled chicken probe" stays Meat.
- **Role help:** the explanation of every role (written for v1.7.0 but never shown) is now the help text of the Role select in Profile details and of the Role column in Check the import.
- README: test count, the Role per profile (the setpoint tick box went in v1.7.0), the import assumptions (Check the import exists since v1.7.0), time zones, the upload limit and the pinned versions.

### Removed
- Unused code: the `TIME_WORDS` list and the `color_start` argument of `dataframe_to_profiles` (D10; colours are set per probe in Check the import).

### Tests
- 14 more regression tests (104 in all): a 25-column file with 6 short rows, the new placement against the old one, US and Australian clock changes, an unknown zone name, a "=SUM(1,2)" header, a CSV error message, the grill rule, the upload limit, escaped names in charts and captions, Clear all (confirmation, state reset, next cook shows every role), all roles hidden, and the role help. The tests now read captions as shown on the page.
- All tests pass on Streamlit 1.66.1 and 1.60.0. Browser contrast scan in dark and light mode with every panel open: no new text below 4.5:1.

### Upgrade note
- **Reboot the app on Streamlit Community Cloud** after deploying (Manage app, three dots, Reboot app): it installs Streamlit 1.66.1 and Pillow 13.0.0 and reloads `profile_loader.py`, `chart_builder.py`, `export_utils.py` and `roles.py`.

## [1.8.0] - 2026-11-04

No sidebar: a Start card and a toolbar under the page title. Commit [`7fe1339`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/7fe1339). Chosen by the user from four drawn options (option A), then reviewed in the app on branch design/v1.8.0-toolbar.

### Changed
- **The sidebar is gone.** Everything it held now sits under the page title, so the chart starts about 250 px higher and uses the full window width.
- **Start card (before the first import).** Where the note "Upload one or more CSV or Excel files from the sidebar to begin" used to be: the file box, the Import files button, and a line saying columns, roles and probes are checked before anything is added.
- **Toolbar.** One row: Add files · Timeline alignment · Smoothing · Chart options · Theme · Clear all.
  - **Add files** opens a small panel with the file box, Keep existing profiles and Import files. It appears once profiles are loaded; before that the Start card does the job.
  - **Chart options** opens a panel with Grid lines, Legend, Line width, Chart text, Target lines (with their names and temperatures) and Image download.
  - The toolbar is also shown on the empty page, so the choices are kept after Clear all. Clear all is greyed out when there is nothing to clear.
  - In windows narrower than about 1,180 px the toolbar wraps onto a second row instead of cutting buttons off.
- **Import notes** are folded under the toolbar, with the number of notes in the title ("Import notes (4)"). A start time typed in Chart-2-Data is still flagged in the profile's status line.

### Fixed
- **Card borders on Streamlit 1.65.** The cards (toolbar, Start, Check the import, Profile details, Setpoint vs measured, Selected profile statistics) were drawn with Streamlit's light-theme border, nearly invisible in dark mode. They now use the theme's card colour and border in both themes.
- The two panels (Add files, Chart options) use the theme's colours; Streamlit draws them white by default.

### Removed
- Sidebar styling that no longer applies.

### Tests
- 3 more regression tests (90 in all): the empty page (Start card, no sidebar, no Add files, Clear all greyed out), the toolbar after an import (both panels, every setting still works), and the folded Import notes with their count. Three older tests updated for the missing sidebar.
- Browser checks on Streamlit 1.65 and 1.60, dark and light, with each panel open: no new text below 4.5:1 contrast; toolbar checked at 800, 1,000, 1,100, 1,180, 1,280 and 1,440 px.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app). Only `app.py` changed, but the layout change is large.

## [1.7.8] - 2026-11-04

Readable upload hint in dark mode. Commit [`d984c6d`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/d984c6d).

### Fixed
- **Upload box hint.** The line "200MB per file • CSV, XLSX, XLS" in the upload box was drawn in Streamlit's light-theme grey and was almost invisible on the dark box (contrast 1.2:1). It now uses the app's muted text colour (above 4.5:1 in dark and light mode).
- Checked with a browser contrast scan of the sidebar in dark and light mode: no other text below 4.5:1.
- 1 more regression test (87 in all).

## [1.7.7] - 2026-10-29

New name: Probe-2-Plot. Commit [`5a0f5dc`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/5a0f5dc).

### Changed
- **The app is now called Probe-2-Plot** (was Cook Profile Dashboard), in the same style as its companion app Chart-2-Data: probe readings in, plots out.
  - The new name is in the browser tab, the sidebar and the page title. The small heading above the title now reads "Cook profile dashboard".
  - The logo (Material "monitoring" icon) is unchanged.
- **Chart-2-Data's new name.** The import note and the status line for a typed start time now say "Chart-2-Data" (was "Chart to Data").
- 1 more regression test (86 in all): the new name in the browser tab, the sidebar and the page title.

### Not changed
- The Excel export (file name "Cook profiles YYYY-MM-DD.xlsx", sheet "Cook profiles", column names), so the Brisket Tenderness Analyzer reads it as before.
- The repository name and the app's web address. Renaming the repository on GitHub is optional and may change the Streamlit address.

## [1.7.6] - 2026-10-19

Switch roles on and off in the comparison chart. Commit [`2ea9b11`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/2ea9b11).

### Added
- **"Roles shown" under the comparison chart.** One button per role present (for example Meat, Ambient, Pit) switches every line of that role on or off.
  - The choice stays when anything else on the page changes.
  - It applies to the comparison chart only. The Excel file, Setpoint vs measured and the selected profile's chart are not affected.
- **The saved image shows the choice:**
  - The legend is grouped by role, with the role as a heading over its lines, in the order of the roles (Meat, Point, Flat, Ambient, Grate, Pit, Hold, Setpoint, Other).
  - Hidden roles are named at the end of the chart's summary line, for example "3 of 7 profiles | 3 devices | ... | hidden: Meat".
- **Why the switches are under the chart.** They can't sit inside the chart's legend: Plotly cannot switch a whole group from a heading, and lines hidden by clicking the legend come back the next time Streamlit refreshes the page.
- 2 more regression tests (85 in all): the grouped legend, and a role switched off, kept off through another change, and switched back on.

### Changed
- **Legend position.** With roles, the legend always sits to the right of the plot, because the role headings make it too tall for the row above it.
- **Summary line wording.** It now says "1 device" rather than "1 devices", and counts only the lines drawn when roles are hidden.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py` changed.

## [1.7.5] - 2026-10-19

Ambient role. Commit [`0f4db45`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/0f4db45).

### Added
- **New role: Ambient,** for the air right next to the meat, wherever the probe sits. Example: the Typhur ambient sensor in the probe handle, which on a whole chicken can be 20-25 cm above the grate and read differently from both the grate and the pit thermostat.
  - It sits next to Grate in the role lists.
  - The air roles are now:
    - **Pit:** the cooker's own thermostat or controller.
    - **Grate:** a sensor fixed at grate level.
    - **Ambient:** air at the meat.
- 1 more regression test (83 in all): Ambient and Grate are separate roles, and both export as the Analyzer's Cook Grate.

### Changed
- **Typhur columns.** "Ambient temperature" columns (as BBQ Chart to Data writes them) are now suggested as Ambient at import, not Grate. Columns with "grate" in the name are still suggested as Grate. Profiles already marked Grate keep that role.
- **In the Excel export,** Ambient profiles keep "Ambient" in their names. The Brisket Tenderness Analyzer has no ambient role and reads "ambient" as its Cook Grate role, the closest it has.

## [1.7.4] - 2026-10-19

Chart text size, and target labels on the left. Commit [`d8e26da`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/d8e26da).

### Added
- **Chart text size.** A "Chart text" choice under Chart options: 100 % (the size until now), 125 %, 150 % or 175 %.
  - It scales every text in the charts: the title and summary line, the axis names, the time and temperature numbers, the legend, the target labels and the hover box.
  - It applies to all three charts and to images saved with the camera icon.
  - The room above the plot grows with the text. When the legend above the chart wraps onto a second row, extra room is added so it stays clear of the summary line.
- 3 more regression tests (82 in all): labels on the left, close targets above and below, and the text sizes on every chart.

### Changed
- **All target-line labels sit at the left end of their line.** In 1.7.3 they alternated between left and right.
- **Close targets stay readable.** When a target is close below another (for example 80 °C and 72 °C), its label goes just under its own line instead of above it, so the two labels do not overlap. How close counts as "close" follows the text size.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py` changed.

## [1.7.3] - 2026-10-19

More target lines, each with its own name. Commit [`3fef10d`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/3fef10d).

### Changed
- **Target lines.** The "Target line" switch under Chart options is replaced by a "Target lines" number, from 0 (none, the default) to 5.
  - For each line there is a Name and a temperature (°C).
  - Lines start as "Target" 200 °C, "Target 2" 95 °C, "Target 3" 120 °C, "Target 4" 150 °C and "Target 5" 80 °C; change them as needed.
  - Each line is labelled on the chart with its name and temperature, for example "Pit 120 °C" and "Meat done 95 °C". An empty name shows as "Target 1", "Target 2" and so on.
  - Labels alternate between the left and right end of the chart, so two targets close together stay readable.
  - As before: dotted, in the text colour, on the comparison chart and the selected profile's chart, included in saved images, and the temperature axis stretches to include them.

### Added
- 3 more regression tests (79 in all): several named lines with an empty name and a special character, lowering the number of lines, and the limit of five.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `chart_builder.py` changed.

## [1.7.2] - 2026-10-18

Logo. Commit [`0e90d49`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/0e90d49).

### Added
- **A logo in the style of BBQ Chart to Data.** That app uses Google's Material "dashboard" icon; this one uses the Material "monitoring" icon (a rising chart), chosen by the user from six options on 18 October.
  - It sits in the browser tab (replacing the letters "CP"), in front of "Cook Profile" in the sidebar, and in front of the page title "Cook Profile Dashboard".
  - It takes the text colour, so it follows light and dark mode.
  - A different icon from Chart to Data's, so the two apps can be told apart in the browser tabs.
- 1 more regression test (76 in all): the logo in the sidebar, the title and the browser tab setting.

## [1.7.1] - 2026-10-17

Line style chosen per profile; no automatic dashes. Commit [`c0b7cb5`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/c0b7cb5).

### Changed
- **Every line is solid unless you choose otherwise.** In 1.7.0 the role set the line style (Pit long dash, Grate dash-dot, Hold long dash-dot), so the Weber pit line was always dashed. The role no longer changes how a line is drawn.
- **New "Line style" choice** in Profile details, next to Color: Solid, Dashed, Dotted, Dash-dot or Long dash.
  - The choice is per profile, like the colour.
  - It shows in the chart, the legend and saved images.
- **Setpoints still start dashed,** as since 1.6.0. Their style can be changed like any other profile's.
- **Labels shortened to fit the extra control on one row:**
  - "Time offset (min)" is now "Offset (min)".
  - The Role help no longer mentions line styles.
  - The Check the import note now says that colour and line style can be changed per profile afterwards.

### Added
- 2 more regression tests (75 in all): lines solid unless chosen, and the Line style choice changing only its own profile, including a setpoint made solid.

### Upgrade note
- Reboot the app on Streamlit Community Cloud after deploying (Manage app, three dots, Reboot app): `roles.py`, `chart_builder.py` and `models.py` changed.

## [1.7.0] - 2026-10-16

Roles for multi-device cooks (Typhur + Weber), as agreed on 16 October 2026. Commit [`aae9a5c`](https://github.com/IamRepository/BBQ_temp_dashboard/commit/aae9a5c).

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

[1.8.2]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/ee3b467...47ce58e
[1.8.1]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/7fe1339...ee3b467
[1.8.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/d984c6d...7fe1339
[1.7.8]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/5a0f5dc...d984c6d
[1.7.7]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/2ea9b11...5a0f5dc
[1.7.6]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/0f4db45...2ea9b11
[1.7.5]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/d8e26da...0f4db45
[1.7.4]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/3fef10d...d8e26da
[1.7.3]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/0e90d49...3fef10d
[1.7.2]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/c0b7cb5...0e90d49
[1.7.1]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/aae9a5c...c0b7cb5
[1.7.0]: https://github.com/IamRepository/BBQ_temp_dashboard/compare/aaecc53...aae9a5c
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
