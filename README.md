# Cook Profile Dashboard v1.6.9

Streamlit dashboard for comparing uploaded cook temperature profiles in degrees Celsius.

**What's new in 1.6.9:** a compact Profile details panel (about 60% shorter) shares one card with the comparison chart, so the controls and the whole chart fit on one screen; the chart's title carries the profile, device and duration summary, and the Excel export sits under the chart. The full history of every release is in [CHANGELOG.md](CHANGELOG.md).

## Features
- Import one or more CSV, XLSX or XLS files; each temperature column becomes a profile. Day-first (03/10/2026) and year-first (2026-10-03) dates, Excel dates, elapsed-time columns, zone names and UTC offsets, the clock change, probe dropouts and Fahrenheit are handled, and an Import notes panel reports what was found and skipped.
- Page layout, top to bottom: overview cards; one card with Profile details (two compact rows and a status line), the comparison chart and the Excel export; Setpoint vs measured; then the selected profile's statistics and chart.
- Overlay profiles on one chart, aligned by start, peak, end or clock time, with optional smoothing (1, 5 or 10 min). Long cooks are drawn with at most 4,000 points per line, keeping each stretch's lowest and highest reading so short spikes still show; statistics, the setpoint comparison and the export use every reading.
- Per profile: display name, channel label, line colour, time offset in minutes, a trim slider for the visible data window, and a setpoint flag (dashed line).
- Trim all profiles together: one slider sets the same time window (clock time, or hours from the start for files without clock times) for every loaded profile.
- Setpoint vs measured: how closely a probe followed the cooker's set temperature, with time within a chosen band.
- Light and dark themes; chart images as PNG or JPEG from each chart's camera icon. The comparison and single-profile charts are 16:9 at any window width and are saved at 3200 × 1800 pixels.
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

`requirements.txt` pins the exact versions each release was tested with (Streamlit 1.65.0, Plotly 6.9.0, pandas 2.3.3, openpyxl 3.1.5, xlrd 2.0.2). The page styling depends on Streamlit's internal element names, which can change between Streamlit versions, so a newer version is adopted on purpose: test it, then raise the pin in a release of its own. numpy is left to follow pandas, because which numpy builds exist depends on the server's Python version. The code also works on Streamlit 1.60, and every release is tested on both.

After a release that changes files other than `app.py`, reboot the app (Manage app, three dots, Reboot app) so no old module stays in memory.

## Files
| File | Purpose |
| --- | --- |
| `app.py` | Page layout, sidebar, profile details and all user interaction |
| `profile_loader.py` | Reading CSV and Excel files into profiles |
| `models.py` | The profile object: data, trim window, offset, setpoint flag |
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
There are 56 tests. `tests/test_import.py` checks file import against the example files in `tests/data` (made by `tests/make_fixtures.py`, no real cook data), plus the export, chart thinning on a made-up 18-hour cook, trimming and the pinned versions. `tests/test_app.py` loads every example file into the page and exercises the main interactions, including Trim all profiles together. Each fixed issue has its own test, named after its audit number (H1, M6, L9 and so on).

## Input assumptions
- Temperatures are Celsius unless the column header says °F, (F) or Fahrenheit; those are converted.
- A time-like column is detected automatically.
- Each detected temperature column becomes one profile.
- For irregular files, the next recommended enhancement is an import-mapping screen.
