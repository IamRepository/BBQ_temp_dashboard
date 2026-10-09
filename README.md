# Cook Profile Dashboard v1.6.3

Streamlit dashboard for comparing uploaded cook temperature profiles in degrees Celsius.

**What's new in 1.6.3:** readable buttons and tooltips in dark mode, and the data download is now one Excel sheet (Timestamp, then one column per profile) with a choice of interval. The full history of every release is in [CHANGELOG.md](CHANGELOG.md).

## Features
- Import one or more CSV, XLSX or XLS files; each temperature column becomes a profile. Timestamps with zone names (such as "CEST") and probe dropouts are handled, and an Import notes panel reports what was found.
- Overlay profiles on one chart, aligned by start, peak, end or clock time, with optional smoothing (1, 5 or 10 min).
- Per profile: display name, channel label, line colour, time offset, a trim slider for the visible data window, and a setpoint flag (dashed line).
- Setpoint vs measured: how closely a probe followed the cooker's set temperature, with time within a chosen band.
- Light and dark themes; chart images as PNG or JPEG from each chart's camera icon.
- Excel export of the visible data, with the trim and time offsets applied.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deployment
The app runs on Streamlit Community Cloud from the `main` branch of this repository, with `app.py` as the entry point. Dependencies come from `requirements.txt` (Streamlit 1.60 or newer).

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
| `example_data.py` | Built-in example profiles (not shown in the interface) |
| `version.py` | The running version number |
| `CHANGELOG.md` | Every release and what changed |

## Input assumptions
- Imported temperatures are Celsius.
- A time-like column is detected automatically.
- Each detected temperature column becomes one profile.
- For irregular files, the next recommended enhancement is an import-mapping screen.
