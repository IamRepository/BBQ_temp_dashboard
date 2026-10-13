"""Import regression tests. Run from the repository root: python -m unittest discover -s tests -v

Each test class matches an issue from the audit of v1.6.4 (H1-H5, M1-M8, L2-L9), a
feature (trimming all profiles at once), or guards a format that already worked. The example files are made by tests/make_fixtures.py.
"""
import io
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / 'data'
sys.path.insert(0, str(ROOT))

from profile_loader import COLORS, load_uploaded_files  # noqa: E402
from export_utils import export_sheets, export_table, profiles_to_excel  # noqa: E402
from chart_builder import MAX_POINTS, comparison, deviation, single, thin  # noqa: E402
from models import CookProfile  # noqa: E402
import numpy as np  # noqa: E402
from analysis import compare  # noqa: E402


class Upload:
    """Stands in for a Streamlit uploaded file."""
    def __init__(self, path):
        self.name = Path(path).name
        self._bytes = Path(path).read_bytes()

    def getvalue(self):
        return self._bytes


def load(*names):
    return load_uploaded_files([Upload(DATA / n) for n in names])


def ts(text):
    return pd.Timestamp(text)


class H1YearFirstDates(unittest.TestCase):
    def test_dates_and_duration_across_midnight(self):
        profiles, _ = load('h1_iso_midnight.csv')
        self.assertEqual(len(profiles), 1)
        data = profiles[0].data
        self.assertEqual(data.timestamp.iloc[0], ts('2026-10-03 23:58'))
        self.assertEqual(data.timestamp.iloc[-1], ts('2026-10-04 00:02'))
        self.assertAlmostEqual(profiles[0].duration_hours, 4 / 60, places=6)


class H2ElapsedTime(unittest.TestCase):
    def test_minutes(self):
        profiles, _ = load('h2_elapsed_minutes.csv')
        self.assertEqual(len(profiles), 1)
        self.assertNotIn('timestamp', profiles[0].data)
        self.assertAlmostEqual(profiles[0].duration_hours, 2.0, places=6)

    def test_hours(self):
        profiles, _ = load('h2_elapsed_hours.csv')
        self.assertEqual([p.channel for p in profiles], ['Pit', 'Meat'])
        for p in profiles:
            self.assertNotIn('timestamp', p.data)
            self.assertAlmostEqual(p.duration_hours, 3.0, places=6)

    def test_excel_date_serials_are_clock_times(self):
        profiles, _ = load('ok_excel_serial_dates.xlsx')
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].data.timestamp.iloc[0], ts('2026-10-03 10:00'))
        self.assertAlmostEqual(profiles[0].duration_hours, 4 / 60, places=4)


class H3UtcOffsets(unittest.TestCase):
    def test_offset_kept_as_local_clock_time(self):
        profiles, _ = load('h3_utc_offset.csv')
        data = profiles[0].data
        self.assertIsNone(data.timestamp.dt.tz)
        self.assertEqual(data.timestamp.iloc[0], ts('2026-10-03 15:00'))

    def test_z_suffix(self):
        profiles, _ = load('h3_utc_z.csv')
        data = profiles[0].data
        self.assertIsNone(data.timestamp.dt.tz)
        self.assertEqual(data.timestamp.iloc[0], ts('2026-10-03 13:00'))

    def test_export_and_comparison_next_to_a_plain_file(self):
        offset, _ = load('h3_utc_offset.csv')
        plain, _ = load('h5_fixed_setpoint.csv')
        profiles = offset + plain
        export_table(profiles, '1 min')
        self.assertGreater(len(profiles_to_excel(profiles, 'As logged')), 0)
        setpoint = next(p for p in plain if p.channel == 'Setpoint')
        setpoint.is_setpoint = True
        result, problem = compare(setpoint, offset[0], 10)
        self.assertTrue(result is not None or problem)  # no exception; no overlap is a valid answer


class H4ClockChange(unittest.TestCase):
    expected_times = ['2026-10-25 02:30', '2026-10-25 02:50', '2026-10-25 03:10', '2026-10-25 03:30', '2026-10-25 04:10']

    def check(self, name):
        profiles, messages = load(name)
        data = profiles[0].data
        self.assertEqual(data.temperature_c.tolist(), [80, 81, 82, 83, 84])
        self.assertEqual(data.timestamp.tolist(), [ts(t) for t in self.expected_times])
        self.assertAlmostEqual(profiles[0].duration_hours, 100 / 60, places=6)
        self.assertTrue(any('clock' in m.lower() for m in messages), messages)

    def test_zone_names(self):
        self.check('h4_dst_zone_names.csv')

    def test_without_zone_names(self):
        self.check('h4_dst_no_zone.csv')


class H5FixedSetpoint(unittest.TestCase):
    def test_constant_setpoint_is_kept(self):
        profiles, _ = load('h5_fixed_setpoint.csv')
        self.assertEqual([p.channel for p in profiles], ['Setpoint', 'Probe 1'])
        self.assertEqual(set(profiles[0].data.temperature_c), {120})


class M1AllTemperatureColumns(unittest.TestCase):
    def test_target_imported_and_non_temperatures_skipped_with_a_note(self):
        profiles, messages = load('m1_extra_columns.csv')
        self.assertEqual([p.channel for p in profiles], ['Pit temp', 'Meat', 'Target'])
        text = ' '.join(messages)
        self.assertIn('Fan %', text)
        self.assertIn('Battery', text)


class M8Fahrenheit(unittest.TestCase):
    def test_converted_to_celsius_with_a_note(self):
        profiles, messages = load('m8_fahrenheit.csv')
        self.assertEqual([p.channel for p in profiles], ['Meat', 'Pit'])
        self.assertAlmostEqual(profiles[0].data.temperature_c.iloc[0], (150 - 32) * 5 / 9, places=6)
        self.assertAlmostEqual(profiles[1].data.temperature_c.iloc[0], (250 - 32) * 5 / 9, places=6)
        self.assertTrue(any('°F' in m or 'Fahrenheit' in m for m in messages), messages)


class FormatsThatAlreadyWork(unittest.TestCase):
    def test_thermometer_export_with_cest_and_probe_dropouts(self):
        profiles, messages = load('ok_device_cest.csv')
        self.assertEqual([p.channel for p in profiles], ['cavity temperature', 'Probe 1', 'Probe 2'])
        self.assertEqual(profiles[0].data.timestamp.iloc[0], ts('2026-10-03 15:34:00'))
        self.assertTrue(any('fewer values than the header' in m for m in messages), messages)

    def test_semicolons_and_decimal_commas(self):
        profiles, _ = load('ok_semicolon_comma.csv')
        self.assertEqual(profiles[0].data.temperature_c.tolist(), [23.5, 24.0, 24.5])
        self.assertEqual(profiles[0].data.timestamp.iloc[0], ts('2026-10-03 10:00'))

    def test_workbook_with_two_sheets(self):
        profiles, _ = load('ok_two_sheets.xlsx')
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[1].data.timestamp.iloc[0], ts('2026-10-04 10:00'))


class M2DuplicateFiles(unittest.TestCase):
    def test_a_file_already_loaded_is_skipped(self):
        first, _ = load('ok_device_cest.csv')
        again, messages = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv')], existing=first)
        self.assertEqual(again, [])
        self.assertTrue(any('already imported' in m for m in messages), messages)

    def test_the_same_file_twice_in_one_import(self):
        profiles, messages = load_uploaded_files([Upload(DATA / 'h5_fixed_setpoint.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.assertEqual(len(profiles), 2)
        self.assertTrue(any('already imported' in m for m in messages), messages)


class M3Colours(unittest.TestCase):
    def test_palette_is_the_validated_one(self):
        self.assertEqual(COLORS, ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'])

    def test_a_second_import_takes_unused_colours(self):
        first, _ = load('ok_device_cest.csv')
        second, _ = load_uploaded_files([Upload(DATA / 'h5_fixed_setpoint.csv')], existing=first)
        used = {p.color for p in first}
        self.assertEqual(len(used), 3)
        self.assertTrue(all(p.color not in used for p in second), [p.color for p in second])
        self.assertEqual(len({p.color for p in first + second}), 5)


class L2NamesOnReimport(unittest.TestCase):
    def test_single_sheet_export_gives_clean_names(self):
        profiles, _ = load('l2_dashboard_export.xlsx')
        self.assertEqual([p.name for p in profiles], ['l2_dashboard_export - Connet - Probe 1', 'l2_dashboard_export - Smoque_XL - Probe 2'])
        self.assertEqual([p.channel for p in profiles], ['Connet - Probe 1', 'Smoque_XL - Probe 2'])

    def test_two_sheets_keep_the_sheet_name(self):
        profiles, _ = load('ok_two_sheets.xlsx')
        self.assertEqual([p.name for p in profiles], ['ok_two_sheets - Cook 1 - Meat', 'ok_two_sheets - Cook 2 - Meat'])


class L3ExportSheets(unittest.TestCase):
    def test_clock_and_elapsed_profiles_go_on_separate_sheets(self):
        clock, _ = load('ok_device_cest.csv')
        elapsed, _ = load('h2_elapsed_hours.csv')
        sheets = export_sheets(clock + elapsed, '1 min')
        self.assertEqual([name for name, _ in sheets], ['Cook profiles', 'Elapsed time'])
        self.assertEqual(sheets[0][1].columns[0], 'Timestamp')
        self.assertEqual(sheets[1][1].columns[0], 'Elapsed time (h)')
        book = pd.ExcelFile(io.BytesIO(profiles_to_excel(clock + elapsed, '1 min')))
        self.assertEqual(book.sheet_names, ['Cook profiles', 'Elapsed time'])

    def test_clock_only_gives_one_sheet(self):
        clock, _ = load('ok_device_cest.csv')
        self.assertEqual([name for name, _ in export_sheets(clock, '1 min')], ['Cook profiles'])


class L4PreviewOffset(unittest.TestCase):
    def test_offset_moves_timestamps_too(self):
        profiles, _ = load('h5_fixed_setpoint.csv')
        p = profiles[0]
        p.offset_hours = 0.5
        frame = p.export_frame()
        self.assertEqual(frame.timestamp.iloc[0], ts('2026-10-03 10:30'))
        self.assertAlmostEqual(frame.elapsed_hours.iloc[0], 0.5)


class L9ClockAlignment(unittest.TestCase):
    def test_elapsed_only_profiles_are_left_out_of_the_clock_chart(self):
        clock, _ = load('ok_device_cest.csv')
        elapsed, _ = load('h2_elapsed_hours.csv')
        settings = {'alignment': 'Clock time', 'theme': 'Light', 'grid': True, 'legend': True, 'width': 2, 'smoothing_minutes': 0}
        names = [t.name for t in comparison(clock + elapsed, settings).data]
        self.assertEqual(names, [p.name for p in clock])
        settings['alignment'] = 'Original timeline'
        self.assertEqual(len(comparison(clock + elapsed, settings).data), len(clock + elapsed))


def long_cook(hours=18, name='Pit'):
    """A made-up cook logged every second, with one 20-second spike (a lid opening) at the 9-hour mark."""
    n = hours * 3600
    temperature = 110 + 3 * np.sin(np.arange(n) / 900)
    temperature[9 * 3600:9 * 3600 + 20] = 160
    data = pd.DataFrame({'timestamp': pd.date_range('2026-10-03 06:00', periods=n, freq='s'),
                         'elapsed_hours': np.arange(n) / 3600, 'temperature_c': temperature})
    return CookProfile('p-' + name, name, 'long.csv', name, COLORS[0], data)


class M6LongCooks(unittest.TestCase):
    settings = {'alignment': 'Clock time', 'theme': 'Light', 'grid': True, 'legend': True, 'width': 2, 'smoothing_minutes': 0}

    def test_thinning_keeps_the_shape_spike_and_ends(self):
        profile = long_cook()
        y = profile.data.temperature_c
        keep = thin(profile.data.timestamp, y)
        self.assertLessEqual(len(keep), MAX_POINTS + 2)
        self.assertEqual((keep[0], keep[-1]), (0, len(y) - 1))
        self.assertEqual(y.iloc[keep].max(), 160)            # the short spike is still drawn
        self.assertAlmostEqual(y.iloc[keep].min(), y.min())
        self.assertTrue(np.all(np.diff(keep) > 0))            # still in time order

    def test_short_lines_are_drawn_in_full(self):
        self.assertEqual(len(thin(range(500), np.arange(500.0))), 500)

    def test_charts_stay_small_and_statistics_use_every_reading(self):
        pit, meat = long_cook(name='Pit'), long_cook(name='Meat')
        fig = comparison([pit, meat], self.settings)
        self.assertTrue(all(len(trace.x) <= MAX_POINTS + 2 for trace in fig.data))
        self.assertLess(len(fig.to_json()), 1_000_000)
        self.assertLessEqual(len(single(pit, dict(self.settings, smoothing_minutes=5)).data[0].x), MAX_POINTS + 2)
        self.assertEqual(pit.maximum_c, 160)
        self.assertEqual(len(export_table([pit], 'As logged')), 18 * 3600)

    def test_setpoint_difference_chart_is_thinned(self):
        setpoint, probe = long_cook(name='Set'), long_cook(name='Probe')
        setpoint.data['temperature_c'] = 110.0
        setpoint.is_setpoint = True
        result, problem = compare(setpoint, probe, 10)
        self.assertIsNone(problem)
        self.assertLessEqual(len(deviation(result, self.settings).data[0].x), MAX_POINTS + 2)


class TrimAllProfiles(unittest.TestCase):
    def test_clock_window_trims_every_profile_that_has_readings_inside(self):
        clock, _ = load('ok_device_cest.csv')        # 15:34:00 to 15:34:12
        setpoint, _ = load('h5_fixed_setpoint.csv')   # 10:00 to 10:09
        start, end = pd.Timestamp('2026-10-03 15:34:03'), pd.Timestamp('2026-10-03 15:34:08')
        for p in clock:
            self.assertTrue(p.trim_to(start, end, True))
            self.assertTrue(p.plotted_data.timestamp.between(start, end).all())
        self.assertEqual(clock[0].plotted_data.timestamp.iloc[0], start)
        self.assertFalse(setpoint[0].trim_to(start, end, True))     # nothing inside: left as it was
        self.assertEqual(len(setpoint[0].plotted_data), 10)

    def test_the_time_offset_is_respected(self):
        profile = load('h5_fixed_setpoint.csv')[0][0]
        profile.offset_hours = 1                       # drawn at 11:00 to 11:09
        profile.trim_to(pd.Timestamp('2026-10-03 11:05'), pd.Timestamp('2026-10-03 12:00'), True)
        self.assertEqual(profile.export_frame().timestamp.iloc[0], pd.Timestamp('2026-10-03 11:05'))
        self.assertEqual(len(profile.plotted_data), 5)

    def test_hours_window_for_profiles_without_clock_times(self):
        profiles, _ = load('h2_elapsed_hours.csv')    # 0 to 3 h every 0.25 h
        for p in profiles:
            self.assertTrue(p.trim_to(0.5, 2.0, False))
            self.assertEqual(p.plotted_data.elapsed_hours.tolist(), [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0])
        self.assertEqual(profiles[0].window(False), (0.5, 2.0))


class M7PinnedVersions(unittest.TestCase):
    def test_streamlit_and_plotly_are_pinned(self):
        lines = (ROOT / 'requirements.txt').read_text().splitlines()
        for package in ('streamlit', 'plotly', 'pandas', 'openpyxl', 'xlrd'):
            self.assertTrue(any(line.startswith(package + '==') for line in lines), package)


class L7NoUnusedFiles(unittest.TestCase):
    def test_example_data_removed(self):
        self.assertFalse((ROOT / 'example_data.py').exists())


if __name__ == '__main__':
    unittest.main()
