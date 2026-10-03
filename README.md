# Cook Profile Dashboard

A GitHub-ready Streamlit application for uploading, organizing, customizing and comparing cook temperature profiles. It is inspired by the visual structure of the Brisket Session Analyser, but it performs no tenderness or rendering analysis.

## Features

- Upload one or more CSV, XLSX or XLS files
- Read all Excel worksheets
- Detect date/time, elapsed-time and temperature columns
- Create a separate profile for each detected temperature channel
- Overlay multiple profiles in an interactive Plotly chart
- Hide or show profiles
- Rename profiles and channels
- Set line colors and time offsets
- Switch between Celsius and Fahrenheit
- Use elapsed time or available clock timestamps
- Export visible profile data as a ZIP of CSV files
- Built-in example profiles

## Repository structure

```text
cook-profile-dashboard/
├── .streamlit/config.toml
├── sample_data/
│   ├── example_profiles.csv
│   └── example_profiles.xlsx
├── app.py
├── chart_builder.py
├── example_data.py
├── export_utils.py
├── models.py
├── profile_loader.py
├── profile_processing.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the application:

```bash
streamlit run app.py
```

## Deploy from GitHub to Streamlit Community Cloud

1. Create a GitHub repository and copy these files into the repository root.
2. Commit and push the files.
3. In Streamlit Community Cloud, create a new app from the repository.
4. Select `app.py` as the entry point.
5. Deploy the app.

## Input expectations

The loader searches for a time-like column using names such as `time`, `date`, `timestamp`, `elapsed`, `hour` or `minute`. It searches for temperature-like numeric columns using names such as `temperature`, `temp`, `probe`, `point`, `flat`, `pit`, `ambient`, `cavity` or `grate`.

If no date/time column is found, an appropriate numeric column is used. If neither exists, row number is used as the elapsed-time axis.

Temperatures are assumed to be Celsius on import. Fahrenheit display is a visualization conversion.

## Example data

The `sample_data` folder contains equivalent CSV and Excel examples with `Timestamp`, `Point`, `Flat` and `Pit` channels.

## Current design assumptions

- Each temperature column is treated as a separate profile.
- Duplicate elapsed-time readings keep the last value.
- Empty rows and columns are removed.
- Imported data is held in the Streamlit session and is not written to a server database.
- Profile edits remain available until the Streamlit session ends or the browser session is reset.

## Recommended next development step

Add an import-mapping screen where users can verify the worksheet, time column, temperature columns, source units and profile names before completing an import.
