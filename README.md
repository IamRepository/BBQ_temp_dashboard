# Probe-2-Plot v1.8.2

Streamlit dashboard for comparing uploaded cook temperature profiles in degrees Celsius.

**What's new in 1.8.2:** a Probe field in Profile details (colour follows the probe), a PROBES count instead of files, Excel export names that always keep a probe name, and the selected profile's legend under its chart. 1.8.1: faster, safer import and export (wide files with probe dropouts no longer stall the import, US and Australian time zones, names shown exactly as written, Excel headers kept as text, a 25 MB upload limit, Streamlit 1.66.1 with Pillow 13), and Clear all now asks first and starts the next cook clean. 1.8.0: no sidebar. Before the first import a Start card holds the file box; after it, one toolbar under the page title has Add files, Timeline alignment, Smoothing, Chart options, Theme and Clear all, so the chart starts higher and uses the full width. 1.7.7 renamed the app to Probe-2-Plot (formerly Cook Profile Dashboard), a companion to Chart-2-Data. Since 1.7.0: roles for multi-device cooks (including Ambient), a Check the import step, colour by probe, a Line style choice per profile, a logo, up to five named target lines, a chart text size, and Excel export names the Brisket Tenderness Analyzer reads correctly. The full history of every release is in [CHANGELOG.md](CHANGELOG.md).

## Features
- Import one or more CSV, XLSX or XLS files, then check the import: tick the columns to add, and set each one's role and probe before anything is added. Each temperature column becomes a profile named "<probe> - <role>". Day-first (03/10/2026) and year-first (2026-10-03) dates, Excel dates, elapsed-time columns, zone names and UTC offsets, the clock change, probe dropouts and Fahrenheit are handled, and Import notes (folded under the toolbar) report what was found and skipped.
- Page layout, top to bottom: title; Start card (before the first import) or the toolbar (Add files, Timeline alignment, Smoothing, Chart options, Theme, Clear all); Import notes; overview cards; one card with Profile details (two compact rows and a status line), the comparison chart and the Excel export; Setpoint vs measured; then the selected profile's statistics and chart.
- Roles shown (under the comparison chart): switch whole roles on or off, for example hide every Meat line. The legend is grouped by role with a heading per role, and hidden roles are named in the chart's summary line ("hidden: Meat"), on screen and in saved images.
- Overlay profiles on one chart, aligned by start, peak, end or clock time, with optional smoothing (1, 5 or 10 min). Long cooks are drawn with at most 4,000 points per line, keeping each stretch's lowest and highest reading so short spikes still show; statistics, the setpoint comparison and the export use every reading.
- Roles: Meat, Point, Flat, Ambient, Grate, Pit, Hold, Setpoint and Other, suggested from the column name (for example Typhur Ambient as Ambient, Typhur Meat as Meat, the Weber cavity as Pit). Ambient is the air right next to the meat wherever the probe sits; Grate is a sensor fixed at grate level; Pit is the cooker's own thermostat. Profiles of one probe share a colour. Every line is solid unless a Line style is chosen in Profile details (Solid, Dashed, Dotted, Dash-dot, Long dash); a setpoint starts dashed. With more than four lines the legend moves beside the chart.
- Chart-2-Data files (Timestamp, Ambient and Meat temperature) import directly; a "Start time source" column saying "typed" is flagged in Import notes and the status line.
- Per profile: display name, probe (colour follows it), channel, line style, line colour, time offset in minutes, a trim slider for the visible data window, and a Role (Meat, Point, Flat, Ambient, Grate, Pit, Hold, Setpoint or Other; a setpoint starts dashed and can be compared with a probe).
- Trim all profiles together: one slider sets the same time window (clock time, or hours from the start for files without clock times) for every loaded profile.
- Setpoint vs measured: how closely a probe followed the cooker's set temperature, with time within a chosen band.
- Chart text size (Chart options): 100 %, 125 %, 150 % or 175 % for the title, axis names, time and temperature numbers, legend and target labels, on screen and in saved images.
- Light and dark themes (dark by default); chart images as JPEG (default) or PNG from each chart's camera icon; line width 3.5 by default.
- Target lines: up to five dotted lines across the comparison and selected-profile charts (Chart options, Target lines), each with its own name and temperature, labelled at the left for example "Pit 120 °C" and included in saved images. The comparison and single-profile charts are 16:9 at any window width and are saved at 3200 × 1800 pixels.
- Excel export of the visible data, with the trim and time offsets applied. The file is built when you click Download, so it never slows down the rest of the page. Profiles with clock times share one sheet; elapsed-only profiles go on a second sheet.
- Files already imported are skipped, and line colours are taken from a palette checked for colour-blind readers, so each profile has its own colour.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deployment
The app runs on Streamlit Community Cloud from the `main` branch of this repository, with `app.py` as the entry point. Dependencies come from `requirements.txt`.

`requirements.txt` pins the exact versions each release was tested with (Streamlit 1.66.1, Pillow 13.0.0, Plotly 6.9.0, pandas 2.3.3, openpyxl 3.1.5, xlrd 2.0.2). The page styling depends on Streamlit's internal element names, which can change between Streamlit versions, so a newer version is adopted on purpose: test it, then raise the pin in a release of its own. numpy is left to follow pandas, because which numpy builds exist depends on the server's Python version. The code also works on Streamlit 1.60, and every release is tested on both.

Tested with Python 3.13 (the version the tests run on; choose it under Advanced settings when deploying on Streamlit Community Cloud).

After a release that changes files other than `app.py`, reboot the app (Manage app, three dots, Reboot app) so no old module stays in memory.

## Files
| File | Purpose |
| --- | --- |
| `app.py` | Page layout, toolbar, profile details and all user interaction |
| `profile_loader.py` | Reading CSV and Excel files into profiles |
| `roles.py` | Roles, probe labels, line style choices and the Analyzer-safe export names |
| `models.py` | The profile object: data, trim window, offset, role, probe and line style |
| `chart_builder.py` | The Plotly charts |
| `analysis.py` | Smoothing and the setpoint comparison |
| `export_utils.py` | The Excel export |
| `version.py` | The running version number |
| `tests/` | Regression tests and the small example files they use |
| `CHANGELOG.md` | Every release and what changed |

## Tests
Run before every release, from the repository root:
```bash
python -m unittest discover -s tests -v
```
There are 111 tests. `tests/test_import.py` checks file import against the example files in `tests/data` (made by `tests/make_fixtures.py`, no real cook data), plus the export, chart thinning on a made-up 18-hour cook, trimming and the pinned versions. `tests/test_app.py` loads every example file into the page and exercises the main interactions, including Trim all profiles together. Each fixed issue has its own test, named after its audit number (H1, M6, L9 and so on).

## Input assumptions
- Temperatures are Celsius unless the column header says °F, (F) or Fahrenheit; those are converted.
- A time-like column is detected automatically.
- Each temperature column is offered as one profile in Check the import, where columns can be left out and given a role and probe before anything is added.
- Time zone names (CET/CEST, US and Australian zones and others) and UTC offsets are put on one continuous clock; a zone name that is not recognised is reported in Import notes.
- Files up to 25 MB each (set in `.streamlit/config.toml`); an 18-hour cook logged every second is about 4 MB.

## Licence

Copyright © 2026 Imran Abdul-Majid. All rights reserved. No licence is granted to copy, change, distribute or use this code; see [LICENSE](LICENSE).
