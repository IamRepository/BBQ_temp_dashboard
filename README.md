# Cook Profile Dashboard v1.5.0

Streamlit dashboard for comparing uploaded cook temperature profiles in degrees Celsius.

## v1.5.0 stability and import fixes
- Fixed crash when clicking "Reset data window"
- Fixed crash when clicking "Remove selected profile"
- Newly imported profiles are now shown automatically (previously hidden after importing more files or re-importing after "Clear all")
- Renaming a profile now updates everywhere immediately
- Column names are trimmed, so "Probe 1" no longer imports as " Probe 1"
- Timestamps with zone names (e.g. "CEST") now parse reliably instead of relying on a deprecated pandas behaviour
- Loggers that drop a reading when a probe disconnects (rows with fewer values than the header) are detected; values are placed in the matching probe column, and an "Import notes" panel reports what happened
- One unreadable file no longer cancels the whole import; it is skipped with a note
- Import messages are kept visible after the page refreshes
- Theme selector can no longer end up empty; multiselect tags follow the dark theme
- ZIP export no longer overwrites profiles that share a name
- Updated to Streamlit's current `width='stretch'` option (requires Streamlit 1.60 or newer)
- Removed unused `profile_processing.py`

## v1.4.0 profile trimming
- Added a dual-handle point-range slider for each selected profile
- Moving the left handle hides leading data points
- Moving the right handle hides trailing data points
- Trimming updates comparison charts, individual charts, statistics and exported CSV data
- Added visible, total and hidden-point counts
- Added a one-click reset for the selected profile data window
- Original uploaded data remains unchanged in memory

## v1.3.0 visual cleanup
- Unified the light surfaces to one page background and white cards
- Replaced warning-red profile chips with neutral slate chips
- Reduced shadows, border contrast and sidebar visual weight
- Increased the main chart height and widened the chart column
- Reduced chart grid intensity and simplified metric labels
- Rounded the line-colour control and removed unnecessary metric arrows
- Retained full light and dark theme support

## v1.2.0 visual redesign
- Light theme is now the default
- Added an in-app Light and Dark theme selector
- Reworked spacing, typography, cards, sidebar, controls and chart surfaces
- Added softer borders, restrained shadows and higher-contrast text
- Redesigned profile details and comparison chart as distinct cards
- Improved Plotly legend, grid, hover labels and tooltip content
- Applied a modern blue accent and accessible neutral palette

## v1.1.1 changes
- Fixed profile-selection crashes by using stable profile IDs
- Added explicit unique keys to stateful Streamlit widgets
- Preserved selection across profile changes and renaming
- Safely resets selection after deleting the active profile

## v1.1 changes
- Removed Fahrenheit and all temperature conversion logic
- Removed example-data loading from the interface
- Improved summary cards: visible profiles, unique channels, duration range and temperature range
- Added selected-profile statistics: name, duration, maximum temperature and sample count
- Added original, peak, end and clock-time alignment modes
- Kept CSV, XLSX and XLS multi-file import, Plotly visualization, profile customization and CSV ZIP export

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## GitHub setup
1. Create a repository named `cook-profile-dashboard`.
2. Extract this package and copy the contents of the inner `cook-profile-dashboard` folder into the repository root.
3. Commit all files to the `main` branch and push to GitHub.

## Streamlit Community Cloud deployment
1. Sign in to Streamlit Community Cloud using the GitHub account that can access the repository.
2. Create a new app.
3. Select the repository and the `main` branch.
4. Set the entry point to `app.py`.
5. Deploy. Dependencies are installed from `requirements.txt`.

## Input assumptions
- Imported temperatures are Celsius.
- A time-like column is detected automatically.
- Each detected temperature column becomes one profile.
- For irregular files, the next recommended enhancement is an import-mapping screen.
