"""Excel export of the visible profiles: one time column, then one temperature column per profile."""
import io

import pandas as pd

EXPORT_INTERVALS = {'As logged': None, '10 s': '10s', '30 s': '30s', '1 min': '1min', '5 min': '5min'}


def _column_names(profiles):
    names, used = [], {}
    for p in profiles:
        name = f'{p.name} (°C)'
        used[name] = used.get(name, 0) + 1
        names.append(name if used[name] == 1 else f'{p.name} {used[name]} (°C)')
    return names


def export_table(profiles, interval='1 min'):
    """Wide table of the visible data window (trim) with time offsets applied. Smoothing is never applied.

    With clock times on every profile the first column is 'Timestamp'; otherwise 'Elapsed time (h)'.
    For an interval, readings are averaged within each interval. Temperatures are rounded to 0.1 °C.
    """
    use_clock = bool(profiles) and all('timestamp' in p.plotted_data for p in profiles)
    time_col = 'Timestamp' if use_clock else 'Elapsed time (h)'
    freq = EXPORT_INTERVALS.get(interval)
    series = []
    for p, column in zip(profiles, _column_names(profiles)):
        frame = p.plotted_data
        if frame.empty:
            continue
        if use_clock:
            t = (frame.timestamp + pd.to_timedelta(p.offset_hours, unit='h')).dt.round('1s')
        else:
            t = pd.to_datetime((frame.elapsed_hours + p.offset_hours).to_numpy() * 3600, unit='s').round('1s')
        s = pd.Series(frame.temperature_c.to_numpy(), index=pd.DatetimeIndex(t), name=column)
        s = s.groupby(s.index.floor(freq) if freq else s.index).mean()
        series.append(s)
    if not series:
        return pd.DataFrame(columns=[time_col])
    table = pd.concat(series, axis=1).sort_index().dropna(how='all').round(1)
    table.index.name = time_col
    table = table.reset_index()
    if not use_clock:
        table[time_col] = ((table[time_col] - pd.Timestamp(0)).dt.total_seconds() / 3600).round(4)
    return table


def profiles_to_excel(profiles, interval='1 min'):
    """The export table as an .xlsx file: real dates, readable column widths, frozen header row."""
    table = export_table(profiles, interval)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        table.to_excel(writer, index=False, sheet_name='Cook profiles')
        sheet = writer.sheets['Cook profiles']
        sheet.freeze_panes = 'A2'
        time_format = 'dd/mm/yyyy hh:mm' if EXPORT_INTERVALS.get(interval) in ('1min', '5min') else 'dd/mm/yyyy hh:mm:ss'
        for index, column in enumerate(table.columns, start=1):
            letter = sheet.cell(row=1, column=index).column_letter
            if index == 1 and column == 'Timestamp':
                sheet.column_dimensions[letter].width = 20
                for cell in sheet[letter][1:]:
                    cell.number_format = time_format
            else:
                sheet.column_dimensions[letter].width = max(12, len(str(column)) + 3)
                for cell in sheet[letter][1:]:
                    cell.number_format = '0.0' if index > 1 else '0.0000'
    return buffer.getvalue()


def export_filename(profiles):
    starts = [p.plotted_data.timestamp.min() for p in profiles if 'timestamp' in p.plotted_data and not p.plotted_data.empty]
    return f"Cook profiles {min(starts):%Y-%m-%d}.xlsx" if starts else 'Cook profiles.xlsx'
